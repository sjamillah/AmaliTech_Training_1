from abc import ABC, abstractmethod
from typing import Optional

from amalitech_training.clean_code_testing_and_git.LAB_3.models import User


class UserRepository(ABC):
    """
    Contract for any class that stores and retrieves User objects
    """

    @abstractmethod
    def save(self, user: User) -> User:
        """
        Persist a new user to storage

        Raises:
            UserAlreadyExistsError: If a user with the same username or email/phone already exists
        """
        ...


    @abstractmethod
    def find_by_username(self, username: str) -> Optional[User]:
        """
        Find the user by username

        Returns None if not found
        """
        ...


    @abstractmethod
    def find_by_email_or_phone(self, email_or_phone: str) -> Optional[User]:
        """
        Find user by email or phone (case-insensitive for email)

        Returns None if not found
        """
        ...


class PasswordHasher(ABC):
    """
    Contract for hashing and verifying passwords
    """

    @abstractmethod
    def hash(self, raw_password: str) -> str:
        """
        Hash a plain text password

        Must be one-way; the original password cannot be recovered.
        """
        ...


    @abstractmethod
    def verify(self, raw_password: str, hashed_password: str) -> bool:
        """
        Check if a raw password matches a stored hash

        Returns True if it matches, False otherwise
        Must be timing-attack safe
        """
        ...
