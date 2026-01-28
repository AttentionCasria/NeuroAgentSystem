import json
import logging
from typing import List, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from makeData.dataRetrieve import UnifiedSearchEngine, CONFIG

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
# import json
# import logging
# from typing import List, Dict, Any
# from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
#
# # 确保能导入这些依赖（根据你项目结构调整）
# from makeData.dataRetrieve import UnifiedSearchEngine, CONFIG
#
# logger = logging.getLogger(__name__)
#
#
# class MedicalReActAgent:
#     def __init__(self, llm, retriever: UnifiedSearchEngine):
#         self.llm = llm
#         self.retriever = retriever
#         # 定义工具 Schema
#         self.tools_schema = [
#             {
#                 "type": "function",
#                 "function": {
#                     "name": "search_clinical_guidelines",
#                     "description": "搜索临床诊疗指南和医学文献，获取症状相关的病因、诊断和治疗建议。",
#                     "parameters": {
#                         "type": "object",
#                         "properties": {
#                             "query": {"type": "string", "description": "具体的医学搜索关键词"}
#                         },
#                         "required": ["query"]
#                     }
#                 }
#             }
#         ]
#
#     def _execute_tool(self, name: str, args: dict) -> str:
#         """执行具体的工具逻辑（带异常处理）"""
#         if name == "search_clinical_guidelines":
#             query = args.get("query")
#             if not query:
#                 return "错误：未提供搜索关键词"
#
#             logger.info(f"🔍 [ReAct] 正在检索: {query}")
#             try:
#                 # 增加 try-catch 防止检索挂掉整个服务
#                 docs = self.retriever.search(query, top_k_final=CONFIG.get("top_k_final", 6))
#                 if not docs:
#                     return "未检索到相关文档。"
#
#                 # 返回内容去重/格式化
#                 return "\n\n".join([f"【证据】{doc.page_content}" for doc in docs])
#             except Exception as e:
#                 logger.error(f"❌ [ReAct] 检索出错: {e}")
#                 return f"检索服务暂时不可用: {str(e)}"
#
#         return f"未找到工具: {name}"
#
#     def run(self, system_prompt: str, user_question: str, max_steps: int = 3) -> str:
#         """执行 ReAct 循环，返回搜集到的证据或模型的直接回答"""
#
#         # 💡 提示词微调：允许模型在非必要时直接回答
#         enhanced_prompt = system_prompt + "\n\n对于需要事实依据的医学问题，请务必调用工具 'search_clinical_guidelines'。对于日常问候或不需要检索的简单问题，请直接回答。"
#
#         messages = [
#             SystemMessage(content=enhanced_prompt),
#             HumanMessage(content=f"{user_question}")  # 去掉了强制检索的 "请针对...进行证据检索" 前缀，让模型根据语境判断
#         ]
#
#         final_context = []
#         last_direct_response = ""  # 用于记录模型最后的直接回复
#
#         logger.info(f"🚀 [Agent Start] 开始处理: {user_question}")
#
#         for step in range(max_steps):
#             try:
#                 # 1. 让 LLM 决定动作
#                 response = self.llm.invoke(messages, tools=self.tools_schema)
#                 messages.append(response)
#
#                 # 记录模型此时的内容（可能是思考过程，也可能是直接回答）
#                 if response.content:
#                     last_direct_response = response.content
#
#                 # 如果 LLM 不再需要调用工具，说明推理完成
#                 if not response.tool_calls:
#                     logger.info(f"🛑 [Agent Stop] Step {step}: 模型停止调用工具 (或未触发工具)")
#                     break
#
#                 logger.info(f"🤖 [Agent Decision] Step {step}: 需要调用 {len(response.tool_calls)} 个工具")
#
#                 # medicalAgent.py 中的 run 方法
#                 for tool_call in response.tool_calls:
#                     tool_name = tool_call["name"]
#                     tool_args = tool_call["args"]
#
#                     # 执行工具
#                     observation = self._execute_tool(tool_name, tool_args)
#
#                     # 【关键修改】：确保 observation 是字符串，并显式传入所有必需字段
#                     messages.append(ToolMessage(
#                         tool_call_id=tool_call["id"],
#                         name=tool_name,  # 必须匹配工具名
#                         content=str(observation)  # 必须是字符串
#                     ))

                # 在 append 完所有 ToolMessage 后，下一轮 invoke 前可以打印一下 messages 列表的类型
                # logger.info(f"当前消息序列类型: {[type(m) for m in messages]}")
                # # 2. 执行工具调用
                # for tool_call in response.tool_calls:
                #     tool_name = tool_call["name"]
                #     tool_args = tool_call["args"]
                #
                #     observation = self._execute_tool(tool_name, tool_args)
                #
                #     # 记录检索到的硬性证据
                #     final_context.append(f"Query: {tool_args.get('query')}\nResult:\n{observation}")
                #
                #     messages.append(ToolMessage(
                #         tool_call_id=tool_call["id"],
                #         content=observation,
                #         name=tool_name
                #     ))
        #     except Exception as e:
        #         logger.error(f"⚠️ [Agent Loop Error]: {e}")
        #         break
        #
        # # 🎯 返回逻辑优化
        # # 优先级 1: 如果有检索到的证据，优先返回证据
        # if final_context:
        #     return "\n\n".join(final_context)
        #
        # # 优先级 2: 如果没有证据，但模型有直接回答（闲聊/常识），返回直接回答
        # if last_direct_response:
        #     return last_direct_response
        #
        # # 优先级 3: 既无检索也无回答（极为罕见），返回兜底信息
        # return "（无检索结果，且模型未给出回复）"

    # def run(self, system_prompt: str, user_question: str, max_steps: int = 3) -> str:
    #     """执行 ReAct 循环，返回搜集到的所有证据"""
    #
    #     # 💡 Tip: Append an instruction to the System Prompt to force the model to use tools
    #     enhanced_prompt = system_prompt + "\n\nPlease be sure to call the tool 'search_clinical_guidelines' to obtain factual evidence, and do not rely solely on memory to answer."
    #
    #     messages = [
    #         SystemMessage(content=enhanced_prompt),
    #         HumanMessage(content=f"Please conduct evidence retrieval for the following question: {user_question}")
    #     ]
    #     # # 💡 技巧：给 System Prompt 追加一句指令，强制模型去使用工具
    #     # enhanced_prompt = system_prompt + "\n\n请务必调用工具 'search_clinical_guidelines' 来获取事实依据，不要仅凭记忆回答。"
    #     #
    #     # messages = [
    #     #     SystemMessage(content=enhanced_prompt),
    #     #     HumanMessage(content=f"请针对以下问题进行证据检索：{user_question}")
    #     # ]
    #
    #     final_context = []  # 使用列表比字符串拼接性能更好
    #
    #     logger.info(f"🚀 [Agent Start] 开始处理: {user_question}")
    #
    #     for step in range(max_steps):
    #         try:
    #             # 1. 让 LLM 决定动作
    #             response = self.llm.invoke(messages, tools=self.tools_schema)
    #             messages.append(response)
    #
    #             # 如果 LLM 不再需要调用工具，说明推理完成
    #             if not response.tool_calls:
    #                 logger.info(f"🛑 [Agent Stop] Step {step}: 模型停止调用工具")
    #                 break
    #
    #             logger.info(f"🤖 [Agent Decision] Step {step}: 需要调用 {len(response.tool_calls)} 个工具")
    #
    #             # 2. 执行工具调用
    #             for tool_call in response.tool_calls:
    #                 tool_name = tool_call["name"]
    #                 tool_args = tool_call["args"]
    #
    #                 observation = self._execute_tool(tool_name, tool_args)
    #
    #                 # 记录证据
    #                 final_context.append(f"Query: {tool_args.get('query')}\nResult:\n{observation}")
    #
    #                 # 将结果反馈给 LLM，以便它决定是否需要通过新关键词再次搜索
    #                 messages.append(ToolMessage(
    #                     tool_call_id=tool_call["id"],
    #                     content=observation,
    #                     name=tool_name
    #                 ))
    #         except Exception as e:
    #             logger.error(f"⚠️ [Agent Loop Error]: {e}")
    #             break
    #
    #     # 结果合成
    #     if final_context:
    #         return "\n\n".join(final_context)
    #     else:
    #         return "（无检索结果，模型认为无需检索或未找到相关信息）"

