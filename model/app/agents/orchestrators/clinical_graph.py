import logging
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.core.schema import ClinicalState
from app.agents.orchestrators.nodes.intent_node import IntentNode
from app.agents.orchestrators.nodes.analysis_node import AnalysisNode
from app.agents.orchestrators.nodes.retrieve_node import RetrieveNode
from app.agents.orchestrators.nodes.reason_node import ReasonNode
from app.agents.orchestrators.nodes.report_node import ReportNode

logger = logging.getLogger(__name__)


class ClinicalGraphBuilder:
    """临床推理图构建器"""

    def __init__(
        self,
        intent_node: IntentNode,
        analysis_node: AnalysisNode,
        retrieve_node: RetrieveNode,
        reason_node: ReasonNode,
        report_node: ReportNode,
        llm_critic=None,
        report_manager=None,
    ):
        self.intent_node = intent_node
        self.analysis_node = analysis_node
        self.retrieve_node = retrieve_node
        self.reason_node = reason_node
        self.report_node = report_node
        self.llm_critic = llm_critic
        self.report_manager = report_manager

    def build(self):
        """构建并编译临床推理图"""
        graph = StateGraph(ClinicalState)

        # 添加节点
        graph.add_node("intent", self.intent_node.run)
        graph.add_node("reject", self._reject_node)
        graph.add_node("knowledge_answer", self._knowledge_node)
        graph.add_node("analysis", self.analysis_node.run)
        graph.add_node("retrieve", self.retrieve_node.run)
        graph.add_node("reason", self.reason_node.run)
        graph.add_node("generate_report", self.report_node.run)

        # 设置入口点
        graph.set_entry_point("intent")

        # 添加条件边
        graph.add_conditional_edges(
            "intent",
            self._route_intent,
            {
                "irrelevant": "reject",
                "knowledge": "knowledge_answer",
                "consultation": "analysis",
            }
        )

        # 添加边
        graph.add_edge("reject", END)
        graph.add_edge("knowledge_answer", END)
        graph.add_edge("analysis", "retrieve")
        graph.add_edge("retrieve", "reason")
        graph.add_edge("reason", "generate_report")
        graph.add_edge("generate_report", END)

        return graph.compile()

    def _route_intent(self, state: ClinicalState) -> str:
        """路由意图分类结果"""
        t = state.intent_type
        if t in ("consultation", "knowledge"):
            return t
        return "irrelevant"

    async def _reject_node(self, state: ClinicalState) -> dict:
        """拒绝节点"""
        return {"report": "请提供脑卒中医疗临床相关查询，此输入无关。"}

    async def _knowledge_node(self, state: ClinicalState) -> dict:
        """知识回答节点"""
        if not self.llm_critic:
            return {"report": "知识回答服务未就绪"}

        knowledge_prompt = f"""你是三甲医院神经内科主任医师。请基于循证医学知识，直接回答以下脑卒中相关通用问题。

问题：{state.case_text}

回答要求：
- 用中文，简洁专业
- 禁止确诊语气
- 禁止具体剂量
- 如果需要，引用权威指南"""

        messages = [
            SystemMessage(content=self.report_manager.system_role if self.report_manager else "你是一位专业的神经内科医生。"),
            HumanMessage(content=knowledge_prompt),
        ]

        content = ""
        async for chunk in self.llm_critic.astream(messages):
            c = chunk.content if hasattr(chunk, "content") else str(chunk)
            content += c

        return {"report": content}