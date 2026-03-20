"""
Test file for the User Authentication Service Module
"""

import pytest
from amalitech_training.clean_code_testing_and_git.LAB_3.exceptions import (
    InvalidPasswordError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from amalitech_training.clean_code_testing_and_git.LAB_3.interfaces import (
    PasswordHasher,
    UserRepository,
)
from amalitech_training.clean_code_testing_and_git.LAB_3.models import User
from amalitech_training.clean_code_testing_and_git.LAB_3.password_hasher import (
    BcryptPasswordHasher,
)
from amalitech_training.clean_code_testing_and_git.LAB_3.repositories import (
    InMemoryUserRepository,
)
from amalitech_training.clean_code_testing_and_git.LAB_3.user_service import (
    MIN_PASSWORD_LENGTH,
    UserService,
)


def make_service() -> UserService:
    """Return a fresh UserService backed by in-memory fakes"""
    return UserService(
        repository=InMemoryUserRepository(),
        hasher=PlainTextHasher(),
    )


class TestCustomExceptions:
    """
    Verify all three custom exceptions exist and behave correctly
    """

    def test_user_already_exists_error(self) -> None:
        """Raise error if user exists"""
        with pytest.raises(UserAlreadyExistsError):
            raise UserAlreadyExistsError("username already taken")

    def test_user_not_found_error(self) -> None:
        """Raises error if user ain't found"""
        with pytest.raises(UserNotFoundError):
            raise UserNotFoundError("user does not exist")

    def test_invalid_password_error(self) -> None:
        """Raises error if password is invalid"""
        with pytest.raises(InvalidPasswordError):
            raise InvalidPasswordError("password does not match")

    def test_all_exceptions_inherit_from_exception(self) -> None:
        """Checks if custom exceptions inherit from exception object"""
        assert issubclass(UserAlreadyExistsError, Exception)
        assert issubclass(UserNotFoundError, Exception)
        assert issubclass(InvalidPasswordError, Exception)

    def test_exception_message_is_preserved(self) -> None:
        """The message passed in is accessible via str()"""
        msg = "username already taken"
        error = UserAlreadyExistsError(msg)
        assert msg in str(error)


class TestUserModel:
    """
    Verify User dataclass fields and normalization
    """

    def test_username_is_lowercased(self) -> None:
        user = User(
            name="Jammy Jam",
            username="Jam_J",
            email_or_phone="jammyj@gmail.com",
            hashed_password="jam",
        )
        assert user.username == "jam_j"

    def test_username_is_stripped_off_whitespace(self) -> None:
        user = User(
            name="Jammy Jam",
            username=" Jam_J  ",
            email_or_phone="jammyj@gmail.com",
            hashed_password="jam",
        )
        assert user.username == "jam_j"

    def test_email_is_lowercased(self) -> None:
        user = User(
            name="Jammy Jam",
            username="Jam_J",
            email_or_phone="JAMMYJ@GMAIL.COM",
            hashed_password="jam",
        )
        assert user.email_or_phone == "jammyj@gmail.com"

    def test_email_is_stripped_off_whitespace(self) -> None:
        user = User(
            name="Jammy Jam",
            username="Jam_J",
            email_or_phone="  jammyj@gmail.com",
            hashed_password="jam",
        )
        assert user.email_or_phone == "jammyj@gmail.com"

    def test_is_active_is_true_by_default(self) -> None:
        user = User(
            name="Jammy Jam",
            username="Jam_J",
            email_or_phone="jammyj@gmail.com",
            hashed_password="jam",
        )
        assert user.is_active == True

    def test_created_at_is_set_automatically(self) -> None:
        user = User(
            name="Jammy Jam",
            username="Jam_J",
            email_or_phone="jammyj@gmail.com",
            hashed_password="jam",
        )
        assert user.created_at is not None

    def test_phone_is_normalized_to_digits(self) -> None:
        user = User(
            name="Jammy Jam",
            username="Jam_J",
            email_or_phone="+233 (20) 123-4567",
            hashed_password="jam",
        )
        assert user.email_or_phone == "233201234567"

    def test_deactivate_sets_user_inactive(self) -> None:
        user = User(
            name="Jammy Jam",
            username="Jam_J",
            email_or_phone="jammyj@gmail.com",
            hashed_password="jam",
        )
        user.deactivate()
        assert user.is_active is False

    def test_activate_sets_user_active(self) -> None:
        user = User(
            name="Jammy Jam",
            username="Jam_J",
            email_or_phone="jammyj@gmail.com",
            hashed_password="jam",
        )
        user.deactivate()
        user.activate()
        assert user.is_active is True


class TestUserRepositoryContract:
    """Verify UserRepository blocks incomplete implementations."""

    def test_cannot_instantiate_without_all_methods(self) -> None:
        class Incomplete(UserRepository):
            pass

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_complete_implementation_is_accepted(self) -> None:
        class Complete(UserRepository):
            def save(self, user: User) -> User:
                return user

            def find_by_username(self, u: str) -> User | None:
                return None

            def find_by_email_or_phone(self, e: str) -> User | None:
                return None

        assert isinstance(Complete(), UserRepository)


class TestPasswordHasherContract:
    """Verify PasswordHasher blocks incomplete implementations."""

    def test_cannot_instantiate_without_all_methods(self) -> None:
        class Incomplete(PasswordHasher):
            pass

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_complete_implementation_is_accepted(self) -> None:
        class Complete(PasswordHasher):
            def hash(self, p: str) -> str:
                return p

            def verify(self, p: str, h: str) -> bool:
                return p == h

        assert isinstance(Complete(), PasswordHasher)


class TestBcryptPasswordHasher:
    """Verify concrete bcrypt hasher behavior."""

    def test_hash_returns_string_and_not_raw_password(self) -> None:
        hasher = BcryptPasswordHasher()
        hashed = hasher.hash("secret123")

        assert isinstance(hashed, str)
        assert hashed != "secret123"

    def test_verify_returns_true_for_match_and_false_for_mismatch(self) -> None:
        hasher = BcryptPasswordHasher()
        hashed = hasher.hash("secret123")

        assert hasher.verify("secret123", hashed) is True
        assert hasher.verify("wrong-password", hashed) is False


class PlainTextHasher(PasswordHasher):
    """Simple deterministic hasher used in unit tests only."""

    def hash(self, raw_password: str) -> str:
        return f"plain::{raw_password}"

    def verify(self, raw_password: str, hashed_password: str) -> bool:
        return hashed_password == self.hash(raw_password)


class TestUserServiceRegister:

    def setup_method(self) -> None:
        self.service = make_service()

    def test_register_returns_user_with_correct_username(self) -> None:
        user = self.service.register(
            name="Joshua Alana",
            username="joshua_a",
            email="j@example.com",
            password="secure123",
            confirm_password="secure123",
        )
        assert user.username == "joshua_a"

    def test_register_returns_user_with_correct_email(self) -> None:
        user = self.service.register(
            name="Joshua Alana",
            username="joshua_a",
            email="j@example.com",
            password="secure123",
            confirm_password="secure123",
        )
        assert user.email == "j@example.com"

    def test_register_does_not_store_raw_password(self) -> None:
        user = self.service.register(
            name="Joshua Alana",
            username="joshua_a",
            email="j@example.com",
            password="secure123",
            confirm_password="secure123",
        )
        assert user.hashed_password is not None
        assert user.hashed_password != ""

    def test_register_sets_user_active_by_default(self) -> None:
        user = self.service.register(
            name="Joshua Alana",
            username="joshua_a",
            email="j@example.com",
            password="secure123",
            confirm_password="secure123",
        )
        assert user.is_active is True

    def test_mismatched_passwords_raise_invalid_password_error(self) -> None:
        with pytest.raises(InvalidPasswordError):
            self.service.register(
                name="Joshua Alana",
                username="joshua_a",
                email="j@example.com",
                password="secure123",
                confirm_password="different456",
            )

    def test_password_too_short_raises_invalid_password_error(self) -> None:
        short = "x" * (MIN_PASSWORD_LENGTH - 1)
        with pytest.raises(InvalidPasswordError):
            self.service.register(
                name="Joshua Alana",
                username="joshua_a",
                email="j@example.com",
                password=short,
                confirm_password=short,
            )

    def test_password_at_minimum_length_is_accepted(self) -> None:
        exact = "x" * MIN_PASSWORD_LENGTH
        user = self.service.register(
            name="Joshua Alana",
            username="joshua_a",
            email="j@example.com",
            password=exact,
            confirm_password=exact,
        )
        assert user.username == "joshua_a"

    def test_duplicate_username_raises_user_already_exists(self) -> None:
        self.service.register(
            name="Joshua Alana",
            username="joshua_a",
            email="j@example.com",
            password="secure123",
            confirm_password="secure123",
        )
        with pytest.raises(UserAlreadyExistsError):
            self.service.register(
                name="Another",
                username="joshua_a",
                email="another@example.com",
                password="secure123",
                confirm_password="secure123",
            )

    def test_duplicate_email_raises_user_already_exists(self) -> None:
        self.service.register(
            name="Joshua Alana",
            username="joshua_a",
            email="shared@example.com",
            password="secure123",
            confirm_password="secure123",
        )
        with pytest.raises(UserAlreadyExistsError):
            self.service.register(
                name="Another",
                username="another_user",
                email="shared@example.com",
                password="secure123",
                confirm_password="secure123",
            )

    def test_repository_save_not_called_on_password_mismatch(
        self, mocker: pytest.FixtureRequest
    ) -> None:
        mock_repo = mocker.MagicMock(spec=UserRepository)
        service = UserService(repository=mock_repo, hasher=PlainTextHasher())
        with pytest.raises(InvalidPasswordError):
            service.register(
                name="Joshua Alana",
                username="joshua_a",
                email="j@example.com",
                password="secure123",
                confirm_password="wrong",
            )
        mock_repo.save.assert_not_called()
