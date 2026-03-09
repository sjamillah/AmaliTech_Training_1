from ..students.student_info import Student
from ..courses.courses_info import Course

class Enroll:
    def __init__(self, student: Student, course: Course):
        self.student = student
        self.course = course

    def __str__(self):
        return f"{self.student.name} in year {self.student.year} is enrolled in {self.course.course_name} (Facilitator: {self.course.course_facilitator})"

    def __repr__(self):
        return f"Student(name={self.student.name!r}, year={self.student.year!r}, course={self.course.course_name!r}, Facilitator={self.course_facilitator!r})."
