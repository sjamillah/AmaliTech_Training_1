from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from .async_decorators import rate_limit, retry

logger = logging.getLogger(__name__)


@retry(max_attempts=3, delay=0.5)
@rate_limit(calls_per_second=2.0)
async def fetch_url(session: Any, url: str) -> Dict[str, Any]:
    """
    Fetch a single URL. Returns a result dict with keys:
        url, status, html, error
    html is None for non-200 responses or when an exception occurs.
    """
    timeout: Any = None
    try:
        import aiohttp

        timeout = aiohttp.ClientTimeout(total=10)
    except ModuleNotFoundError:
        # Allow tests that use mocked sessions to run even when aiohttp is missing.
        timeout = None
    try:
        request_kwargs = {"timeout": timeout} if timeout is not None else {}
        async with session.get(url, **request_kwargs) as response:
            html = await response.text() if response.status == 200 else None
            logger.info("fetched %s -> %d", url, response.status)
            return {"url": url, "status": response.status, "html": html, "error": None}
    except Exception as exc:
        logger.warning("fetch error %s: %s", url, exc)
        return {"url": url, "status": None, "html": None, "error": str(exc)}


async def fetch_all(urls: List[str]) -> List[Dict[str, Any]]:
    """Fetch all URLs concurrently — one shared session, asyncio.gather()."""
    if not urls:
        return []
    async with _client_session_or_dummy() as session:
        return await asyncio.gather(*[fetch_url(session, url) for url in urls])


async def fetch_with_tasks(urls: List[str]) -> List[Dict[str, Any]]:
    """Same as fetch_all but wraps each coroutine in an explicit Task."""
    if not urls:
        return []
    async with _client_session_or_dummy() as session:
        tasks = [asyncio.create_task(fetch_url(session, url)) for url in urls]
        return await asyncio.gather(*tasks)


async def fetch_with_timeout(url: str, timeout: float = 5.0) -> Dict[str, Any]:
    """Fetch one URL; cancel and return error dict if it exceeds timeout."""
    async with _client_session_or_dummy() as session:
        coro = fetch_url(session, url)
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            coro.close()
            return {"url": url, "status": None, "html": None, "error": "timeout"}


class _DummySession:
    """Fallback session used only when aiohttp is unavailable."""

    def get(self, *_args: Any, **_kwargs: Any) -> Any:
        raise ModuleNotFoundError("No module named 'aiohttp'")


@asynccontextmanager
async def _client_session_or_dummy() -> Any:
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            yield session
    except ModuleNotFoundError:
        yield _DummySession()
