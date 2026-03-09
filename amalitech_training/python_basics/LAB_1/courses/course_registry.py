from .courses_info import Course

class CourseRegistry:
    def __init__(self):
        self.courses = {}

    def add_course(self, course_code, course_name, course_facilitator):
        """Adds a single course to the registry"""
        if course_code in self.courses:
            raise ValueError(f"Course code {course_code} already exists")
        course = Course(course_code, course_name, course_facilitator)
        self.courses[course_code] = course
        return course
    
    def get_course(self, course_code):
        return self.courses.get(course_code)

    def get_all_courses(self):
        """Retrieves all the courses"""
        return list(self.courses.values())

    