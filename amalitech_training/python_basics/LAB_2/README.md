# LAB 2: Employee Management System

LAB 2 builds on the registry idea from LAB 1 and adds contract handling.
The main focus here is validation and salary calculation.

## What You Can Do

- Add employees with age checks
- Assign contracts (full-time, part-time, temporary, intern)
- Include salary, bonus, and tax values
- View all contracts and calculate a specific employee's net salary

## Run It

From the project root:

```powershell
poetry run python -m amalitech_training.python_basics.LAB_2.main
```

## Run The Tests

```powershell
poetry run pytest amalitech_training/python_basics/LAB_2/test_lab2.py -q
```

## Example Session (Short)

```text
=== Employee Management System ===
1. Add Employee
2. Show Employees
3. Assign Contract
4. Show Contracts
5. Calculate Net Salary
0. Exit
Select option: 1
Enter employee name: Esi
Enter the age: 25
Enter the department they're working in: IT
Employee added: ...
```
