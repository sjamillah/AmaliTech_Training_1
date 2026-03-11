from abc import ABC, abstractmethod
from datetime import datetime, timedelta

class Vehicle(ABC):
    def __init__(self, vehicle_type, cost):
        self._vehicle_type = vehicle_type
        self._cost = cost
        self.is_available = True
        self._rented_at = None
        self._rental_duration = None

    @property
    def vehicle_type(self):
        return self._vehicle_type
    
    @property
    def cost(self):
        return self._cost

    @property
    def rental_duration(self):
        return self._rental_duration

    @abstractmethod
    def calculate_rental_price(self, duration_hours):
        pass
    

    def rent(self, duration_minutes):
        """Rent the vehicle for a duration in minutes"""
        if not self.is_available:
            print(f"{self.vehicle_type} is not available")
            return None

        self._rented_at = datetime.now()
        self._rental_duration = timedelta(minutes=duration_minutes)
        self.is_available = False

        # convert to hours for pricing
        duration_hours = duration_minutes / 60
        price = self.calculate_rental_price(duration_hours)

        print(f"{self.vehicle_type} rented for {duration_minutes} minutes. Price: {price:.2f}")
        return price
    
    def return_vehicle(self):
        """Return the vehicle and calculate actual rental duration"""
        if self.is_available:
            print(f"{self.vehicle_type} was not rented")
            return None

        now = datetime.now()
        actual_duration = now - self._rented_at
        self.is_available = True
        self._rented_at = None
        self._rental_duration = None

        actual_hours = actual_duration.total_seconds() / 3600
        actual_price = self.calculate_rental_price(actual_hours)

        print(f"{self.vehicle_type} returned after {actual_hours:.2f} hours. Total price: {actual_price:.2f}")
        return actual_price

    
class Car(Vehicle):
    cost = 100000

    def __init__(self):
        super().__init__("Car", self.cost)
        self.seats = 4

    def calculate_rental_price(self, duration_hours):
        return self.cost * duration_hours


class Bike(Vehicle):
    cost = 10000

    def __init__(self):
        super().__init__("Bike", self.cost)
        self.has_helmet = True

    def calculate_rental_price(self, duration_hours):
        return self.cost * duration_hours


class Truck(Vehicle):
    cost = 200000

    def __init__(self):
        super().__init__("Truck", self.cost)
        self.load_capacity_tons = 5

    def calculate_rental_price(self, duration_hours):
        return self.cost * duration_hours
        

        
