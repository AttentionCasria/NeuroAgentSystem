
from typing import List
import re
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from makeData.Retrieve import multi_collection_rag_retrieval
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MedicalAssistant:
    def __init__(self, llm):
        self.llm = llm  # llm 是 ChatOpenAI 实例（已配置为DeepSeek）

    def decompose_and_diagnose(self, sum_talk: List[str], original_result: str, all_info: str, content: str) -> str:
        """
        优化后：统一使用 self.llm.invoke() 进行调用
        """
        # —— 一、拆分子问题（英文输出） ——
        decomposition_prompt = "\n".join([
            "Given a number of patient complaint summaries (sum_talk), please identify the common symptoms that appear multiple times in these summaries",
            "and based on these commonalities, decompose into 3 clinically relevant sub-questions.",
            "Each sub-question should be expressed as one concise sentence in English.",
            "sum_talk list:",
            *[f"- {talk}" for talk in sum_talk]
        ])

        try:
            # 统一使用 invoke 方法
            resp_decomp = self.llm.invoke([
                SystemMessage(content=(
                    "You are a senior medical assistant, skilled at extracting clinical key points "
                    "from patient histories and formulating sub-questions."
                )),
                HumanMessage(content=decomposition_prompt)
            ])

            # 确保处理 AIMessage 对象
            if isinstance(resp_decomp, AIMessage):
                sub_questions_raw = resp_decomp.content.strip()
            else:
                sub_questions_raw = str(resp_decomp).strip()
        except Exception as e:
            logger.error(f"子问题分解失败: {e}")
            sub_questions_raw = ""

        # 解析成问题列表（英文） - 保持不变
        questions = []
        for line in sub_questions_raw.splitlines():
            line = line.strip()
            if not line:
                continue
            m = re.match(r'^\s*\d+[\.\)\、]\s*(.+)', line)
            if m:
                questions.append(m.group(1).strip())
            else:
                if line.startswith('-'):
                    q = line.lstrip('-').strip()
                    if q:
                        questions.append(q)
                else:
                    questions.append(line)

        if not (1 <= len(questions) <= 7):
            logger.warning(f"子问题解析异常，使用原始内容: {sub_questions_raw}")
            questions = [sub_questions_raw]

        # —— 二、针对每个子问题检索 ——
        per_q_results = {}
        for q in questions:
            try:
                res = multi_collection_rag_retrieval(q)
                # 假设 res 返回 (results_list, combined_content)
                if isinstance(res, tuple) and len(res) == 2:
                    _, combined_content = res
                    summary = combined_content
                else:
                    summary = str(res)
            except Exception as e:
                logger.error(f"子问题检索失败: {e}")
                summary = f"检索时出错: {e}"
            per_q_results[q] = summary

        # —— 三、合并提示，让 GPT 用中文给综合诊断 ——
        parts = []
        # 原始病史
        parts.append("Below is the patient's original medical history information (patient_result):")
        parts.append(original_result)
        parts.append("——————")
        # Sub-questions (English)
        parts.append("Sub-questions to focus on (in English):")
        for idx, q in enumerate(questions, start=1):
            parts.append(f"{idx}. {q}")
        parts.append("——————")
        # Search summaries
        parts.append("Below are the summary search results corresponding to each sub-question:")
        parts.append(
            f"Please focus solely on avoiding and addressing the symptoms of {original_result}. The following sub-questions are for reference only, and must be explicitly addressed in the response without evasion.")
        for idx, q in enumerate(questions, start=1):
            summary = per_q_results.get(q, "")
            parts.append(f"{idx}. Sub-question: {q}")
            parts.append(f"   Search summary: {summary}")
        # Key: constraint not to mention new symptoms
        parts.append(f"Note: Please focus particularly on {content}")
        parts.append(
            "Please, based on the original medical history, sub-questions, and their respective search results, provide several most likely comprehensive diagnostic considerations, but avoid making overly certain judgments. Please note that the sub-questions are only to broaden your thinking; focus more on the original medical history.")
        parts.append(
            "Note: If you believe the information initially provided by the patient is not typical or insufficient, you may reasonably continue to ask the patient based on your judgment.")
        parts.append(f"Below is the previous conversation information\n{all_info}")
        parts.append(
            "Important notice: Please ensure that the final response is entirely in Chinese; do not reply in any other language.")
        doctor_prompt = "\n".join(parts)

        try:
            resp_doctor = self.llm.invoke([
                SystemMessage(content=(
                    "You are an experienced physician, adept at combining the latest literature "
                    "to provide diagnostic and treatment suggestions."
                )),
                HumanMessage(content=doctor_prompt)
            ])

            # 确保处理 AIMessage 对象
            if isinstance(resp_doctor, AIMessage):
                diagnosis = resp_doctor.content.strip()
            else:
                diagnosis = str(resp_doctor).strip()
        except Exception as e:
            logger.error(f"综合诊断失败: {e}")
            diagnosis = "综合诊断过程中发生错误"


        return diagnosis