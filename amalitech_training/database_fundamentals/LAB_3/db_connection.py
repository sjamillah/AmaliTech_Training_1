from psycopg2 import pool
from dotenv import load_dotenv
from contextlib import contextmanager
import os

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),
    "database": os.getenv("DB_NAME_1"),
    "user": os.getenv("DB_USER_1"),
    "password": os.getenv("DB_PASSWORD_1"),
}

connection_pool = pool.ThreadedConnectionPool(
    minconn=2, maxconn=10, **DB_CONFIG
)

print("Connection pool created successfully.")


def get_connection():
    """
    Get a connection from the pool.

    The pool returns an available connection or creates a new one
    until the configured limit is reached.
    """
    conn = connection_pool.getconn()
    return conn


def release_connection(conn):
    """
    Return a connection to the pool so it can be reused.
    """
    connection_pool.putconn(conn)


def close_all_connections():
    """
    Close every connection managed by the pool.
    """
    connection_pool.closeall()
    print("All connections closed.")


@contextmanager
def get_managed_connection():
    """
    Context manager that automatically returns the connection to the pool.

    Example:
        with get_managed_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
    """
    conn = get_connection()
    try:
        yield conn
    finally:
        release_connection(conn)
