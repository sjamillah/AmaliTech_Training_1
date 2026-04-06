from db_connection import get_connection, release_connection
from redis_cache import get_course_progress
from forum import get_thread_count_per_course
from dotenv import load_dotenv
import os

load_dotenv()

DASHBOARD_DEMO_STUDENT_ID = int(os.getenv("DASHBOARD_DEMO_STUDENT_ID", "1"))


def get_student_dashboard(student_id: int) -> dict:
    """
    Build and return the student dashboard data.
    """
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT full_name, email FROM students WHERE student_id = %s",
            (student_id,)
        )
        student = cursor.fetchone()
        if not student:
            return {'error': f'Student {student_id} not found'}

        full_name, email = student

        cursor.execute(
            """
            SELECT
                c.course_id,
                c.title           AS course_title,
                i.full_name       AS instructor_name,
                e.enrolled_at,
                c.total_lessons
            FROM enrollments e
            JOIN courses c     ON e.course_id = c.course_id
            JOIN instructors i ON c.instructor_id = i.instructor_id
            WHERE e.student_id = %s
            ORDER BY e.enrolled_at DESC
            """,
            (student_id,)
        )
        enrolled_courses = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                m.course_id,
                MAX(lc.completed_at) AS last_activity
            FROM lesson_completions lc
            JOIN lessons l ON lc.lesson_id = l.lesson_id
            JOIN modules m ON l.module_id = m.module_id
            WHERE lc.student_id = %s
            GROUP BY m.course_id
            """,
            (student_id,)
        )
        activity_map = {row[0]: row[1] for row in cursor.fetchall()}

    finally:
        release_connection(conn)

    course_ids = [row[0] for row in enrolled_courses]
    thread_counts = get_thread_count_per_course(course_ids)

    courses_data = []

    for course_id, title, instructor, enrolled_at, total_lessons in enrolled_courses:
        progress_pct = get_course_progress(student_id, course_id)

        courses_data.append({
            'course_id':      course_id,
            'title':          title,
            'instructor':     instructor,
            'enrolled_at':    str(enrolled_at),
            'total_lessons':  total_lessons,
            'progress_pct':   progress_pct,
            'last_activity':  str(activity_map.get(course_id, 'Never')),
            'forum_threads':  thread_counts.get(course_id, 0),
            'status':         _get_status(progress_pct)
        })

    return {
        'student_id':  student_id,
        'full_name':   full_name,
        'email':       email,
        'course_count': len(courses_data),
        'courses':     courses_data
    }


def _get_status(pct: float) -> str:
    """Map completion percentage to a human-readable status."""
    if pct == 0:
        return 'Not Started'
    elif pct < 25:
        return 'Just Begun'
    elif pct < 75:
        return 'In Progress'
    elif pct < 100:
        return 'Almost Done'
    else:
        return 'Completed!'


def get_time_between_lessons(student_id: int) -> list:
    """
    Return timeline entries with elapsed time between lesson completions.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                l.title                   AS lesson_title,
                c.title                   AS course_title,
                lc.completed_at,
                LAG(lc.completed_at) OVER (
                    PARTITION BY lc.student_id
                    ORDER BY lc.completed_at
                )                         AS prev_completed_at,
                lc.completed_at - LAG(lc.completed_at) OVER (
                    PARTITION BY lc.student_id
                    ORDER BY lc.completed_at
                )                         AS time_since_last

            FROM lesson_completions lc
            JOIN lessons l  ON lc.lesson_id = l.lesson_id
            JOIN modules m  ON l.module_id = m.module_id
            JOIN courses c  ON m.course_id = c.course_id
            WHERE lc.student_id = %s
            ORDER BY lc.completed_at
            """,
            (student_id,)
        )
        rows = cursor.fetchall()

        return [
            {
                'lesson':           row[0],
                'course':           row[1],
                'completed_at':     str(row[2]),
                'time_since_last':  str(row[4]) if row[4] else 'First lesson'
            }
            for row in rows
        ]

    finally:
        release_connection(conn)

if __name__ == "__main__":
    import json

    print("=" * 60)
    print("Student Dashboard Demo")
    print("=" * 60)

    dashboard = get_student_dashboard(student_id=DASHBOARD_DEMO_STUDENT_ID)
    print(json.dumps(dashboard, indent=2, default=str))

    print("\n" + "=" * 60)
    print("Time Between Lessons (LAG Window Function)")
    print("=" * 60)

    timeline = get_time_between_lessons(student_id=DASHBOARD_DEMO_STUDENT_ID)
    for entry in timeline:
        print(f"  {entry['lesson']:<30} | {entry['time_since_last']}")
