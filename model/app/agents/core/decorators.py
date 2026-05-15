import functools
import time
import logging
from typing import Callable, Type, Tuple, Any

logger = logging.getLogger(__name__)


def retry(
    max_retries: int = 2,
    delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    rate_limit_key: str = "RateQuota"
):
    """自动重试装饰器，支持限流检测"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    err_str = str(e)
                    if rate_limit_key in err_str and attempt < max_retries:
                        wait = delay * (attempt + 1)
                        logger.warning(
                            f"重试 {func.__name__}: {wait}s 后重试 ({attempt+1}/{max_retries})"
                        )
                        time.sleep(wait)
                        last_exc = e
                        continue
                    raise
            raise last_exc
        return wrapper
    return decorator


def timeit(func: Callable) -> Callable:
    """计时装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"{func.__name__} 执行耗时: {elapsed:.2f}s")
        return result
    return wrapper
