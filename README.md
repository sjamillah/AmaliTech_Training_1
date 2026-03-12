# AmaliTech Training 1 (Python Basics)

This repo is a collection of five hands-on Python labs I worked on during training.
Each lab focuses on object-oriented design, clean structure, and basic testing with `pytest`.

If you are reviewing this project for the first time, start with LAB 1 and move upward. The labs get a little richer as you go.

## What Is In Here?

- `LAB_1`: Student, course, and enrollment workflow
- `LAB_2`: Employee + contract management
- `LAB_3`: Library inventory with save/load JSON support
- `LAB_4`: Vehicle rental flow (rent/return + time handling)
- `LAB_5`: Personal finance tracker with report output

Full paths are under `amalitech_training/python_basics/`.

## Requirements

- Python 3.10+
- Poetry (recommended)

## Setup

From the project root:

```powershell
poetry install
```

Alternative setup with virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install pytest
```

## Running The Labs

Use module mode from the project root.

```powershell
poetry run python -m amalitech_training.python_basics.LAB_1.main
poetry run python -m amalitech_training.python_basics.LAB_2.main
poetry run python -m amalitech_training.python_basics.LAB_3.main
poetry run python -m amalitech_training.python_basics.LAB_4.main
poetry run python -m amalitech_training.python_basics.LAB_5.main
```

## Running Tests

Run everything:

```powershell
poetry run pytest -q
```

Run one lab test file (example):

```powershell
poetry run pytest amalitech_training/python_basics/LAB_3/test_lab3.py -q
```

## Example Console Output

### LAB 1 Menu

```text
=== Student Management System ===
1. Add Student
2. Add Course
3. Enroll student
4. Show students
5. Show courses
6. Show reports
7. Calculate average grade
8. Show student type reports
0. Exit
Select option:
```

### LAB 5 Report Snapshot

```text
=== Personal Finance Report ===
Accounts: 2
Total balance: 1525.00
Income: 750.00
Expense: 120.00
Saving: 100.00
Net cashflow: 530.00
- A-100 (Ama): balance=1380.00, income=500.00, expense=120.00, saving=0.00
- A-200 (Kojo): balance=145.00, income=250.00, expense=0.00, saving=100.00
```

## Per-Lab Readme Files

- `amalitech_training/python_basics/LAB_1/README.md`
- `amalitech_training/python_basics/LAB_2/README.md`
- `amalitech_training/python_basics/LAB_3/README.md`
- `amalitech_training/python_basics/LAB_4/README.md`
- `amalitech_training/python_basics/LAB_5/README.md`
