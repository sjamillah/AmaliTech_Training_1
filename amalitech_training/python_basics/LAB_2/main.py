from .contract.contract_registry import ContractRegistry
from .employee.employee_registry import EmployeeRegistry

employee_registry = EmployeeRegistry()
contract_registry = ContractRegistry()

def add_employee():
    try:
        employee_name = input("Enter employee name: ").strip()
        age = int(input("Enter the age: ").strip())
        department = input("Enter the department they're working in: ").strip()

        employee = employee_registry.add_employee(employee_name, age, department)
        print(f"Employee added: {employee}")
        return employee
    except ValueError as e:
        print(f"Could not add employee: {e}")
        return None

def show_employees():
    """Display all registered employees"""
    employees = employee_registry.get_all_employees()
    if not employees:
        print("No employees registered yet.")
        return
    
    print("\nRegistered Employees: ")
    for emp in employees:
        print(f"{emp.employee_id} | {emp.employee_name} | {emp.department}")

def assign_contract_to_employee():
    employees = employee_registry.get_all_employees()
    if not employees:
        print("No employees found. Add an employee")
        return
    
    print("\nSelect an employee by ID:")
    for emp in employees:
        print(f"{emp.employee_id} | {emp.employee_name} | {emp.department}")

    emp_id = input("Enter employee ID: ").strip()
    employee = employee_registry.get_employee(emp_id)
    if not employee:
        print(f"Employee with ID '{emp_id}' not found")
        return
    
    try:
        print("\nContract Types:")
        print("1 = Full-Time")
        print("2 = Part-Time")
        print("3 = Temporary")
        print("4 = Intern")

        contract_type = input("Enter contract type (1=Full-Time, 2=Part-Time, 3=Contract, 4=Intern): ").strip()
        salary = float(input("Enter salary: ").strip())
        bonus = float(input("Enter bonus: ").strip())
        taxes = float(input("Enter tax rate (%): ")) / 100

        contract = contract_registry.add_salary_and_bonus(employee, contract_type, taxes, salary, bonus)

        print(
            f"Contract assigned to {employee.employee_name} "
            f"({employee.employee_id}) | Type: {contract.contract_type_name} | "
            f"Salary: {contract.salary} | Bonus: {contract.bonus}"
        )
    except ValueError as e:
        print(f"Could not assign contract: {e}")
    
def show_contracts():
    """Show all employee contracts"""
    if not contract_registry.contracts:
        print("No contracts assigned yet.")
        return

    print("\nEmployee Contracts:")
    for emp_id, contract in contract_registry.contracts.items():
        employee = employee_registry.get_employee(emp_id)
        if not employee:
            continue

        net_salary = contract.calculate_net_salary()
        print(
            f"{employee.employee_name} | {employee.department} | "
            f"Contract: {contract.contract_type_name} | "
            f"Salary: {contract.salary} | Bonus: {contract.bonus} | Net: {net_salary}"
        )
        
def calculate_net_salary():
    """Calculate net salary for a single employee"""
    emp_id = input("Enter employee ID: ")
    employee = employee_registry.get_employee(emp_id)
    if not employee:
        print("Employee not found.")
        return
    
    try:
        net = contract_registry.calculate_employee_salary(employee)
        print(f"Net salary for {employee.employee_name}: {net}")
    except ValueError as e:
        print(e)

def menu():
    while True:
        print("\n=== Employee Management System ===")
        print("1. Add Employee")
        print("2. Show Employees")
        print("3. Assign Contract")
        print("4. Show Contracts")
        print("5. Calculate Net Salary")
        print("0. Exit")

        choice = input("Select option: ").strip()

        if choice == '1':
            add_employee()
        elif choice == '2':
            show_employees()
        elif choice == '3':
            assign_contract_to_employee()
        elif choice == '4':
            show_contracts()
        elif choice == '5':
            calculate_net_salary()
        elif choice == '0':
            answer = input("Are you sure you want to exit? (Yes/No): ").strip().lower()
            print("Goodbye" if answer == "yes" else "Returning to menu...")
            if answer == "yes":
                break
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    menu()
