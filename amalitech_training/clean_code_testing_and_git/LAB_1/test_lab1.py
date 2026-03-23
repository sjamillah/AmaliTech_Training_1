import pytest
import json
import runpy
import sys

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
from .repository import JsonRepository
from .importer import CsvImporter, ImportResult
from . import main as cli_main


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

    def test_os_error_raises_file_format_error(self, tmp_path: Path, mocker) -> None:
        """Ensure low-level OS read errors are mapped to FileFormatError."""
        p = tmp_path / "users.csv"
        mocker.patch("builtins.open", side_effect=OSError("disk failure"))
        with pytest.raises(FileFormatError):
            list(CsvParser().parse(p))
 
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


@pytest.fixture
def db(tmp_path: Path) -> Path:
    """Create an empty JSON database file for repository tests."""
    p = tmp_path / "db.json"
    p.write_text("{}")
    return p
 
 
class TestJsonRepository:
    """Tests for JSON-backed user persistence behavior."""

    def test_save_writes_user_to_file(self, db: Path) -> None:
        """Ensure saving a user writes the expected payload to disk."""
        repo = JsonRepository(db)
        repo.save(User(1, "Joshua", "j@ex.com"))
        data = json.loads(db.read_text())
        assert "1" in data
        assert data["1"]["name"] == "Joshua"
 
    def test_duplicate_raises(self, db: Path) -> None:
        """Verify saving the same user twice raises DuplicateUserError."""
        repo = JsonRepository(db)
        u = User(1, "Joshua", "j@ex.com")
        repo.save(u)
        with pytest.raises(DuplicateUserError):
            repo.save(u)
 
    def test_exists_true_after_save(self, db: Path) -> None:
        """Confirm exists returns True after a user has been saved."""
        repo = JsonRepository(db)
        repo.save(User(1, "J", "j@ex.com"))
        assert repo.exists(1) is True
 
    def test_exists_false_when_not_saved(self, db: Path) -> None:
        """Confirm exists returns False for unknown user ids."""
        assert JsonRepository(db).exists(99) is False
 
    def test_load_all_returns_all_users(self, db: Path) -> None:
        """Ensure load_all returns all users currently stored in the file."""
        repo = JsonRepository(db)
        repo.save(User(1, "A", "a@ex.com"))
        repo.save(User(2, "B", "b@ex.com"))
        assert len(repo.load_all()) == 2
 
    def test_corrupt_db_starts_empty(self, tmp_path: Path) -> None:
        """Verify corrupt JSON content is treated as an empty repository."""
        p = tmp_path / "db.json"
        p.write_text("not valid json")
        assert JsonRepository(p).load_all() == []
 
    def test_missing_db_starts_empty(self, tmp_path: Path) -> None:
        """Verify a missing database file is handled as an empty repository."""
        assert JsonRepository(tmp_path / "new.json").load_all() == []


@pytest.fixture
def imp(tmp_path: Path):
    """Build a CsvImporter instance with a temporary JSON repository."""
    db = tmp_path / "db.json"
    db.write_text("{}")
    return CsvImporter(
        parser=CsvParser(),
        validator=CsvValidator(),
        repository=JsonRepository(db),
    ), tmp_path
 
 
class TestCsvImporter:
    """Tests for end-to-end CSV import result accounting."""

    def test_happy_path(self, imp) -> None:
        """Verify valid rows are imported with zero skips and errors."""
        importer, tmp = imp
        csv = tmp / "u.csv"
        csv.write_text("user_id,name,email\n1,Joshua,j@ex.com\n2,Lynn,l@ex.com")
        r = importer.run(csv)
        assert r.imported == 2 and r.skipped == 0 and r.errors == 0
 
    def test_duplicate_counted_as_skipped(self, imp) -> None:
        """Ensure duplicate user ids are counted as skipped rows."""
        importer, tmp = imp
        csv = tmp / "u.csv"
        csv.write_text("user_id,name,email\n1,J,j@ex.com\n1,J,j@ex.com")
        r = importer.run(csv)
        assert r.imported == 1 and r.skipped == 1
 
    def test_bad_email_counted_as_error(self, imp) -> None:
        """Ensure invalid email rows increment the error counter."""
        importer, tmp = imp
        csv = tmp / "u.csv"
        csv.write_text("user_id,name,email\n1,J,notanemail")
        r = importer.run(csv)
        assert r.errors == 1 and r.imported == 0

    def test_missing_field_counted_as_skipped(self, imp) -> None:
        """Ensure rows missing required columns are counted as skipped."""
        importer, tmp = imp
        csv = tmp / "u.csv"
        csv.write_text("user_id,name\n1,J")
        r = importer.run(csv)
        assert r.skipped == 1 and r.imported == 0 and r.errors == 0

    def test_bad_user_id_counted_as_skipped(self, imp) -> None:
        """Ensure rows with invalid user_id values are counted as skipped."""
        importer, tmp = imp
        csv = tmp / "u.csv"
        csv.write_text("user_id,name,email\nabc,J,j@ex.com")
        r = importer.run(csv)
        assert r.skipped == 1 and r.imported == 0 and r.errors == 0
 
    def test_missing_file_raises(self, imp) -> None:
        """Verify running import on a missing file raises FileFormatError."""
        importer, tmp = imp
        with pytest.raises(FileFormatError):
            importer.run(tmp / "missing.csv")
 
    def test_result_str_contains_counts(self, imp) -> None:
        """Confirm ImportResult string output includes imported counts."""
        importer, tmp = imp
        csv = tmp / "u.csv"
        csv.write_text("user_id,name,email\n1,J,j@ex.com")
        assert "Imported: 1" in str(importer.run(csv))


class TestCli:
    """Tests for command-line behavior and exit status handling."""

    def test_success_exits_zero(self, tmp_path: Path) -> None:
        """Verify CLI returns exit code 0 for a successful import run."""
        csv = tmp_path / "u.csv"
        csv.write_text("user_id,name,email\n1,Joshua,j@ex.com")
        db = tmp_path / "db.json"
        db.write_text("{}")
        assert cli_main.main([str(csv), "--db", str(db)]) == 0
 
    def test_missing_file_exits_one(self, tmp_path: Path) -> None:
        """Verify CLI returns exit code 1 when the CSV file is missing."""
        db = tmp_path / "db.json"
        db.write_text("{}")
        assert cli_main.main([str(tmp_path / "nope.csv"), "--db", str(db)]) == 1
 
    def test_calls_importer(self, tmp_path: Path, mocker) -> None:
        """Ensure the CLI invokes importer.run exactly once for a valid input."""
        csv = tmp_path / "u.csv"
        csv.write_text("user_id,name,email\n1,J,j@ex.com")
        mock_imp = mocker.MagicMock()
        mock_imp.run.return_value = ImportResult(imported=1)
        mocker.patch.object(cli_main, "CsvImporter", return_value=mock_imp)
        cli_main.main([str(csv)])
        mock_imp.run.assert_called_once()

    def test_module_entrypoint_calls_sys_exit(self, tmp_path: Path, mocker, monkeypatch) -> None:
        """Ensure running the module as __main__ routes through sys.exit."""
        csv = tmp_path / "u.csv"
        db = tmp_path / "db.json"
        csv.write_text("user_id,name,email\n1,J,j@ex.com")
        db.write_text("{}")
        monkeypatch.setattr(sys, "argv", ["main.py", str(csv), "--db", str(db)])
        exit_mock = mocker.patch("sys.exit")

        runpy.run_module(
            "amalitech_training.clean_code_testing_and_git.LAB_1.main",
            run_name="__main__",
        )

        exit_mock.assert_called_once_with(0)

