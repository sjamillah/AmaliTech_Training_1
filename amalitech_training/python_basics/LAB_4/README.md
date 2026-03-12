# LAB 4: Vehicle Rental System

LAB 4 is a straightforward rental flow for different vehicle types.
It focuses on duration handling (minutes vs hours), availability tracking, and return logic.

## What You Can Do

- Add vehicles (`Car`, `Bike`, `Truck`)
- Rent a selected vehicle for a chosen duration
- Return rented vehicles
- List current vehicle availability

## Run It

From the project root:

```powershell
poetry run python -m amalitech_training.python_basics.LAB_4.main
```

## Run The Tests

```powershell
poetry run pytest amalitech_training/python_basics/LAB_4/test_lab4.py -q
```

## Example Session (Short)

```text
=== Vehicle Rental System ===
1. Add Vehicle
2. Rent Vehicle
3. Return Vehicle
4. List Vehicles
5. Exit
Select option: 1

Vehicle Types
1. Car
2. Bike
3. Truck
Select vehicle type: 1
Car added successfully
```
