"""
cli/staff.py
============
Staff and Housekeeping Management module for the Hotel Management System CLI.

Functions:
    add_staff()        — insert a new staff record
    show_staff()       — list all staff in a formatted table
    update_staff()     — update a staff record (blank = keep existing)
    delete_staff()     — remove a staff record
    assign_room()      — assign / update a housekeeping record for a room
    show_housekeeping()— list all housekeeping assignments

NOTE: The original staff-reports.py imported `from Rooms import ...`.
This module imports from `rooms` (the cli/ package sibling) instead.

The interactive CLI menu is guarded by `if __name__ == "__main__":`.
"""

from db import get_connection
from rooms import show_rooms, get_room_numbers


# ---------------------------------------------------------------------------
# Staff Operations
# ---------------------------------------------------------------------------

def add_staff():
    """Prompt for staff details and insert a new row into `staff`."""
    name         = input("Full Name                                                    : ").strip()
    designation  = input("Designation (Manager/Receptionist/Housekeeping/Chef/Security): ").strip()
    phone        = input("Phone                                                        : ").strip()
    email        = input("Email                                                        : ").strip()
    salary       = input("Salary                                                       : ").strip()
    joining_date = input("Joining Date (YYYY-MM-DD)                                    : ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO staff(full_name, designation, phone, email, salary, joining_date) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (name, designation, phone, email, salary, joining_date),
        )
        conn.commit()
        print("Staff Added Successfully!")
    except Exception as e:
        print(f"Error adding staff: {e}")
    finally:
        cursor.close()
        conn.close()


def show_staff():
    """Print all staff records in a formatted table."""
    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM staff ORDER BY staff_id")
        rows = cursor.fetchall()

        if not rows:
            print("No staff records found.")
            return

        print(f"\n{'ID':<5}{'Name':<20}{'Designation':<18}{'Phone':<15}"
              f"{'Email':<28}{'Salary':<10}{'Joining Date':<14}")
        print("-" * 110)
        for row in rows:
            print(f"{row[0]:<5}{row[1]:<20}{row[2]:<18}{row[3]:<15}"
                  f"{row[4]:<28}{str(row[5]):<10}{str(row[6]):<14}")
        print()
    except Exception as e:
        print(f"Error fetching staff: {e}")
    finally:
        cursor.close()
        conn.close()


def update_staff():
    """Update a staff record. Blank input keeps the existing value."""
    staff_id = input("Enter Staff ID to update: ").strip()

    print("(Press Enter to leave a field unchanged.)")
    name         = input("Full Name         : ").strip()
    designation  = input("Designation       : ").strip()
    phone        = input("Phone             : ").strip()
    email        = input("Email             : ").strip()
    salary       = input("Salary            : ").strip()
    joining_date = input("Joining Date      : ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM staff WHERE staff_id = %s", (staff_id,))
        existing = cursor.fetchone()

        if not existing:
            print("Staff ID not found.")
            return

        cursor.execute(
            """
            UPDATE staff
               SET full_name    = %s,
                   designation  = %s,
                   phone        = %s,
                   email        = %s,
                   salary       = %s,
                   joining_date = %s
             WHERE staff_id = %s
            """,
            (
                name         or existing[1],
                designation  or existing[2],
                phone        or existing[3],
                email        or existing[4],
                salary       or existing[5],
                joining_date or existing[6],
                staff_id,
            ),
        )
        conn.commit()
        print("Staff Updated Successfully!")
    except Exception as e:
        print(f"Error updating staff: {e}")
    finally:
        cursor.close()
        conn.close()


def delete_staff():
    """Delete a staff record by staff_id."""
    staff_id = input("Enter Staff ID to delete: ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM staff WHERE staff_id = %s", (staff_id,))
        conn.commit()
        if cursor.rowcount > 0:
            print("Staff Deleted Successfully!")
        else:
            print("Staff ID Not Found.")
    except Exception as e:
        print(f"Error deleting staff: {e}")
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------------------------
# Housekeeping Operations
# ---------------------------------------------------------------------------

def assign_room():
    """Assign a staff member to a room for housekeeping (upsert)."""
    room_numbers = get_room_numbers()

    if not room_numbers:
        print("No rooms found. Please add a room first.")
        return

    print("Available Rooms: " + ", ".join(str(r) for r in room_numbers))
    room = input("Room No        : ").strip()

    if room not in [str(r) for r in room_numbers]:
        print("Invalid Room No. Please choose from the list above.")
        return

    assign = input("Assign Staff   : ").strip()
    status = input("Status (Clean/Dirty/In Progress): ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO housekeeping (room_no, assigned_staff, status)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                assigned_staff = VALUES(assigned_staff),
                status         = VALUES(status)
            """,
            (room, assign, status),
        )
        conn.commit()
        print("Room Assigned Successfully!")
    except Exception as e:
        print(f"Error assigning room: {e}")
    finally:
        cursor.close()
        conn.close()


def show_housekeeping():
    """Print all housekeeping assignments."""
    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM housekeeping ORDER BY room_no")
        rows = cursor.fetchall()

        if not rows:
            print("No housekeeping records found.")
            return

        print(f"\n{'Room No':<12}{'Assigned Staff':<22}{'Status':<15}")
        print("-" * 50)
        for row in rows:
            print(f"{row[0]:<12}{row[1]:<22}{row[2]:<15}")
        print()
    except Exception as e:
        print(f"Error fetching housekeeping records: {e}")
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------------------------
# Interactive CLI menu — only runs when executed directly
# ---------------------------------------------------------------------------

def staff_menu():
    while True:
        print("\n===== STAFF & HOUSEKEEPING MANAGEMENT =====")
        print("  1. Add Staff")
        print("  2. View Staff")
        print("  3. Update Staff")
        print("  4. Delete Staff")
        print("  5. Assign Room (Housekeeping)")
        print("  6. View Housekeeping")
        print("  0. Exit")

        choice = input("Enter your choice: ").strip()

        if   choice == "1": add_staff()
        elif choice == "2": show_staff()
        elif choice == "3": update_staff()
        elif choice == "4": delete_staff()
        elif choice == "5": assign_room()
        elif choice == "6": show_housekeeping()
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    staff_menu()
