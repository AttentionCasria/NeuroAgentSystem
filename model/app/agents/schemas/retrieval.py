from dataclasses import dataclass
from typing import Optional


@dataclass
class RerankResult:
    index: int
    content: str
    score: float


@dataclass
class RetrievalDocument:
    content: str
    source: str
    page: Optional[int]
    score: float