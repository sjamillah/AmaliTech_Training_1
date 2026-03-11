class RentalService:
    def __init__(self):
        self.vehicles = []

    def add_vehicle(self, vehicle):
        if vehicle not in self.vehicles:
            self.vehicles.append(vehicle)

    def _get_filtered_vehicles(self, available_only=None):
        if available_only is None:
            return list(enumerate(self.vehicles))

        return [
            (index, vehicle)
            for index, vehicle in enumerate(self.vehicles)
            if vehicle.is_available is available_only
        ]

    def show_vehicles(self, available_only=None):
        filtered_vehicles = self._get_filtered_vehicles(available_only)

        if not filtered_vehicles:
            if available_only is True:
                print("No available vehicles")
            elif available_only is False:
                print("No rented vehicles")
            else:
                print("No vehicles available")
            return []

        for display_index, (_, v) in enumerate(filtered_vehicles, start=1):
            status = "Available" if v.is_available else "Not Available"
            print(f"{display_index}. {v.vehicle_type} - {status}")

        return filtered_vehicles

    def _convert_duration_to_minutes(self, duration, unit):
        unit_map = {
            "h": "hours",
            "hr": "hours",
            "hrs": "hours",
            "hour": "hours",
            "hours": "hours",
            "m": "minutes",
            "min": "minutes",
            "mins": "minutes",
            "minute": "minutes",
            "minutes": "minutes",
        }

        normalized_unit = unit_map.get(unit.strip().lower())

        if normalized_unit == "hours":
            return duration * 60
        if normalized_unit == "minutes":
            return duration
        return None

    def rent_vehicle(self, index, duration, unit="hours"):
        try:
            vehicle = self.vehicles[index]

            duration_minutes = self._convert_duration_to_minutes(duration, unit)
            if duration_minutes is None:
                print("Invalid unit. Use 'hours' or 'minutes'.")
                return

            if duration_minutes <= 0:
                print("Duration must be greater than 0")
                return

            vehicle.rent(duration_minutes)

        except IndexError:
            print("Invalid vehicle selection")

    def return_vehicle(self, index):
        rented_vehicles = self._get_filtered_vehicles(False)

        try:
            actual_index, vehicle = rented_vehicles[index]
            vehicle.return_vehicle()
            return actual_index
        except IndexError:
            print("Invalid vehicle selection")
