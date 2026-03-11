from .library import LibraryResource
import json

from ..models.author import Author
from ..models.book import AudioBook, Book, EBook
from ..models.borrow import Borrow

class LibraryRegistry:
    def __init__(self):
        self.resources = {}
        self._authors_by_name = {}
        self._next_author_id = 1
        self._next_resource_id = 1

    def _generate_author_id(self):
        author_id = self._next_author_id
        self._next_author_id += 1
        return author_id

    def _generate_resource_id(self):
        resource_id = self._next_resource_id
        self._next_resource_id += 1
        return resource_id

    def _sync_id_counters(self):
        max_author_id = 0
        max_resource_id = 0
        self._authors_by_name.clear()

        for resource in self.resources.values():
            author = resource.author
            self._authors_by_name[author.author_name.lower()] = author

            if isinstance(author.author_id, int) and author.author_id > max_author_id:
                max_author_id = author.author_id

            if isinstance(resource.resource_id, int) and resource.resource_id > max_resource_id:
                max_resource_id = resource.resource_id

        self._next_author_id = max_author_id + 1
        self._next_resource_id = max_resource_id + 1

    def get_or_create_author(self, author_name):
        key = author_name.strip().lower()
        if key in self._authors_by_name:
            return self._authors_by_name[key]

        author = Author(author_name.strip(), self._generate_author_id())
        self._authors_by_name[key] = author
        return author

    def _get_or_create_author_with_id(self, author_name, author_id):
        key = author_name.strip().lower()
        if key in self._authors_by_name:
            return self._authors_by_name[key]

        author = Author(author_name.strip(), author_id)
        self._authors_by_name[key] = author
        return author

    def create_resource(self, kind, title, author_name, file_format=None, duration=None, borrower_name=None):
        resource_id = self._generate_resource_id()
        author = self.get_or_create_author(author_name)

        if kind == "1":
            resource = Book(resource_id, title, author)
        elif kind == "2":
            resource = EBook(resource_id, title, author, file_format or "pdf")
        elif kind == "3":
            resource = AudioBook(resource_id, title, author, duration or 0)
        elif kind == "4":
            resource = Borrow(resource_id, title, author, borrower_name or "Unknown")
        else:
            raise ValueError("Invalid resource type")

        self.add_resource(resource)
        return resource

    def add_resource(self, resource: LibraryResource):
        if resource.resource_id in self.resources:
            raise ValueError("Resource already exists")
        
        self.resources[resource.resource_id] = resource
        self._authors_by_name[resource.author.author_name.lower()] = resource.author

        resource.author.add_book(resource)
        self._sync_id_counters()

    def borrow_resource(self, resource_id):
        resource = self.resources.get(resource_id)

        if resource and not resource.is_borrowed:
            resource.is_borrowed = True
            print(f"{resource.title} borrowed")
        else:
            print("Resource unavailable")

    def return_resource(self, resource_id):
        resource = self.resources.get(resource_id)

        if resource:
            resource.is_borrowed = False

    def list_resources(self):
        for r in self.resources.values():
            print(f"{r.title} ({r.get_type()}) - Borrowed: {r.is_borrowed}")

    def search_by_title(self, keyword):
        key = keyword.lower()
        return [r for r in self.resources.values() if key in r.title.lower()]

    def categorize_by_type(self):
        types = {r.get_type() for r in self.resources.values()}
        return {t: [r for r in self.resources.values() if r.get_type() == t] for t in types}

    def generate_report_lines(self):
        return [f"{r.resource_id}: {r.title} ({r.get_type()})" for r in self.resources.values()]

    def save_to_json(self, file_path):
        data = []
        for r in self.resources.values():
            item = {
                "resource_id": r.resource_id,
                "title": r.title,
                "author_name": r.author.author_name,
                "author_id": r.author.author_id,
                "is_borrowed": r.is_borrowed,
                "kind": r.__class__.__name__,
            }

            if isinstance(r, EBook):
                item["file_format"] = r.file_format
            if isinstance(r, AudioBook):
                item["duration"] = r.duration
            if isinstance(r, Borrow):
                item["borrower_name"] = r.borrower_name

            data.append(item)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return len(data)

    def load_from_json(self, file_path, replace=True):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if replace:
            self.resources.clear()
            self._authors_by_name.clear()

        loaded_count = 0
        for item in data:
            if not replace and item["resource_id"] in self.resources:
                continue

            author = self._get_or_create_author_with_id(item["author_name"], item["author_id"])
            kind = item.get("kind", "Book")

            if kind == "EBook":
                resource = EBook(item["resource_id"], item["title"], author, item.get("file_format", "pdf"))
            elif kind == "AudioBook":
                resource = AudioBook(item["resource_id"], item["title"], author, item.get("duration", 0))
            elif kind == "Borrow":
                resource = Borrow(
                    item["resource_id"],
                    item["title"],
                    author,
                    item.get("borrower_name", "Unknown"),
                )
            else:
                resource = Book(item["resource_id"], item["title"], author)

            resource.is_borrowed = item.get("is_borrowed", False)
            self.add_resource(resource)
            loaded_count += 1

        self._sync_id_counters()
        return loaded_count