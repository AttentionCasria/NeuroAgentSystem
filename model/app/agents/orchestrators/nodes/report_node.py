import logging
import json
from typing import Dict
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.core.schema import ClinicalState
from app.agents.orchestrators.nodes.base import BaseNode
from app.agents.constants import MAX_PROPOSAL_CHARS, MAX_CRITIQUE_CHARS
from app.agents.utils.text_utils import truncate_text

logger = logging.getLogger(__name__)


class ReportNode(BaseNode):
    """报告生成节点"""

    def __init__(self, llm_proposer, report_manager):
        self.llm_proposer = llm_proposer
        self.report_manager = report_manager

    async def run(self, state: ClinicalState) -> Dict:
        if state.user_questions:
            return {"report": state.proposal}

        context_str = (
            json.dumps(state.context, ensure_ascii=False, indent=2)
            if isinstance(state.context, dict) else str(state.context)
        )
        report_template = self.report_manager.get_template(state.report_mode)
        prompt_text = report_template.format(
            context=context_str,
            all_info=state.all_info or "无历史记录",
            evidence=state.evidence or "未检索到相关证据",
            proposal=truncate_text(state.proposal, MAX_PROPOSAL_CHARS) or "无",
            critique=truncate_text(state.critique, MAX_CRITIQUE_CHARS) or "无批判意见",
        )
        messages = [
            SystemMessage(content=self.report_manager.system_role),
            HumanMessage(content=prompt_text),
        ]
        report = ""
        async for chunk in self.llm_proposer.astream(messages):
            c = chunk.content if hasattr(chunk, "content") else str(chunk)
            report += c
        return {"report": report}