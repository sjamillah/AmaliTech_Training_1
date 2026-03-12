from datetime import timedelta

import pytest

from amalitech_training.python_basics.LAB_4.rental_service import RentalService
from amalitech_training.python_basics.LAB_4.vehicle import Bike, Car, Truck


def test_rent_vehicle_converts_hours_to_minutes():
    service = RentalService()
    car = Car()
    service.add_vehicle(car)

    service.rent_vehicle(0, 2, "hours")

    assert car.is_available is False
    assert car.rental_duration == timedelta(hours=2)


def test_vehicle_types_have_unique_attributes():
    car = Car()
    bike = Bike()
    truck = Truck()

    assert car.seats == 4
    assert bike.has_helmet is True
    assert truck.load_capacity_tons == 5


def test_return_vehicle_uses_rented_vehicle_list():
    service = RentalService()
    car = Car()
    bike = Bike()
    service.add_vehicle(car)
    service.add_vehicle(bike)

    service.rent_vehicle(1, 30, "minutes")
    returned_index = service.return_vehicle(0)

    assert returned_index == 1
    assert bike.is_available is True
    assert car.is_available is True


def test_return_vehicle_calculates_actual_time_spent():
    service = RentalService()
    truck = Truck()
    service.add_vehicle(truck)

    service.rent_vehicle(0, 2, "hours")
    truck._rented_at -= timedelta(minutes=30)

    price = truck.return_vehicle()

    assert price == pytest.approx(100000, rel=0.05)
    assert truck.is_available is True


def test_rent_vehicle_rejects_invalid_unit():
    service = RentalService()
    car = Car()
    service.add_vehicle(car)

    price = service.rent_vehicle(0, 2, "days")

    assert price is None
    assert car.is_available is True


def test_rent_vehicle_rejects_non_positive_duration():
    service = RentalService()
    bike = Bike()
    service.add_vehicle(bike)

    price = service.rent_vehicle(0, 0, "hours")

    assert price is None
    assert bike.is_available is True


def test_return_vehicle_with_invalid_filtered_index_returns_none():
    service = RentalService()
    car = Car()
    service.add_vehicle(car)
    service.rent_vehicle(0, 30, "minutes")

    returned_index = service.return_vehicle(1)

    assert returned_index is None
    assert car.is_available is False