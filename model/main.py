# main.py

import logging
import sys
import asyncio
import concurrent.futures
from contextlib import asynccontextmanager
import os
import json
import jwt
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

from Agent.qwen.qwenAgent import qwenAgent
from Agent.qwen.qwenAssistant import MedicalAssistant
from Agent.namingModel import NamingModel
from makeData.Retrieve import UnifiedSearchEngine, CONFIG
from config.config_loader import get_prompt_manager, get_report_manager

from langchain_community.chat_models import ChatTongyi

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

resources = {"model": None, "naming_model": None, "executor": None}


class QueryRequest(BaseModel):
    question: str
    round: int = 2
    all_info: str = ""
    token: str
    report_mode: str = "emergency"
    show_thinking: bool = True  # 是否输出中间思考过程


def init_all_resources():
    logging.info(">>> 开始组装模型依赖链...")

    prompt_mgr = get_prompt_manager()
    report_mgr = get_report_manager()
    logging.info(f">>> 可用报告模式: {report_mgr.list_modes()}")

    llm_max = ChatTongyi(model_name="qwen-max")
    llm_plus = ChatTongyi(model_name="qwen-plus")

    retriever = UnifiedSearchEngine(
        persist_dir=CONFIG.get("persist_dir", "./chroma_db_unified"),
        top_k=CONFIG.get("top_k_final", 3)
    )

    medical_assistant = MedicalAssistant(
        llm_main=llm_max,
        llm_fast=llm_plus,
        retriever=retriever,
        prompt_manager=prompt_mgr,
        report_manager=report_mgr
    )

    agent = qwenAgent(
        llm_proposer=llm_max,
        llm_critic=llm_plus,
        medical_assistant=medical_assistant,
        prompt_manager=prompt_mgr,
        report_manager=report_mgr
    )

    naming_model = NamingModel()
    return agent, naming_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info(">>> 正在初始化资源及加载模型...")
    resources["executor"] = concurrent.futures.ThreadPoolExecutor(max_workers=10)
    loop = asyncio.get_running_loop()

    try:
        agent, naming = await loop.run_in_executor(
            resources["executor"], init_all_resources
        )
        resources["model"] = agent
        resources["naming_model"] = naming
        logging.info(">>> 所有模型组装完成，服务已就绪")
    except Exception as e:
        logging.error(f"!!! 模型初始化严重失败: {e}")
        import traceback
        logging.error(traceback.format_exc())
        raise

    yield

    logging.info("<<< 正在释放资源...")
    if resources["executor"]:
        resources["executor"].shutdown()


app = FastAPI(lifespan=lifespan)


def verify_token(token: str):
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.post("/model/get_result")
async def get_model_result(request: QueryRequest):
    verify_token(request.token)

    if not resources["model"]:
        raise HTTPException(status_code=503, detail="Model service not ready")

    async def generate():
        try:
            # 添加请求参数调试日志
            logging.info(f"=== 开始处理请求 ===")
            logging.info(f"请求问题: {request.question}")
            logging.info(f"请求all_info: {request.all_info}")
            logging.info(f"请求report_mode: {request.report_mode}")
            logging.info(f"请求show_thinking: {request.show_thinking}")

            loop = asyncio.get_running_loop()
            stream_queue = asyncio.Queue()

            def run_stream_in_thread():
                try:
                    for chunk in resources["model"].run_clinical_reasoning(
                        case_text=request.question,
                        all_info=request.all_info,
                        report_mode=request.report_mode,
                        show_thinking=request.show_thinking
                    ):
                        asyncio.run_coroutine_threadsafe(
                            stream_queue.put(chunk), loop
                        )
                except Exception as e:
                    logging.error(f"模型流式生成出错: {e}")
                    import traceback
                    logging.error(traceback.format_exc())
                    asyncio.run_coroutine_threadsafe(
                        stream_queue.put({"type": "error", "content": str(e)}),
                        loop
                    )
                finally:
                    asyncio.run_coroutine_threadsafe(
                        stream_queue.put(None), loop
                    )

            loop.run_in_executor(resources["executor"], run_stream_in_thread)

            naming_future = None
            if not request.all_info:
                naming_future = loop.run_in_executor(
                    resources["executor"],
                    resources["naming_model"].run_naming,
                    request.question
                )

            generated_name = None
            while True:
                item = await stream_queue.get()
                # 在第167行之后添加：
                if item is None:
                    yield json.dumps({"type": "done", "content": ""}, ensure_ascii=False) + "\n"
                    break

                if isinstance(item, dict) and item.get("type") == "error":
                    yield json.dumps(
                        {"error": item["content"]}, ensure_ascii=False
                    ) + "\n"
                    break

                if naming_future and naming_future.done() and not generated_name:
                    try:
                        generated_name = naming_future.result()
                    except Exception:
                        generated_name = "咨询"

                response_chunk = {}

                chunk_type = item.get("type", "") if isinstance(item, dict) else ""

                if chunk_type == "result":
                    content = item["content"]
                    if hasattr(content, "content"):
                        content = content.content
                    response_chunk["result"] = str(content)

                elif chunk_type == "thinking":
                    response_chunk["thinking"] = {
                        "step": item.get("step", ""),
                        "title": item.get("title", ""),
                        "content": str(item.get("content", ""))
                    }

                elif chunk_type == "meta":
                    response_chunk["meta"] = item["content"]

                if generated_name:
                    response_chunk["name"] = generated_name

                if response_chunk:
                    yield json.dumps(
                        response_chunk, ensure_ascii=False
                    ) + "\n"

        except Exception as e:
            logging.error(f"generate() 外层异常: {e}")
            import traceback
            logging.error(traceback.format_exc())
            yield json.dumps({"error": str(e)}, ensure_ascii=False) + "\n"

    # 第215行，修改为：
    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )

@app.post("/admin/reload_config")
async def reload_config():
    try:
        get_prompt_manager().reload()
        get_report_manager().reload()
        return {"status": "ok", "message": "配置已热更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/report_modes")
async def list_report_modes():
    mgr = get_report_manager()
    modes = mgr.list_modes()
    return {
        "modes": [
            {"key": m, "name": mgr.get_template_name(m)}
            for m in modes
        ]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)