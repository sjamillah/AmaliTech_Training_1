import redis
import os
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

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))


def get_cache_key(student_id: int, course_id: int) -> str:
    """
    Build the Redis key for a student's course progress.
    """
    return f'progress:{student_id}:{course_id}'


def _calculate_progress_from_db(student_id: int, course_id: int) -> float:
    """
    Query PostgreSQL and calculate completion percentage.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                c.total_lessons,
                COUNT(lc.completion_id) AS completed_lessons
            FROM enrollments e
            JOIN courses c
                ON e.course_id = c.course_id
            LEFT JOIN modules m
                ON m.course_id = c.course_id
            LEFT JOIN lessons l
                ON l.module_id = m.module_id
            LEFT JOIN lesson_completions lc
                ON lc.lesson_id = l.lesson_id
                AND lc.student_id = e.student_id
            WHERE e.student_id = %s
              AND e.course_id  = %s
            GROUP BY c.total_lessons
            """,
            (student_id, course_id)
        )
        result = cursor.fetchone()

        if not result or result[0] == 0:
            return 0.0

        total_lessons, completed_count = result
        percentage = round((completed_count / total_lessons) * 100, 2)
        return percentage

    finally:
        release_connection(conn)


def get_course_progress(student_id: int, course_id: int) -> float:
    """
    Return course completion percentage, using Redis cache when available.
    """
    cache_key = get_cache_key(student_id, course_id)

    try:
        cached_value = redis_client.get(cache_key)
        if cached_value is not None:
            print(f"CACHE HIT: {cache_key} = {cached_value}%")
            return float(cached_value)
    except redis.RedisError as e:
        print(f"Redis unavailable ({e}), calculating from DB...")

    print(f"CACHE MISS: {cache_key} - querying PostgreSQL...")
    progress = _calculate_progress_from_db(student_id, course_id)

    try:
        redis_client.setex(
            name=cache_key,
            time=CACHE_TTL_SECONDS,
            value=str(progress)
        )
        print(f"CACHED: {cache_key} = {progress}% (TTL: {CACHE_TTL_SECONDS}s)")
    except redis.RedisError as e:
        print(f"Warning: Could not cache to Redis ({e})")

    return progress


def invalidate_progress_cache(student_id: int, course_id: int):
    """
    Remove cached progress for a specific student and course.
    """
    cache_key = get_cache_key(student_id, course_id)
    try:
        deleted = redis_client.delete(cache_key)
        if deleted:
            print(f"CACHE INVALIDATED: {cache_key}")
        else:
            print(f"Key not in cache (nothing to invalidate): {cache_key}")
    except redis.RedisError as e:
        print(f"Warning: Could not invalidate cache ({e})")


def invalidate_progress_cache_for_lesson(student_id: int, lesson_id: int):
    """
    Invalidate cache for the course linked to a completed lesson.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT m.course_id
               FROM lessons l
               JOIN modules m ON l.module_id = m.module_id
               WHERE l.lesson_id = %s""",
            (lesson_id,)
        )
        result = cursor.fetchone()
        if result:
            course_id = result[0]
            invalidate_progress_cache(student_id, course_id)
    finally:
        release_connection(conn)


def get_all_progress_for_student(student_id: int) -> dict:
    """
    Return progress percentages for all courses a student is enrolled in.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT course_id FROM enrollments WHERE student_id = %s",
            (student_id,)
        )
        course_ids = [row[0] for row in cursor.fetchall()]
    finally:
        release_connection(conn)

    progress_map = {}
    for course_id in course_ids:
        progress_map[course_id] = get_course_progress(student_id, course_id)

    return progress_map
