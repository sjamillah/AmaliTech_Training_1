import logging
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

logger = logging.getLogger(__name__)
MIN_PASSWORD_LENGTH = 8


class UserService:
    """
    Main entry point for user registration and authentication.
    """

    def __init__(self, repository: UserRepository, hasher: PasswordHasher) -> None:
        self._repository = repository
        self._hasher = hasher

    def register(
        self,
        name: str,
        username: str,
        email_or_phone: str,
        password: str,
        confirm_password: str,
    ) -> User:
        """
        Register a new user.

        Order: validate password -> hash -> build User -> save -> return.

        Raises:
            InvalidPasswordError: passwords don't match or too short.
            UserAlreadyExistsError: username or email/phonenumber already taken.
        """
        self._validate_password(password, confirm_password)
        hashed = self._hasher.hash(password)
        user = User(
            name=name,
            username=username,
            email_or_phone=email_or_phone,
            hashed_password=hashed,
        )
        try:
            saved = self._repository.save(user)
        except UserAlreadyExistsError:
            logger.warning("Registration failed. User already exists: '%s", username)
            raise
        logger.info("User registered successfully: '%s'", saved.username)
        return saved

    def _validate_password(self, password: str, confirm_password: str) -> None:
        """
        Enforce password match and minimum length.

        Raises:
            InvalidPasswordError: on any violation.
        """
        if password != confirm_password:
            raise InvalidPasswordError(
                "Passwords do not match. Enter the same password twice."
            )
        if len(password) < MIN_PASSWORD_LENGTH:
            raise InvalidPasswordError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters. "
                f"You entered {len(password)}."
            )

    def login(self, username: str, password: str) -> User:
        """
        Verify credentials and return the authenticated User.

        Order: find user -> raise if not found -> verify password
               -> raise if wrong -> return user.

        Raises:
            UserNotFoundError: if username does not exist.
            InvalidPasswordError: if password does not match hash.
        """
        user = self._repository.find_by_username(username)
        if user is None:
            logger.warning("Login failed. User not found: '%s'", username)
            raise UserNotFoundError(...)
        if not self._hasher.verify(password, user.hashed_password):
            logger.warning("Login failed. Invalid password for: '%s'", username)
            raise InvalidPasswordError(...)

        logger.info("Login successful: '%s'", user.username)
        return user
