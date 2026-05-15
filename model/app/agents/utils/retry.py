import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def retry(
    retries=3,
    delay=1,
    exceptions=(Exception,)
):

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    logger.warning(
                        f"重试 {attempt + 1}/{retries}: {e}"
                    )

                    if attempt == retries - 1:
                        raise

                    time.sleep(delay * (attempt + 1))

        return wrapper

    return decorator