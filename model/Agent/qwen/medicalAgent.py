import json
import logging
from typing import List, Dict, Any

from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from makeData.Retrieve import UnifiedSearchEngine, CONFIG


load_dotenv()
logger = logging.getLogger(__name__)


class MedicalReActAgent:
    def __init__(self, llm, retriever: UnifiedSearchEngine):
        self.llm = llm
        self.retriever = retriever
        self.tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": "search_clinical_guidelines",
                    "description": "搜索临床诊疗指南和医学文献。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "医学搜索关键词"}
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

    def _execute_tool(self, name: str, args: dict) -> str:
        """执行具体的工具逻辑"""
        if name == "search_clinical_guidelines":
            try:
                query = args.get("query")
                if not query:
                    return "Error: No query provided"

                docs = self.retriever.search(query, top_k_final=CONFIG.get("top_k_final", 4))
                if not docs:
                    return "未检索到相关文档。"

                return "\n\n".join([f"{doc.page_content}" for doc in docs])  # 移除【证据】标记
            except Exception as e:
                logger.error(f"❌ 检索出错: {e}")
                return f"检索服务异常: {str(e)}"

        return f"未知工具: {name}"

    def run(self, system_prompt: str, user_question: str, max_steps: int = 3) -> str:
        """
        完全避免 ToolMessage，改用纯文本传递工具结果
        """
        logger.info(f"🚀 [Agent Start] 处理问题: {user_question}")

        collected_evidence = []  # 收集所有检索结果

        try:
            # 第一次调用：让模型决定是否需要工具
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_question)
            ]

            response = self.llm.invoke(messages, tools=self.tools_schema)

            # 如果模型直接回答，不调用工具
            if not response.tool_calls:
                return str(response.content)

            # 执行所有工具调用
            logger.info(f"🤖 需要调用 {len(response.tool_calls)} 个工具")
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                observation = self._execute_tool(tool_name, tool_args)
                collected_evidence.append(f"检索关键词: {tool_args.get('query')}\n\n检索结果:\n{observation}")

            # 【核心改动】将工具结果作为新的用户消息传递
            # 不使用 ToolMessage，避免 "Got unknown type" 错误
            evidence_text = "\n\n---\n\n".join(collected_evidence)
            final_messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=f"原始问题: {user_question}\n\n我已为您检索到以下医学文献证据:\n\n{evidence_text}\n\n请基于这些证据给出专业的医学分析。")
            ]

            # 第二次调用：让模型基于证据生成答案（不带 tools 参数）
            final_response = self.llm.invoke(final_messages)
            return str(final_response.content)

        except Exception as e:
            logger.error(f"⚠️ Agent 执行出错: {e}")

            # 降级策略：直接返回检索到的原始证据
            if collected_evidence:
                return "（由于系统原因，以下是为您检索到的原始医学文献）:\n\n" + "\n\n".join(collected_evidence)

            return "很抱歉，当前服务繁忙，请稍后再试。"
