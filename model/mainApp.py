import logging
import sys
import asyncio
import concurrent.futures
from contextlib import asynccontextmanager
import os

import jwt
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from Agent.qwen.qwenAgent import qwenAgent
# 假设 NamingModel 定义在 Agent.namingModel 中
from Agent.namingModel import NamingModel

# 配置常量
# 建议：生产环境请使用 os.getenv("SECRET_KEY")
SECRET_KEY = "/jdhn:836**1"
ALGORITHM = "HS256"

# 配置日志
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
    logging.info("正在初始化资源及加载模型...")
    # 初始化线程池
    resources["executor"] = concurrent.futures.ThreadPoolExecutor(max_workers=10)
    loop = asyncio.get_running_loop()

    try:
        # 并行加载两个模型，减少启动等待时间
        # 【注意】确保 ActRound 和 NamingModel 的 __init__ 方法是耗时操作才需要放入 executor
        tasks = [
            loop.run_in_executor(resources["executor"], qwenAgent),
            loop.run_in_executor(resources["executor"], NamingModel)
        ]

        # 设置超时时间，避免无限等待
        resources["model"], resources["naming_model"] = await asyncio.wait_for(
            asyncio.gather(*tasks), timeout=120.0
        )
        logging.info("所有模型预加载完成")
    except asyncio.TimeoutError:
        logging.error("模型加载超时，服务启动失败")
        raise
    except Exception as e:
        logging.error(f"模型初始化严重失败: {e}")
        # 这里可以选择 raise e 来阻止服务启动

    yield  # 服务运行中

    logging.info("正在释放资源...")
    if resources["executor"]:
        resources["executor"].shutdown()


app = FastAPI(lifespan=lifespan)


def verify_token(token: str):
    """校验 JWT Token"""
    try:
        # 尝试解码
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # 校验成功后打印日志
        logging.info("JWT Token 校验成功")
    except jwt.ExpiredSignatureError:
        # Token 过期时记录警告日志
        logging.warning("JWT 校验失败: Token 已过期")
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        # Token 无效时记录错误日志
        logging.error(f"JWT 校验失败: 无效的 Token ({e})")
        raise HTTPException(status_code=401, detail="Invalid token")



@app.post("/model/get_result")
async def get_model_result(request: QueryRequest):
    # 1. 安全校验
    verify_token(request.token)

    # 2. 服务状态检查
    if not resources["model"] or not resources["naming_model"]:
        raise HTTPException(status_code=503, detail="Model service not ready")

    logging.info(f"处理请求: {request.question}")

    try:
        loop = asyncio.get_running_loop()
        executor = resources["executor"]
        tasks = []

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

        return {"result": model_res, "summary": summary, "name": name}

    except Exception as e:
        logging.error(f"请求处理异常: {e}")
        # 返回 500 错误码比返回 {"error": ...} JSON 更符合 RESTful 规范，但也取决于前端约定
        return {"error": str(e)}

# import logging
# import sys
# import asyncio
# import concurrent.futures
# from contextlib import asynccontextmanager
#
# import jwt
# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
#
# from Agent.qwen.qwenAgent import qwenAgent
# from Agent.namingModel import NamingModel
#
# # 配置常量 (对应 Java 端的设置)
# SECRET_KEY = "/jdhn:836**1"
# ALGORITHM = "HS256"
#
# # 配置日志
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(levelname)s - %(message)s",
#     handlers=[logging.StreamHandler(sys.stdout)]
# )
#
# # 全局资源容器
# resources = {"model": None, "naming_model": None, "executor": None}
#
#
# class QueryRequest(BaseModel):
#     question: str
#     round: int = 2
#     all_info: str = ""
#     token: str  # 必传字段
#
#
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """应用生命周期：模型预加载与资源清理"""
#     logging.info("正在初始化资源及加载模型...")
#     resources["executor"] = concurrent.futures.ThreadPoolExecutor(max_workers=10)
#     loop = asyncio.get_running_loop()
#
#     try:
#         # 并行加载两个模型
#         tasks = [
#             loop.run_in_executor(resources["executor"], ActRound),
#             loop.run_in_executor(resources["executor"], NamingModel)
#         ]
#         resources["model"], resources["naming_model"] = await asyncio.wait_for(
#             asyncio.gather(*tasks), timeout=120.0
#         )
#         logging.info("模型预加载完成")
#     except Exception as e:
#         logging.error(f"模型初始化严重失败: {e}")
#         # 生产环境建议根据需求决定是否在此处 raise 阻断启动
#
#     yield
#
#     logging.info("正在释放资源...")
#     if resources["executor"]:
#         resources["executor"].shutdown()
#
#
# app = FastAPI(lifespan=lifespan)
#
#
# def verify_token(token: str):
#     """校验 JWT Token"""
#     try:
#         # PyJWT 会自动校验签名和过期时间(如果 payload 包含 exp)
#         jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(status_code=401, detail="Token has expired")
#     except jwt.InvalidTokenError:
#         raise HTTPException(status_code=401, detail="Invalid token")
#
#
# @app.post("/model/get_result")
# async def get_model_result(request: QueryRequest):
#     # 1. 安全校验
#     verify_token(request.token)
#
#     # 2. 服务状态检查
#     if not resources["model"] or not resources["naming_model"]:
#         raise HTTPException(status_code=503, detail="Model service not ready")
#
#     logging.info(f"处理请求: {request.question}")
#
#     try:
#         loop = asyncio.get_running_loop()
#         executor = resources["executor"]
#         tasks = []
#
#         # 3. 构建主模型任务
#         tasks.append(loop.run_in_executor(
#             executor, resources["model"].run, request.question, request.round, request.all_info
#         ))
#
#         # 4. 根据条件构建取名任务
#         needs_naming = not request.all_info
#         if needs_naming:
#             tasks.append(loop.run_in_executor(
#                 executor, resources["naming_model"].run_naming, request.question
#             ))
#
#         # 5. 并行执行并获取结果
#         results = await asyncio.gather(*tasks)
#
#         # 结果解包
#         model_res, summary = results[0]
#         name = results[1] if len(results) > 1 else None
#
#         return {"result": model_res, "summary": summary, "name": name}
#
#     except Exception as e:
#         logging.error(f"请求处理异常: {e}")
#         return {"error": str(e)}




