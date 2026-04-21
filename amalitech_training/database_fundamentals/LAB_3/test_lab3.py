from __future__ import annotations

import importlib.util
import sys
import types
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock


LAB_DIR = Path(__file__).parent


def load_module_from_path(module_name: str, path: Path, stubs: dict[str, types.ModuleType]):
    original_modules: dict[str, types.ModuleType | None] = {}
    try:
        for name, module in stubs.items():
            original_modules[name] = sys.modules.get(name)
            sys.modules[name] = module

        spec = importlib.util.spec_from_file_location(module_name, str(path))
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        for name, original in original_modules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


class FakeMongoCursor:
    def __init__(self, documents):
        self.documents = list(documents)

    def sort(self, *args, **kwargs):
        return self

    def skip(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def __iter__(self):
        return iter(self.documents)


class FakeMongoCollection:
    def __init__(self, find_docs=None, find_one_doc=None, aggregate_docs=None, modified_count=1):
        self.find_docs = find_docs or []
        self.find_one_doc = find_one_doc
        self.aggregate_docs = aggregate_docs or []
        self.modified_count = modified_count
        self.inserted_docs = []
        self.updated_calls = []
        self.find_calls = []
        self.find_one_calls = []
        self.aggregate_calls = []
        self.indexes = []

    def create_index(self, fields):
        self.indexes.append(fields)

    def insert_one(self, document):
        self.inserted_docs.append(document)
        return types.SimpleNamespace(inserted_id="abc123")

    def update_one(self, filter_doc, update_doc):
        self.updated_calls.append((filter_doc, update_doc))
        return types.SimpleNamespace(modified_count=self.modified_count)

    def find(self, filter_doc, projection=None):
        self.find_calls.append((filter_doc, projection))
        return FakeMongoCursor(self.find_docs)

    def find_one(self, filter_doc):
        self.find_one_calls.append(filter_doc)
        return self.find_one_doc

    def aggregate(self, pipeline):
        self.aggregate_calls.append(pipeline)
        return iter(self.aggregate_docs)


class FakeMongoDB:
    def __init__(self, collection):
        self.collection = collection

    def __getitem__(self, _name):
        return self.collection


class FakeMongoClient:
    def __init__(self, uri, collection):
        self.uri = uri
        self.collection = collection

    def __getitem__(self, _name):
        return FakeMongoDB(self.collection)


def test_dashboard_get_status_mapping() -> None:
    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: None
    db_stub.release_connection = lambda conn: None

    redis_stub = types.ModuleType("redis_cache")
    redis_stub.get_course_progress = lambda student_id, course_id: 0.0

    forum_stub = types.ModuleType("forum")
    forum_stub.get_thread_count_per_course = lambda course_ids: {}

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    dashboard = load_module_from_path(
        "dashboard_module",
        LAB_DIR / "dashboard.py",
        {
            "db_connection": db_stub,
            "redis_cache": redis_stub,
            "forum": forum_stub,
            "dotenv": dotenv_stub,
        },
    )

    assert dashboard._get_status(0) == "Not Started"
    assert dashboard._get_status(10) == "Just Begun"
    assert dashboard._get_status(50) == "In Progress"
    assert dashboard._get_status(90) == "Almost Done"
    assert dashboard._get_status(100) == "Completed!"


def test_dashboard_builds_response_from_dependencies() -> None:
    fake_cursor = Mock()
    fake_cursor.fetchone.return_value = ("Ama", "ama@example.com")
    fake_cursor.fetchall.side_effect = [
        [(7, "SQL Basics", "Mr. Kofi", "2026-04-01", 12)],
        [(7, "2026-04-05 10:00:00")],
    ]

    fake_conn = Mock()
    fake_conn.cursor.return_value = fake_cursor

    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: fake_conn
    db_stub.release_connection = Mock()

    redis_stub = types.ModuleType("redis_cache")
    redis_stub.get_course_progress = lambda student_id, course_id: 75.0

    forum_stub = types.ModuleType("forum")
    forum_stub.get_thread_count_per_course = lambda course_ids: {7: 4}

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    dashboard = load_module_from_path(
        "dashboard_module_data",
        LAB_DIR / "dashboard.py",
        {
            "db_connection": db_stub,
            "redis_cache": redis_stub,
            "forum": forum_stub,
            "dotenv": dotenv_stub,
        },
    )

    result = dashboard.get_student_dashboard(1)

    assert result["student_id"] == 1
    assert result["full_name"] == "Ama"
    assert result["course_count"] == 1
    assert result["courses"][0]["progress_pct"] == 75.0
    assert result["courses"][0]["forum_threads"] == 4
    db_stub.release_connection.assert_called_once_with(fake_conn)


def test_dashboard_returns_error_for_unknown_student() -> None:
    fake_cursor = Mock()
    fake_cursor.fetchone.return_value = None

    fake_conn = Mock()
    fake_conn.cursor.return_value = fake_cursor

    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: fake_conn
    db_stub.release_connection = Mock()

    redis_stub = types.ModuleType("redis_cache")
    redis_stub.get_course_progress = lambda student_id, course_id: 0.0

    forum_stub = types.ModuleType("forum")
    forum_stub.get_thread_count_per_course = lambda course_ids: {}

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    dashboard = load_module_from_path(
        "dashboard_module_missing",
        LAB_DIR / "dashboard.py",
        {
            "db_connection": db_stub,
            "redis_cache": redis_stub,
            "forum": forum_stub,
            "dotenv": dotenv_stub,
        },
    )

    result = dashboard.get_student_dashboard(999)

    assert result == {"error": "Student 999 not found"}
    db_stub.release_connection.assert_called_once_with(fake_conn)


def test_dashboard_get_time_between_lessons_uses_lag_results() -> None:
    fake_cursor = Mock()
    fake_cursor.fetchall.return_value = [
        ("Intro", "SQL Basics", "2026-04-01", None, None),
        ("Select", "SQL Basics", "2026-04-02", "2026-04-01", "1 day"),
    ]

    fake_conn = Mock()
    fake_conn.cursor.return_value = fake_cursor

    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: fake_conn
    db_stub.release_connection = Mock()

    redis_stub = types.ModuleType("redis_cache")
    redis_stub.get_course_progress = lambda student_id, course_id: 0.0

    forum_stub = types.ModuleType("forum")
    forum_stub.get_thread_count_per_course = lambda course_ids: {}

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    dashboard = load_module_from_path(
        "dashboard_module_timeline",
        LAB_DIR / "dashboard.py",
        {
            "db_connection": db_stub,
            "redis_cache": redis_stub,
            "forum": forum_stub,
            "dotenv": dotenv_stub,
        },
    )

    result = dashboard.get_time_between_lessons(1)

    assert result == [
        {
            "lesson": "Intro",
            "course": "SQL Basics",
            "completed_at": "2026-04-01",
            "time_since_last": "First lesson",
        },
        {
            "lesson": "Select",
            "course": "SQL Basics",
            "completed_at": "2026-04-02",
            "time_since_last": "1 day",
        },
    ]
    db_stub.release_connection.assert_called_once_with(fake_conn)


def test_redis_cache_key_format() -> None:
    redis_mod = types.ModuleType("redis")

    class DummyRedisError(Exception):
        pass

    class DummyRedisClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    redis_mod.Redis = DummyRedisClient
    redis_mod.RedisError = DummyRedisError

    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: None
    db_stub.release_connection = lambda conn: None

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    redis_cache = load_module_from_path(
        "redis_cache_module",
        LAB_DIR / "redis_cache.py",
        {
            "redis": redis_mod,
            "db_connection": db_stub,
            "dotenv": dotenv_stub,
        },
    )

    assert redis_cache.get_cache_key(3, 8) == "progress:3:8"


def test_redis_get_course_progress_uses_cache_hit() -> None:
    redis_mod = types.ModuleType("redis")

    class DummyRedisError(Exception):
        pass

    class DummyRedisClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def get(self, key):
            return "88.5"

    redis_mod.Redis = DummyRedisClient
    redis_mod.RedisError = DummyRedisError

    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: None
    db_stub.release_connection = lambda conn: None

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    redis_cache = load_module_from_path(
        "redis_cache_hit_module",
        LAB_DIR / "redis_cache.py",
        {
            "redis": redis_mod,
            "db_connection": db_stub,
            "dotenv": dotenv_stub,
        },
    )

    redis_cache._calculate_progress_from_db = Mock(side_effect=AssertionError("DB should not be called"))

    assert redis_cache.get_course_progress(1, 1) == 88.5


def test_redis_get_course_progress_sets_cache_on_miss() -> None:
    redis_mod = types.ModuleType("redis")

    class DummyRedisError(Exception):
        pass

    class DummyRedisClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.saved = None

        def get(self, key):
            return None

        def setex(self, name, time, value):
            self.saved = (name, time, value)

    redis_mod.Redis = DummyRedisClient
    redis_mod.RedisError = DummyRedisError

    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: None
    db_stub.release_connection = lambda conn: None

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    redis_cache = load_module_from_path(
        "redis_cache_miss_module",
        LAB_DIR / "redis_cache.py",
        {
            "redis": redis_mod,
            "db_connection": db_stub,
            "dotenv": dotenv_stub,
        },
    )

    redis_cache._calculate_progress_from_db = Mock(return_value=42.0)

    assert redis_cache.get_course_progress(2, 9) == 42.0
    assert redis_cache.redis_client.saved == ("progress:2:9", redis_cache.CACHE_TTL_SECONDS, "42.0")


def test_redis_invalidate_for_lesson_looks_up_course_and_invalidates() -> None:
    fake_cursor = Mock()
    fake_cursor.fetchone.return_value = (11,)

    fake_conn = Mock()
    fake_conn.cursor.return_value = fake_cursor

    redis_mod = types.ModuleType("redis")

    class DummyRedisError(Exception):
        pass

    class DummyRedisClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def delete(self, key):
            return 1

    redis_mod.Redis = DummyRedisClient
    redis_mod.RedisError = DummyRedisError

    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: fake_conn
    db_stub.release_connection = Mock()

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    redis_cache = load_module_from_path(
        "redis_cache_invalidate_module",
        LAB_DIR / "redis_cache.py",
        {
            "redis": redis_mod,
            "db_connection": db_stub,
            "dotenv": dotenv_stub,
        },
    )

    redis_cache.invalidate_progress_cache = Mock()

    redis_cache.invalidate_progress_cache_for_lesson(5, 101)

    redis_cache.invalidate_progress_cache.assert_called_once_with(5, 11)
    db_stub.release_connection.assert_called_once_with(fake_conn)


def test_redis_get_course_progress_falls_back_when_redis_errors() -> None:
    redis_mod = types.ModuleType("redis")

    class DummyRedisError(Exception):
        pass

    class DummyRedisClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.saved = None

        def get(self, key):
            raise DummyRedisError("down")

        def setex(self, name, time, value):
            self.saved = (name, time, value)

    redis_mod.Redis = DummyRedisClient
    redis_mod.RedisError = DummyRedisError

    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: None
    db_stub.release_connection = lambda conn: None

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    redis_cache = load_module_from_path(
        "redis_cache_fallback_module",
        LAB_DIR / "redis_cache.py",
        {
            "redis": redis_mod,
            "db_connection": db_stub,
            "dotenv": dotenv_stub,
        },
    )

    redis_cache._calculate_progress_from_db = Mock(return_value=33.3)

    assert redis_cache.get_course_progress(4, 8) == 33.3
    assert redis_cache.redis_client.saved == ("progress:4:8", redis_cache.CACHE_TTL_SECONDS, "33.3")


def test_enrollment_complete_lesson_accepts_explicit_conn() -> None:
    psycopg2_stub = types.ModuleType("psycopg2")
    psycopg2_stub.Error = Exception

    fake_cursor = Mock()
    fake_cursor.fetchone.return_value = (44, "2026-04-08T20:00:00Z")

    fake_conn = Mock()
    fake_conn.cursor.return_value = fake_cursor

    db_stub = types.ModuleType("db_connection")
    db_stub.get_managed_connection = lambda: nullcontext(fake_conn)

    enrollment = load_module_from_path(
        "enrollment_module_explicit_conn",
        LAB_DIR / "enrollment.py",
        {
            "db_connection": db_stub,
            "psycopg2": psycopg2_stub,
        },
    )

    result = enrollment.complete_lesson(3, 9, 95.0, conn=fake_conn)

    assert result == {"completion_id": 44, "completed_at": "2026-04-08T20:00:00Z"}
    fake_conn.commit.assert_called_once()


def test_redis_get_all_progress_for_student_collects_all_courses() -> None:
    redis_mod = types.ModuleType("redis")

    class DummyRedisError(Exception):
        pass

    class DummyRedisClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def get(self, key):
            return None

        def setex(self, name, time, value):
            return None

    redis_mod.Redis = DummyRedisClient
    redis_mod.RedisError = DummyRedisError

    fake_cursor = Mock()
    fake_cursor.fetchall.return_value = [(1,), (2,)]

    fake_conn = Mock()
    fake_conn.cursor.return_value = fake_cursor

    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: fake_conn
    db_stub.release_connection = Mock()

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    redis_cache = load_module_from_path(
        "redis_cache_all_module",
        LAB_DIR / "redis_cache.py",
        {
            "redis": redis_mod,
            "db_connection": db_stub,
            "dotenv": dotenv_stub,
        },
    )

    redis_cache.get_course_progress = Mock(side_effect=[25.0, 50.0])

    result = redis_cache.get_all_progress_for_student(7)

    assert result == {1: 25.0, 2: 50.0}
    db_stub.release_connection.assert_called_once_with(fake_conn)


def test_redis_calculate_progress_returns_zero_for_empty_result() -> None:
    redis_mod = types.ModuleType("redis")

    class DummyRedisError(Exception):
        pass

    class DummyRedisClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    redis_mod.Redis = DummyRedisClient
    redis_mod.RedisError = DummyRedisError

    fake_cursor = Mock()
    fake_cursor.fetchone.return_value = None

    fake_conn = Mock()
    fake_conn.cursor.return_value = fake_cursor

    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: fake_conn
    db_stub.release_connection = Mock()

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    redis_cache = load_module_from_path(
        "redis_cache_zero_module",
        LAB_DIR / "redis_cache.py",
        {
            "redis": redis_mod,
            "db_connection": db_stub,
            "dotenv": dotenv_stub,
        },
    )

    assert redis_cache._calculate_progress_from_db(3, 4) == 0.0
    db_stub.release_connection.assert_called_once_with(fake_conn)


def test_mongo_create_thread_returns_inserted_id() -> None:
    pymongo_stub = types.ModuleType("pymongo")

    class FakeMongoClient:
        def __init__(self, uri):
            self.uri = uri

        def __getitem__(self, _name):
            return {"forum_threads": fake_collection}

    class InsertResult:
        inserted_id = "abc123"

    fake_collection = Mock()
    fake_collection.insert_one.return_value = InsertResult()

    pymongo_stub.MongoClient = FakeMongoClient
    pymongo_stub.DESCENDING = -1
    pymongo_stub.TEXT = "text"

    bson_stub = types.ModuleType("bson")
    bson_stub.ObjectId = lambda value=None: value or "generated_object_id"

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    mongo_module = load_module_from_path(
        "mongo_integrator_module",
        LAB_DIR / "mongo_integrator.py",
        {
            "pymongo": pymongo_stub,
            "bson": bson_stub,
            "dotenv": dotenv_stub,
        },
    )

    thread_id = mongo_module.create_thread(1, 2, "Ama", "T", "C")

    assert thread_id == "abc123"
    saved_doc = fake_collection.insert_one.call_args[0][0]
    assert saved_doc["upvotes"] == 0
    assert saved_doc["replies"] == []


def test_mongo_add_reply_returns_none_if_thread_not_found() -> None:
    pymongo_stub = types.ModuleType("pymongo")

    class FakeMongoClient:
        def __init__(self, uri):
            self.uri = uri

        def __getitem__(self, _name):
            return {"forum_threads": fake_collection}

    fake_collection = Mock()
    fake_collection.update_one.return_value = types.SimpleNamespace(modified_count=0)

    pymongo_stub.MongoClient = FakeMongoClient
    pymongo_stub.DESCENDING = -1
    pymongo_stub.TEXT = "text"

    bson_stub = types.ModuleType("bson")
    bson_stub.ObjectId = lambda value=None: value or "generated_object_id"

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    mongo_module = load_module_from_path(
        "mongo_integrator_reply_module",
        LAB_DIR / "mongo_integrator.py",
        {
            "pymongo": pymongo_stub,
            "bson": bson_stub,
            "dotenv": dotenv_stub,
        },
    )

    assert mongo_module.add_reply("thread-1", 2, "Ama", "Reply") is None


def test_mongo_thread_count_per_course_maps_aggregation_result() -> None:
    fake_collection = Mock()
    fake_collection.aggregate.return_value = [
        {"_id": 1, "count": 3},
        {"_id": 2, "count": 5},
    ]

    pymongo_stub = types.ModuleType("pymongo")

    class ClientFactory:
        def __call__(self, uri):
            return FakeMongoClient(uri, fake_collection)

    pymongo_stub.MongoClient = ClientFactory()
    pymongo_stub.DESCENDING = -1
    pymongo_stub.TEXT = "text"

    bson_stub = types.ModuleType("bson")
    bson_stub.ObjectId = lambda value=None: value or "generated_object_id"

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    mongo_module = load_module_from_path(
        "mongo_integrator_agg_module",
        LAB_DIR / "mongo_integrator.py",
        {
            "pymongo": pymongo_stub,
            "bson": bson_stub,
            "dotenv": dotenv_stub,
        },
    )

    assert mongo_module.get_thread_count_per_course([1, 2]) == {1: 3, 2: 5}


def test_mongo_get_course_threads_returns_projection_without_replies() -> None:
    fake_collection = FakeMongoCollection(
        find_docs=[{"_id": 1, "course_id": 9, "title": "Thread A"}]
    )

    pymongo_stub = types.ModuleType("pymongo")
    pymongo_stub.MongoClient = lambda uri: FakeMongoClient(uri, fake_collection)
    pymongo_stub.DESCENDING = -1
    pymongo_stub.TEXT = "text"

    bson_stub = types.ModuleType("bson")
    bson_stub.ObjectId = lambda value=None: value or "generated_object_id"

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    mongo_module = load_module_from_path(
        "mongo_integrator_threads_module",
        LAB_DIR / "mongo_integrator.py",
        {
            "pymongo": pymongo_stub,
            "bson": bson_stub,
            "dotenv": dotenv_stub,
        },
    )

    result = mongo_module.get_course_threads(9, limit=5, skip=2, pinned_first=True)

    assert result == fake_collection.find_docs
    assert fake_collection.find_calls[0][0] == {"course_id": 9}
    assert fake_collection.find_calls[0][1] == {"replies": 0}


def test_mongo_get_thread_with_replies_returns_document() -> None:
    fake_collection = FakeMongoCollection(find_one_doc={"_id": 1, "title": "Thread A"})

    pymongo_stub = types.ModuleType("pymongo")
    pymongo_stub.MongoClient = lambda uri: FakeMongoClient(uri, fake_collection)
    pymongo_stub.DESCENDING = -1
    pymongo_stub.TEXT = "text"

    bson_stub = types.ModuleType("bson")
    bson_stub.ObjectId = lambda value=None: value or "generated_object_id"

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    mongo_module = load_module_from_path(
        "mongo_integrator_thread_module",
        LAB_DIR / "mongo_integrator.py",
        {
            "pymongo": pymongo_stub,
            "bson": bson_stub,
            "dotenv": dotenv_stub,
        },
    )

    result = mongo_module.get_thread_with_replies("thread-1")

    assert result == {"_id": 1, "title": "Thread A"}
    assert fake_collection.find_one_calls[0] == {"_id": "thread-1"}


def test_mongo_search_threads_uses_text_query() -> None:
    fake_collection = FakeMongoCollection(find_docs=[{"_id": 1, "title": "Match"}])

    pymongo_stub = types.ModuleType("pymongo")
    pymongo_stub.MongoClient = lambda uri: FakeMongoClient(uri, fake_collection)
    pymongo_stub.DESCENDING = -1
    pymongo_stub.TEXT = "text"

    bson_stub = types.ModuleType("bson")
    bson_stub.ObjectId = lambda value=None: value or "generated_object_id"

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    mongo_module = load_module_from_path(
        "mongo_integrator_search_module",
        LAB_DIR / "mongo_integrator.py",
        {
            "pymongo": pymongo_stub,
            "bson": bson_stub,
            "dotenv": dotenv_stub,
        },
    )

    result = mongo_module.search_threads(12, "python", limit=3)

    assert result == fake_collection.find_docs
    assert fake_collection.find_calls[0][0] == {"course_id": 12, "$text": {"$search": "python"}}


def test_mongo_upvote_thread_returns_true_when_modified() -> None:
    fake_collection = FakeMongoCollection(modified_count=1)

    pymongo_stub = types.ModuleType("pymongo")
    pymongo_stub.MongoClient = lambda uri: FakeMongoClient(uri, fake_collection)
    pymongo_stub.DESCENDING = -1
    pymongo_stub.TEXT = "text"

    bson_stub = types.ModuleType("bson")
    bson_stub.ObjectId = lambda value=None: value or "generated_object_id"

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    mongo_module = load_module_from_path(
        "mongo_integrator_upvote_module",
        LAB_DIR / "mongo_integrator.py",
        {
            "pymongo": pymongo_stub,
            "bson": bson_stub,
            "dotenv": dotenv_stub,
        },
    )

    assert mongo_module.upvote_thread("thread-9") is True
    assert fake_collection.updated_calls[0][0] == {"_id": "thread-9"}
