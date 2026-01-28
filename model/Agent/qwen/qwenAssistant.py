import logging
import re
from typing import List, Dict

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# 【修复】替换失效的函数引用，使用统一检索引擎和配置
from makeData.dataRetrieve import UnifiedSearchEngine, CONFIG

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MedicalAssistant:
    # 系统提示词常量
    SYS_DECOMPOSER = (
        "You are a senior medical assistant, skilled at extracting clinical key points "
        "from patient histories and formulating sub-questions."
    )
    SYS_DOCTOR = (
        "You are an experienced physician, adept at combining the latest literature "
        "to provide diagnostic and treatment suggestions."
    )

    def __init__(self, llm):
        self.llm = llm
        logger.info("🔧 [MedicalAssistant] 初始化检索引擎...")
        try:
            # 【新增】初始化检索引擎，适配新的数据检索方式
            self.retriever = UnifiedSearchEngine(
                persist_dir=CONFIG["persist_dir"],
                top_k=CONFIG["top_k_per_store"]
            )
            logger.info("✅ [MedicalAssistant] 检索引擎就绪")
        except Exception as e:
            logger.error(f"❌ [MedicalAssistant] 检索引擎初始化失败: {e}")
            raise

    def decompose_and_diagnose(self, sum_talk: List[str], original_result: str, all_info: str, content: str) -> str:
        """执行分解诊断全流程（带详细日志追踪）"""
        logger.info("=" * 40)
        logger.info("🚀 [MedicalAssistant] 开始执行分解诊断全流程")

        # 1. 拆分子问题
        logger.info("🔹 [Step 1/4] 正在根据病史拆解临床子问题 (LLM Thinking)...")
        sub_questions_raw = self._decompose_questions(sum_talk)

        # 2. 解析问题列表
        questions = self._parse_questions(sub_questions_raw)
        logger.info(f"🔹 [Step 2/4] 解析得到 {len(questions)} 个关键子问题:")
        for idx, q in enumerate(questions, 1):
            logger.info(f"    {idx}. {q}")

        # 3. 针对性检索
        logger.info(f"🔹 [Step 3/4] 开始针对子问题进行证据检索 (Search)...")
        per_q_results = self._retrieve_evidence(questions)
        logger.info("✅ [Step 3/4] 证据检索完成")

        # 4. 综合诊断
        logger.info("🔹 [Step 4/4] 汇总证据，生成综合诊断报告 (LLM Diagnosis)...")
        diagnosis = self._generate_diagnosis(original_result, questions, per_q_results, content, all_info)

        logger.info("🎉 [MedicalAssistant] 流程结束，诊断生成完毕。")
        logger.info("=" * 40)
        return diagnosis

    def _invoke_llm(self, system_content: str, user_content: str) -> str:
        """封装大模型调用与结果解析"""
        try:
            response = self.llm.invoke([
                SystemMessage(content=system_content),
                HumanMessage(content=user_content)
            ])
            return response.content.strip() if isinstance(response, AIMessage) else str(response).strip()
        except Exception as e:
            logger.error(f"❌ LLM 调用失败: {e}")
            return ""

    def _decompose_questions(self, sum_talk: List[str]) -> str:
        """步骤一：生成英文分解问题"""
        prompt_parts = [
            "Given a number of patient complaint summaries (sum_talk), please identify the common symptoms that appear multiple times in these summaries",
            "and based on these commonalities, decompose into 3 clinically relevant sub-questions.",
            "Each sub-question should be expressed as one concise sentence in English.",
            "sum_talk list:",
        ]
        prompt_parts.extend([f"- {talk}" for talk in sum_talk])
        prompt = "\n".join(prompt_parts)

        result = self._invoke_llm(self.SYS_DECOMPOSER, prompt)
        return result

    def _parse_questions(self, raw_text: str) -> List[str]:
        """步骤二：解析问题文本结构"""
        questions = []
        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue

            # 匹配数字开头的列表项 (如 "1. xxx" 或 "1) xxx")
            m = re.match(r'^\s*\d+[\.\)\、]\s*(.+)', line)
            if m:
                questions.append(m.group(1).strip())
            else:
                # 匹配破折号开头的项
                if line.startswith('-'):
                    q = line.lstrip('-').strip()
                    if q:
                        questions.append(q)
                else:
                    questions.append(line)

        # 校验问题数量，如果不合理则使用原始内容
        if not (1 <= len(questions) <= 7):
            logger.warning(f"⚠️ 子问题解析格式异常，退回使用原始内容: {raw_text}")
            return [raw_text]
        return questions

    def _retrieve_evidence(self, questions: List[str]) -> Dict[str, str]:
        """步骤三：使用 UnifiedSearchEngine 进行检索"""
        results = {}
        for i, q in enumerate(questions, 1):
            try:
                # 增加检索日志
                logger.info(f"   🔍 [{i}/{len(questions)}] 正在检索: {q}")

                # 调用新的 search 方法
                docs = self.retriever.search(q, top_k_final=CONFIG.get("top_k_final", 6))

                logger.info(f"      -> 找到 {len(docs)} 条相关文献")

                # 将文档内容合并为字符串
                summary = "\n\n".join([doc.page_content for doc in docs])
            except Exception as e:
                logger.error(f"   ❌ 子问题 '{q}' 检索失败: {e}")
                summary = f"检索时出错: {e}"
            results[q] = summary
        return results

    def _generate_diagnosis(self, original_result, questions, per_q_results, content, all_info) -> str:
        """步骤四：构建提示词并生成最终诊断"""
        parts = []
        # 严格保持原有提示词结构
        parts.append("Below is the patient's original medical history information (patient_result):")
        parts.append(original_result)
        parts.append("——————")

        parts.append("Sub-questions to focus on (in English):")
        for idx, q in enumerate(questions, start=1):
            parts.append(f"{idx}. {q}")
        parts.append("——————")

        parts.append("Below are the summary search results corresponding to each sub-question:")
        parts.append(
            f"Please focus solely on avoiding and addressing the symptoms of {original_result}. The following sub-questions are for reference only, and must be explicitly addressed in the response without evasion.")

        for idx, q in enumerate(questions, start=1):
            summary = per_q_results.get(q, "")
            parts.append(f"{idx}. Sub-question: {q}")
            parts.append(f"   Search summary: {summary}")

        parts.append(f"Note: Please focus particularly on {content}")
        parts.append(
            "Please, based on the original medical history, sub-questions, and their respective search results, provide several most likely comprehensive diagnostic considerations, but avoid making overly certain judgments. Please note that the sub-questions are only to broaden your thinking; focus more on the original medical history.")
        parts.append(
            "Note: If you believe the information initially provided by the patient is not typical or insufficient, you may reasonably continue to ask the patient based on your judgment.")
        parts.append(f"Below is the previous conversation information\n{all_info}")
        parts.append(
            "Important notice: Please ensure that the final response is entirely in Chinese; do not reply in any other language.")

        prompt = "\n".join(parts)

        diagnosis = self._invoke_llm(self.SYS_DOCTOR, prompt)
        return diagnosis if diagnosis else "❌ 综合诊断过程中发生错误，未生成有效回应。"

