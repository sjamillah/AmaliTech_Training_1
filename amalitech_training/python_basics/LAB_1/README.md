# LAB 1: Student Management System

LAB 1 is a menu-driven program for managing students, courses, and enrollments.
It is a good starting point because it introduces IDs, registries, and simple reporting.

## What You Can Do

- Add students (regular, undergraduate, graduate)
- Register courses
- Enroll a student in a course and assign a grade
- View students, courses, and grade report lines
- Calculate average grade across all stored results

## Run It

From the project root:

```powershell
poetry run python -m amalitech_training.python_basics.LAB_1.main
```

## Run The Tests

```powershell
poetry run pytest amalitech_training/python_basics/LAB_1/test_lab1.py -q
```

## Example Session (Short)

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
Select option: 1
Student name: Ama
Age: 20
Year: 2
Student type (regular/undergraduate/graduate): undergraduate
Major: Computer Science
Student added: ...
```
