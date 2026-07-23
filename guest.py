"""
cli/guest.py
============
Guest Management module for the Hotel Management System CLI.
Self-contained — does NOT re-export from root guest.py to avoid circular
imports when cli/ is on sys.path.

Provides the same interface as root guest.py:
    add_guest()    view_guests()    search_guest()
    update_guest() delete_guest()   guest_menu()
"""

from db import get_connection


# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

def add_guest():
    """Prompt for guest details and insert a new row into `guests`."""
    full_name    = input("Enter Guest Full Name   : ").strip()
    gender       = input("Enter Gender            : ").strip()
    phone        = input("Enter Contact Number    : ").strip()
    email        = input("Enter Email             : ").strip()
    address      = input("Enter Address           : ").strip()
    id_proof     = input("Enter ID Proof Type     : ").strip()
    proof_number = input("Enter ID Proof Number   : ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO guests
                (full_name, gender, phone, email, address, id_proof, id_proof_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (full_name, gender, phone, email, address, id_proof, proof_number),
        )
        conn.commit()
        print("Guest Added Successfully!")
    except Exception as e:
        print(f"Error adding guest: {e}")
    finally:
        cursor.close()
        conn.close()


def view_guests():
    """Fetch and print every row from the `guests` table."""
    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM guests ORDER BY guest_id")
        records = cursor.fetchall()

        if not records:
            print("No Guest Records Found.")
            return

        print("\n========== Guest List ==========")
        for data in records:
            print(f"  Guest ID   : {data[0]}")
            print(f"  Full Name  : {data[1]}")
            print(f"  Gender     : {data[2]}")
            print(f"  Phone      : {data[3]}")
            print(f"  Email      : {data[4]}")
            print(f"  Address    : {data[5]}")
            print(f"  ID Proof   : {data[6]}")
            print(f"  Proof No   : {data[7]}")
            print("  " + "-" * 34)
    except Exception as e:
        print(f"Error fetching guests: {e}")
    finally:
        cursor.close()
        conn.close()


def search_guest():
    """Search for a guest by their numeric guest_id."""
    guest_id = input("Enter Guest ID to Search : ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM guests WHERE guest_id = %s", (guest_id,))
        data = cursor.fetchone()

        if data:
            print("\nGuest Found:")
            print(f"  Guest ID   : {data[0]}")
            print(f"  Full Name  : {data[1]}")
            print(f"  Gender     : {data[2]}")
            print(f"  Phone      : {data[3]}")
            print(f"  Email      : {data[4]}")
            print(f"  Address    : {data[5]}")
            print(f"  ID Proof   : {data[6]}")
            print(f"  Proof No   : {data[7]}")
        else:
            print("Guest Not Found.")
    except Exception as e:
        print(f"Error searching guest: {e}")
    finally:
        cursor.close()
        conn.close()


def update_guest():
    """Update an existing guest record. Blank input keeps the existing value."""
    guest_id = input("Enter Guest ID to Update : ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM guests WHERE guest_id = %s", (guest_id,))
        existing = cursor.fetchone()

        if not existing:
            print("Guest ID Not Found.")
            return

        print("(Press Enter to leave a field unchanged.)")
        full_name    = input("New Full Name           : ").strip()
        gender       = input("New Gender              : ").strip()
        phone        = input("New Phone               : ").strip()
        email        = input("New Email               : ").strip()
        address      = input("New Address             : ").strip()
        id_proof     = input("New ID Proof Type       : ").strip()
        proof_number = input("New ID Proof Number     : ").strip()

        cursor.execute(
            """
            UPDATE guests
               SET full_name        = %s,
                   gender           = %s,
                   phone            = %s,
                   email            = %s,
                   address          = %s,
                   id_proof         = %s,
                   id_proof_number  = %s
             WHERE guest_id = %s
            """,
            (
                full_name    or existing[1],
                gender       or existing[2],
                phone        or existing[3],
                email        or existing[4],
                address      or existing[5],
                id_proof     or existing[6],
                proof_number or existing[7],
                guest_id,
            ),
        )
        conn.commit()
        print("Guest Updated Successfully!" if cursor.rowcount > 0 else "No changes made.")
    except Exception as e:
        print(f"Error updating guest: {e}")
    finally:
        cursor.close()
        conn.close()


def delete_guest():
    """Delete a guest record after confirmation."""
    guest_id = input("Enter Guest ID to Delete : ").strip()
    confirm  = input(f"Delete guest {guest_id}? (y/n): ").strip().lower()

    if confirm != "y":
        print("Deletion cancelled.")
        return

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM guests WHERE guest_id = %s", (guest_id,))
        conn.commit()
        print("Guest Deleted Successfully!" if cursor.rowcount > 0 else "Guest ID Not Found.")
    except Exception as e:
        print(f"Error deleting guest: {e}")
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------------------------
# Interactive CLI menu — only runs when executed directly
# ---------------------------------------------------------------------------

def guest_menu():
    while True:
        print("\n========== GUEST MANAGEMENT SYSTEM ==========")
        print("  1. Add Guest")
        print("  2. View All Guests")
        print("  3. Search Guest")
        print("  4. Update Guest")
        print("  5. Delete Guest")
        print("  0. Exit")

        choice = input("Enter Your Choice : ").strip()

        if   choice == "1": add_guest()
        elif choice == "2": view_guests()
        elif choice == "3": search_guest()
        elif choice == "4": update_guest()
        elif choice == "5": delete_guest()
        elif choice == "0":
            print("Thank You! Goodbye.")
            break
        else:
            print("Invalid Choice. Please Try Again.")


if __name__ == "__main__":
    guest_menu()
