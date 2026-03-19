from dataclasses import dataclass, field
from datetime import datetime
import re


@dataclass
class User:
    """
    Represents a registered user in the system

    Attributes:
        name(str)
        username(str)
        email/phone number(str)
        hashed_password(str)
        created_at(datetime)
        is_active(bool)
    """

    name: str
    username: str
    email_or_phone: str
    hashed_password: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = field(default=True)

    def __post_init__(self) -> None:
        """Normalize fields after object initialization"""
        self.username = self.username.lower().strip()
        self.name = self.name.strip()

        # Normalize email if it looks like an email
        if self.is_email(self.email_or_phone):
            self.email_or_phone = self.email_or_phone.lower().strip()
        else:
            # Remove non-digit characters for phone numbers
            self.email_or_phone = re.sub(r"\D", "", self.email_or_phone)

    @staticmethod
    def is_email(value: str) -> bool:
        """Simple check to see if the value looks like an email"""
        return "@" in value

    def deactivate(self) -> None:
        """Deactivate a user account"""
        self.is_active = False

    def activate(self) -> None:
        """Activate a user account"""
        self.is_active = True
