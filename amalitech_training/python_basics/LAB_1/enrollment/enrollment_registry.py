class EnrollmentRegistry:
    def __init__(self):
        self.enrollments = set() # store the student id and course code as a pair
        self.grades = {}

    def enroll_student(self, student_id, course_code):
        enroll_info = (student_id, course_code)

        if enroll_info in self.enrollments:
            raise ValueError("Student already enrolled")
        
        self.enrollments.add(enroll_info)

    def get_all_enrollments(self):
        return list(self.enrollments)
    
    def assign_grade(self, student_id, course_code, grade):
        enroll_info = (student_id, course_code)

        if enroll_info not in self.enrollments:
            raise ValueError("Student not enrolled in this course")

        if not isinstance(grade, (int, float)):
            raise ValueError("Grade must be a number")

        if not 0 <= grade <= 100:
            raise ValueError("Grade must be between 0 and 100")
        
        self.grades[enroll_info] = grade
        return grade
