import logging
import json
from typing import Dict
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from app.agents.core.schema import ClinicalState
from app.agents.orchestrators.nodes.base import BaseNode

logger = logging.getLogger(__name__)

_INTENT_PROMPT = ChatPromptTemplate.from_messages([
    ("human", """你是意图分类专家。请判断以下输入的类型：

- consultation: 具体患者问诊或病例分析（包含患者症状、检查等细节）
- knowledge: 脑卒中通用知识询问（如症状、药品作用、禁忌、预防等，无具体患者细节）
- irrelevant: 非脑卒中医疗相关

输入：{case_text}

输出 JSON：

{{
    "type": "consultation/knowledge/irrelevant",
    "reason": "简要原因"
}}

严格区分：如果有患者具体信息，为consultation；如果是一般性问题，为knowledge；否则irrelevant。""")
])


class IntentNode(BaseNode):
    """意图分类节点"""

    def __init__(self, llm):
        self.chain = _INTENT_PROMPT | llm | StrOutputParser()

    async def run(self, state: ClinicalState) -> Dict:
        content = await self.chain.ainvoke({"case_text": state.case_text})
        result = self._parse_json(content)
        intent_type = result.get("type", "irrelevant")
        logger.info(f"[intent] 分类结果: {intent_type}")
        return {"intent_type": intent_type}

    def _parse_json(self, text: str):
        try:
            return json.loads(text)
        except:
            return {"type": "irrelevant"}
