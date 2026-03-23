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
from pathlib import Path
from .parser import CsvParser
from .validator import CsvValidator


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


@pytest.fixture
def valid_csv(tmp_path: Path) -> Path:
    """Create a temporary CSV file with two valid user rows."""
    p = tmp_path / "users.csv"
    p.write_text("user_id,name,email\n1,Joshua,j@ex.com\n2,Lynn,l@ex.com")
    return p
 

class TestCsvParser:
    """Tests for CSV parsing behavior and file handling edge cases."""

    def test_yields_correct_row_count(self, valid_csv: Path) -> None:
        """Ensure parsing a valid file yields the expected number of rows."""
        rows = list(CsvParser().parse(valid_csv))
        assert len(rows) == 2
 
    def test_row_has_correct_values(self, valid_csv: Path) -> None:
        """Verify parsed row dictionaries contain correct field values."""
        row = list(CsvParser().parse(valid_csv))[0]
        assert row["user_id"] == "1"
        assert row["name"] == "Joshua"
 
    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Confirm parsing a missing CSV path raises FileFormatError."""
        with pytest.raises(FileFormatError):
            list(CsvParser().parse(tmp_path / "nope.csv"))
 
    def test_empty_body_yields_nothing(self, tmp_path: Path) -> None:
        """Ensure a header-only CSV produces no parsed data rows."""
        p = tmp_path / "e.csv"
        p.write_text("user_id,name,email\n")
        assert list(CsvParser().parse(p)) == []
 
    @pytest.mark.parametrize("data,expected", [
        ("1,A,a@b.com", 1),
        ("1,A,a@b.com\n2,B,b@b.com", 2),
        ("", 0),
    ])
    def test_row_count(self, tmp_path: Path, data: str, expected: int) -> None:
        """Check row counts across different CSV body inputs."""
        p = tmp_path / "t.csv"
        p.write_text(f"user_id,name,email\n{data}")
        assert len(list(CsvParser().parse(p))) == expected


class TestCsvValidator:
    """Tests for CSV row validation rules and expected exceptions."""

    def setup_method(self) -> None:
        """Create a fresh validator instance for each test."""
        self.v = CsvValidator()
 
    def test_valid_row_returns_user(self) -> None:
        """Ensure a valid row is converted into a User object."""
        u = self.v.validate({"user_id":"1","name":"Joshua","email":"j@ex.com"})
        assert u.user_id == 1 and u.name == "Joshua"
 
    @pytest.mark.parametrize("field", ["user_id", "name", "email"])
    def test_missing_field_raises(self, field: str) -> None:
        """Verify that removing any required field raises MissingFieldError."""
        row = {"user_id":"1","name":"Joshua","email":"j@ex.com"}
        del row[field]
        with pytest.raises(MissingFieldError):
            self.v.validate(row)
 
    @pytest.mark.parametrize("bad", ["abc", "0", "-1", ""])
    def test_bad_user_id_raises(self, bad: str) -> None:
        """Confirm invalid user_id values raise ValidationError."""
        with pytest.raises(ValidationError):
            self.v.validate({"user_id":bad,"name":"J","email":"j@ex.com"})
 
    def test_blank_name_raises(self) -> None:
        """Ensure blank or whitespace-only names are rejected."""
        with pytest.raises(ValidationError):
            self.v.validate({"user_id":"1","name":"  ","email":"j@ex.com"})
 
    @pytest.mark.parametrize("bad", ["notanemail","missing@","","nodot"])
    def test_bad_email_raises(self, bad: str) -> None:
        """Verify malformed emails raise InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            self.v.validate({"user_id":"1","name":"J","email":bad})
 
    def test_invalid_email_also_caught_as_validation_error(self) -> None:
        """Confirm invalid email errors are also caught by ValidationError."""
        with pytest.raises(ValidationError):
            self.v.validate({"user_id":"1","name":"J","email":"bad"})

