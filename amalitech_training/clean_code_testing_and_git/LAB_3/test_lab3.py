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
        user = User(name="Jammy Jam", username="Jam_J", email="jammyj@gmail.com", hashed_password="jam")
        assert user.username == "jam_j"

    def test_username_is_stripped_off_whitespace(self) -> None:
        user = User(name="Jammy Jam", username=" Jam_J  ", email="jammyj@gmail.com", hashed_password="jam")
        assert user.username == "jam_j"

    def test_email_is_lowercased(self) -> None:
        user = User(name="Jammy Jam", username="Jam_J", email="JAMMYJ@GMAIL.COM", hashed_password="jam")
        assert user.email == "jammyj@gmail.com"

    def test_email_is_stripped_off_whitespace(self) -> None:
        user = User(name="Jammy Jam", username="Jam_J", email="  jammyj@gmail.com", hashed_password="jam")
        assert user.email == "jammyj@gmail.com"

    def test_is_active_is_true_by_default(self) -> None:
        user = User(name="Jammy Jam", username="Jam_J", email="jammyj@gmail.com", hashed_password="jam")
        assert user.is_active == True

    def test_created_at_is_set_automatically(self) -> None:
        user = User(name="Jammy Jam", username="Jam_J", email="jammyj@gmail.com", hashed_password="jam")
        assert user.created_at is not None
