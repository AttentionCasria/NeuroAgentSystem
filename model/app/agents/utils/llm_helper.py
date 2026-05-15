import logging

from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)


class LLMHelper:

    @staticmethod
    async def ainvoke(llm, system_prompt: str, user_prompt: str):
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])

        return getattr(response, "content", str(response))

    @staticmethod
    def invoke(llm, system_prompt: str, user_prompt: str):
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])

        return getattr(response, "content", str(response))