from dataclasses import dataclass
 
 
@dataclass
class User:
    """
    One imported user record.
 
    Attributes:
        user_id: Unique positive integer.
        name: Full name.
        email: Contact email.
    """
 
    user_id: int
    name: str
    email: str
