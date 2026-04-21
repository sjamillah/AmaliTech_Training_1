import psycopg2
from contextlib import contextmanager

from db_connection import get_managed_connection

# Custom exception


class AlreadyEnrolled(Exception):
    """Raised when student is already enrolled in the course."""

    pass


class PrerequisiteNotMet(Exception):
    """Raised when student hasn't completed a prerequisite course."""

    pass


class CourseNotFound(Exception):
    """Raised when the requested course doesn't exist."""

    pass


# Main enrollment function


@contextmanager
def _connection_scope(conn=None):
    """Use caller-provided connection or borrow one from the pool."""
    if conn is not None:
        yield conn
        return

    with get_managed_connection() as managed_conn:
        yield managed_conn


@contextmanager
def _transaction_scope(conn=None):
    """Wrap operations in commit/rollback semantics."""
    with _connection_scope(conn) as active_conn:
        try:
            yield active_conn
            active_conn.commit()
        except Exception:
            active_conn.rollback()
            raise


def enroll_student(student_id: int, course_id: int, conn=None) -> dict:
    """
    Enroll a student in a course as a single atomic transaction.

    Args:
        student_id: The ID of the student to enroll
        course_id:  The ID of the course to enroll in

    Returns:
        dict with enrollment_id and enrolled_at on success

    Raises:
        AlreadyEnrolled:    if student is already in this course
        PrerequisiteNotMet: if a required course isn't completed
        CourseNotFound:     if the course doesn't exist
        psycopg2.Error:     on database errors
    """
    with _transaction_scope(conn) as active_conn:
        try:
            cursor = active_conn.cursor()

            # STEP 1: Verify the course exists
            cursor.execute(
                "SELECT course_id, title FROM courses WHERE course_id = %s", (course_id,)
            )
            course = cursor.fetchone()
            if not course:
                raise CourseNotFound(f"Course {course_id} does not exist.")

            _, course_title = course
            print(f"Enrolling student {student_id} in '{course_title}'...")

            # STEP 2: Check for duplicate enrollment
            cursor.execute(
                """SELECT enrollment_id
                   FROM enrollments
                   WHERE student_id = %s AND course_id = %s""",
                (student_id, course_id),
            )
            if cursor.fetchone():
                raise AlreadyEnrolled(
                    f"Student {student_id} is already enrolled in course {course_id}."
                )

            # STEP 3: Get all prerequisites for this course
            cursor.execute(
                """SELECT cp.prerequisite_id, c.title
                   FROM course_prerequisites cp
                   JOIN courses c ON cp.prerequisite_id = c.course_id
                   WHERE cp.course_id = %s""",
                (course_id,),
            )
            prerequisites = cursor.fetchall()
            print(f"  Found {len(prerequisites)} prerequisite(s) to check.")

            # STEP 4: Verify each prerequisite is completed
            # A prerequisite is "completed" when the student has
            # finished ALL lessons in that course.
            for prereq_id, prereq_title in prerequisites:
                print(f"  Checking prerequisite: '{prereq_title}' (ID: {prereq_id})")

                cursor.execute(
                    """
                    SELECT
                        c.total_lessons,
                        COUNT(lc.completion_id) AS lessons_completed
                    FROM enrollments e
                    JOIN courses c
                        ON e.course_id = c.course_id
                    -- Get all lessons in the prerequisite course
                    LEFT JOIN modules m
                        ON m.course_id = c.course_id
                    LEFT JOIN lessons l
                        ON l.module_id = m.module_id
                    -- Check how many THIS student has completed
                    LEFT JOIN lesson_completions lc
                        ON lc.lesson_id = l.lesson_id
                        AND lc.student_id = e.student_id
                    WHERE e.student_id = %s
                      AND e.course_id = %s
                    GROUP BY c.total_lessons
                    """,
                    (student_id, prereq_id),
                )
                result = cursor.fetchone()

                # Not enrolled OR hasn't completed all lessons
                if not result:
                    raise PrerequisiteNotMet(
                        f"Student {student_id} is not enrolled in prerequisite "
                        f"course '{prereq_title}' (ID: {prereq_id})."
                    )

                total_lessons, completed_count = result
                if completed_count < total_lessons:
                    raise PrerequisiteNotMet(
                        f"Student {student_id} has only completed {completed_count}/"
                        f"{total_lessons} lessons in prerequisite '{prereq_title}'. "
                        f"Must finish all lessons first."
                    )

                print(
                    f"  Prerequisite '{prereq_title}' satisfied! ({completed_count}/{total_lessons})"
                )

            # STEP 5: Insert the enrollment record
            cursor.execute(
                """INSERT INTO enrollments (student_id, course_id)
                   VALUES (%s, %s)
                   RETURNING enrollment_id, enrolled_at""",
                (student_id, course_id),
            )
            enrollment_id, enrolled_at = cursor.fetchone()

            print(f"SUCCESS: Enrolled! (enrollment_id={enrollment_id}, at={enrolled_at})")

            return {
                "enrollment_id": enrollment_id,
                "student_id": student_id,
                "course_id": course_id,
                "course_title": course_title,
                "enrolled_at": enrolled_at,
            }

        except (AlreadyEnrolled, PrerequisiteNotMet, CourseNotFound) as e:
            print(f"ENROLLMENT REJECTED: {e}")
            raise

        except psycopg2.Error as e:
            print(f"DATABASE ERROR: {e}")
            raise


def complete_lesson(
    student_id: int,
    lesson_id: int,
    score: float = None,
    conn=None,
) -> dict:
    """
    Record that a student has completed a lesson.

    Args:
        student_id: The student's ID
        lesson_id:  The lesson's ID
        score:      Optional quiz score (0.0 - 100.0)

    Returns:
        dict with completion details
    """
    with _transaction_scope(conn) as active_conn:
        try:
            cursor = active_conn.cursor()

            cursor.execute(
                """INSERT INTO lesson_completions (student_id, lesson_id, score)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (student_id, lesson_id) DO NOTHING
                   RETURNING completion_id, completed_at""",
                (student_id, lesson_id, score),
            )
            result = cursor.fetchone()

            if result:
                completion_id, completed_at = result
                print(f"Lesson {lesson_id} marked complete for student {student_id}.")

                try:
                    from redis_cache import invalidate_progress_cache_for_lesson

                    invalidate_progress_cache_for_lesson(student_id, lesson_id)
                except ImportError:
                    pass  # Redis not available

                return {
                    "completion_id": completion_id,
                    "completed_at": str(completed_at),
                }

            print(f"Lesson {lesson_id} was already completed by student {student_id}.")
            return None

        except psycopg2.Error as e:
            print(f"DATABASE ERROR: {e}")
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Enrollment Transaction")
    print("=" * 60)

    # Test 1: Valid enrollment (should succeed)
    try:
        result = enroll_student(student_id=2, course_id=2)
        print(f"Test 1 PASSED: {result}")
    except Exception as e:
        print(f"Test 1 result: {e}")

    print()

    # Test 2: Duplicate enrollment (should fail gracefully)
    try:
        result = enroll_student(student_id=1, course_id=1)
        print(f"Test 2 unexpected success: {result}")
    except AlreadyEnrolled as e:
        print(f"Test 2 PASSED (caught expected error): {e}")

    print()

    # Test 3: Prerequisite not met (should fail gracefully)
    try:
        result = enroll_student(student_id=2, course_id=3)
        print(f"Test 3 unexpected success: {result}")
    except PrerequisiteNotMet as e:
        print(f"Test 3 PASSED (caught expected error): {e}")
