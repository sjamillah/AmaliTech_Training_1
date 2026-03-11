import pytest

from amalitech_training.python_basics.LAB_3.library.library_registry import LibraryRegistry


def test_author_is_reused_for_same_name():
    registry = LibraryRegistry()

    first = registry.create_resource("1", "Python 101", "Mike")
    second = registry.create_resource("2", "Advanced Python", "Mike", file_format="pdf")

    assert first.author.author_id == second.author.author_id


def test_borrow_and_return_changes_resource_status():
    registry = LibraryRegistry()
    resource = registry.create_resource("1", "Domain-Driven Design", "Eric Evans")

    registry.borrow_resource(resource.resource_id)
    assert resource.is_borrowed is True

    registry.return_resource(resource.resource_id)
    assert resource.is_borrowed is False


def test_search_by_title_finds_matching_resources():
    registry = LibraryRegistry()
    registry.create_resource("1", "Python Basics", "Author A")
    registry.create_resource("3", "Python Audio", "Author B", duration=30)

    matches = registry.search_by_title("python")

    assert len(matches) == 2
