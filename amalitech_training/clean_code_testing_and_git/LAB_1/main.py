"""Command-line entry point for running the CSV importer."""

import argparse
import logging
import sys
from pathlib import Path

from .exceptions import FileFormatError
from .importer import CsvImporter
from .parser import CsvParser
from .repository import JsonRepository
from .validator import CsvValidator

DEFAULT_DB = Path("db.json")


def main(argv: list[str] | None = None) -> int:
    """Run the CLI import command and return a process-style exit code."""
    p = argparse.ArgumentParser(description="Import users from a CSV file")
    p.add_argument("csv_file", type=Path)
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)-7s] %(message)s",
        stream=sys.stdout,
    )

    imp = CsvImporter(
        parser=CsvParser(),
        validator=CsvValidator(),
        repository=JsonRepository(args.db),
    )
    try:
        print(imp.run(args.csv_file))
        return 0
    except FileFormatError as e:
        logging.error("%s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
