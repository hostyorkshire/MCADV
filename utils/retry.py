import time
import functools
import logging
from typing import Callable, Tuple, Type

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """Decorator that retries a function with exponential back-off on failure."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = 1.0
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        logger.warning(
                            "Attempt %d/%d for %s failed: %s – retrying in %.1fs",
                            attempt,
                            max_attempts,
                            func.__name__,
                            exc,
                            delay,
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            "All %d attempts for %s failed: %s",
                            max_attempts,
                            func.__name__,
                            exc,
                        )
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator
