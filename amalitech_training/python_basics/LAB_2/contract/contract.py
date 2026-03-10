class Contract:
    def __init__(self, taxes):
        if not 0 <= taxes <= 1:
            raise ValueError("Tax rate must be between 0 and 1")

        self.taxes = taxes
        self._salary = None
        self._bonus = None

    @property
    def salary(self):
        return self._salary
    
    @property
    def bonus(self):
        return self._bonus
    
    def set_salary_and_bonus(self, salary, bonus):
        if salary < 0 or bonus < 0:
            raise ValueError("Salary and bonus must be positive")
        self._salary = salary
        self._bonus = bonus

    def calculate_net_salary(self):
        raise NotImplementedError("Will be implemented based on contract type")

class FullTimeContract(Contract):

    @property
    def contract_type_name(self):
        return "Full-Time"
    
    def calculate_net_salary(self):
        return self.salary + self.bonus - (self.taxes * self.salary)

class PartTimeContract(Contract):

    @property
    def contract_type_name(self):
        return "Part-Time"

    def calculate_net_salary(self):
        return self.salary - (self.taxes * self.salary)

class TemporaryContract(Contract):

    @property
    def contract_type_name(self):
        return "Contract"

    def calculate_net_salary(self):
        return (self.salary + self.bonus) - (self.taxes * self.salary * 1.2)
    
class InternContract(Contract):

    @property
    def contract_type_name(self):
        return "Intern"

    def calculate_net_salary(self):
        return self.salary