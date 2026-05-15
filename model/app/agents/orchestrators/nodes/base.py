from abc import ABC, abstractmethod
from typing import Dict, Any
from app.agents.core.schema import ClinicalState


class BaseNode(ABC):
    """节点基类"""

    @abstractmethod
    async def run(self, state: ClinicalState) -> Dict[str, Any]:
        """
        执行节点逻辑

        Args:
            state: 当前状态

        Returns:
            状态更新字典
        """
        pass
