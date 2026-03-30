import time
import logging
from functools import wraps, lru_cache

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def timer(func):
    """Measure and log how long a function takes to run"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info("timer | %s finished in %.4fs", func.__name__, elapsed)
        return result

    return wrapper


def log_call(func):
    """Log each call with argument summary and return value type"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        arg_summary = ", ".join(
            [repr(a)[:40] for a in args]
            + [f"{k}={repr(v)[:40]}" for k, v in kwargs.items()]
        )
        logger.debug("call | %s(%s)", func.__name__, arg_summary)
        result = func(*args, **kwargs)
        logger.debug("return | %s -> %s", func.__name__, type(result).__name__)
        return result

    return wrapper


def cache(maxsize=128):
    """
    Parameterised decorator that wraps functools.lru_cache.

    Usage:
        @cache(maxsize=256)
        def expensive(key): ...

        @cache()          # default maxsize=128
        def also_cached(x): ...
    """

    def decorator(func):
        cached_func = lru_cache(maxsize=maxsize)(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return cached_func(*args, **kwargs)

        # Expose cache_info and cache_clear so callers can inspect/reset
        wrapper.cache_info = cached_func.cache_info
        wrapper.cache_clear = cached_func.cache_clear
        return wrapper

    return decorator
