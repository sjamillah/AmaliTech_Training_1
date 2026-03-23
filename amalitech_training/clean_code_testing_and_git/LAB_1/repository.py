"""Repository layer for storing and retrieving users in JSON format."""

import dataclasses
import json
import logging
from pathlib import Path
 
from .exceptions import DuplicateUserError
from .models import User
 
logger = logging.getLogger(__name__)
 
 
class JsonRepository:
    """Persists users to a JSON file keyed by str(user_id)."""
 
    def __init__(self, path: Path) -> None:
        """Initialize repository state from the backing JSON file path."""
        self._path = path
        self._data: dict[str, dict] = self._load()
 
    def save(self, user: User) -> None:
        """Write user to disk. Raises DuplicateUserError if already stored."""
        key = str(user.user_id)
        if key in self._data:
            raise DuplicateUserError(f"user_id={user.user_id} already exists")
        self._data[key] = dataclasses.asdict(user)
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)
        logger.info("Saved user_id=%s", user.user_id)
 
    def exists(self, user_id: int) -> bool:
        """Return True if a user with the given id is already stored."""
        return str(user_id) in self._data
 
    def load_all(self) -> list[User]:
        """Load all stored users and return them as User objects."""
        return [User(**r) for r in self._data.values()]
 
    def _load(self) -> dict:
        """Read JSON data from disk or return an empty mapping on failure."""
        try:
            with open(self._path, encoding="utf-8") as fh:
                return json.load(fh) or {}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
