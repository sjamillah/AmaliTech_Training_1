from .rental_service import RentalService
from .vehicle import Car, Bike, Truck

service = RentalService()


def _get_vehicle_index(prompt, available_only=None):
    vehicles = service.show_vehicles(available_only)
    if not vehicles:
        return None

    try:
        return int(input(prompt)) - 1
    except ValueError:
        print("Invalid input")
        return None


def _get_rental_duration():
    raw_duration = input(
        "Enter rental duration (examples: 2, 2 hours, 120 minutes): "
    ).strip().lower()

    if not raw_duration:
        print("Invalid input")
        return None

    parts = raw_duration.split()

    if len(parts) == 1:
        try:
            return int(parts[0]), "hours"
        except ValueError:
            print("Invalid input")
            return None

    try:
        duration = int(parts[0])
    except ValueError:
        print("Invalid input")
        return None

    unit = parts[1]
    return duration, unit

def add_vehicle():
    print("\nVehicle Types")
    print("1. Car")
    print("2. Bike")
    print("3. Truck")

    choice = input("Select vehicle type: ")

    vehicle_map = {"1": Car, "2": Bike, "3": Truck}
    vehicle_class = vehicle_map.get(choice)

    if vehicle_class:
        service.add_vehicle(vehicle_class())
        print(f"{vehicle_class.__name__} added successfully")
    else:
        print("Invalid option")

def rent_vehicle():
    index = _get_vehicle_index("Select vehicle number: ")
    if index is None:
        return

    duration_input = _get_rental_duration()
    if duration_input is None:
        return

    duration, unit = duration_input
    service.rent_vehicle(index, duration, unit)

def return_vehicle():
    index = _get_vehicle_index("Select vehicle number to return: ", available_only=False)
    if index is None:
        return

    service.return_vehicle(index)

def menu():
    while True:
        print("\n=== Vehicle Rental System ===")
        print("1. Add Vehicle")
        print("2. Rent Vehicle")
        print("3. Return Vehicle")
        print("4. List Vehicles")
        print("5. Exit")

        choice = input("Select option: ").strip()

        if choice == "1":
            add_vehicle()
        elif choice == "2":
            rent_vehicle()
        elif choice == "3":
            return_vehicle()
        elif choice == "4":
            service.show_vehicles()
        elif choice == "5":
            print("Goodbye")
            break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    menu()
