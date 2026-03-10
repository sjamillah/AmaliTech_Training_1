class Employee:
    def __init__(self, employee_id, employee_name, age, department):
        self._employee_id = employee_id
        self.employee_name = employee_name
        self.department = department
        self._age = None
        self.age = age

    @property
    def employee_id(self):
        return self._employee_id
    
    @property
    def age(self):
        return self._age
    
    @age.setter
    def age(self, value):
        if not 16 <= value <= 60:
            raise ValueError("Working age needs to be between 16 and 60")
        self._age = value

    def __str__(self):
        return f"{self.employee_name} is in the {self.department} department."

    def __repr__(self):
        return f"Employee(employee_id={self.employee_id!r}, name={self.employee_name!r}, age={self.age!r}, department={self.department!r})"

