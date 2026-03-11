from ..library.library import LibraryResource
from .author import Author


class Borrow(LibraryResource):
    def __init__(self, resource_id, title, author: Author, borrower_name):
        super().__init__(resource_id, title, author)
        self.borrower_name = borrower_name

    def get_type(self):
        return "Borrow"

    def __repr__(self):
        return f"Borrow({self.title}, borrower={self.borrower_name})"
