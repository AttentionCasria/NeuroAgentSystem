# qwenAgent.py — 原则驱动 + 动态结构版（修正并行调用）

import logging
import asyncio
import json
import time
from typing import Generator, List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from langchain_core.messages import HumanMessage, SystemMessage
from config.config_loader import PromptManager, ReportTemplateManager

logger = logging.getLogger(__name__)

MAX_SUB_QUESTIONS = 3
MAX_CRITIC_SUMMARY_CHARS = 500
MAX_EVIDENCE_FOR_REPORT = 2500
MAX_PROPOSAL_FOR_REPORT = 2500


class qwenAgent:

    def __init__(
        self,
        llm_proposer,
        llm_critic,
        medical_assistant,
        prompt_manager: PromptManager,
        report_manager: ReportTemplateManager
    ):
        self.llm_proposer = llm_proposer
        self.llm_critic = llm_critic
        self.medical_assistant = medical_assistant
        self.prompts = prompt_manager
        self.reports = report_manager
        self._thread_pool = ThreadPoolExecutor(max_workers=3)

    # =========================================================
    # 工具方法
    # =========================================================

    def _get_prompt(self, key, fallback, **kwargs):
        prompt = None
        if self.prompts:
            prompt = self.prompts.get(key, **kwargs)
        if not prompt:
            try:
                prompt = fallback.format(**kwargs)
            except KeyError:
                prompt = fallback
        return prompt

    def _emit_thinking(self, step, title, content) -> dict:
        if isinstance(content, (dict, list)):
            content_str = json.dumps(content, ensure_ascii=False, indent=2)
        else:
            content_str = str(content)
        logger.info(f"[{step}] {title}")
        logger.info(
            content_str[:500] + ("..." if len(content_str) > 500 else "")
        )
        return {
            "type": "thinking",
            "step": step,
            "title": title,
            "content": content_str
        }

    def _parse_json(self, text, default=None):
        content = text.strip()
        try:
            return json.loads(content)
        except Exception:
            pass
        for marker in ["```json", "```"]:
            if marker in content:
                try:
                    s = content.split(marker)[1].split("```")[0].strip()
                    return json.loads(s)
                except Exception:
                    pass
        for sc, ec in [("{", "}"), ("[", "]")]:
            si, ei = content.find(sc), content.rfind(ec)
            if si != -1 and ei > si:
                try:
                    return json.loads(content[si:ei + 1])
                except Exception:
                    pass
        return default

    def _truncate(self, text: str, max_chars: int) -> str:
        if not text or len(text) <= max_chars:
            return text
        head = int(max_chars * 0.7)
        tail = max_chars - head
        return (
            text[:head]
            + f"\n[...省略{len(text) - max_chars}字...]\n"
            + text[-tail:]
        )

    def _extract_critic_summary(self, critic_raw: str) -> str:
        if not critic_raw:
            return "✅ 未发现被忽视的致命风险"
        if len(critic_raw) <= MAX_CRITIC_SUMMARY_CHARS:
            return critic_raw
        return critic_raw[:MAX_CRITIC_SUMMARY_CHARS] + "\n[已截断]"

    def _merge_evidence(self, pre: str, precise: str) -> str:
        if not pre:
            return precise
        if not precise:
            return pre
        precise_sources = set()
        for line in precise.split("来源:"):
            if "》" in line:
                precise_sources.add(line.split("》")[0][-20:])
        extra = []
        for block in pre.split("【文献"):
            if block.strip() and not any(s in block for s in precise_sources):
                extra.append("【文献" + block)
        if extra:
            return precise + "\n\n---\n### 补充检索\n" + "\n\n".join(extra)
        return precise

    # =========================================================
    # 复杂度自适应 Proposer prompt
    # =========================================================

    def _build_proposer_prompt(
        self, context_str, evidence_str, all_info_str, complexity
    ) -> str:
        if complexity in ("low", "medium"):
            structure_hint = (
                "结构要求：\n"
                f"本病例复杂度为 {complexity}，请精简输出：\n"
                "- 最危险问题 + 立即动作\n"
                "- 鉴别诊断（2-3个）\n"
                "- 关键风险点名\n"
                "- 缺失信息"
            )
        else:
            structure_hint = (
                "结构要求：\n"
                f"本病例复杂度为 {complexity}，请完整输出：\n"
                "- 按气道→呼吸→循环→神经的优先级展开危险评估\n"
                "- 鉴别诊断必须包含非卒中可能\n"
                "- 必须评估再灌注治疗路径（溶栓/取栓的适应症与禁忌）\n"
                "- 抗凝决策必须带前提条件\n"
                "- 所有风险必须点名延误后果"
            )

        return _PROPOSER_TEMPLATE.format(
            structure_hint=structure_hint,
            context=context_str,
            all_info=all_info_str,
            evidence=evidence_str
        )

    # =========================================================
    # 对外入口
    # =========================================================

    def run_clinical_reasoning(
        self,
        case_text: str,
        all_info: str = "",
        report_mode: str = "emergency",
        show_thinking: bool = True
    ) -> Generator[dict, None, None]:

        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            t_start = time.time()

            # ── Step 1: 统一分析 + 预检索并行 ──
            if show_thinking:
                yield self._emit_thinking(
                    "Step 1", "🏥 病例分析 + 预检索并行...",
                    "LLM结构化分析与RAG预检索同时启动"
                )

            pre_search_future = self._thread_pool.submit(
                self.medical_assistant.fast_parallel_retrieve,
                [case_text[:200]]
            )

            analysis = loop.run_until_complete(
                self._unified_analysis(case_text, all_info)
            )

            context = analysis.get(
                "structured_context", {"原始病例": case_text}
            )
            clinical_questions = analysis.get("clinical_questions", [])
            key_risks = analysis.get("key_risks", [])
            complexity = analysis.get("complexity", "high")

            if not clinical_questions:
                clinical_questions = ["该患者当前最紧急的临床问题和处置要点"]
            clinical_questions = clinical_questions[:MAX_SUB_QUESTIONS]

            t1 = time.time()
            if show_thinking:
                yield self._emit_thinking(
                    "Step 1", f"✅ 完成 ({t1 - t_start:.1f}s)", {
                        "complexity": complexity,
                        "questions": clinical_questions,
                        "key_risks": key_risks
                    }
                )

            yield {
                "type": "meta",
                "content": {
                    "complexity": complexity,
                    "report_mode": report_mode,
                    "key_risks": key_risks
                }
            }

            # ── Step 2: 精准检索 ──
            if show_thinking:
                yield self._emit_thinking(
                    "Step 2", "🔍 精准证据检索...",
                    f"检索 {len(clinical_questions)} 个子问题"
                )

            precise_evidence = self.medical_assistant.fast_parallel_retrieve(
                clinical_questions
            )
            try:
                pre_evidence = pre_search_future.result(timeout=5)
            except Exception:
                pre_evidence = ""

            evidence = self._merge_evidence(pre_evidence, precise_evidence)

            t2 = time.time()
            if show_thinking:
                yield self._emit_thinking(
                    "Step 2", f"✅ 完成 ({t2 - t1:.1f}s)",
                    f"{len(evidence)} 字符证据"
                )

            # ── Step 3: Proposer + Critic 并行 ──
            if show_thinking:
                yield self._emit_thinking(
                    "Step 3", "🧠 决策推理 + 致命盲区检查 并行...",
                    "ICU主治推理和质控同时进行"
                )

            proposal, critic_raw = loop.run_until_complete(
                self._parallel_propose_and_critique(
                    context, evidence, all_info, complexity
                )
            )

            critic_summary = self._extract_critic_summary(critic_raw)

            t3 = time.time()
            if show_thinking:
                yield self._emit_thinking(
                    "Step 3a", f"✅ 决策推理完成 ({len(proposal)}字)",
                    proposal
                )
                yield self._emit_thinking(
                    "Step 3b",
                    f"✅ 盲区检查完成 [{t3 - t2:.1f}s]",
                    critic_summary
                )

            # ── Step 4: 最终报告 ──
            if show_thinking:
                yield self._emit_thinking(
                    "Step 4", f"📝 生成最终报告 ({report_mode})...",
                    "融合决策 + 盲区修正 → 最终报告"
                )

            final_stream = self.medical_assistant.stream_final_report(
                context=context,
                proposal=self._truncate(proposal, MAX_PROPOSAL_FOR_REPORT),
                critique=critic_summary,
                evidence=self._truncate(evidence, MAX_EVIDENCE_FOR_REPORT),
                all_info=all_info,
                report_mode=report_mode
            )

            async def consume():
                async for chunk in final_stream:
                    yield chunk

            agen = consume()
            while True:
                try:
                    chunk = loop.run_until_complete(agen.__anext__())
                    if isinstance(chunk, str) and chunk:
                        yield {"type": "result", "content": chunk}
                    elif hasattr(chunk, "content") and chunk.content:
                        yield {"type": "result", "content": chunk.content}
                except StopAsyncIteration:
                    break

            t_end = time.time()
            if show_thinking:
                yield self._emit_thinking(
                    "Done", "✅ 全部完成",
                    f"总耗时: {t_end - t_start:.1f}s "
                    f"(分析{t1-t_start:.0f}s + 检索{t2-t1:.0f}s + "
                    f"推理{t3-t2:.0f}s + 报告{t_end-t3:.0f}s)"
                )

        except Exception as e:
            logger.error(f"临床推理管线异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            yield {"type": "error", "content": str(e)}
        finally:
            if loop:
                loop.close()

    # =========================================================
    # LLM #1: 统一分析
    # =========================================================

    async def _unified_analysis(self, case_text, all_info):
        prompt = f"""你是神经急诊专家。对以下病例完成三项任务，一次性输出JSON。

【病例】
{case_text}

【历史上下文】
{all_info if all_info else "无"}

直接输出JSON（不要代码块）：
{{
    "structured_context": {{
        "基本信息": {{"年龄": "", "性别": ""}},
        "起病方式": "",
        "主要症状": [],
        "神经系统查体": {{}},
        "意识水平": "",
        "生命体征": {{}},
        "既往史": [],
        "用药史": [],
        "危险因素": [],
        "非卒中线索": []
    }},
    "complexity": "low/medium/high/critical",
    "key_risks": ["风险1", "风险2"],
    "clinical_questions": [
        "中文检索问题1（30字以内）",
        "中文检索问题2（30字以内）",
        "中文检索问题3（30字以内）"
    ]
}}"""

        response = await self.llm_critic.ainvoke([
            HumanMessage(content=prompt)
        ])
        result = self._parse_json(response.content, None)
        if result and isinstance(result, dict):
            return result
        return {
            "structured_context": {"原始病例": case_text},
            "complexity": "high",
            "key_risks": [],
            "clinical_questions": ["该患者当前最紧急的临床问题和处置要点"]
        }

    # =========================================================
    # LLM #2 + #3: Proposer + Critic 并行
    # =========================================================

    async def _parallel_propose_and_critique(
        self, context, evidence, all_info, complexity
    ):
        context_str = json.dumps(context, ensure_ascii=False, indent=2)
        evidence_str = evidence if evidence else "未检索到相关证据"
        all_info_str = all_info if all_info else "无"

        proposer_prompt = self._build_proposer_prompt(
            context_str, evidence_str, all_info_str, complexity
        )

        critic_prompt = _CRITIC_TEMPLATE.format(
            context=context_str,
            evidence=evidence_str
        )

        p_task = self.llm_proposer.ainvoke([
            HumanMessage(content=proposer_prompt)
        ])
        c_task = self.llm_critic.ainvoke([
            HumanMessage(content=critic_prompt)
        ])

        p_resp, c_resp = await asyncio.gather(p_task, c_task)
        return p_resp.content, c_resp.content


# ═══════════════════════════════════════════════════════════════
# Proposer：原则驱动 + 动态结构
#
# 第一层：决策身份（1句话）
# 第二层：三条硬性原则（不可违反，但不规定格式）
# 第三层：语言纪律（精简为核心3条+红线4条）
# 第四层：复杂度驱动的结构提示（自适应，由代码注入）
# 其余：模型自由组织
# ═══════════════════════════════════════════════════════════════

_PROPOSER_TEMPLATE = """本输出为ICU当班决策记录。先给立即动作，再给解释。

══════════ 三条决策原则（不可违反）══════════

原则一【先动作后解释】
第一段必须是：当前最危险的问题是什么 + 立即要做什么。

原则二【关键动作绑定触发条件】
任何侵入性操作或高风险决策，必须写明客观触发条件。
格式自由，但必须包含：若【客观指标】→【动作】
例：GCS 5分，已丧失气道保护能力 → 立即经口气管插管。

原则三【点名延误后果】
每个关键风险必须写：不处理会怎样。
不允许只说"存在风险"。

══════════ 语言纪律 ══════════

禁止模糊动词：不允许出现"可考虑""建议进一步""视情况""需要评估"。
禁止确诊语气：使用"考虑""倾向于""不能排除"。
禁止具体药物剂量。

红线（必须主动提及，不允许遗漏）：
- 抗凝决策必须写前提（"在影像排除出血后"）
- 氧疗目标区分COPD（88-92%）与非COPD（>94%）
- 出血转化风险必须主动点名
- 溶栓如涉及，必须核查禁忌症

══════════ {structure_hint} ══════���═══

【患者信息】
{context}

【历史上下文】
{all_info}

【循证证据】
{evidence}

根据病例复杂度和临床实际，自行组织最合适的输出结构。
必须满足三条决策原则和语言纪律。优先级不能乱。"""


# ═══════════════════════════════════════════════════════════════
# Critic：只找被忽视的致命盲区
# ═══════════════════════════════════════════════════════════════

_CRITIC_TEMPLATE = """你是ICU质控专家。

职责：指出最可能被忽视的致命风险。

规则：
- 最多3条
- 每条不超过80字
- 只关注"被忽视的"——显而易见的不需要重复
- 禁止扩展解释、禁止框架、禁止评分

【患者信息】
{context}

【医学证据】
{evidence}

输出：
🔴 [被忽视的致命风险 → 不处理的后果]
🔴 [被忽视的致命风险 → 不处理的后果]
🔴 [被忽视的致命风险 → 不处理的后果]

没有被忽视的致命风险：
✅ 未发现"""