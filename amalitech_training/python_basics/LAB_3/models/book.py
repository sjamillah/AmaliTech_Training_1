from ..library.library import LibraryResource
from .author import Author

class Book(LibraryResource):
    def get_type(self):
        return "Physical"
    
class EBook(LibraryResource):
    def __init__(self, resource_id, title, author: Author, file_format):
        super().__init__(resource_id, title, author)
        self.file_format = file_format

    def get_type(self):
        return f"EBook ({self.file_format})"
    
class AudioBook(LibraryResource):
    def __init__(self, resource_id, title, author, duration):
        super().__init__(resource_id, title, author)
        self.duration = duration

    def get_type(self):
        return f"AudioBook ({self.duration} mins)"
