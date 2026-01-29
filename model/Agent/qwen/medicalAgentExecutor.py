



import json
import os
from typing import List, Dict

# 【修复 1】引入通用工具代理 create_tool_calling_agent，而非 create_openai_functions_agent
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_community.chat_models import ChatTongyi

# 导入你现有的检索引擎和配置
from makeData.Retrieve import UnifiedSearchEngine, CONFIG

# 1. 定义工具 (Tools)
retriever = UnifiedSearchEngine(
    persist_dir=CONFIG["persist_dir"],
    top_k=CONFIG["top_k_per_store"]
)

@tool
def search_medical_guidelines(query: str):
    """
    当需要查询专业临床指南、疾病症状、诊断建议或治疗方案时使用此工具。
    输入应该是具体的英文或中文医疗查询词。
    """
    # 增加异常防护，防止检索服务未启动导致 Agent 崩溃
    try:
        docs = retriever.search(query, top_k_final=CONFIG.get("top_k_final", 6))
        if not docs:
            return "未找到相关��档。"
        return "\n\n".join([d.page_content for d in docs])
    except Exception as e:
        return f"检索出错: {str(e)}"

# 2. 定义医疗 Agent 类
class MedicalAgent:
    def __init__(self):
        self.llm = ChatTongyi(
            model="qwen-max",
            dashscope_api_key=os.getenv("QWEN-API-KEY"),
            temperature=0  # 医疗场景需要严谨，降低随机性
        )
        self.tools = [search_medical_guidelines]
        self.executor = self._create_agent_executor()

    def _create_agent_executor(self):
        # 定义 Prompt
        # 【注意】create_tool_calling_agent 强制要求 prompt 包含 agent_scratchpad
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a professional medical assistant. Use the provided tools to help answer medical questions accurately."),
            MessagesPlaceholder(variable_name="chat_history"), # 即使不用记忆，占位符不仅保留了扩展性，也是某些 Agent 类型的要求
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # 【修复 2】使用 create_tool_calling_agent 构建 Agent
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True # 自动纠正模型输出格式错误，增强稳定性
        )

    def run_task(self, question: str):
        # invoke 时必须传入 chat_history，因为 Prompt中有这个占位符
        return self.executor.invoke({
            "input": question,
            "chat_history": []
        })



#
# import json
# import os
# from typing import List, Dict
#
# # 【修复 1】引入通用工具代理 create_tool_calling_agent，而非 create_openai_functions_agent
# from langchain.agents import AgentExecutor, create_tool_calling_agent
# from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# from langchain_core.tools import tool
# from langchain_community.chat_models import ChatTongyi
#
# # 导入你现有的检索引擎和配置
# from makeData.dataRetrieveEnglish import UnifiedSearchEngine, CONFIG
#
# # 1. 定义工具 (Tools)
# retriever = UnifiedSearchEngine(
#     persist_dir=CONFIG["persist_dir"],
#     top_k=CONFIG["top_k_per_store"]
# )
#
# @tool
# def search_medical_guidelines(query: str):
#     """
#     当需要查询专业临床指南、疾病症状、诊断建议或治疗方案时使用此工具。
#     输入应该是具体的英文或中文医疗查询词。
#     """
#     # 增加异常防护，防止检索服务未启动导致 Agent 崩溃
#     try:
#         docs = retriever.search(query, top_k_final=CONFIG.get("top_k_final", 6))
#         if not docs:
#             return "未找到相关��档。"
#         return "\n\n".join([d.page_content for d in docs])
#     except Exception as e:
#         return f"检索出错: {str(e)}"
#
# # 2. 定义医疗 Agent 类
# class MedicalAgent:
#     def __init__(self):
#         self.llm = ChatTongyi(
#             model="qwen-max",
#             dashscope_api_key=os.getenv("QWEN-API-KEY"),
#             temperature=0  # 医疗场景需要严谨，降低随机性
#         )
#         self.tools = [search_medical_guidelines]
#         self.executor = self._create_agent_executor()
#
#     def _create_agent_executor(self):
#         # 定义 Prompt
#         # 【注意】create_tool_calling_agent 强制要求 prompt 包含 agent_scratchpad
#         prompt = ChatPromptTemplate.from_messages([
#             ("system", "You are a professional medical assistant. Use the provided tools to help answer medical questions accurately."),
#             MessagesPlaceholder(variable_name="chat_history"), # 即使不用记忆，占位符不仅保留了扩展性，也是某些 Agent 类型的要求
#             ("human", "{input}"),
#             MessagesPlaceholder(variable_name="agent_scratchpad"),
#         ])
#
#         # 【修复 2】使用 create_tool_calling_agent 构建 Agent
#         agent = create_tool_calling_agent(self.llm, self.tools, prompt)
#
#         return AgentExecutor(
#             agent=agent,
#             tools=self.tools,
#             verbose=True,
#             handle_parsing_errors=True # 自动纠正模型输出格式错误，增强稳定性
#         )
#
#     def run_task(self, question: str):
#         # invoke 时必须传入 chat_history，因为 Prompt中有这个占位符
#         return self.executor.invoke({
#             "input": question,
#             "chat_history": []
#         })
#
