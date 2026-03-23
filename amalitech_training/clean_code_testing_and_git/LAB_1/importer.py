"""CSV import orchestration for parsing, validation, and persistence."""

import logging
from dataclasses import dataclass
from pathlib import Path
 
from .exceptions import (
    DuplicateUserError, InvalidEmailError, MissingFieldError, ValidationError,
)
from .parser import CsvParser
from .repository import JsonRepository
from .validator import CsvValidator
 
logger = logging.getLogger(__name__)
 
 
@dataclass
class ImportResult:
    """Tracks import outcomes for imported, skipped, and errored rows."""

    imported: int = 0
    skipped:  int = 0
    errors:   int = 0
 
    def __str__(self) -> str:
        """Return a readable summary of import results."""
        return f"Imported: {self.imported}  Skipped: {self.skipped}  Errors: {self.errors}"
 
 
class CsvImporter:
    """Runs parser -> validator -> repository for each CSV row."""
 
    def __init__(
        self,
        parser: CsvParser,
        validator: CsvValidator,
        repository: JsonRepository,
    ) -> None:
        """Initialize importer dependencies for parsing, validation, and storage."""
        self._parser = parser
        self._validator = validator
        self._repository = repository
 
    def run(self, path: Path) -> ImportResult:
        """Import all rows from path and return a summary.
 
        Raises:
            FileFormatError: if the source file cannot be opened or read.
        """
        result = ImportResult()
        logger.info("Starting import: %s", path)
 
        for n, row in enumerate(self._parser.parse(path), start=2):
            try:
                user = self._validator.validate(row)
                self._repository.save(user)
            except MissingFieldError as e:
                result.skipped += 1
                logger.warning("Row %d skipped — %s", n, e)
            except InvalidEmailError as e:
                result.errors += 1
                logger.error("Row %d error — %s", n, e)
            except ValidationError as e:
                result.skipped += 1
                logger.warning("Row %d skipped — %s", n, e)
            except DuplicateUserError as e:
                result.skipped += 1
                logger.warning("Row %d skipped — %s", n, e)
            else:
                result.imported += 1
                logger.info("Imported user_id=%s", user.user_id)
 
        logger.info("%s", result)
        return result
