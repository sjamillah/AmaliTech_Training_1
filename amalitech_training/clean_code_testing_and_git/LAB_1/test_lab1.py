import pytest

from .exceptions import (
        DuplicateUserError,
        FileFormatError,
        ImporterError,
        InvalidEmailError,
        MissingFieldError,
        ValidationError,
    )


class TestExceptions:
    """Tests for the custom exception classes used by the importer."""

    def test_hierarchy(self) -> None:
        """Verify each custom exception inherits from the expected parent class."""
        assert issubclass(FileFormatError,   ImporterError)
        assert issubclass(MissingFieldError,  FileFormatError)
        assert issubclass(ValidationError,   ImporterError)
        assert issubclass(InvalidEmailError,  ValidationError)
        assert issubclass(DuplicateUserError, ImporterError)
 
    def test_base_catches_child(self) -> None:
        """Ensure raising a child exception is caught by the base exception type."""
        with pytest.raises(ImporterError):
            raise DuplicateUserError("already exists")
 
    def test_message_preserved(self) -> None:
        """Confirm the original error message is preserved in the exception string."""
        err = DuplicateUserError("user_id=5")
        assert "5" in str(err)
