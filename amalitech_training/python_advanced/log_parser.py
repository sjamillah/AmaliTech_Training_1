"""
Log parsing and functional transformation pipeline.

Parses raw log lines into structured dicts, then provides
map/filter/reduce helpers to build readable processing pipelines.
"""

from __future__ import annotations

from datetime import datetime
from functools import reduce
from typing import Callable, Dict, Iterable, Iterator, List, Optional

from .decorators import log_call, timer
from .regex_patterns import (
    LOG_PATTERN,
    TIMESTAMP_PATTERN,
    clean_log_line,
    clean_url,
)

MONTH_MAP = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}

LogEntry = Dict[str, object]


def parse_timestamp(raw: str) -> Optional[datetime]:
    """Convert an timestamp string to a datetime object."""
    m = TIMESTAMP_PATTERN.match(raw)
    if not m:
        return None
    return datetime(
        year=int(m.group("year")),
        month=MONTH_MAP.get(m.group("month"), 1),
        day=int(m.group("day")),
        hour=int(m.group("hour")),
        minute=int(m.group("minute")),
        second=int(m.group("second")),
    )


@log_call
def parse_line(line: str) -> Optional[LogEntry]:
    """
    Parse one log line into a structured dict.
    Returns None if the line does not match the expected format.
    """
    line = clean_log_line(line.strip())
    match = LOG_PATTERN.match(line)
    if not match:
        return None

    data = match.groupdict()
    size_raw = data.get("size", "-")

    return {
        "ip": data["ip"],
        "user": data.get("user", "-"),
        "timestamp_raw": data["timestamp"],
        "timestamp": parse_timestamp(data["timestamp"]),
        "method": data.get("method", ""),
        "url": clean_url(data.get("url", "")),
        "protocol": data.get("protocol", ""),
        "status": int(data["status"]),
        "size": int(size_raw) if size_raw and size_raw != "-" else 0,
        "referer": data.get("referer", "-") or "-",
        "agent": data.get("agent", "-") or "-",
    }


def parse_lines(lines: Iterable[str]) -> Iterator[LogEntry]:
    """Map parse_line over an iterable of strings, dropping unparseable lines."""
    return filter(None, map(parse_line, lines))


def filter_by_status(entries: Iterable[LogEntry], status: int) -> Iterator[LogEntry]:
    """Keep only entries matching an exact HTTP status code."""
    return filter(lambda e: e["status"] == status, entries)


def filter_by_status_range(
    entries: Iterable[LogEntry], low: int, high: int
) -> Iterator[LogEntry]:
    """Keep entries whose status falls within [low, high]."""
    return filter(lambda e: low <= e["status"] <= high, entries)


def filter_by_ip(entries: Iterable[LogEntry], ip: str) -> Iterator[LogEntry]:
    """Keep only entries from a specific IP address."""
    return filter(lambda e: e["ip"] == ip, entries)


def filter_by_method(entries: Iterable[LogEntry], method: str) -> Iterator[LogEntry]:
    """Keep only entries with the given HTTP method (case-insensitive)."""
    method_upper = method.upper()
    return filter(lambda e: e["method"] == method_upper, entries)


def filter_by_time_range(
    entries: Iterable[LogEntry],
    start: datetime,
    end: datetime,
) -> Iterator[LogEntry]:
    """Keep entries whose timestamp falls within [start, end]."""
    return filter(
        lambda e: e["timestamp"] and start <= e["timestamp"] <= end,
        entries,
    )


def extract_field(entries: Iterable[LogEntry], field: str) -> Iterator[object]:
    """Map entries to a single field value."""
    return map(lambda e: e[field], entries)


def total_bytes(entries: Iterable[LogEntry]) -> int:
    """Sum the response sizes across all entries using reduce."""
    return reduce(lambda acc, e: acc + e["size"], entries, 0)


def count_by_status(entries: Iterable[LogEntry]) -> Dict[int, int]:
    """Aggregate entry count per HTTP status code using reduce."""

    def _accumulate(acc: dict, entry: LogEntry) -> dict:
        acc[entry["status"]] = acc.get(entry["status"], 0) + 1
        return acc

    return reduce(_accumulate, entries, {})


def count_by_ip(entries: Iterable[LogEntry]) -> Dict[str, int]:
    """Aggregate request count per IP address using reduce."""

    def _accumulate(acc: dict, entry: LogEntry) -> dict:
        acc[entry["ip"]] = acc.get(entry["ip"], 0) + 1
        return acc

    return reduce(_accumulate, entries, {})


def count_by_url(entries: Iterable[LogEntry]) -> Dict[str, int]:
    """Aggregate request count per URL path using reduce."""

    def _accumulate(acc: dict, entry: LogEntry) -> dict:
        acc[entry["url"]] = acc.get(entry["url"], 0) + 1
        return acc

    return reduce(_accumulate, entries, {})


@timer
def build_pipeline(
    lines: Iterable[str],
    filters: Optional[List[Callable]] = None,
) -> List[LogEntry]:
    """
    Parse lines and apply an optional list of filter functions.

    Each filter in the list must accept an iterable of LogEntry
    and return an iterable of LogEntry.

    Example:
        build_pipeline(
            lines,
            filters=[
                lambda entries: filter_by_status(entries, 200),
                lambda entries: filter_by_method(entries, "GET"),
            ]
        )
    """
    entries: Iterable[LogEntry] = parse_lines(lines)
    for f in filters or []:
        entries = f(entries)
    return list(entries)
