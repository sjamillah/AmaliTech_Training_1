import redis
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from db_connection import get_connection, release_connection

load_dotenv()

REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", "6379")),
    "db": int(os.getenv("REDIS_DB", "0")),
    "decode_responses": True,
}

redis_client = redis.Redis(**REDIS_CONFIG)

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "60"))

def _slot_key(restaurant_id: int, starts_at: datetime, party_size: int) -> str:
    """
    Build the Redis key for one availability request.
    """
    date_str = starts_at.strftime('%Y-%m-%d')
    hour_str = starts_at.strftime('%H')
    return f"availability:{restaurant_id}:{date_str}:{hour_str}:{party_size}"


def _restaurant_pattern(restaurant_id: int) -> str:
    """Return the key pattern for all cache entries of one restaurant."""
    return f"availability:{restaurant_id}:*"


def get_available_tables_cached(
    restaurant_id: int,
    party_size:    int,
    starts_at:     datetime,
    ends_at:       datetime
) -> list:
    """
    Return available tables, using Redis cache when possible.
    """
    cache_key = _slot_key(restaurant_id, starts_at, party_size)

    try:
        cached = redis_client.get(cache_key)
        if cached is not None:
            print(f"CACHE HIT: {cache_key}")
            return json.loads(cached)
    except redis.RedisError as e:
        print(f"Redis error (will use DB): {e}")

    print(f"CACHE MISS: {cache_key} — querying PostgreSQL...")
    tables = _query_available_tables(restaurant_id, party_size, starts_at, ends_at)

    try:
        redis_client.setex(
            name=cache_key,
            time=CACHE_TTL_SECONDS,
            value=json.dumps(tables)
        )
        print(f"CACHED: {cache_key} ({len(tables)} tables) TTL={CACHE_TTL_SECONDS}s")
    except redis.RedisError as e:
        print(f"Could not cache result: {e}")

    return tables


def _query_available_tables(
    restaurant_id: int,
    party_size:    int,
    starts_at:     datetime,
    ends_at:       datetime
) -> list:
    """Run the availability query against PostgreSQL."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            WITH busy_tables AS (
                SELECT DISTINCT r.table_id
                FROM reservations r
                WHERE r.restaurant_id = %s
                  AND r.status = 'confirmed'
                  AND r.starts_at < %s
                  AND r.ends_at   > %s
            )
            SELECT
                t.table_id,
                t.table_number,
                t.capacity,
                t.capacity - %s AS extra_seats
            FROM tables t
            WHERE t.restaurant_id = %s
              AND t.is_active = TRUE
              AND t.capacity  >= %s
              AND t.table_id NOT IN (SELECT table_id FROM busy_tables)
            ORDER BY t.capacity ASC
            """,
            (restaurant_id, ends_at, starts_at,
             party_size, restaurant_id, party_size)
        )
        rows = cursor.fetchall()
        return [
            {
                'table_id':     r[0],
                'table_number': r[1],
                'capacity':     r[2],
                'extra_seats':  r[3]
            }
            for r in rows
        ]
    finally:
        release_connection(conn)


def invalidate_restaurant_cache(restaurant_id: int):
    """
    Delete all cached availability entries for a restaurant.
    """
    pattern = _restaurant_pattern(restaurant_id)
    try:
        cursor = redis_client.scan_iter(pattern)
        deleted = 0
        for key in cursor:
            redis_client.delete(key)
            deleted += 1
        if deleted > 0:
            print(f"CACHE INVALIDATED: {deleted} keys matching '{pattern}'")
        else:
            print(f"No cached keys to invalidate for restaurant {restaurant_id}")
    except redis.RedisError as e:
        print(f"Cache invalidation error: {e}")


def invalidate_slot_cache(restaurant_id: int, starts_at: datetime, party_size: int):
    """Delete the cache entry for one specific slot."""
    key = _slot_key(restaurant_id, starts_at, party_size)
    try:
        redis_client.delete(key)
        print(f"CACHE INVALIDATED: {key}")
    except redis.RedisError as e:
        print(f"Cache error: {e}")


def cache_status():
    """Print all current availability cache keys and their TTL."""
    try:
        keys = list(redis_client.scan_iter("availability:*"))
        print(f"\nCurrent cache entries ({len(keys)}):")
        for key in sorted(keys):
            ttl = redis_client.ttl(key)
            print(f"  {key}  (TTL: {ttl}s)")
    except redis.RedisError as e:
        print(f"Redis error: {e}")
