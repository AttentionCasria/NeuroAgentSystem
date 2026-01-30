import logging
import re
from typing import List, Dict
import traceback
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from Agent.qwen.medicalAgent import MedicalReActAgent
# 【修复】替换失效的函数引用，使用统一检索引擎和配置
from makeData.Retrieve import UnifiedSearchEngine, CONFIG

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MedicalAssistant:
    # 系统提示词常量

    # 1. 强化“拆解逻辑”与“关联性”
    SYS_DECOMPOSER = (
        "You are a Clinical Logic Analyst. Your expertise lies in deconstructing complex "
        "patient complaints into high-value retrieval queries. You prioritize 'Symptom Clustering' "
        "over isolated symptoms—when symptoms co-occur, you focus on their pathological links "
        "and common etiologies to ensure more precise medical evidence retrieval."
    )

    # 2. 强化“证据合成”与“临床决策支撑”
    SYS_DOCTOR = (
        "You are a Senior Attending Physician specializing in Evidence-Based Medicine (EBM). "
        "Your role is to synthesize retrieved medical literature with patient histories to provide "
        "structured diagnostic reasoning and treatment suggestions. You prioritize patient safety, "
        "differential diagnosis, and the latest clinical guidelines in your professional analysis."
    )

    def __init__(self, llm):
        self.llm = llm
        logger.info("🔧 [MedicalAssistant] 初始化检索引擎...")
        try:
            # 1. 初始化检索引擎
            # 请确保 CONFIG 字典中必须有 'persist_dir' 和 'top_k_per_store' 这两个Key
            # 否则这里会抛出 KeyError
            self.retriever = UnifiedSearchEngine(
                persist_dir=CONFIG.get("persist_dir", "./chroma_db_unified"),  # 增加默认值防崩
                top_k=CONFIG.get("top_k_per_store", 4)
            )

            # 2. 初始化 Agent
            # 如果 medicalAgent.py 里面有代码错误（如 logger 未定义），这里会报错
            self.agent = MedicalReActAgent(self.llm, self.retriever)

            logger.info("✅ [MedicalAssistant] 检索引擎与 Agent 就绪")

        except Exception as e:
            # 【修改点2】打印完整的堆栈信息！
            logger.error("❌ [MedicalAssistant] 初始化严重失败，详细堆栈如下：")
            logger.error(traceback.format_exc())  # <--- 这行代码能告诉你具体死在哪一行
            # 重新抛出异常，让 main.py 知道启动失败了
            raise RuntimeError(f"MedicalAssistant Init Failed: {str(e)}")

    # def __init__(self, llm):
    #     self.llm = llm
    #     logger.info("🔧 [MedicalAssistant] 初始化检索引擎...")
    #     try:
    #         # 【新增】初始化检索引擎，适配新的数据检索方式
    #         self.retriever = UnifiedSearchEngine(
    #             persist_dir=CONFIG["persist_dir"],
    #             top_k=CONFIG["top_k_per_store"]
    #         )
    #         # 初始化 Agent
    #         self.agent = MedicalReActAgent(self.llm, self.retriever)
    #         logger.info("✅ [MedicalAssistant] 检索引擎就绪")
    #     except Exception as e:
    #         logger.error(f"❌ [MedicalAssistant] 检索引擎初始化失败: {e}")
    #         raise

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
        # """步骤一：生成英文分解问题（强化医疗关联规则版）"""
        prompt_parts = [
            "### Role",
            "You are a medical clinical expert specialized in diagnostic reasoning.",
            "",
            "### Task",
            # 修改 1：明确要求输出中文，以匹配中文临床文档库
            "Analyze the following patient complaint summaries (sum_talk) and decompose them into 3 concise Chinese sub-questions optimized for RAG retrieval against Chinese clinical guidelines.",
            "",
            "### Decomposition Rules (Clinical Logic)",
            "1. **Symptom Clustering**: ...",
            "2. **Contextual Specificity**: ...",
            "3. **Retrieval Focus**: Formulate questions that help differentiate between similar conditions based on the patterns found in the summaries.",
            "",
            "### Constraints",
            "- Generate exactly 3 sub-questions.",
            # 修改 2：语言一致性
            "- Each sub-question must be one concise sentence in Chinese.",
            "- Use standard Chinese medical terminology (e.g., use '基底动脉尖综合征' instead of 'TOBS').",
            "- Focus on high-frequency and clinically significant symptoms in the provided list.",
            "",
            "### Patient Complaint Summaries (sum_talk):",
        ]
        # prompt_parts = [
        #     "### Role",
        #     "You are a medical clinical expert specialized in diagnostic reasoning.",
        #     "",
        #     "### Task",
        #     "Analyze the following patient complaint summaries (sum_talk) and decompose them into 3 concise English sub-questions for medical evidence retrieval.",
        #     "",
        #     "### Decomposition Rules (Clinical Logic)",
        #     "1. **Symptom Clustering**: If two or more symptoms co-occur (e.g., headache and nausea), prioritize a combined search logic (e.g., 'symptom A accompanied by symptom B') to explore potential underlying etiologies, rather than decomposing them into isolated symptoms.",
        #     "2. **Contextual Specificity**: Each sub-question must include specific symptoms and their associated clinical scenarios (e.g., 'common causes of headache accompanied by nausea' or 'diagnostic evaluation for chronic cough with fever').",
        #     "3. **Retrieval Focus**: Formulate questions that help differentiate between similar conditions based on the patterns found in the summaries.",
        #     "",
        #     "### Constraints",
        #     "- Generate exactly 3 sub-questions.",
        #     "- Each sub-question must be one concise sentence in English.",
        #     "- Focus on high-frequency and clinically significant symptoms in the provided list.",
        #     "",
        #     "### Patient Complaint Summaries (sum_talk):",
        # ]
        prompt_parts.extend([f"- {talk}" for talk in sum_talk])
        prompt = "\n".join(prompt_parts)

        result = self._invoke_llm(self.SYS_DECOMPOSER, prompt)
        return result

    def _parse_questions(self, raw_text: str) -> List[str]:
        """解析 LLM 返回的子问题文本"""
        if not raw_text:
            return []

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
        """步骤三：改用 Agent 进行动态检索，支持多步思考和工具调用"""
        # --- 新增逻辑：如果列表为空，直接返回 ---
        if not questions:
            logger.info("⚠️ [MedicalAssistant] 检测到无有效子问题，跳过 Agent 检索逻辑。")
            return {}
        # ------------------------------------

        results = {}
        for i, q in enumerate(questions, 1):
            try:
                logger.info(f"🧠 [Agent Loop] 正在处理第 {i} 个子问题: {q}")

                # 调用 Agent 的 run 方法
                # system_prompt 依然使用你定义的 SYS_DECOMPOSER
                evidence = self.agent.run(
                    system_prompt=self.SYS_DECOMPOSER,
                    user_question=q
                )

                results[q] = evidence
            except Exception as e:
                logger.error(f"❌ Agent 处理问题 '{q}' 失败: {e}")
                results[q] = f"Agent 检索过程中出错: {e}"
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
