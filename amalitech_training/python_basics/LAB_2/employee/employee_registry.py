from .employee import Employee

class EmployeeRegistry:
    def __init__(self):
        self.employees = {}
        self._next_id = 1

    def _generate_employee_id(self):
        employee_id = f"E{self._next_id:03d}"
        self._next_id += 1
        return employee_id
    
    def add_employee(self, employee_name, age, department):
        """Create employee object and add it to the registry"""
        employee_id = self._generate_employee_id()
        employee = Employee(employee_id, employee_name, age, department)
        self.employees[employee_id] = employee
        return employee
    
    def get_employee(self, employee_id):
        """Return the list of registered employees"""
        return self.employees.get(employee_id)
    
    def get_all_employees(self):
        """Get all employees"""
        return list(self.employees.values())
    
    def show_employees(self):
        """Print all registered employees"""
        for employee in self.employees.values():
            print(employee)

    def __str__(self):
        if not self.employees:
            return "No employees registered"
        return "\n".join(str(employee) for employee in self.employees.values())
