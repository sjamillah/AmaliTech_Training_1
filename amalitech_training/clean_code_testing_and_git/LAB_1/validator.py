"""Validation utilities for converting raw CSV rows into User objects."""

import re
import logging

from .exceptions import (
    InvalidEmailError,
    MissingFieldError,
    ValidationError,
)
from .models import User

logger = logging.getLogger(__name__)

# Required input columns for each imported CSV row.
REQUIRED = ("user_id", "name", "email")
# Simple email pattern used for basic format validation.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CsvValidator:
    """Validates a raw CSV row and returns a User."""

    def validate(self, row: dict[str, str]) -> User:
        """Check all fields and return User on success.

        Raises:
            MissingFieldError: required column absent.
            ValidationError: value fails a rule.
            InvalidEmailError: email format is wrong.
        """
        for f in REQUIRED:
            if f not in row:
                raise MissingFieldError(f"Missing field: {f}")

        uid = self._parse_id(row["user_id"])
        name = row["name"].strip()
        if not name:
            raise ValidationError("name cannot be blank")
        email = self._parse_email(row["email"])
        return User(user_id=uid, name=name, email=email)

    def _parse_id(self, value: str) -> int:
        """Parse and validate user_id as a positive integer."""
        try:
            n = int(value)
        except ValueError:
            raise ValidationError(f"user_id must be an integer, got: {value!r}")
        if n <= 0:
            raise ValidationError(f"user_id must be > 0, got: {n}")
        return n

    def _parse_email(self, value: str) -> str:
        """Normalize and validate email text using the configured regex."""
        if not EMAIL_RE.match(value.strip()):
            raise InvalidEmailError(f"Invalid email: {value!r}")
        return value.strip().lower()
