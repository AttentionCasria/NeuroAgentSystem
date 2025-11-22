import os
import logging
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from dataRetrieve import multi_collection_rag_retrieval
from Qwen_Assistant import MedicalAssistant
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatTongyi
import os
# ------------------ 日志配置 ------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ------------------ ActRound 类 ------------------
class ActRound(object):
    def __init__(self):
        api_key = os.getenv("QWEN-API-KEY")  # 注意变量名！
        if not api_key:
            raise ValueError("未找到环境变量 QWEN-API-KEY，请设置该环境变量")

        # ✅ 正确方式：使用 ChatTongyi
        self.llm = ChatTongyi(
            model="qwen-max",
            dashscope_api_key=api_key,
            temperature=0.7,
            max_tokens=4000
        )

        # 如果你确实要用 DeepSeek（另一个模型），请用独立的 DeepSeek API Key
        # 但不要和 Qwen 混用同一个 key！
        deepseek_key = os.getenv("DEEPSEEK-API-KEY")
        if not deepseek_key:
            logger.warning("未设置 DEEPSEEK-API-KEY，simple_llm 将无法使用")
        else:
            from langchain_openai import ChatOpenAI
        self.simple_llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_base="https://api.deepseek.com/v1",
            openai_api_key=deepseek_key,  # 必须是 DeepSeek 的 key
            temperature=0.3,
            max_tokens=300
        )

        self.patient_chain, self.doctor_chain = self.make_chain()
        self.medical_assistant = MedicalAssistant(self.llm)
        logger.info("ActRound 初始化完成")

    # ------------------ 主运行函数 ------------------
    def run(self, words, round=2, all_info=""):
        logger.info(f"开始执行 run() 方法，输入词语: {words}")  # <-- 添加此行
        sum_talk = []

        patient_result = self.translation(words)
        logger.info(f'翻译结果: {patient_result}')

        if isinstance(patient_result, AIMessage):
            patient_result = patient_result.content
        else:
            patient_result = str(patient_result).strip()
        original_result = patient_result

        # 调用 RAG 检索
        temp_c = multi_collection_rag_retrieval(original_result)
        logger.info(f'RAG 检索到 {len(temp_c)} 条文档')
        # 将Document对象列表转换为字符串列表，然后再处理
        doc_strings = [doc.page_content for doc in temp_c]
        # 然后可以根据需要使用doc_strings，例如:
        temp_c_str = "\n\n".join(doc_strings)


        doctor_result = ""
        for i in range(round):
            query = str(patient_result).strip()
            content = multi_collection_rag_retrieval(query)
            logger.info(f'第{i+1}轮 RAG 检索到 {len(content)} 条文档')

            # 医生回答
            doctor_msg = self.doctor_chain.invoke({
                "document": content,
                "doctor_info": doctor_result + patient_result,
            })
            if isinstance(doctor_msg, AIMessage):
                doctor_result = doctor_msg.content
            else:
                doctor_result = str(doctor_msg).strip()
            sum_talk.append(doctor_result)
            logger.info(f'第{i+1}轮 医生说: {doctor_result}')

            # 病人回应
            patient_msg = self.patient_chain.invoke({
                "patient_info": doctor_result,
                "former_result": patient_result,
                "original_result": original_result,
            })
            if isinstance(patient_msg, AIMessage):
                patient_result = patient_msg.content
            else:
                patient_result = str(patient_msg).strip()
            logger.info(f'第{i+1}轮 假扮患者说: {patient_result}')

        # 综合诊断
        answer = self.medical_assistant.decompose_and_diagnose(sum_talk, original_result,
                                                               all_info, temp_c_str)

        summary = self.ask_ds(original_result, answer, all_info)
        logger.info(f'最终医生回答: {answer}')
        return "\n这是综合诊疗结果：\n" + answer, summary

    # ------------------ 翻译函数 ------------------
    def translation(self, words):
        logger.info(f"开始执行 translation() 方法，待翻译内容: {words}")  # <-- 添加此行
        response = self.llm.invoke([
            SystemMessage(content="你是一位专业翻译人员，请将输入文本准确翻译成英文。"),
            HumanMessage(content=f"请将以下内容翻译成英文：\n{words}")
        ])
        raw_output = response.content.strip()
        logger.info(f"翻译结果: {raw_output}")
        return raw_output

    # ------------------ 构建链条 ------------------
    def make_chain(self):
        act_patient_template = """
        Please role-play as a patient who might have the illness the user is concerned about. 
        Keep your responses concise and focused solely on relevant symptoms and experiences. 
        Avoid any unnecessary details, explanations, or off-topic remarks.
        Please pay close attention to the {original_result} and let it guide your responses based on the following information.
        Your answer should not be identical to "{former_result}"
        Patient information:
        {patient_info}
        """
        act_doctor_template = """
        You are a medical expert. 
        Provide clear and concise medical advice based on the patient's information. 
        Keep responses brief, professional, and directly related to the medical context. 
        Avoid any extraneous comments or opinions.
        Patient information:
        {doctor_info}
        Reference Materials:
        {document}
        """
        patient_prompt = PromptTemplate(
            template=act_patient_template,
            input_variables=["patient_info", "former_result", "original_result"],
        )
        doctor_prompt = PromptTemplate(
            template=act_doctor_template,
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

    # ------------------ 总结函数 ------------------
    def ask_ds(self, question, answer, all_info):
        try:
            messages = [
                SystemMessage(content=(
                    "你是一个擅长总结对话的医疗助手。\n"
                    "请根据回答和已有信息总结对后续医疗诊断有用的内容。"
                )),
                HumanMessage(content=f"问题：{question}\n回答：{answer}\n已有信息：{all_info}")
            ]
            response = self.llm(messages)
            logger.info("ask_ds 总结完成")
            return response.content.strip()
        except Exception as e:
            logger.error(f"ask_ds 错误: {str(e)}")
            return f"发生错误: {str(e)}"


# ------------------ 测试运行 ------------------
if __name__ == '__main__':
    A = ActRound()
    result, summary = A.run("感冒吃什么药？")
    logger.info(result)
    logger.info(summary)