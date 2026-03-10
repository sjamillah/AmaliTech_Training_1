from .contract import (FullTimeContract, PartTimeContract, TemporaryContract, InternContract)

class ContractRegistry:
    def __init__(self):
        self.contracts = {}

    def _create_contract(self, contract_type, taxes):
        contract_map = {
            '1': FullTimeContract,
            '2': PartTimeContract,
            '3': TemporaryContract,
            '4': InternContract
        }

        if contract_type not in contract_map:
            raise ValueError("Invalid contract type")
        
        return contract_map[contract_type](taxes)

    def add_salary_and_bonus(self, employee, contract_type, taxes, salary=0, bonus=0):
        """"Assign salary and bonus to an existing employee if they have valid info"""
        if not all([employee.employee_id, employee.employee_name, employee.department]):
            raise ValueError("Employee information incomplete")
        
        contract = self._create_contract(contract_type, taxes)
        contract.set_salary_and_bonus(salary, bonus)

        self.contracts[employee.employee_id] = contract

        # link the salary and bonus to the employee
        employee.salary = salary
        employee.bonus = bonus
        employee.contract_type = contract.contract_type_name

        return contract

    def calculate_employee_salary(self, employee):
        contract = self.contracts.get(employee.employee_id)
        if not contract:
            raise ValueError("Employee has no contract")
            
        return contract.calculate_net_salary()
