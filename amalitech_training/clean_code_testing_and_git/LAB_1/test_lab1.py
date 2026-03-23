import pytest

from .exceptions import (
        DuplicateUserError,
        FileFormatError,
        ImporterError,
        InvalidEmailError,
        MissingFieldError,
        ValidationError,
    )
from .models import User


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


class TestUser:
    """Tests for the User model behavior and representation."""

    def test_stores_fields(self) -> None:
        """Verify a user instance stores constructor values correctly."""
        u = User(user_id=1, name="Joshua Alana", email="j@example.com")
        assert u.user_id == 1
        assert u.name == "Joshua Alana"
        assert u.email == "j@example.com"
 
    def test_equality(self) -> None:
        """Ensure two users with the same field values compare as equal."""
        u1 = User(1, "Joshua", "j@example.com")
        u2 = User(1, "Joshua", "j@example.com")
        assert u1 == u2
 
    def test_repr_contains_name(self) -> None:
        """Confirm the string representation includes the user's name."""
        u = User(1, "Joshua", "j@example.com")
        assert "Joshua" in repr(u)

