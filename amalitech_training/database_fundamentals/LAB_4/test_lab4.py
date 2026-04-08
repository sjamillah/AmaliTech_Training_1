from __future__ import annotations

import importlib.util
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

LAB_DIR = Path(__file__).parent


def load_module_from_path(
    module_name: str, path: Path, stubs: dict[str, types.ModuleType]
):
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


def test_reservation_book_rejects_invalid_time_slot() -> None:
    psycopg2_stub = types.ModuleType("psycopg2")
    psycopg2_stub.Error = Exception

    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: Mock()
    db_stub.release_connection = lambda conn: None

    reservation = load_module_from_path(
        "reservation_mod_invalid_time",
        LAB_DIR / "reservation.py",
        {
            "db_connection": db_stub,
            "psycopg2": psycopg2_stub,
        },
    )

    starts = datetime(2026, 4, 8, 20, 0, 0, tzinfo=timezone.utc)
    ends = datetime(2026, 4, 8, 19, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(reservation.InvalidTimeSlot):
        reservation.book_reservation(1, 1, 1, 2, starts, ends)


def test_reservation_book_rejects_too_small_table() -> None:
    psycopg2_stub = types.ModuleType("psycopg2")
    psycopg2_stub.Error = Exception

    fake_cursor = Mock()
    fake_cursor.fetchone.side_effect = [
        (10, "T10", 2, True),
    ]

    fake_conn = Mock()
    fake_conn.cursor.return_value = fake_cursor

    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: fake_conn
    db_stub.release_connection = Mock()

    reservation = load_module_from_path(
        "reservation_mod_small_table",
        LAB_DIR / "reservation.py",
        {
            "db_connection": db_stub,
            "psycopg2": psycopg2_stub,
        },
    )

    starts = datetime(2026, 4, 8, 19, 0, 0, tzinfo=timezone.utc)
    ends = datetime(2026, 4, 8, 21, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(reservation.TableTooSmall):
        reservation.book_reservation(1, 1, 10, 4, starts, ends)

    fake_conn.rollback.assert_called_once()
    db_stub.release_connection.assert_called_once_with(fake_conn)


def test_reservation_book_success_commits_and_returns_payload() -> None:
    psycopg2_stub = types.ModuleType("psycopg2")
    psycopg2_stub.Error = Exception

    fake_cursor = Mock()
    fake_cursor.fetchone.side_effect = [
        (10, "T10", 6, True),
        None,
        (999, "2026-04-08T18:00:00Z"),
    ]

    fake_conn = Mock()
    fake_conn.cursor.return_value = fake_cursor

    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: fake_conn
    db_stub.release_connection = Mock()

    reservation = load_module_from_path(
        "reservation_mod_success",
        LAB_DIR / "reservation.py",
        {
            "db_connection": db_stub,
            "psycopg2": psycopg2_stub,
        },
    )

    starts = datetime(2026, 4, 8, 19, 0, 0, tzinfo=timezone.utc)
    ends = datetime(2026, 4, 8, 21, 0, 0, tzinfo=timezone.utc)

    result = reservation.book_reservation(2, 1, 10, 4, starts, ends)

    assert result["reservation_id"] == 999
    assert result["table_number"] == "T10"
    assert result["status"] == "confirmed"
    fake_conn.commit.assert_called_once()
    db_stub.release_connection.assert_called_once_with(fake_conn)


def test_reservation_cancel_returns_true_when_row_updated() -> None:
    psycopg2_stub = types.ModuleType("psycopg2")
    psycopg2_stub.Error = Exception

    fake_cursor = Mock()
    fake_cursor.fetchone.return_value = (15,)

    fake_conn = Mock()
    fake_conn.cursor.return_value = fake_cursor

    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: fake_conn
    db_stub.release_connection = Mock()

    reservation = load_module_from_path(
        "reservation_mod_cancel",
        LAB_DIR / "reservation.py",
        {
            "db_connection": db_stub,
            "psycopg2": psycopg2_stub,
        },
    )

    assert reservation.cancel_reservation(15, 3) is True
    fake_conn.commit.assert_called_once()


def test_dashboard_get_full_dashboard_integrates_sources() -> None:
    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: None
    db_stub.release_connection = lambda conn: None

    redis_stub = types.ModuleType("redis_caching")
    redis_stub.get_available_tables_cached = (
        lambda rid, party_size, starts_at, ends_at: [
            {"table_id": 1},
            {"table_id": 2},
            {"table_id": 3},
            {"table_id": 4},
        ]
    )

    reviews_stub = types.ModuleType("reviews")
    reviews_stub.get_review_stats = lambda rid: {"avg_food": 4.1, "avg_service": 4.6}

    dashboard = load_module_from_path(
        "dashboard_mod_full",
        LAB_DIR / "dashboard.py",
        {
            "db_connection": db_stub,
            "redis_caching": redis_stub,
            "reviews": reviews_stub,
        },
    )

    dashboard.get_restaurant_rankings = Mock(
        return_value=[
            {
                "restaurant_id": 7,
                "name": "Sky Grill",
                "cuisine": "Fusion",
                "city": "Kigali",
                "review_count": 12,
                "avg_rating": 4.4,
                "city_rank": 1,
            }
        ]
    )

    starts = datetime(2026, 4, 8, 19, 0, 0, tzinfo=timezone.utc)
    ends = datetime(2026, 4, 8, 21, 0, 0, tzinfo=timezone.utc)

    result = dashboard.get_full_dashboard("Kigali", 4, starts, ends)

    assert result["city"] == "Kigali"
    assert result["restaurants"][0]["available_tables"] == 4
    assert len(result["restaurants"][0]["tables"]) == 3
    assert result["restaurants"][0]["mongo_avg_food"] == 4.1


def test_dashboard_get_full_dashboard_rejects_invalid_window() -> None:
    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: None
    db_stub.release_connection = lambda conn: None

    redis_stub = types.ModuleType("redis_caching")
    redis_stub.get_available_tables_cached = (
        lambda rid, party_size, starts_at, ends_at: []
    )

    reviews_stub = types.ModuleType("reviews")
    reviews_stub.get_review_stats = lambda rid: {}

    dashboard = load_module_from_path(
        "dashboard_mod_window",
        LAB_DIR / "dashboard.py",
        {
            "db_connection": db_stub,
            "redis_caching": redis_stub,
            "reviews": reviews_stub,
        },
    )

    starts = datetime(2026, 4, 8, 19, 0, 0, tzinfo=timezone.utc)
    ends = datetime(2026, 4, 8, 18, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError):
        dashboard.get_full_dashboard("Kigali", 4, starts, ends)


def test_redis_cache_key_format() -> None:
    redis_stub = types.ModuleType("redis")

    class DummyRedisError(Exception):
        pass

    class DummyRedisClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    redis_stub.Redis = DummyRedisClient
    redis_stub.RedisError = DummyRedisError

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: None
    db_stub.release_connection = lambda conn: None

    redis_mod = load_module_from_path(
        "redis_mod_key",
        LAB_DIR / "redis_caching.py",
        {
            "redis": redis_stub,
            "dotenv": dotenv_stub,
            "db_connection": db_stub,
        },
    )

    starts = datetime(2026, 4, 8, 19, 30, 0, tzinfo=timezone.utc)
    assert redis_mod._slot_key(3, starts, 4) == "availability:3:2026-04-08:19:4"


def test_redis_get_available_tables_cached_uses_hit() -> None:
    redis_stub = types.ModuleType("redis")

    class DummyRedisError(Exception):
        pass

    class DummyRedisClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def get(self, key):
            return '[{"table_id": 11}]'

    redis_stub.Redis = DummyRedisClient
    redis_stub.RedisError = DummyRedisError

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None

    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: None
    db_stub.release_connection = lambda conn: None

    redis_mod = load_module_from_path(
        "redis_mod_hit",
        LAB_DIR / "redis_caching.py",
        {
            "redis": redis_stub,
            "dotenv": dotenv_stub,
            "db_connection": db_stub,
        },
    )

    redis_mod._query_available_tables = Mock(
        side_effect=AssertionError("DB should not be called")
    )

    starts = datetime(2026, 4, 8, 19, 0, 0, tzinfo=timezone.utc)
    ends = datetime(2026, 4, 8, 21, 0, 0, tzinfo=timezone.utc)

    result = redis_mod.get_available_tables_cached(1, 4, starts, ends)
    assert result == [{"table_id": 11}]


def test_reviews_submit_review_rolls_back_mongo_when_sql_fails() -> None:
    pymongo_stub = types.ModuleType("pymongo")

    class FakeCollection:
        def __init__(self):
            self.deleted = []

        def create_index(self, fields):
            return None

        def insert_one(self, doc):
            return types.SimpleNamespace(inserted_id="mongo123")

        def delete_one(self, query):
            self.deleted.append(query)

    fake_collection = FakeCollection()

    class FakeDB:
        def __getitem__(self, _name):
            return fake_collection

    class FakeMongoClient:
        def __init__(self, uri):
            self.uri = uri

        def __getitem__(self, _name):
            return FakeDB()

    pymongo_stub.MongoClient = FakeMongoClient
    pymongo_stub.DESCENDING = -1
    pymongo_stub.TEXT = "text"

    bson_stub = types.ModuleType("bson")
    bson_stub.ObjectId = lambda value=None: value

    db_stub = types.ModuleType("db_connection")

    fake_cursor = Mock()

    class DummySQLError(Exception):
        pass

    fake_cursor.execute.side_effect = DummySQLError("sql failed")
    fake_conn = Mock()
    fake_conn.cursor.return_value = fake_cursor

    db_stub.get_connection = lambda: fake_conn
    db_stub.release_connection = Mock()

    psycopg2_stub = types.ModuleType("psycopg2")
    psycopg2_stub.Error = DummySQLError

    reviews_mod = load_module_from_path(
        "reviews_mod_rollback",
        LAB_DIR / "reviews.py",
        {
            "pymongo": pymongo_stub,
            "bson": bson_stub,
            "db_connection": db_stub,
            "psycopg2": psycopg2_stub,
        },
    )

    with pytest.raises(DummySQLError):
        reviews_mod.submit_review(1, 1, 1, 4.5, "Great", "Nice place")

    assert fake_collection.deleted == [{"_id": "mongo123"}]
    fake_conn.rollback.assert_called_once()
    db_stub.release_connection.assert_called_once_with(fake_conn)


def test_reviews_get_review_stats_returns_empty_when_no_rows() -> None:
    pymongo_stub = types.ModuleType("pymongo")

    class FakeCollection:
        def create_index(self, fields):
            return None

        def aggregate(self, pipeline):
            return iter([])

    fake_collection = FakeCollection()

    class FakeDB:
        def __getitem__(self, _name):
            return fake_collection

    class FakeMongoClient:
        def __init__(self, uri):
            self.uri = uri

        def __getitem__(self, _name):
            return FakeDB()

    pymongo_stub.MongoClient = FakeMongoClient
    pymongo_stub.DESCENDING = -1
    pymongo_stub.TEXT = "text"

    bson_stub = types.ModuleType("bson")
    bson_stub.ObjectId = lambda value=None: value

    db_stub = types.ModuleType("db_connection")
    db_stub.get_connection = lambda: None
    db_stub.release_connection = lambda conn: None

    psycopg2_stub = types.ModuleType("psycopg2")
    psycopg2_stub.Error = Exception

    reviews_mod = load_module_from_path(
        "reviews_mod_stats",
        LAB_DIR / "reviews.py",
        {
            "pymongo": pymongo_stub,
            "bson": bson_stub,
            "db_connection": db_stub,
            "psycopg2": psycopg2_stub,
        },
    )

    assert reviews_mod.get_review_stats(10) == {}
