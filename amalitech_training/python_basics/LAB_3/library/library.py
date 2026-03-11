from abc import ABC, abstractmethod
from ..models.author import Author

class LibraryResource(ABC):
    def __init__(self, resource_id, title, author: Author):
        self._resource_id = resource_id
        self.title = title
        self.author = author
        self.is_borrowed = False

    @property
    def resource_id(self):
        return self._resource_id

    @abstractmethod
    def get_type(self):
        pass

    def __repr__(self):
        return f"{self.title} by {self.author.author_name}"

    def __eq__(self, other):
        if not isinstance(other, LibraryResource):
            return NotImplemented
        return self.resource_id == other.resource_id





             

