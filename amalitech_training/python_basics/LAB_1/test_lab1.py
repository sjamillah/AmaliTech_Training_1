import pytest

from amalitech_training.python_basics.LAB_1.courses.course_registry import CourseRegistry
from amalitech_training.python_basics.LAB_1.enrollment.enrollment_registry import EnrollmentRegistry
from amalitech_training.python_basics.LAB_1.students.student_registry import StudentRegistry


def test_student_registry_creates_sequential_ids():
    registry = StudentRegistry()

    first = registry.add_student("Ama", 20, 2)
    second = registry.add_student("Kojo", 22, 3)

    assert first.student_id == "S001"
    assert second.student_id == "S002"


def test_course_registry_rejects_duplicate_code():
    registry = CourseRegistry()
    registry.add_course("CS101", "Python Basics", "Mr. Doe")

    with pytest.raises(ValueError):
        registry.add_course("CS101", "Another Course", "Ms. Smith")


def test_enrollment_records_grade_for_registered_pair():
    students = StudentRegistry()
    courses = CourseRegistry()
    enrollments = EnrollmentRegistry()

    student = students.add_student("Akosua", 19, 1)
    course = courses.add_course("MTH100", "Algebra", "Mrs. Mensah")

    enrollments.enroll_student(student.student_id, course.course_code)
    enrollments.assign_grade(student.student_id, course.course_code, 88.5)

    assert enrollments.grades[(student.student_id, course.course_code)] == 88.5


def test_enrollment_rejects_grade_outside_0_to_100():
    students = StudentRegistry()
    courses = CourseRegistry()
    enrollments = EnrollmentRegistry()

    student = students.add_student("Akosua", 19, 1)
    course = courses.add_course("MTH100", "Algebra", "Mrs. Mensah")

    enrollments.enroll_student(student.student_id, course.course_code)

    with pytest.raises(ValueError, match="between 0 and 100"):
        enrollments.assign_grade(student.student_id, course.course_code, 120)


def test_student_year_ranges_depend_on_student_type():
    registry = StudentRegistry()

    regular = registry.add_student("Ama", 20, 6, student_type="regular")
    undergraduate = registry.add_student(
        "Kojo", 21, 4, student_type="undergraduate", major="Computer Science"
    )
    graduate = registry.add_student(
        "Esi", 25, 2, student_type="graduate", research_topic="AI"
    )

    assert regular.year == 6
    assert undergraduate.year == 4
    assert graduate.year == 2

    with pytest.raises(ValueError, match="1 and 6"):
        registry.add_student("A", 20, 7, student_type="regular")

    with pytest.raises(ValueError, match="1 and 4"):
        registry.add_student("B", 20, 5, student_type="undergraduate", major="Math")

    with pytest.raises(ValueError, match="1 and 2"):
        registry.add_student("C", 20, 3, student_type="graduate", research_topic="ML")
