"""
db.py — Shared MySQL connection module for the Hotel Management System.

Every module (main.py, gui.py, cli/rooms.py, cli/booking.py,
cli/billing.py, cli/service.py, cli/staff.py, cli/guest.py, ...) should
import get_connection() from here instead of opening its own connection.
This keeps a single, consistent place to change host / credentials.
"""

import sys
import mysql.connector
from mysql.connector import Error


DB_CONFIG = {
    "host": "sql12.freesqldatabase.com",
    "port": 3306,
    "user": "sql12832782",        # <-- replace if your username differs
    "password": "ypxHYNxUHt",  # <-- put your real password here
    "database": "sql12832782",
}


def get_connection():
    """
    Open and return a new MySQL connection using DB_CONFIG.

    Returns a live mysql.connector connection on success.
    Raises mysql.connector.Error if the TCP/auth connection fails.
    Raises RuntimeError if the driver returns an object that reports
    is_connected() == False (should not normally happen, but prevents
    callers from receiving a silent None and crashing later).
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
        # Guard: connection object exists but reports not connected.
        raise RuntimeError(
            "[db.py] mysql.connector.connect() returned an object "
            "but is_connected() is False — check DB_CONFIG."
        )
    except Error as e:
        print(f"[db.py] Could not connect to MySQL: {e}", file=sys.stderr)
        raise


def get_cursor(conn, dictionary=True):
    return conn.cursor(dictionary=dictionary)


def close_connection(conn):
    if conn is not None and conn.is_connected():
        conn.close()


if __name__ == "__main__":
    # Quick manual test run python db.py to check the connection
    try:
        connection = get_connection()
        cursor = get_cursor(connection, dictionary=False)
        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]
        print("Connected successfully. Tables found:")
        for t in tables:
            print(f"  - {t}")
        cursor.close()
        close_connection(connection)
    except Error:
        print("Connection test failed — check DB_CONFIG values above.")