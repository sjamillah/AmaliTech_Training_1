from .student_info import Student

class StudentRegistry:
    """Manages a collection of Student objects"""

    def __init__(self):
        self.students = {}
        self._next_id = 1

    def _generate_student_id(self):
        student_id = f"S{self._next_id:03d}"
        self._next_id += 1
        return student_id

    def add_student(self, name, age, year):
        """Create a student object and add it to the registry"""

        student_id = self._generate_student_id()
        
        student = Student(student_id, name, age, year)
        self.students[student_id] = student
        return student

    def get_student(self, student_id):
        """Return the list of registered students"""
        return self.students.get(student_id)
    
    def get_all_students(self):
        """Get all students"""
        return list(self.students.values())
    
    def show_students(self):
        """Print all registered students"""
        for student in self.students.values():
            print(student)

    def __str__(self):
        if not self.students:
            return "No students in registry"
        return "\n".join(str(student) for student in self.students.values())
