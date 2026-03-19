"""
Test file for the User Authentication Service Module
"""
import pytest
from amalitech_training.clean_code_testing_and_git.LAB_3.exceptions import (
    InvalidPasswordError,
    UserAlreadyExistsError,
    UserNotFoundError,
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
