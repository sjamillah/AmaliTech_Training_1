class Course:
    def __init__(self, course_code, course_name, course_facilitator):
        self.course_code = course_code
        self.course_name = course_name
        self.course_facilitator = course_facilitator

    def __str__(self):
        return f"The course is {self.course_name} and taught by {self.course_facilitator}."
    
    def __repr__(self):
        return f"Course(code={self.course_code!r}), Course(name={self.course_name!r}), Facilitator(name={self.course_facilitator!r})."
