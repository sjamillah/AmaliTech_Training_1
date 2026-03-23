import csv
import logging
from pathlib import Path
from typing import Generator
 
from .exceptions import FileFormatError
 
logger = logging.getLogger(__name__)
 
 
class CsvParser:
    """Opens a CSV file and yields one raw dict per data row."""
 
    def parse(self, path: Path) -> Generator[dict[str, str], None, None]:
        """
        Yield each row as a dict keyed by column name.
 
        Raises:
            FileFormatError: file not found or not readable.
        """
        try:
            with open(path, newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    yield dict(row)
        except FileNotFoundError as exc:
            raise FileFormatError(f"File not found: {path}") from exc
        except (OSError, UnicodeDecodeError) as exc:
            raise FileFormatError(f"Cannot read file: {path}") from exc
