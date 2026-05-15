from langchain_core.messages import HumanMessage, SystemMessage


class EvidenceSynthesisService:

    FALLBACK_PROMPT = """你是循证医学专家。

临床问题：{question}

医学证据：
{evidence}

请进行循证医学总结。"""

    def __init__(
        self,
        llm,
        prompt_manager=None
    ):
        self.llm = llm
        self.prompts = prompt_manager

    def synthesize(
        self,
        question: str,
        evidence: str
    ) -> str:

        prompt = None

        if self.prompts:
            prompt = self.prompts.get(
                "evidence_synthesis",
                question=question,
                evidence=evidence
            )

        if not prompt:
            prompt = self.FALLBACK_PROMPT.format(
                question=question,
                evidence=evidence
            )

        response = self.llm.invoke([
            SystemMessage(content="你是循证医学专家"),
            HumanMessage(content=prompt)
        ])

        return response.content