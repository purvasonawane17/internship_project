"""
cli/booking.py
==============
Room Booking and Check-In / Check-Out module for the Hotel Management System CLI.

Functions:
    book_room()       — create a new booking record
    view_booking()    — list all bookings
    search_booking()  — search a booking by guest name
    modify_booking()  — update booking details
    cancel_booking()  — set a booking status to Cancelled
    check_in()        — set a booking status to Checked In
    check_out()       — set a booking status to Checked Out

NOTE: The original `ROOMBOOKING (1).py` had two bugs that are fixed here:
  1. search_booking() queried column "gurest_name" (typo) → corrected to "guest_name"
  2. cancel_booking() had a stray "6" corrupting the UPDATE SQL → removed

All connections use try/finally. The CLI menu is guarded by `__name__ == "__main__"`.
"""

from db import get_connection


# ---------------------------------------------------------------------------
# CRUD / State Operations
# ---------------------------------------------------------------------------

def book_room():
    """Prompt for booking details and insert a confirmed booking."""
    guest_name = input("Enter Guest Name                          : ").strip()
    guest_id   = input("Enter Guest ID                            : ").strip()
    room_id    = input("Enter Room ID                             : ").strip()
    check_in   = input("Enter Check-In Date  (YYYY-MM-DD)         : ").strip()
    check_out  = input("Enter Check-Out Date (YYYY-MM-DD)         : ").strip()

    adults_raw   = input("Number of Adults   (default 1)           : ").strip()
    children_raw = input("Number of Children (default 0)           : ").strip()
    adults   = int(adults_raw)   if adults_raw   else 1
    children = int(children_raw) if children_raw else 0

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO bookings
                (guest_name, guest_id, room_id, check_in, check_out,
                 adults, children, booking_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (guest_name, guest_id, room_id, check_in, check_out,
             adults, children, "Confirmed"),
        )
        conn.commit()
        print(f"Room Booked Successfully! Booking ID: {cursor.lastrowid}")
    except Exception as e:
        print(f"Error booking room: {e}")
    finally:
        cursor.close()
        conn.close()


def view_booking():
    """Print all booking records."""
    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM bookings ORDER BY booking_id")
        records = cursor.fetchall()

        if not records:
            print("No Booking Records Found.")
            return

        print("\n===== Booking Details =====")
        for data in records:
            print(f"  Booking ID   : {data[0]}")
            print(f"  Guest Name   : {data[1]}")
            print(f"  Guest ID     : {data[2]}")
            print(f"  Room ID      : {data[3]}")
            print(f"  Check-In     : {data[4]}")
            print(f"  Check-Out    : {data[5]}")
            print(f"  Adults       : {data[6]}")
            print(f"  Children     : {data[7]}")
            print(f"  Status       : {data[8]}")
            print(f"  Created At   : {data[9]}")
            print("  " + "-" * 30)
    except Exception as e:
        print(f"Error fetching bookings: {e}")
    finally:
        cursor.close()
        conn.close()


def search_booking():
    """Search for a booking by guest name."""
    guest_name = input("Enter Guest Name to search: ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        # Note: original file had typo "gurest_name" — fixed here.
        cursor.execute(
            "SELECT * FROM bookings WHERE guest_name = %s",
            (guest_name,),
        )
        data = cursor.fetchone()

        if data:
            print("\nBooking Found:")
            print(f"  Booking ID   : {data[0]}")
            print(f"  Guest Name   : {data[1]}")
            print(f"  Guest ID     : {data[2]}")
            print(f"  Room ID      : {data[3]}")
            print(f"  Check-In     : {data[4]}")
            print(f"  Check-Out    : {data[5]}")
            print(f"  Adults       : {data[6]}")
            print(f"  Children     : {data[7]}")
            print(f"  Status       : {data[8]}")
        else:
            print("Booking Not Found.")
    except Exception as e:
        print(f"Error searching booking: {e}")
    finally:
        cursor.close()
        conn.close()


def modify_booking():
    """Update room, check-in, and check-out dates for an existing booking."""
    guest_name = input("Enter Guest Name         : ").strip()
    booking_id = input("Enter Booking ID         : ").strip()
    room_id    = input("New Room ID              : ").strip()
    check_in   = input("New Check-In  (YYYY-MM-DD): ").strip()
    check_out  = input("New Check-Out (YYYY-MM-DD): ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE bookings
               SET guest_name = %s,
                   room_id    = %s,
                   check_in   = %s,
                   check_out  = %s
             WHERE booking_id = %s
            """,
            (guest_name, room_id, check_in, check_out, booking_id),
        )
        conn.commit()
        if cursor.rowcount > 0:
            print("Booking Modified Successfully!")
        else:
            print("Booking ID Not Found.")
    except Exception as e:
        print(f"Error modifying booking: {e}")
    finally:
        cursor.close()
        conn.close()


def cancel_booking():
    """Set a booking's status to 'Cancelled'."""
    booking_id = input("Enter Booking ID to Cancel: ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        # Note: original file had a stray "6" corrupting the SQL — fixed here.
        cursor.execute(
            "UPDATE bookings SET booking_status = 'Cancelled' WHERE booking_id = %s",
            (booking_id,),
        )
        conn.commit()
        if cursor.rowcount > 0:
            print("Booking Cancelled Successfully!")
        else:
            print("Booking ID Not Found.")
    except Exception as e:
        print(f"Error cancelling booking: {e}")
    finally:
        cursor.close()
        conn.close()


def check_in():
    """Mark a booking as 'Checked In'."""
    booking_id = input("Enter Booking ID for Check-In: ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE bookings SET booking_status = 'Checked In' WHERE booking_id = %s",
            (booking_id,),
        )
        conn.commit()
        if cursor.rowcount > 0:
            print("Guest Checked-In Successfully!")
        else:
            print("Booking ID Not Found.")
    except Exception as e:
        print(f"Error during check-in: {e}")
    finally:
        cursor.close()
        conn.close()


def check_out():
    """Mark a booking as 'Checked Out'."""
    booking_id = input("Enter Booking ID for Check-Out: ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE bookings SET booking_status = 'Checked Out' WHERE booking_id = %s",
            (booking_id,),
        )
        conn.commit()
        if cursor.rowcount > 0:
            print("Guest Checked-Out Successfully!")
        else:
            print("Booking ID Not Found.")
    except Exception as e:
        print(f"Error during check-out: {e}")
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------------------------
# Interactive CLI menu — only runs when executed directly
# ---------------------------------------------------------------------------

def booking_menu():
    while True:
        print("\n====== ROOM BOOKING & CHECK-IN/CHECK-OUT ======")
        print("  1. Book Room")
        print("  2. View Bookings")
        print("  3. Search Booking")
        print("  4. Modify Booking")
        print("  5. Cancel Booking")
        print("  6. Guest Check-In")
        print("  7. Guest Check-Out")
        print("  0. Exit")

        choice = input("Enter Your Choice: ").strip()

        if   choice == "1": book_room()
        elif choice == "2": view_booking()
        elif choice == "3": search_booking()
        elif choice == "4": modify_booking()
        elif choice == "5": cancel_booking()
        elif choice == "6": check_in()
        elif choice == "7": check_out()
        elif choice == "0":
            print("Thank You!")
            break
        else:
            print("Invalid Choice. Please Try Again.")


if __name__ == "__main__":
    booking_menu()
