import bcrypt
from amalitech_training.clean_code_testing_and_git.LAB_3.interfaces import (
    PasswordHasher,
)


class BcryptPasswordHasher(PasswordHasher):
    """
    Password hasher for production
    """

    def hash(self, raw_password: str) -> str:
        """Hash raw password with a fresh random salt"""
        salt = bcrypt.gensalt()
        hashed_bytes = bcrypt.hashpw(raw_password.encode("utf-8"), salt)
        return hashed_bytes.decode("utf-8")

    def verify(self, raw_password: str, hashed_password: str) -> bool:
        """Timing-safe comparison of raw_password against stored hash"""
        return bcrypt.checkpw(
            raw_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
