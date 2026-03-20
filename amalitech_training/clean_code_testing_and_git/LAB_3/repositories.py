import re

from amalitech_training.clean_code_testing_and_git.LAB_3.exceptions import UserAlreadyExistsError
from amalitech_training.clean_code_testing_and_git.LAB_3.interfaces import UserRepository
from amalitech_training.clean_code_testing_and_git.LAB_3.models import User


class InMemoryUserRepository(UserRepository):
    """
    Stores the users in a dict. Data is lost on the process exit.
    """
    
    def __init__(self) -> None:
        self._store: dict[str, User] = {}  # key = lowercase username
 
    def save(self, user: User) -> User:
        """Persist user. Raises UserAlreadyExistsError on duplicate."""
        if user.username in self._store:
            raise UserAlreadyExistsError(
                f"Username '{user.username}' is already registered."
            )
        if self.find_by_email_or_phone(user.email_or_phone) is not None:
            raise UserAlreadyExistsError(
                f"Email or Phone number '{user.email_or_phone}' is already registered."
            )
        self._store[user.username] = user
        return user
 
    def find_by_username(self, username: str) -> User | None:
        return self._store.get(username.lower().strip())
 
    def find_by_email_or_phone(self, email_or_phone: str) -> User | None:
        if User.is_email(email_or_phone):
            normalised = email_or_phone.lower().strip()
        else:
            normalised = re.sub(r"\D", "", email_or_phone)

        for user in self._store.values():
            if user.email_or_phone == normalised:
                return user
        return None
