class Author():
    def __init__(self, author_name, author_id):
        self._author_id = author_id
        self.author_name = author_name
        self.books = []

    @property
    def author_id(self):
        return self._author_id
    
    def add_book(self, book):
        self.books.append(book)
    
    def __repr__(self):
        return f"Author({self.author_name})"
             