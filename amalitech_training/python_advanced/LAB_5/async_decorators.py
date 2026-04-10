from __future__ import annotations
"""Async utility decorators for retry and rate limiting behavior."""

import asyncio
import functools
import logging
import time

logger = logging.getLogger(__name__)


def retry(max_attempts: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """
    Retry a failing async function up to max_attempts times.
    Wait time doubles after each failure (exponential back-off).
    Raises the original exception after the final attempt.
    """

    def decorator(func):
        """Wrap an async callable with retry behavior."""
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            wait = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        logger.error(
                            "retry | %s failed after %d attempts: %s",
                            func.__name__,
                            max_attempts,
                            exc,
                        )
                        raise
                    logger.warning(
                        "retry | %s attempt %d failed, retrying in %.1fs",
                        func.__name__,
                        attempt,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    wait *= 2

        return wrapper

    return decorator


def rate_limit(calls_per_second: float = 2.0):
    """
    Throttle an async function to at most calls_per_second calls per second.
    A shared asyncio.Lock serialises the timing check across concurrent callers.
    """
    min_interval = 1.0 / calls_per_second
    lock = asyncio.Lock()
    last_called: list[float] = [0.0]

    def decorator(func):
        """Wrap an async callable with a minimum interval between calls."""
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            async with lock:
                gap = time.monotonic() - last_called[0]
                if gap < min_interval:
                    await asyncio.sleep(min_interval - gap)
                last_called[0] = time.monotonic()
            return await func(*args, **kwargs)

        return wrapper

    return decorator
