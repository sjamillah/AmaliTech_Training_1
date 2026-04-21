import psycopg2
from contextlib import contextmanager
from datetime import datetime
from db_connection import get_managed_connection

class TableNotAvailable(Exception):
    """Raised when the requested table has a conflicting reservation."""
    pass


class TableTooSmall(Exception):
    """Raised when the table capacity is less than the party size."""
    pass


class TableNotFound(Exception):
    """Raised when the table_id doesn't exist or isn't active."""
    pass


class InvalidTimeSlot(Exception):
    """Raised when end time is not after start time."""
    pass


@contextmanager
def _connection_scope(conn=None):
    """Use caller-provided connection or borrow one from the pool."""
    if conn is not None:
        yield conn
        return

    with get_managed_connection() as managed_conn:
        yield managed_conn


@contextmanager
def _transaction_scope(conn=None):
    """Wrap operations in commit/rollback semantics."""
    with _connection_scope(conn) as active_conn:
        try:
            yield active_conn
            active_conn.commit()
        except Exception:
            active_conn.rollback()
            raise




def book_reservation(
    customer_id: int,
    restaurant_id: int,
    table_id: int,
    party_size: int,
    starts_at: datetime,
    ends_at: datetime,
    special_requests: str = None,
    conn=None,
) -> dict:
    """
    Create a reservation in one transaction.

    The function validates the request, locks the target table, checks for
    overlapping bookings, inserts the reservation, and commits only when all
    checks succeed.
    """
    if ends_at <= starts_at:
        raise InvalidTimeSlot(
            f"ends_at ({ends_at}) must be after starts_at ({starts_at})."
        )
    if party_size < 1:
        raise ValueError("party_size must be at least 1.")

    with _transaction_scope(conn) as active_conn:
        try:
            cursor = active_conn.cursor()

            cursor.execute(
                """
                SELECT table_id, table_number, capacity, is_active
                FROM tables
                WHERE table_id = %s
                FOR UPDATE
                """,
                (table_id,)
            )
            table = cursor.fetchone()

            if not table:
                raise TableNotFound(f"Table {table_id} does not exist.")

            _, table_number, capacity, is_active = table

            if not is_active:
                raise TableNotFound(f"Table {table_number} is not currently active.")

            if capacity < party_size:
                raise TableTooSmall(
                    f"Table {table_number} seats {capacity} people, "
                    f"but party size is {party_size}."
                )

            cursor.execute(
                """
                SELECT reservation_id, starts_at, ends_at
                FROM reservations
                WHERE table_id = %s
                  AND status = 'confirmed'
                  AND starts_at < %s
                  AND ends_at   > %s
                LIMIT 1
                """,
                (table_id, ends_at, starts_at)
            )
            conflict = cursor.fetchone()

            if conflict:
                conflict_id, conf_start, conf_end = conflict
                raise TableNotAvailable(
                    f"Table {table_number} is already booked "
                    f"from {conf_start.strftime('%H:%M')} to {conf_end.strftime('%H:%M')} "
                    f"(reservation #{conflict_id}). "
                    f"Please choose a different table or time."
                )

            cursor.execute(
                """
                INSERT INTO reservations
                    (customer_id, table_id, restaurant_id, party_size,
                     starts_at, ends_at, status, special_requests)
                VALUES (%s, %s, %s, %s, %s, %s, 'confirmed', %s)
                RETURNING reservation_id, created_at
                """,
                (customer_id, table_id, restaurant_id, party_size,
                 starts_at, ends_at, special_requests)
            )
            reservation_id, created_at = cursor.fetchone()

            print(f"BOOKING CONFIRMED: Reservation #{reservation_id} | "
                  f"Table {table_number} | {starts_at.strftime('%Y-%m-%d %H:%M')}")

            return {
                'reservation_id':    reservation_id,
                'customer_id':       customer_id,
                'restaurant_id':     restaurant_id,
                'table_id':          table_id,
                'table_number':      table_number,
                'party_size':        party_size,
                'starts_at':         str(starts_at),
                'ends_at':           str(ends_at),
                'status':            'confirmed',
                'special_requests':  special_requests,
                'created_at':        str(created_at)
            }

        except (TableNotFound, TableTooSmall, TableNotAvailable, InvalidTimeSlot) as e:
            print(f"BOOKING REJECTED: {e}")
            raise

        except psycopg2.Error as e:
            print(f"DATABASE ERROR: {e}")
            raise


def cancel_reservation(reservation_id: int, customer_id: int, conn=None) -> bool:
    """
    Cancel a future reservation owned by the customer.
    """
    with _transaction_scope(conn) as active_conn:
        try:
            cursor = active_conn.cursor()
            cursor.execute(
                """
                UPDATE reservations
                SET status = 'cancelled'
                WHERE reservation_id = %s
                  AND customer_id    = %s
                  AND status         = 'confirmed'
                  AND starts_at      > NOW()
                RETURNING reservation_id
                """,
                (reservation_id, customer_id)
            )
            result = cursor.fetchone()

            if result:
                print(f"Reservation #{reservation_id} cancelled.")
                return True

            print(f"Reservation #{reservation_id} not found or cannot be cancelled.")
            return False

        except psycopg2.Error as e:
            print(f"DATABASE ERROR: {e}")
            raise


def find_available_tables(restaurant_id: int, party_size: int,
                           starts_at: datetime, ends_at: datetime,
                           conn=None) -> list:
    """
    Return active tables that can seat the party and are free in the time slot.
    """
    with _connection_scope(conn) as active_conn:
        cursor = active_conn.cursor()
        cursor.execute(
            """
            WITH busy_tables AS (
                SELECT DISTINCT r.table_id
                FROM reservations r
                WHERE r.restaurant_id = %s
                  AND r.status = 'confirmed'
                  AND r.starts_at < %s
                  AND r.ends_at   > %s
            )
            SELECT
                t.table_id,
                t.table_number,
                t.capacity,
                t.capacity - %s AS extra_seats
            FROM tables t
            WHERE t.restaurant_id = %s
              AND t.is_active = TRUE
              AND t.capacity  >= %s
              AND t.table_id NOT IN (SELECT table_id FROM busy_tables)
            ORDER BY t.capacity ASC
            """,
            (restaurant_id, ends_at, starts_at,
             party_size, restaurant_id, party_size)
        )
        rows = cursor.fetchall()
        return [
            {'table_id': r[0], 'table_number': r[1],
             'capacity': r[2], 'extra_seats': r[3]}
            for r in rows
        ]
