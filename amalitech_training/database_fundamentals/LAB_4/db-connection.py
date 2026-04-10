import psycopg2
from dotenv import load_dotenv
from contextlib import contextmanager
import os

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

connection_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=2, maxconn=10, **DB_CONFIG
)

print("Connection pool created successfully.")


def get_connection():
    """Borrow a connection from the pool."""
    return connection_pool.getconn()


def release_connection(conn):
    """Return a connection to the pool. NEVER call conn.close() directly."""
    connection_pool.putconn(conn)


@contextmanager
def get_managed_connection():
    """Context manager — automatically releases connection on exit."""
    conn = get_connection()
    try:
        yield conn
    finally:
        release_connection(conn)


def close_all():
    """Call at application shutdown."""
    connection_pool.closeall()
    print("All connections closed.")