# # 导入模块和类
# import logging
# import sys
# import asyncio
# import concurrent.futures
#
# from fastapi import FastAPI
# from pydantic import BaseModel
# # from Deepseek_Agent import ActRound这是唯一需要修改的
# from Agent.qwen.Qwen_Agent import ActRound
# from Agent.NamingModel import NamingModel
#
# # 配置日志（只配置一次）
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(levelname)s - %(message)s",
#     handlers=[logging.StreamHandler(sys.stdout)]
# )
#
# app = FastAPI()
#
#
# # 请求数据模型
# class QueryRequest(BaseModel):
#     question: str
#     round: int = 2
#     all_info: str = ""
#
#
# # 全局模型变量
# model: ActRound = None
# naming_model: NamingModel = None
#
# # 创建自定义线程池，增加线程数量
# executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
#
#
# @app.on_event("startup")
# async def startup_event():
#     """应用启动时初始化模型"""
#     global model, naming_model
#     logging.info("开始初始化模型，请稍等...")
#
#     try:
#         loop = asyncio.get_running_loop()
#         # 并行初始化两个模型，减少启动时间
#         model_task = loop.run_in_executor(executor, ActRound)
#         naming_model_task = loop.run_in_executor(executor, NamingModel)
#
#         # 增加超时时间到120秒
#         model, naming_model = await asyncio.wait_for(
#             asyncio.gather(model_task, naming_model_task),
#             timeout=120.0  # 增加到120秒超时
#         )
#
#         logging.info("模型预加载完成")
#     except asyncio.TimeoutError:
#         logging.error("模型初始化超时")
#     except Exception as e:
#         logging.error(f"模型初始化失败: {str(e)}")
#
#
# async def run_model_async(question: str, round: int, all_info: str) -> tuple:
#     """异步运行主模型推理"""
#     logging.info(f"开始运行模型推理: {question}")
#     loop = asyncio.get_running_loop()
#
#     try:
#         # 使用自定义线程池
#         result, summary = await loop.run_in_executor(
#             executor,
#             model.run,
#             question,
#             round,
#             all_info
#         )
#         logging.info("模型推理完成")
#         return result, summary
#     except Exception as e:
#         logging.error(f"模型推理出错: {str(e)}")
#         raise
#
#
# async def run_Naming_model_async(question: str) -> str:
#     """异步运行取名模型"""
#     logging.info(f"开始运行取名模型，问题: {question}")
#
#     # 检查naming_model是否已初始化
#     if naming_model is None:
#         logging.error("取名模型未初始化")
#         return "医学咨询标题"
#
#     loop = asyncio.get_running_loop()
#
#     try:
#         # 使用自定义线程池
#         name = await loop.run_in_executor(
#             executor,
#             naming_model.run_naming,
#             question
#         )
#         logging.info(f"取名模型运行完成，结果: {name}")
#         return name
#     except Exception as e:
#         logging.error(f"取名模型出错: {str(e)}")
#         return "医学咨询标题"
#
#
# @app.post("/model/get_result")
# async def get_model_result(request: QueryRequest):
#     """处理模型推理请求的API端点"""
#     logging.info(f"接收到请求: {request.question}")
#
#     try:
#         name = None
#         # 修复逻辑：只有当all_info为空时才运行取名模型
#         if not request.all_info:
#             name = await run_Naming_model_async(request.question)
#
#         # 异步执行模型推理
#         result, summary = await run_model_async(
#             request.question,
#             request.round,
#             request.all_info,
#         )
#
#         logging.info("请求处理完成")
#         return {"result": result, "summary": summary, "name": name}
#     except Exception as e:
#         logging.error(f"处理请求时出错: {str(e)}")
#         return {"error": str(e)}
#
#
