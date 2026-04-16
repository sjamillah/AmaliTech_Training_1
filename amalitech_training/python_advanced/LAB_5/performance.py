from __future__ import annotations
"""Benchmark utilities comparing sequential, threaded, and async scraping."""

import asyncio
import json
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
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


def run_process_pool(
    urls: List[str], max_workers: int = 4
) -> tuple[List[Dict], float]:
    """
    Fetch URLs with a process pool.

    Note: for this I/O-bound workload, process pools are usually slower than
    threads/async because of process startup and IPC overhead. It is still
    useful as a side-by-side comparison point.
    """
    start = time.perf_counter()
    results: List[Dict] = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
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
    # Preferred path uses aiohttp + shared async session.
    try:
        # Imported locally so sequential/threaded paths do not require async deps at import time.
        from .fetcher import fetch_url
        import aiohttp

        async with aiohttp.ClientSession() as session:
            raw = await asyncio.gather(*[fetch_url(session, url) for url in urls])
        return [extract_all(r) for r in raw]
    except ModuleNotFoundError:
        # Fallback when aiohttp is unavailable: keep async orchestration by
        # delegating blocking fetches to worker threads.
        raw = await asyncio.gather(*[asyncio.to_thread(_blocking_fetch, url) for url in urls])
        return [extract_all(r) for r in raw]


def run_async(urls: List[str]) -> tuple[List[Dict], float]:
    """Run the async scraper synchronously and return results + elapsed time."""
    start = time.perf_counter()
    results = asyncio.run(_async_scrape(urls))
    return results, time.perf_counter() - start

# Runner
def benchmark(urls: List[str], include_process_pool: bool = False) -> Dict[str, Any]:
    """
    Run timing comparisons and return a summary dict.

    By default compares sequential, threaded, and async.
    Set include_process_pool=True to also benchmark process-pool execution.
    """
    print(f"\nBenchmarking {len(urls)} URLs...\n")

    _, t_seq = run_sequential(urls)
    print(f"  Sequential : {t_seq:.3f}s")

    _, t_thr = run_threaded(urls)
    print(f"  Threaded   : {t_thr:.3f}s")

    _, t_asy = run_async(urls)
    print(f"  Async      : {t_asy:.3f}s")

    t_proc = None
    if include_process_pool:
        _, t_proc = run_process_pool(urls)
        print(f"  Process    : {t_proc:.3f}s")

    baseline = t_seq if t_seq > 0 else 1.0
    report = {
        "generated_at":    datetime.now().isoformat(timespec="seconds"),
        "urls_count":       len(urls),
        "sequential_s":     round(t_seq, 3),
        "threaded_s":       round(t_thr, 3),
        "async_s":          round(t_asy, 3),
        "threaded_speedup": round(baseline / t_thr, 2) if t_thr else None,
        "async_speedup":    round(baseline / t_asy, 2) if t_asy else None,
    }

    if include_process_pool:
        report["process_pool_s"] = round(t_proc, 3) if t_proc is not None else None
        report["process_pool_speedup"] = (
            round(baseline / t_proc, 2) if t_proc else None
        )

    return report


def save_benchmark_report(
    report: Dict[str, Any], output_dir: Path | str = "output"
) -> Path:
    """Save benchmark report JSON to output directory and return file path."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"benchmark_{ts}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def save_benchmark_graphs(
    report: Dict[str, Any], output_dir: Path | str = "output"
) -> Dict[str, Path]:
    """
    Save benchmark graphs as PNG files and return a path mapping.

    If matplotlib is unavailable, returns an empty dict.
    """
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError:
        return {}

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    timing_data = {
        "sequential": report.get("sequential_s"),
        "threaded": report.get("threaded_s"),
        "async": report.get("async_s"),
    }
    if report.get("process_pool_s") is not None:
        timing_data["process_pool"] = report.get("process_pool_s")

    timing_pairs = [
        (label, value)
        for label, value in timing_data.items()
        if isinstance(value, (int, float))
    ]
    if not timing_pairs:
        return {}

    # Lower runtime is better; sort ascending to make ranking obvious.
    timing_pairs.sort(key=lambda x: x[1])
    labels = [label for label, _ in timing_pairs]
    times = [value for _, value in timing_pairs]

    color_map = {
        "sequential": "#9AA5B1",
        "threaded": "#2A9D8F",
        "async": "#1D4ED8",
        "process_pool": "#F59E0B",
    }
    colors = [color_map.get(label, "#6B7280") for label in labels]

    plt.style.use("ggplot")

    timings_path = out_dir / f"benchmark_timings_{ts}.png"
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(labels, times, color=colors)
    ax.set_title("Benchmark Runtime Comparison (lower is better)")
    ax.set_xlabel("Seconds")
    ax.grid(axis="x", linestyle="--", alpha=0.35)

    max_time = max(times)
    x_pad = max(0.05, max_time * 0.03)
    for bar, value in zip(bars, times):
        ax.text(
            value + x_pad,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.3f}s",
            va="center",
            fontsize=10,
        )

    ax.set_xlim(0, max_time + x_pad * 7)
    fig.tight_layout()
    fig.savefig(timings_path, dpi=150)
    plt.close(fig)

    speedup_data = {
        "threaded": report.get("threaded_speedup"),
        "async": report.get("async_speedup"),
    }
    if report.get("process_pool_speedup") is not None:
        speedup_data["process_pool"] = report.get("process_pool_speedup")

    speedup_pairs = [
        (label, value)
        for label, value in speedup_data.items()
        if isinstance(value, (int, float))
    ]
    speedup_pairs.sort(key=lambda x: x[1], reverse=True)

    paths = {"timings": timings_path}
    if speedup_pairs:
        s_labels = [label for label, _ in speedup_pairs]
        s_vals = [value for _, value in speedup_pairs]
        s_colors = [color_map.get(label, "#6B7280") for label in s_labels]

        speedup_path = out_dir / f"benchmark_speedups_{ts}.png"
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(s_labels, s_vals, color=s_colors)
        ax.set_title("Speedup vs Sequential Baseline")
        ax.set_ylabel("Speedup (x)")
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        ax.axhline(1.0, color="#374151", linewidth=1.2, linestyle="--")
        ax.text(-0.45, 1.03, "1.0x baseline", color="#374151", fontsize=9)

        max_speedup = max(s_vals)
        y_pad = max(0.05, max_speedup * 0.03)
        for bar, value in zip(bars, s_vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + y_pad,
                f"{value:.2f}x",
                ha="center",
                va="bottom",
                fontsize=10,
            )

        ax.set_ylim(0, max_speedup + y_pad * 5)
        fig.tight_layout()
        fig.savefig(speedup_path, dpi=150)
        plt.close(fig)
        paths["speedups"] = speedup_path

    return paths
