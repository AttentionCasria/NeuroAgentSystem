import logging
import os
from typing import Union

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.chat_models import ChatTongyi

# 尝试导入 DeepSeek 依赖
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

# 【修复】导入 UnifiedSearchEngine 类和配置，替代不存在的函数
from makeData.dataRetrieve import UnifiedSearchEngine, CONFIG
# 从项目根目录开始的全路径
from Agent.qwen.qwenAssistant import MedicalAssistant



# ------------------ 日志配置 ------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class qwenAgent:
    # ------------------ 提示词常量 ------------------
    ACT_PATIENT_TEMPLATE = """
        Please role-play as a patient who might have the illness the user is concerned about.
        Keep your responses concise and focused solely on relevant symptoms and experiences.
        Avoid any unnecessary details, explanations, or off-topic remarks.
        Please pay close attention to the {original_result} and let it guide your responses based on the following information.
        Your answer should not be identical to "{former_result}"
        Patient information:
        {patient_info}
        """

    ACT_DOCTOR_TEMPLATE = """
        You are a medical expert.
        Provide clear and concise medical advice based on the patient's information.
        Keep responses brief, professional, and directly related to the medical context.
        Avoid any extraneous comments or opinions.
        Patient information:
        {doctor_info}
        Reference Materials:
        {document}
        """

    def __init__(self):
        self._init_llms()
        # 【修复】初始化检索引擎实例
        self.retriever_engine = UnifiedSearchEngine(
            persist_dir=CONFIG["persist_dir"],
            top_k=CONFIG["top_k_per_store"]
        )
        self.patient_chain, self.doctor_chain = self._build_chains()
        self.medical_assistant = MedicalAssistant(self.llm)
        logger.info("ActRound 初始化完成")

    def _init_llms(self):
        """初始化大模型实例"""
        qwen_key = os.getenv("QWEN-API-KEY")
        if not qwen_key:
            raise ValueError("未找到环境变量 QWEN-API-KEY，请设置该环境变量")

        self.llm = ChatTongyi(
            model="qwen3-max",
            dashscope_api_key=qwen_key,
            temperature=0.7,
            max_tokens=4000
        )

        deepseek_key = os.getenv("DEEPSEEK-API-KEY")
        self.simple_llm = None

        if not deepseek_key:
            logger.warning("未设置 DEEPSEEK-API-KEY")
        elif ChatOpenAI is None:
            logger.warning("未安装 langchain_openai，无法初始化 DeepSeek 模型")
        else:
            self.simple_llm = ChatOpenAI(
                model="deepseek-chat",
                openai_api_base="https://api.deepseek.com/v1",
                openai_api_key=deepseek_key,
                temperature=0.3,
                max_tokens=300
            )

    def _build_chains(self):
        """构建医患对话链"""
        if not self.simple_llm:
            raise RuntimeError("DeepSeek LLM (simple_llm) 未初始化，无法构建对话链。")

        patient_prompt = PromptTemplate(
            template=self.ACT_PATIENT_TEMPLATE,
            input_variables=["patient_info", "former_result", "original_result"],
        )
        doctor_prompt = PromptTemplate(
            template=self.ACT_DOCTOR_TEMPLATE,
            input_variables=["doctor_info", "document"],
        )

        patient_chain = (
            RunnablePassthrough.assign(
                patient_info=lambda x: x["patient_info"],
                former_result=lambda x: x["former_result"],
                original_result=lambda x: x["original_result"],
            )
            | patient_prompt
            | self.simple_llm
        )

        doctor_chain = (
            RunnablePassthrough.assign(
                doctor_info=lambda x: x["doctor_info"],
                document=lambda x: x["document"],
            )
            | doctor_prompt
            | self.simple_llm
        )

        return patient_chain, doctor_chain

    @staticmethod
    def _parse_msg(msg: Union[AIMessage, str]) -> str:
        """统一解析消息内容"""
        return msg.content.strip() if isinstance(msg, AIMessage) else str(msg).strip()

    def run(self, words: str, round_num: int = 2, all_info: str = ""):
        # 增加一个分类判断
        intent_msg = self.llm.invoke([
            SystemMessage(content="判断用户输入是否为医疗咨询。如果是闲聊或问候，返回'GREETING'，否则返回'MEDICAL'。"),
            HumanMessage(content=words)
        ]).content

        if "GREETING" in intent_msg.upper():
            return "您好！我是您的医疗助手，请问有什么具体的症状或医学问题我可以帮您？", ""

        logger.info(f"开始执行 run()，输入: {words}")
        conversation_history = []

        # 1. 初始翻译
        patient_result = self._parse_msg(self.translation(words))
        original_result = patient_result

        # 2. 初始文档检索 【修复：调用 search 方法】
        initial_docs = self.retriever_engine.search(
            original_result,
            top_k_final=CONFIG["top_k_final"]
        )
        logger.info(f'初始 RAG 检索到 {len(initial_docs)} 条文档')
        initial_docs_content = "\n\n".join([doc.page_content for doc in initial_docs])

        # 3. 医患模拟循环
        doctor_result = ""
        for i in range(round_num):
            # 检索上下文 【修复：调用 search 方法】
            current_docs = self.retriever_engine.search(
                patient_result,
                top_k_final=CONFIG["top_k_final"]
            )
            logger.info(f'第{i + 1}轮 RAG 检索到 {len(current_docs)} 条文档')

            # 医生作答
            doctor_msg = self.doctor_chain.invoke({
                "document": current_docs,
                "doctor_info": doctor_result + patient_result,
            })
            doctor_result = self._parse_msg(doctor_msg)
            conversation_history.append(doctor_result)
            logger.info(f'第{i + 1}轮 医生说: {doctor_result}')

            # 患者回应
            patient_msg = self.patient_chain.invoke({
                "patient_info": doctor_result,
                "former_result": patient_result,
                "original_result": original_result,
            })
            patient_result = self._parse_msg(patient_msg)
            logger.info(f'第{i + 1}轮 假扮患者说: {patient_result}')

        # 4. 综合诊断
        answer = self.medical_assistant.decompose_and_diagnose(
            conversation_history, original_result, all_info, initial_docs_content
        )

        # 5. 总结
        summary = self.ask_ds(original_result, answer, all_info)

        logger.info(f'最终医生回答: {answer}')
        return "\n这是综合诊疗结果：\n" + answer, summary

    def translation(self, words: str) -> str:
        logger.info(f"正在翻译: {words}")
        messages = [
            SystemMessage(content="你是一位专业翻译人员，请将输入文本准确翻译成英文。"),
            HumanMessage(content=f"请将以下内容翻译成英文：\n{words}")
        ]
        response = self.llm.invoke(messages)
        result = response.content.strip()
        logger.info(f"翻译结果: {result}")
        return result

    def ask_ds(self, question: str, answer: str, all_info: str) -> str:
        try:
            messages = [
                SystemMessage(
                    content="你是一个擅长总结对话的医疗助手。\n请根据回答和已有信息总结对后续医疗诊断有用的内容。"),
                HumanMessage(content=f"问题：{question}\n回答：{answer}\n已有信息：{all_info}")
            ]
            response = self.llm.invoke(messages)
            logger.info("ask_ds 总结完成")
            return response.content.strip()
        except Exception as e:
            logger.error(f"ask_ds 运行错误: {e}")
            return f"发生错误: {str(e)}"


if __name__ == '__main__':
    try:
        app = qwenAgent()
        res, sum_res = app.run("感冒吃什么药？")
        logger.info(res)
        logger.info(sum_res)
    except Exception as error:
        logger.error(f"程序运行出错: {error}")