# import json
# import logging
# from typing import List, Dict, Any
# from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
# # 导入你现有的配置和检索引擎
# from makeData.dataRetrieve import UnifiedSearchEngine, CONFIG
#
# logger = logging.getLogger(__name__)
#
#
# class MedicalReActAgent:
#     def __init__(self, llm, retriever: UnifiedSearchEngine):
#         self.llm = llm
#         self.retriever = retriever
#         # 定义工具 Schema，对应你之前要求的格式
#         self.tools_schema = [
#             {
#                 "type": "function",
#                 "function": {
#                     "name": "search_clinical_guidelines",
#                     "description": "搜索临床诊疗指南和医学文献，获取症状相关的病因、诊断和治疗建议。",
#                     "parameters": {
#                         "type": "object",
#                         "properties": {
#                             "query": {"type": "string", "description": "具体的医学搜索查询词"}
#                         },
#                         "required": ["query"]
#                     }
#                 }
#             }
#         ]
#
#     def _execute_tool(self, name: str, args: dict) -> str:
#         """执行具体的工具逻辑"""
#         if name == "search_clinical_guidelines":
#             query = args.get("query")
#             logger.info(f"🛠️ 执行检索工具: {query}")
#             docs = self.retriever.search(query, top_k_final=CONFIG.get("top_k_final", 6))
#             return "\n\n".join([doc.page_content for doc in docs])
#         return f"未找到工具: {name}"
#
#     def run(self, system_prompt: str, user_question: str, max_steps: int = 3) -> str:
#         """执行 ReAct 循环"""
#         # 初始上下文
#         messages = [
#             SystemMessage(content=system_prompt),
#             HumanMessage(content=f"请针对以下问题进行深度推理和证据检索：{user_question}")
#         ]
#
#         final_context = ""
#
#         for step in range(max_steps):
#             logger.info(f"--- Agent 推理步数: {step + 1} ---")
#
#             # 1. 让 LLM 决定动作 (Thought + Action)
#             response = self.llm.invoke(messages, tools=self.tools_schema)
#             messages.append(response)
#
#             # 如果 LLM 不再需要调用工具，说明推理完成
#             if not response.tool_calls:
#                 break
#
#             # 2. 执行工具调用 (Action -> Observation)
#             for tool_call in response.tool_calls:
#                 tool_name = tool_call["name"]
#                 tool_args = tool_call["args"]
#
#                 observation = self._execute_tool(tool_name, tool_args)
#                 final_context += f"\nObservation from {tool_name}:\n{observation}"
#
#                 # 将结果反馈给 LLM
#                 messages.append(ToolMessage(
#                     tool_call_id=tool_call["id"],
#                     content=observation
#                 ))
#
#         return final_context if final_context else "未检索到额外证据。"