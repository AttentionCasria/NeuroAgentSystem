from dataclasses import dataclass, field
from typing import Optional, List, Any, TypeVar, Generic

T = TypeVar('T')


@dataclass
class Result(Generic[T]):
    """统一结果封装，替代裸值返回"""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @classmethod
    def ok(cls, data: T, metadata: dict = None) -> 'Result[T]':
        return cls(success=True, data=data, metadata=metadata or {})

    @classmethod
    def fail(cls, error: str, metadata: dict = None) -> 'Result[T]':
        return cls(success=False, error=error, metadata=metadata or {})


@dataclass
class RetrievalResult:
    """检索结果封装"""
    success: bool
    documents: List[dict]
    query: str = ""
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)
