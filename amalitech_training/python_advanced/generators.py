from __future__ import annotations

import itertools
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, List
from .log_parser import LogEntry, parse_line


def read_log_file(path: str | Path) -> Iterator[str]:
    """
    Yield lines from a log file one at a time.
    Never loads the whole file into memory.
    """
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            yield line


def read_multiple_files(*paths: str | Path) -> Iterator[str]:
    """
    Yield lines from several log files as if they were one stream.
    Uses itertools.chain so the files are opened in sequence.
    """
    return itertools.chain.from_iterable(read_log_file(p) for p in paths)


def parse_file(path: str | Path) -> Iterator[LogEntry]:
    """
    Parse a single log file, yielding structured dicts one at a time.
    Skips lines that do not match the expected format.
    """
    for line in read_log_file(path):
        entry = parse_line(line)
        if entry is not None:
            yield entry


class BatchIterator:
    """
    Wrap any iterable and produce fixed-size batches as lists.
    """

    def __init__(self, source: Iterable, size: int = 100):
        self._source = iter(source)
        self._size = size

    def __iter__(self):
        return self

    def __next__(self) -> list:
        batch = list(itertools.islice(self._source, self._size))
        if not batch:
            raise StopIteration
        return batch


def paginate(entries: Iterable[LogEntry], page: int, page_size: int) -> List[LogEntry]:
    """
    Return one page of entries.
    Uses itertools.islice to avoid materialising the full list.
    """
    start = page * page_size
    sliced = itertools.islice(entries, start, start + page_size)
    return list(sliced)


def group_by_status(entries: Iterable[LogEntry]) -> dict[int, list[LogEntry]]:
    """
    Group a sorted iterable of entries by HTTP status code.
    The entries MUST be sorted by status before calling this.

    Returns a plain dict mapping status_code -> [entry, ...].
    """
    sorted_entries = sorted(entries, key=lambda e: e["status"])
    return {
        status: list(group)
        for status, group in itertools.groupby(
            sorted_entries, key=lambda e: e["status"]
        )
    }


def group_by_hour(entries: Iterable[LogEntry]) -> dict[int, list[LogEntry]]:
    """
    Group entries by the hour of their timestamp (0-23).
    Entries without a valid timestamp are skipped.
    """
    valid = (e for e in entries if e.get("timestamp"))
    sorted_entries = sorted(valid, key=lambda e: e["timestamp"].hour)
    return {
        hour: list(group)
        for hour, group in itertools.groupby(
            sorted_entries, key=lambda e: e["timestamp"].hour
        )
    }


def group_by_ip(entries: Iterable[LogEntry]) -> dict[str, list[LogEntry]]:
    """Group entries by originating IP address."""
    sorted_entries = sorted(entries, key=lambda e: e["ip"])
    return {
        ip: list(group)
        for ip, group in itertools.groupby(sorted_entries, key=lambda e: e["ip"])
    }


def take_until_time(
    entries: Iterable[LogEntry], cutoff: datetime
) -> Iterator[LogEntry]:
    """
    Yield entries whose timestamp is before the cutoff.
    Uses itertools.takewhile, so it stops at the first entry that is
    at or after the cutoff (assumes chronological order).
    """
    return itertools.takewhile(
        lambda e: e.get("timestamp") and e["timestamp"] < cutoff,
        entries,
    )


def sliding_window(
    entries: Iterable[LogEntry], size: int
) -> Iterator[tuple[LogEntry, ...]]:
    """
    Yield overlapping windows of `size` entries.
    Useful for detecting request bursts.
    """
    it = iter(entries)
    window = tuple(itertools.islice(it, size))
    if len(window) == size:
        yield window
    for item in it:
        window = window[1:] + (item,)
        yield window
