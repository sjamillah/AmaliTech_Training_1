"""Main entry point for the log file analyzer tool.

Provides CLI to parse and analyze Apache/Nginx access logs, generating
detailed reports on requests, errors, top IPs/URLs, and more. Supports
batch processing with example data or real log files.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from .analytics import format_report, generate_report
from .generators import BatchIterator, group_by_hour, parse_file

SAMPLE_LOGS = [
    '192.168.1.1 - - [10/Oct/2023:08:00:01 -0700] "GET /index.html HTTP/1.1" 200 1024 "-" "Mozilla/5.0"',
    '192.168.1.2 - - [10/Oct/2023:08:00:05 -0700] "POST /login HTTP/1.1" 200 512 "-" "curl/7.68"',
    '10.0.0.5 - - [10/Oct/2023:08:01:10 -0700] "GET /missing HTTP/1.1" 404 128 "-" "Mozilla/5.0"',
    '10.0.0.5 - - [10/Oct/2023:08:01:15 -0700] "GET /admin HTTP/1.1" 403 64 "-" "Mozilla/5.0"',
    '172.16.0.1 - - [10/Oct/2023:09:00:00 -0700] "GET /api/data HTTP/1.1" 500 256 "-" "Python-requests"',
    '192.168.1.1 - - [10/Oct/2023:09:15:00 -0700] "GET /style.css HTTP/1.1" 200 2048 "-" "Mozilla/5.0"',
    '192.168.1.3 - - [10/Oct/2023:10:00:00 -0700] "DELETE /resource/1 HTTP/1.1" 204 0 "-" "curl/7.68"',
    '192.168.1.1 - - [10/Oct/2023:10:05:00 -0700] "GET /index.html HTTP/1.1" 304 0 "-" "Mozilla/5.0"',
    '10.0.0.9 - - [10/Oct/2023:11:00:00 -0700] "GET /crash HTTP/1.1" 503 128 "-" "Mozilla/5.0"',
    '192.168.1.2 - - [10/Oct/2023:11:30:00 -0700] "PUT /api/update HTTP/1.1" 200 768 "-" "Python-requests"',
]


def write_sample_file(path: Path) -> None:
    """Write sample log lines to a file."""
    path.write_text("\n".join(SAMPLE_LOGS) + "\n", encoding="utf-8")


def process_file(log_path: Path) -> None:
    """Parse a log file and print a full analytics report."""
    print(f"\nProcessing: {log_path}\n")

    # Collect entries via generator (memory-efficient)
    entries = list(parse_file(log_path))
    if not entries:
        print("No parseable log entries found.")
        return

    # Generate and display report
    report = generate_report(entries)
    print(format_report(report))

    # Group by hour using itertools.groupby
    by_hour = group_by_hour(entries)
    print("\n  Requests by hour:")
    for hour in sorted(by_hour):
        print(f"    {hour:02d}:00  ->  {len(by_hour[hour])} requests")

    # Show batch processing
    print(f"\n  Batch processing ({len(entries)} entries in batches of 3):")
    for i, batch in enumerate(BatchIterator(parse_file(log_path), size=3)):
        print(f"    Batch {i + 1}: {len(batch)} entries")


def run_demo() -> None:
    """Run against generated sample data."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".log", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write("\n".join(SAMPLE_LOGS) + "\n")
        tmp_path = Path(tmp.name)

    try:
        process_file(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Log File Analyzer - Apache/Nginx access log parser"
    )
    parser.add_argument(
        "log_file",
        nargs="?",
        help="Path to an Apache/Nginx access log file. Omit to run demo.",
    )
    args = parser.parse_args()

    if args.log_file:
        path = Path(args.log_file)
        if not path.exists():
            print(f"Error: file not found: {path}", file=sys.stderr)
            sys.exit(1)
        process_file(path)
    else:
        print("No file provided. Running demo with sample data...")
        run_demo()


if __name__ == "__main__":
    main()
