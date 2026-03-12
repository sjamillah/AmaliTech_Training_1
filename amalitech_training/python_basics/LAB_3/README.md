# LAB 3: Library Inventory System

LAB 3 introduces a mini library app with multiple resource types and JSON persistence.
This is where the project starts to feel closer to a real-world workflow.

## What You Can Do

- Add resources: Book, EBook, AudioBook, and Borrow records
- Borrow and return resources by ID
- Search resources by title
- View categorized output and report lines
- Save current data to JSON and load it later

## Run It

From the project root:

```powershell
poetry run python -m amalitech_training.python_basics.LAB_3.main
```

## Run The Tests

```powershell
poetry run pytest amalitech_training/python_basics/LAB_3/test_lab3.py -q
```

## Example Session (Short)

```text
=== Library Inventory System ===
1. Add Resource
2. Borrow Resource
3. Return Resource
4. List Resources
5. Search by Title
6. Show Categories
7. Show Report
8. Save Data
9. Load Data
0. Exit
Select option: 8
Enter file name (default: lab3_library_data.json):
Saved 1 resource(s) to C:\...\lab3_library_data.json
```
