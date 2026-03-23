"""Custom exceptions for the CSV importer."""


class ImporterError(Exception):
    """Base for all importer errors."""


class FileFormatError(ImporterError):
    """File is missing, unreadable, or not valid UTF-8."""


class MissingFieldError(FileFormatError):
    """A required column is absent in a row."""


class ValidationError(ImporterError):
    """A field value fails a business rule."""


class InvalidEmailError(ValidationError):
    """Email does not match a valid format."""


class DuplicateUserError(ImporterError):
    """user_id already exists in the database."""
