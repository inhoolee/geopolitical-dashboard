"""Exponential-backoff retry decorator for HTTP extractors."""

import functools
import logging
import time
from typing import Callable, Type

logger = logging.getLogger(__name__)


def retry(
    max_attempts: int = 4,
    backoff_base: float = 2.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        raise
                    wait = backoff_base ** (attempt - 1)
                    logger.warning(
                        "%s failed (attempt %d/%d): %s – retrying in %.1fs",
                        fn.__name__, attempt, max_attempts, exc, wait,
                    )
                    time.sleep(wait)

        return wrapper

    return decorator
