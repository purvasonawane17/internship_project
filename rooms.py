"""
cli/rooms.py
============
Room Management module for the Hotel Management System CLI.

Functions:
    add_room()              — insert a new room record
    show_rooms()            — list all rooms in a formatted table
    get_room_numbers()      — return a list of all room numbers (used by housekeeping)
    update_room()           — update a room by room_id (blank field = keep existing)
    delete_room()           — remove a room by room_id
    search_room_by_status() — filter rooms by status

All database connections use try/finally to guarantee clean-up.
The interactive CLI menu is guarded by `if __name__ == "__main__":`.
"""

from db import get_connection


# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

def add_room():
    """Prompt for room details and insert a new row into `rooms`."""
    room_number     = input("Room Number                              : ").strip()
    room_type       = input("Room Type (Single/Double/Deluxe/Suite)   : ").strip()
    price_per_night = input("Price Per Night                          : ").strip()
    status          = input("Status (Available/Booked/Maintenance)    : ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO rooms(room_number, room_type, price_per_night, status) "
            "VALUES (%s, %s, %s, %s)",
            (room_number, room_type, price_per_night, status),
        )
        conn.commit()
        print("Room Added Successfully!")
    except Exception as e:
        print(f"Error adding room: {e}")
    finally:
        cursor.close()
        conn.close()


def show_rooms():
    """Fetch and print every room from the `rooms` table."""
    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM rooms ORDER BY room_id")
        rows = cursor.fetchall()

        if not rows:
            print("No room records found.")
            return

        print(f"\n{'ID':<5}{'Room No':<12}{'Type':<15}{'Price/Night':<15}{'Status':<15}")
        print("-" * 62)
        for row in rows:
            print(f"{row[0]:<5}{row[1]:<12}{row[2]:<15}{str(row[3]):<15}{row[4]:<15}")
        print()
    except Exception as e:
        print(f"Error fetching rooms: {e}")
    finally:
        cursor.close()
        conn.close()


def get_room_numbers():
    """Return a list of all room numbers. Used by housekeeping assignment."""
    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT room_number FROM rooms")
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        print(f"Error fetching room numbers: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def update_room():
    """Update a room record. Blank input keeps the existing value."""
    room_id = input("Enter Room ID to update: ").strip()

    print("(Press Enter to leave a field unchanged.)")
    room_number     = input("Room Number     : ").strip()
    room_type       = input("Room Type       : ").strip()
    price_per_night = input("Price Per Night : ").strip()
    status          = input("Status          : ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM rooms WHERE room_id = %s", (room_id,))
        existing = cursor.fetchone()

        if not existing:
            print("Room ID not found.")
            return

        cursor.execute(
            """
            UPDATE rooms
               SET room_number     = %s,
                   room_type       = %s,
                   price_per_night = %s,
                   status          = %s
             WHERE room_id = %s
            """,
            (
                room_number     or existing[1],
                room_type       or existing[2],
                price_per_night or existing[3],
                status          or existing[4],
                room_id,
            ),
        )
        conn.commit()
        print("Room Updated Successfully!")
    except Exception as e:
        print(f"Error updating room: {e}")
    finally:
        cursor.close()
        conn.close()


def delete_room():
    """Delete a room by room_id."""
    room_id = input("Enter Room ID to delete: ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM rooms WHERE room_id = %s", (room_id,))
        conn.commit()
        if cursor.rowcount > 0:
            print("Room Deleted Successfully!")
        else:
            print("Room ID not found.")
    except Exception as e:
        print(f"Error deleting room: {e}")
    finally:
        cursor.close()
        conn.close()


def search_room_by_status():
    """Filter rooms by their status (Available / Booked / Maintenance)."""
    status = input("Enter Status to search (Available/Booked/Maintenance): ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM rooms WHERE status = %s", (status,))
        rows = cursor.fetchall()

        if not rows:
            print("No rooms found with that status.")
            return

        print(f"\n{'ID':<5}{'Room No':<12}{'Type':<15}{'Price/Night':<15}{'Status':<15}")
        print("-" * 62)
        for row in rows:
            print(f"{row[0]:<5}{row[1]:<12}{row[2]:<15}{str(row[3]):<15}{row[4]:<15}")
        print()
    except Exception as e:
        print(f"Error searching rooms: {e}")
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------------------------
# Interactive CLI menu — only runs when executed directly
# ---------------------------------------------------------------------------

def rooms_menu():
    while True:
        print("\n===== ROOM MANAGEMENT =====")
        print("  1. Add Room")
        print("  2. View Rooms")
        print("  3. Update Room")
        print("  4. Delete Room")
        print("  5. Search Rooms by Status")
        print("  0. Exit")

        choice = input("Enter your choice: ").strip()

        if   choice == "1":
            add_room()
        elif choice == "2":
            show_rooms()
        elif choice == "3":
            update_room()
        elif choice == "4":
            delete_room()
        elif choice == "5":
            search_room_by_status()
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    rooms_menu()
