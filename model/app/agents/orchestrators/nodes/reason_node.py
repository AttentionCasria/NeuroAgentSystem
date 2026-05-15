import logging
from typing import Dict
from app.agents.core.schema import ClinicalState
from app.agents.orchestrators.nodes.base import BaseNode

logger = logging.getLogger(__name__)


class ReasonNode(BaseNode):
    """临床推理节点"""

    def __init__(self, qwen_agent):
        self.qwen_agent = qwen_agent

    async def run(self, state: ClinicalState) -> Dict:
        uq = state.user_questions
        logger.info(f"[reason] user_questions count={len(uq)}, items={uq}")
        proposal, critique = await self.qwen_agent._parallel_propose_and_critique(
            state.context,
            state.evidence,
            state.all_info,
            uq,
        )
        logger.info(f"[reason] proposal_len={len(proposal)}, critique_len={len(critique)}")
        return {"proposal": proposal, "critique": critique}