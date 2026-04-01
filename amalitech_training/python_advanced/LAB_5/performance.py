from __future__ import annotations
"""Benchmark utilities comparing sequential, threaded, and async scraping."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List
from urllib import request as urllib_request
from urllib.error import URLError

from .extractor import extract_all

# Shared blocking fetch — stdlib only, no aiohttp
def _blocking_fetch(url: str) -> Dict[str, Any]:
    """
    Fetch a URL synchronously using urllib.
    This is the blocking version used by sequential and threaded approaches.
    """
    try:
        req = urllib_request.Request(url, headers={"User-Agent": "LAB4-Scraper/1.0"})
        with urllib_request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            return {"url": url, "status": resp.status, "html": html, "error": None}
    except URLError as exc:
        return {"url": url, "status": None, "html": None, "error": str(exc)}
    except Exception as exc:
        return {"url": url, "status": None, "html": None, "error": str(exc)}


# Sequential
def run_sequential(urls: List[str]) -> tuple[List[Dict], float]:
    """
    Fetch and extract one URL at a time.
    CPU sits idle waiting for each network response before the next starts.
    """
    start = time.perf_counter()
    results = [extract_all(_blocking_fetch(url)) for url in urls]
    return results, time.perf_counter() - start

# Threaded
def run_threaded(urls: List[str], max_workers: int = 5) -> tuple[List[Dict], float]:
    """
    Fetch URLs with a thread pool.

    The GIL is released during network I/O, so threads genuinely overlap
    waiting time. This is exactly how LAB_3 used ThreadPoolExecutor for
    I/O-bound file downloads — the same pattern now applied to scraping.

    as_completed() yields futures as they finish rather than in submission
    order, so fast responses are processed immediately.
    """
    start = time.perf_counter()
    results: List[Dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_blocking_fetch, url): url for url in urls}
        for future in as_completed(futures):
            try:
                raw = future.result()
            except Exception as exc:
                url = futures[future]
                raw = {"url": url, "status": None, "html": None, "error": str(exc)}
            results.append(extract_all(raw))
    return results, time.perf_counter() - start

# Async
async def _async_scrape(urls: List[str]) -> List[Dict]:
    """Run the full async pipeline and return enriched results."""
    # Imported locally so sequential/threaded paths do not require async deps at import time.
    from fetcher import fetch_url
    import aiohttp
    async with aiohttp.ClientSession() as session:
        raw = await asyncio.gather(*[fetch_url(session, url) for url in urls])
    return [extract_all(r) for r in raw]


def run_async(urls: List[str]) -> tuple[List[Dict], float]:
    """Run the async scraper synchronously and return results + elapsed time."""
    start = time.perf_counter()
    results = asyncio.run(_async_scrape(urls))
    return results, time.perf_counter() - start

# Runner
def benchmark(urls: List[str]) -> Dict[str, Any]:
    """Run all three approaches and return a timing comparison dict."""
    print(f"\nBenchmarking {len(urls)} URLs...\n")

    _, t_seq = run_sequential(urls)
    print(f"  Sequential : {t_seq:.3f}s")

    _, t_thr = run_threaded(urls)
    print(f"  Threaded   : {t_thr:.3f}s")

    _, t_asy = run_async(urls)
    print(f"  Async      : {t_asy:.3f}s")

    baseline = t_seq if t_seq > 0 else 1.0
    return {
        "urls_count":       len(urls),
        "sequential_s":     round(t_seq, 3),
        "threaded_s":       round(t_thr, 3),
        "async_s":          round(t_asy, 3),
        "threaded_speedup": round(baseline / t_thr, 2) if t_thr else None,
        "async_speedup":    round(baseline / t_asy, 2) if t_asy else None,
    }
