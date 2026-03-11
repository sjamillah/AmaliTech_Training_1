import pytest

from amalitech_training.python_basics.LAB_2.contract.contract_registry import ContractRegistry
from amalitech_training.python_basics.LAB_2.employee.employee_registry import EmployeeRegistry


def test_employee_age_validation_rejects_invalid_age():
    registry = EmployeeRegistry()

    with pytest.raises(ValueError):
        registry.add_employee("Kojo", 14, "Engineering")


def test_employee_registry_generates_ids():
    registry = EmployeeRegistry()

    employee = registry.add_employee("Esi", 25, "IT")

    assert employee.employee_id == "E001"


def test_full_time_contract_net_salary_calculation():
    employees = EmployeeRegistry()
    contracts = ContractRegistry()

    employee = employees.add_employee("Nana", 28, "HR")
    contracts.add_salary_and_bonus(employee, contract_type="1", taxes=0.1, salary=5000, bonus=1000)

    assert contracts.calculate_employee_salary(employee) == 5500
