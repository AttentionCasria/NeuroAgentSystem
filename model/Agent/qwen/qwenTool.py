import os
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_models import ChatTongyi

def make_chain():
    # 从环境变量获取API密钥
    api_key = os.getenv("QWEN-API-KEY")
    if not api_key:
        raise ValueError("未找到环境变量 QWEN_API_KEY，请设置该环境变量")

    # 使用阿里云Qwen API（正确调用方式）
    llm = ChatTongyi(
        model="qwen-max",
        dashscope_api_key=api_key,
        temperature=0.7,
        max_tokens=4000
    )

    act_patient_template = """
    Please role-play as a patient who might have the illness the user is concerned about. Respond to the doctor based on previous conversation history, with the following requirements:
    1. Your tone should be calm, friendly, and match how a patient would speak.
    2. In this response, ask the doctor questions based on most symptoms (not all), and ensure all symptoms are mentioned over three rounds of questioning (partial symptoms may overlap between rounds). If asked about medical information, provide it truthfully.
    3. Crucially: Never disclose all key symptoms at once! Never state your suspected illness unless the doctor identifies it first.
    4. Keep responses under 30 words. Avoid unrelated topics.
    Here is your information:
    {patient_info}
    """

    act_doctor_template = """
    You are a medical expert. Your task is to:
    1. Analyze the patient's symptoms using the provided clinical documents
    2. Determine the diagnosis through step-by-step reasoning
    3. Provide a treatment plan
    4. Always give a definitive conclusion

    Requirements:
    - Systematically integrate all given medical references
    - Base your diagnosis on documented clinical evidence
    - Keep responses research-oriented and conclusive

    Patient information:
    {doctor_info}
    """

    patient_prompt = PromptTemplate(
        template=act_patient_template,
        input_variables=["patient_info"],
    )

    doctor_prompt = PromptTemplate(
        template=act_doctor_template,
        input_variables=["doctor_info"],
    )

    # 添加输出解析器处理AIMessage对象
    patient_chain = (
            RunnablePassthrough.assign(
                patient_info=lambda x: x["patient_info"],
            )
            | patient_prompt
            | llm
            | StrOutputParser()  # 将AIMessage转为字符串
    )

    doctor_chain = (
            RunnablePassthrough.assign(
                doctor_info=lambda x: x["doctor_info"],
            )
            | doctor_prompt
            | llm
            | StrOutputParser()  # 将AIMessage转为字符串
    )

    return patient_chain, doctor_chain