# import logging
# import re
# from typing import List, Dict
#
# from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
#
# # 【修复】替换失效的函数引用，使用统一检索引擎和配置
# from makeData.dataRetrieve import UnifiedSearchEngine, CONFIG
#
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
#
#
# class MedicalAssistant:
#     # 系统提示词常量
#     SYS_DECOMPOSER = (
#         "You are a senior medical assistant, skilled at extracting clinical key points "
#         "from patient histories and formulating sub-questions."
#     )
#     SYS_DOCTOR = (
#         "You are an experienced physician, adept at combining the latest literature "
#         "to provide diagnostic and treatment suggestions."
#     )
#
#     def __init__(self, llm):
#         self.llm = llm
#         # 【新增】初始化检索引擎，适配新的数据检索方式
#         self.retriever = UnifiedSearchEngine(
#             persist_dir=CONFIG["persist_dir"],
#             top_k=CONFIG["top_k_per_store"]
#         )
#
#     def decompose_and_diagnose(self, sum_talk: List[str], original_result: str, all_info: str, content: str) -> str:
#         """执行分解诊断全流程"""
#         # 1. 拆分子问题
#         sub_questions_raw = self._decompose_questions(sum_talk)
#
#         # 2. 解析问题列表
#         questions = self._parse_questions(sub_questions_raw)
#
#         # 3. 针对性检索
#         per_q_results = self._retrieve_evidence(questions)
#
#         # 4. 综合诊断
#         diagnosis = self._generate_diagnosis(original_result, questions, per_q_results, content, all_info)
#
#         return diagnosis
#
#     def _invoke_llm(self, system_content: str, user_content: str) -> str:
#         """封装大模型调用与结果解析"""
#         try:
#             response = self.llm.invoke([
#                 SystemMessage(content=system_content),
#                 HumanMessage(content=user_content)
#             ])
#             return response.content.strip() if isinstance(response, AIMessage) else str(response).strip()
#         except Exception as e:
#             logger.error(f"LLM调用失败 [{system_content[:20]}...]: {e}")
#             return ""
#
#     def _decompose_questions(self, sum_talk: List[str]) -> str:
#         """步骤一：生成英文分解问题"""
#         prompt_parts = [
#             "Given a number of patient complaint summaries (sum_talk), please identify the common symptoms that appear multiple times in these summaries",
#             "and based on these commonalities, decompose into 3 clinically relevant sub-questions.",
#             "Each sub-question should be expressed as one concise sentence in English.",
#             "sum_talk list:",
#         ]
#         prompt_parts.extend([f"- {talk}" for talk in sum_talk])
#         prompt = "\n".join(prompt_parts)
#
#         result = self._invoke_llm(self.SYS_DECOMPOSER, prompt)
#         return result
#
#     def _parse_questions(self, raw_text: str) -> List[str]:
#         """步骤二：解析问题文本结构（保持原逻辑）"""
#         questions = []
#         for line in raw_text.splitlines():
#             line = line.strip()
#             if not line:
#                 continue
#
#             # 匹配数字开头的列表项 (如 "1. xxx" 或 "1) xxx")
#             m = re.match(r'^\s*\d+[\.\)\、]\s*(.+)', line)
#             if m:
#                 questions.append(m.group(1).strip())
#             else:
#                 # 匹配破折号开头的项
#                 if line.startswith('-'):
#                     q = line.lstrip('-').strip()
#                     if q:
#                         questions.append(q)
#                 else:
#                     questions.append(line)
#
#         # 校验问题数量，如果不合理则使用原始内容
#         if not (1 <= len(questions) <= 7):
#             logger.warning(f"子问题解析异常，使用原始内容: {raw_text}")
#             return [raw_text]
#         return questions
#
#     def _retrieve_evidence(self, questions: List[str]) -> Dict[str, str]:
#         """步骤三：使用 UnifiedSearchEngine 进行检索"""
#         results = {}
#         for q in questions:
#             try:
#                 # 调用新的 search 方法
#                 docs = self.retriever.search(q, top_k_final=CONFIG.get("top_k_final", 6))
#                 # 将文档内容合并为字符串
#                 summary = "\n\n".join([doc.page_content for doc in docs])
#             except Exception as e:
#                 logger.error(f"子问题 '{q}' 检索失败: {e}")
#                 summary = f"检索时出错: {e}"
#             results[q] = summary
#         return results
#
#     def _generate_diagnosis(self, original_result, questions, per_q_results, content, all_info) -> str:
#         """步骤四：构建提示词并生成最终诊断"""
#         parts = []
#         # 严格保持原有提示词结构
#         parts.append("Below is the patient's original medical history information (patient_result):")
#         parts.append(original_result)
#         parts.append("——————")
#
#         parts.append("Sub-questions to focus on (in English):")
#         for idx, q in enumerate(questions, start=1):
#             parts.append(f"{idx}. {q}")
#         parts.append("——————")
#
#         parts.append("Below are the summary search results corresponding to each sub-question:")
#         parts.append(
#             f"Please focus solely on avoiding and addressing the symptoms of {original_result}. The following sub-questions are for reference only, and must be explicitly addressed in the response without evasion.")
#
#         for idx, q in enumerate(questions, start=1):
#             summary = per_q_results.get(q, "")
#             parts.append(f"{idx}. Sub-question: {q}")
#             parts.append(f"   Search summary: {summary}")
#
#         parts.append(f"Note: Please focus particularly on {content}")
#         parts.append(
#             "Please, based on the original medical history, sub-questions, and their respective search results, provide several most likely comprehensive diagnostic considerations, but avoid making overly certain judgments. Please note that the sub-questions are only to broaden your thinking; focus more on the original medical history.")
#         parts.append(
#             "Note: If you believe the information initially provided by the patient is not typical or insufficient, you may reasonably continue to ask the patient based on your judgment.")
#         parts.append(f"Below is the previous conversation information\n{all_info}")
#         parts.append(
#             "Important notice: Please ensure that the final response is entirely in Chinese; do not reply in any other language.")
#
#         prompt = "\n".join(parts)
#
#         diagnosis = self._invoke_llm(self.SYS_DOCTOR, prompt)
#         return diagnosis if diagnosis else "综合诊断过程中发生错误"
#
# # from typing import List
# # import re
# # from langchain.schema import HumanMessage, SystemMessage, AIMessage
# #
# # from makeData.dataRetrieve import multi_collection_rag_retrieval
# # import logging
# #
# # # 配置日志
# # logging.basicConfig(level=logging.INFO)
# # logger = logging.getLogger(__name__)
# #
# #
# # class MedicalAssistant:
# #     def __init__(self, llm):
# #         self.llm = llm
# #
# #     def decompose_and_diagnose(self, sum_talk: List[str], original_result: str, all_info: str, content: str) -> str:
# #         """
# #         优化后：统一使用 self.llm.invoke() 进行调用
# #         """
# #         # —— 一、拆分子问题（英文输出） ——
# #         decomposition_prompt = "\n".join([
# #             "Given a number of patient complaint summaries (sum_talk), please identify the common symptoms that appear multiple times in these summaries",
# #             "and based on these commonalities, decompose into 3 clinically relevant sub-questions.",
# #             "Each sub-question should be expressed as one concise sentence in English.",
# #             "sum_talk list:",
# #             *[f"- {talk}" for talk in sum_talk]
# #         ])
# #
# #         try:
# #             # 统一使用 invoke 方法
# #             resp_decomp = self.llm.invoke([
# #                 SystemMessage(content=(
# #                     "You are a senior medical assistant, skilled at extracting clinical key points "
# #                     "from patient histories and formulating sub-questions."
# #                 )),
# #                 HumanMessage(content=decomposition_prompt)
# #             ])
# #
# #             # 确保处理 AIMessage 对象
# #             if isinstance(resp_decomp, AIMessage):
# #                 sub_questions_raw = resp_decomp.content.strip()
# #             else:
# #                 sub_questions_raw = str(resp_decomp).strip()
# #         except Exception as e:
# #             logger.error(f"子问题分解失败: {e}")
# #             sub_questions_raw = ""
# #
# #         # 解析成问题列表（英文） - 保持不变
# #         questions = []
# #         for line in sub_questions_raw.splitlines():
# #             line = line.strip()
# #             if not line:
# #                 continue
# #             m = re.match(r'^\s*\d+[\.\)\、]\s*(.+)', line)
# #             if m:
# #                 questions.append(m.group(1).strip())
# #             else:
# #                 if line.startswith('-'):
# #                     q = line.lstrip('-').strip()
# #                     if q:
# #                         questions.append(q)
# #                 else:
# #                     questions.append(line)
# #
# #         if not (1 <= len(questions) <= 7):
# #             logger.warning(f"子问题解析异常，使用原始内容: {sub_questions_raw}")
# #             questions = [sub_questions_raw]
# #
# #         # —— 二、针对每个子问题检索 ——
# #         per_q_results = {}
# #         for q in questions:
# #             try:
# #                 res = multi_collection_rag_retrieval(q)
# #                 # 假设 res 返回 (results_list, combined_content)
# #                 if isinstance(res, tuple) and len(res) == 2:
# #                     _, combined_content = res
# #                     summary = combined_content
# #                 else:
# #                     summary = str(res)
# #             except Exception as e:
# #                 logger.error(f"子问题检索失败: {e}")
# #                 summary = f"检索时出错: {e}"
# #             per_q_results[q] = summary
# #
# #         # —— 三、合并提示，让 GPT 用中文给综合诊断 ——
# #         parts = []
# #         # 原始病史
# #         parts.append("Below is the patient's original medical history information (patient_result):")
# #         parts.append(original_result)
# #         parts.append("——————")
# #         # Sub-questions (English)
# #         parts.append("Sub-questions to focus on (in English):")
# #         for idx, q in enumerate(questions, start=1):
# #             parts.append(f"{idx}. {q}")
# #         parts.append("——————")
# #         # Search summaries
# #         parts.append("Below are the summary search results corresponding to each sub-question:")
# #         parts.append(
# #             f"Please focus solely on avoiding and addressing the symptoms of {original_result}. The following sub-questions are for reference only, and must be explicitly addressed in the response without evasion.")
# #         for idx, q in enumerate(questions, start=1):
# #             summary = per_q_results.get(q, "")
# #             parts.append(f"{idx}. Sub-question: {q}")
# #             parts.append(f"   Search summary: {summary}")
# #         # Key: constraint not to mention new symptoms
# #         parts.append(f"Note: Please focus particularly on {content}")
# #         parts.append(
# #             "Please, based on the original medical history, sub-questions, and their respective search results, provide several most likely comprehensive diagnostic considerations, but avoid making overly certain judgments. Please note that the sub-questions are only to broaden your thinking; focus more on the original medical history.")
# #         parts.append(
# #             "Note: If you believe the information initially provided by the patient is not typical or insufficient, you may reasonably continue to ask the patient based on your judgment.")
# #         parts.append(f"Below is the previous conversation information\n{all_info}")
# #         parts.append(
# #             "Important notice: Please ensure that the final response is entirely in Chinese; do not reply in any other language.")
# #         doctor_prompt = "\n".join(parts)
# #
# #         try:
# #             resp_doctor = self.llm.invoke([
# #                 SystemMessage(content=(
# #                     "You are an experienced physician, adept at combining the latest literature "
# #                     "to provide diagnostic and treatment suggestions."
# #                 )),
# #                 HumanMessage(content=doctor_prompt)
# #             ])
# #
# #             # 确保处理 AIMessage 对象
# #             if isinstance(resp_doctor, AIMessage):
# #                 diagnosis = resp_doctor.content.strip()
# #             else:
# #                 diagnosis = str(resp_doctor).strip()
# #         except Exception as e:
# #             logger.error(f"综合诊断失败: {e}")
# #             diagnosis = "综合诊断过程中发生错误"
# #
# #
# #         return diagnosis