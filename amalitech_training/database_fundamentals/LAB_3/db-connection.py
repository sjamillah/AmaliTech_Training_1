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
    """
    Borrow a connection from the pool.

    The pool either gives you an idle existing connection
    or creates a new one (up to maxconn).
    ALWAYS call release_connection() when done!
    """
    conn = connection_pool.getconn()
    return conn


def release_connection(conn):
    """
    Return a connection back to the pool.

    This makes the connection available for other operations.
    NEVER call conn.close() directly — that destroys the connection!
    Use this function instead to return it to the pool.
    """
    connection_pool.putconn(conn)


def close_all_connections():
    """
    Shut down the entire pool.
    Call this when your application is shutting down.
    """
    connection_pool.closeall()
    print("All connections closed.")


@contextmanager
def get_managed_connection():
    """
    Context manager version. Automatically releases connection.

    Usage:
        with get_managed_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
    """
    conn = get_connection()
    try:
        yield conn
    finally:
        release_connection(conn)
