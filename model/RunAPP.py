# 导入模块和类
import logging
import sys
import asyncio
import concurrent.futures

from fastapi import FastAPI
from pydantic import BaseModel
# from Deepseek_Agent import ActRound这是唯一需要修改的
from Qwen_Agent import ActRound
from NamingModel import NamingModel

# 配置日志（只配置一次）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

app = FastAPI()


# 请求数据模型
class QueryRequest(BaseModel):
    question: str
    round: int = 2
    all_info: str = ""


# 全局模型变量
model: ActRound = None
naming_model: NamingModel = None

# 创建自定义线程池，增加线程数量
executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化模型"""
    global model, naming_model
    logging.info("开始初始化模型，请稍等...")

    try:
        loop = asyncio.get_running_loop()
        # 并行初始化两个模型，减少启动时间
        model_task = loop.run_in_executor(executor, ActRound)
        naming_model_task = loop.run_in_executor(executor, NamingModel)

        # 增加超时时间到120秒
        model, naming_model = await asyncio.wait_for(
            asyncio.gather(model_task, naming_model_task),
            timeout=120.0  # 增加到120秒超时
        )

        logging.info("模型预加载完成")
    except asyncio.TimeoutError:
        logging.error("模型初始化超时")
    except Exception as e:
        logging.error(f"模型初始化失败: {str(e)}")


async def run_model_async(question: str, round: int, all_info: str) -> tuple:
    """异步运行主模型推理"""
    logging.info(f"开始运行模型推理: {question}")
    loop = asyncio.get_running_loop()

    try:
        # 使用自定义线程池
        result, summary = await loop.run_in_executor(
            executor,
            model.run,
            question,
            round,
            all_info
        )
        logging.info("模型推理完成")
        return result, summary
    except Exception as e:
        logging.error(f"模型推理出错: {str(e)}")
        raise


async def run_Naming_model_async(question: str) -> str:
    """异步运行取名模型"""
    logging.info(f"开始运行取名模型，问题: {question}")

    # 检查naming_model是否已初始化
    if naming_model is None:
        logging.error("取名模型未初始化")
        return "医学咨询标题"

    loop = asyncio.get_running_loop()

    try:
        # 使用自定义线程池
        name = await loop.run_in_executor(
            executor,
            naming_model.run_naming,
            question
        )
        logging.info(f"取名模型运行完成，结果: {name}")
        return name
    except Exception as e:
        logging.error(f"取名模型出错: {str(e)}")
        return "医学咨询标题"


@app.post("/model/get_result")
async def get_model_result(request: QueryRequest):
    """处理模型推理请求的API端点"""
    logging.info(f"接收到请求: {request.question}")

    try:
        name = None
        # 修复逻辑：只有当all_info为空时才运行取名模型
        if not request.all_info:
            name = await run_Naming_model_async(request.question)

        # 异步执行模型推理
        result, summary = await run_model_async(
            request.question,
            request.round,
            request.all_info,
        )

        logging.info("请求处理完成")
        return {"result": result, "summary": summary, "name": name}
    except Exception as e:
        logging.error(f"处理请求时出错: {str(e)}")
        return {"error": str(e)}


