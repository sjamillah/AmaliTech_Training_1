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
