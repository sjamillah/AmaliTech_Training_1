class Student:
    def __init__(self, student_id, name, age, year):
        self._student_id = student_id
        self.name = name
        self._age = None
        self.age = age
        self._year = None
        self.year = year

    @property
    def student_id(self):
        return self._student_id

    @property
    def age(self):
        return self._age
    
    @property
    def year(self):
        return self._year
    
    @age.setter
    def age(self, value):
        if value < 0:
            raise ValueError("Age cannot be negative")
        self._age = value
    
    @year.setter
    def year(self, value):
        if not Student.is_valid_year(value):
            raise ValueError("Year must be between 1 and 5")
        self._year = value

    @staticmethod
    def is_valid_year(year):
        return 1 <= year <= 5

    def __str__(self):
        return f"{self.name} of {self.age} years old is in the year {self.year}."

    def __repr__(self):
        return f"Student(student_id={self.student_id!r}, name={self.name!r}, age={self.age!r}, year={self.year!r})"
    
    def __eq__(self, other):
        if not isinstance(other, Student):
            return NotImplemented
        return self.student_id == other.student_id

    def generate_report(self):
        return f"Student {self.name} is in year {self.year}."

class UndergraduateStudent(Student):
    def __init__(self, student_id, name, age, year, major):
        super().__init__(student_id, name, age, year)
        self.major = major

    def generate_report(self):
        return f"Undergraduate {self.name} majors in {self.major}"

class GraduateStudent(Student):
    def __init__(self, student_id, name, age, year, research_topic):
        super().__init__(student_id, name, age, year)
        self.research_topic = research_topic

    def generate_report(self):
        return f"Graduate {self.name} researches {self.research_topic}"
