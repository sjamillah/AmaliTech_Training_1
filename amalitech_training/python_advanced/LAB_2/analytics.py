from __future__ import annotations

import functools
from typing import Dict, List

from .decorators import cache, log_call, timer
from .log_parser import (
    LogEntry,
    count_by_ip,
    count_by_status,
    count_by_url,
    filter_by_method,
    filter_by_status_range,
    total_bytes,
)

filter_errors = functools.partial(filter_by_status_range, low=400, high=599)
filter_client_errors = functools.partial(filter_by_status_range, low=400, high=499)
filter_server_errors = functools.partial(filter_by_status_range, low=500, high=599)
filter_success = functools.partial(filter_by_status_range, low=200, high=299)
filter_get = functools.partial(filter_by_method, method="GET")
filter_post = functools.partial(filter_by_method, method="POST")


@timer
@log_call
def top_n_ips(entries: List[LogEntry], n: int = 10) -> List[tuple[str, int]]:
    """Return the n IPs with the most requests, sorted descending."""
    counts = count_by_ip(entries)
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]


@timer
@log_call
def top_n_urls(entries: List[LogEntry], n: int = 10) -> List[tuple[str, int]]:
    """Return the n most requested URL paths, sorted descending."""
    counts = count_by_url(entries)
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]


@timer
@log_call
def status_breakdown(entries: List[LogEntry]) -> Dict[int, int]:
    """Return request count per HTTP status code."""
    return count_by_status(entries)


@timer
@log_call
def error_rate(entries: List[LogEntry]) -> float:
    """Return the fraction of requests that resulted in a 4xx or 5xx."""
    if not entries:
        return 0.0
    errors = list(filter_errors(entries))
    return len(errors) / len(entries)


@timer
@log_call
def bandwidth_used(entries: List[LogEntry]) -> int:
    """Total bytes transferred across all entries."""
    return total_bytes(entries)


@cache(maxsize=64)
def _cached_top_urls(urls_tuple: tuple, n: int) -> List[tuple[str, int]]:
    """
    Cached version of top_n_urls.
    Accepts a tuple of URL strings so the argument is hashable for lru_cache.
    """
    from functools import reduce as _reduce

    def _accumulate(acc: dict, url: str) -> dict:
        acc[url] = acc.get(url, 0) + 1
        return acc

    counts = _reduce(_accumulate, urls_tuple, {})
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]


def cached_top_urls(entries: List[LogEntry], n: int = 10) -> List[tuple[str, int]]:
    """Call the cached URL-count helper (converts list to a hashable tuple of URLs)."""
    return _cached_top_urls(tuple(e["url"] for e in entries), n)


@timer
def generate_report(entries: List[LogEntry]) -> Dict:
    """
    Build a full analytics report as a plain dict.

    Keys:
        total_requests, total_bytes, error_rate,
        status_breakdown, top_ips, top_urls,
        error_entries (4xx/5xx), server_errors (5xx)
    """
    error_list = list(filter_errors(entries))
    server_error_list = list(filter_server_errors(entries))

    return {
        "total_requests": len(entries),
        "total_bytes": bandwidth_used(entries),
        "error_rate": round(error_rate(entries), 4),
        "status_breakdown": status_breakdown(entries),
        "top_ips": top_n_ips(entries, n=5),
        "top_urls": top_n_urls(entries, n=5),
        "error_count": len(error_list),
        "server_error_count": len(server_error_list),
    }


def format_report(report: Dict) -> str:
    """Render a report dict as a human-readable string."""
    lines = [
        "=" * 50,
        "  LOG FILE ANALYTICS REPORT",
        "=" * 50,
        f"  Total requests  : {report['total_requests']:,}",
        f"  Total bytes     : {report['total_bytes']:,}",
        f"  Error rate      : {report['error_rate'] * 100:.2f}%",
        f"  4xx/5xx errors  : {report['error_count']:,}",
        f"  5xx errors      : {report['server_error_count']:,}",
        "",
        "  Status breakdown:",
    ]
    for code, count in sorted(report["status_breakdown"].items()):
        lines.append(f"    {code}  ->  {count:,} requests")

    lines += ["", "  Top 5 IPs:"]
    for ip, count in report["top_ips"]:
        lines.append(f"    {ip:<20}  {count:,} requests")

    lines += ["", "  Top 5 URLs:"]
    for url, count in report["top_urls"]:
        lines.append(f"    {url:<40}  {count:,} requests")

    lines.append("=" * 50)
    return "\n".join(lines)
