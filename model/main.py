import logging
import sys
import asyncio
import concurrent.futures
from contextlib import asynccontextmanager
import os

import jwt
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from Agent.qwen.qwenAgent import qwenAgent
# 假设 NamingModel 定义在 Agent.namingModel 中
from Agent.namingModel import NamingModel

# 配置常量
# 建议：生产环境请使用 os.getenv("SECRET_KEY")
SECRET_KEY = "/jdhn:836**1"
ALGORITHM = "HS256"

# 配置日志 - 确保日志能输出到控制台
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# 全局资源容器
resources = {"model": None, "naming_model": None, "executor": None}


class QueryRequest(BaseModel):
    question: str
    round: int = 2
    all_info: str = ""
    token: str  # 必传字段


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：模型预加载与资源清理"""
    logging.info(">>> 正在初始化资源及加载模型...")
    # 初始化线程池
    resources["executor"] = concurrent.futures.ThreadPoolExecutor(max_workers=10)
    loop = asyncio.get_running_loop()

    try:
        # 并行加载两个模型，减少启动等待时间
        tasks = [
            loop.run_in_executor(resources["executor"], qwenAgent),
            loop.run_in_executor(resources["executor"], NamingModel)
        ]

        # 设置超时时间，避免无限等待
        resources["model"], resources["naming_model"] = await asyncio.wait_for(
            asyncio.gather(*tasks), timeout=2000.0
        )
        logging.info(">>> 所有模型预加载完成，服务已就绪")
    except asyncio.TimeoutError:
        logging.error("!!! 模型加载超时，服务启动失败")
        raise
    except Exception as e:
        logging.error(f"!!! 模型初始化严重失败: {e}")
        # 这里可以选择 raise e 来阻止服务启动

    yield  # 服务运行中

    logging.info("<<< 正在释放资源...")
    if resources["executor"]:
        resources["executor"].shutdown()


app = FastAPI(lifespan=lifespan)


def verify_token(token: str):
    """校验 JWT Token"""
    try:
        # 尝试解码
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # 校验成功后打印日志
        logging.info("--- JWT Token 校验通过 ---")
    except jwt.ExpiredSignatureError:
        # Token 过期时记录警告日志
        logging.warning("--- JWT 校验失败: Token 已过期 ---")
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        # Token 无效时记录错误日志
        logging.error(f"--- JWT 校验失败: 无效的 Token ({e}) ---")
        raise HTTPException(status_code=401, detail="Invalid token")


@app.post("/model/get_result")
async def get_model_result(request: QueryRequest):
    # 1. 安全校验
    verify_token(request.token)

    # 2. 服务状态检查
    if not resources["model"] or not resources["naming_model"]:
        logging.error("服务未就绪：模型资源为空")
        raise HTTPException(status_code=503, detail="Model service not ready")

    logging.info(f"收到用户请求: {request.question}")

    try:
        loop = asyncio.get_running_loop()
        executor = resources["executor"]
        tasks = []

        logging.info("正在提交主模型计算任务...")
        # 3. 构建主模型任务 (run 方法通常包含 I/O 或 heavy compute)
        tasks.append(loop.run_in_executor(
            executor,
            resources["model"].run,
            request.question,
            request.round,
            request.all_info
        ))

        # 4. 根据条件构建取名任务 (并行处理)
        # 只有在初次对话（没有 all_info）时才生成标题
        needs_naming = not request.all_info
        if needs_naming:
            logging.info("检测到新对话，正在提交命名任务...")
            tasks.append(loop.run_in_executor(
                executor,
                resources["naming_model"].run_naming,
                request.question
            ))

        # 5. 并行执行并获取结果
        results = await asyncio.gather(*tasks)

        # 结果解包
        model_res, summary = results[0]
        # 如果并没有运行 naming 任务，则 name 为 None
        name = results[1] if needs_naming and len(results) > 1 else None

        # --- 新增：打印 AI 输出结果关键信息 ---
        log_res = model_res[:50] + "..." if len(model_res) > 50 else model_res
        logging.info(f"AI 回复内容预览: {log_res}")
        if name:
            logging.info(f"AI 生成标题: {name}")
        logging.info("请求处理完成")
        # ------------------------------------

        return {"result": model_res, "summary": summary, "name": name}

    except Exception as e:
        logging.error(f"请求处理发生异常: {e}", exc_info=True)
        return {"error": str(e)}


if __name__ == '__main__':
    # 启动服务
    # host="0.0.0.0" 允许外部访问
    # port=8000 指定端口
    logging.info("正在启动 FastAPI 服务...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
