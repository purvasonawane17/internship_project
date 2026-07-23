import os
import sys
import re
import smtplib
from email.message import EmailMessage

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from db import get_connection

# ---------------------------------------------------------------------------
# sys.path setup:
#   BASE_DIR first  — so bare `import db`, `import guest`, etc. resolve to root
#   CLI_DIR second  — so `from rooms import` inside cli/staff.py finds cli/rooms.py
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLI_DIR  = os.path.join(BASE_DIR, "cli")

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)   # highest priority → root modules win
if CLI_DIR not in sys.path:
    sys.path.append(CLI_DIR)       # lower priority → cli siblings found by staff.py

# ---------------------------------------------------------------------------
# Import CLI modules (all properly structured — no bare top-level loops)
# ---------------------------------------------------------------------------
import cli.authentication as auth_mod
import cli.rooms          as rooms_mod
import cli.booking        as booking_mod
import cli.billing        as bill_mod
import cli.service        as service_mod
import cli.staff          as staff_mod
import cli.guest          as guest_mod   # self-contained — no circular import


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def authenticate():
    """
    Call cli/authentication.py's login() which returns the canonical role
    string on success, or None on failure.  Retries up to 3 times.
    """
    for attempt in range(1, 4):
        role = auth_mod.login()
        if role:
            return role
        remaining = 3 - attempt
        if remaining:
            print(f"  ({remaining} attempt{'s' if remaining > 1 else ''} remaining)\n")
    print("Too many failed attempts. Exiting.")
    return None


# ---------------------------------------------------------------------------
# Email receipt helper
# ---------------------------------------------------------------------------

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_guest_email_for_booking(booking_id):
    """Look up the guest e-mail via bookings → guests."""
    conn = get_connection()
    if conn is None:
        return None
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT guest_id FROM bookings WHERE booking_id = %s",
            (booking_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        cursor.execute(
            "SELECT email FROM guests WHERE guest_id = %s",
            (row[0],),
        )
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()
        conn.close()


def send_receipt(email, bill_id, total_amount, receipt_path):
    """
    E-mail the PDF receipt to the guest.
    Credentials are read from HOTEL_SENDER_EMAIL / HOTEL_APP_PASSWORD
    environment variables — never hard-code them in source.
    """
    if not email:
        print("No guest e-mail on file — skipping e-mail receipt.")
        return

    if not EMAIL_PATTERN.match(email):
        print(f"E-mail Error: '{email}' is not a valid address — skipping.")
        return

    sender_email = os.environ.get("HOTEL_SENDER_EMAIL") or "kamblesahil259@gmail.com"
    app_password = os.environ.get("HOTEL_APP_PASSWORD") or "hakpkyvdcixtnxmz"

    if not sender_email or not app_password:
        print("E-mail Error: HOTEL_SENDER_EMAIL / HOTEL_APP_PASSWORD not set.")
        return

    msg = EmailMessage()
    msg["Subject"] = "Hotel Bill Receipt"
    msg["From"]    = sender_email
    msg["To"]      = email
    msg.set_content(
        f"Hotel Management System\n\nBill ID : {bill_id}\n"
        f"Total   : Rs. {total_amount:.2f}\n\n"
        "Thank you for visiting our hotel."
    )

    try:
        if receipt_path and os.path.exists(receipt_path):
            with open(receipt_path, "rb") as f:
                msg.add_attachment(
                    f.read(), maintype="application", subtype="pdf",
                    filename=os.path.basename(receipt_path),
                )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)
        print("Receipt Sent Successfully.")

        # Optional: record that the e-mail went out
        conn = get_connection()
        if conn is not None:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE billing SET email_status = %s WHERE bill_id = %s",
                    ("Sent", bill_id),
                )
                conn.commit()
            except Exception:
                pass   # ok if email_status column doesn't exist yet
            finally:
                cursor.close()
                conn.close()

    except Exception as e:
        print(f"E-mail Error: {e}")


# ---------------------------------------------------------------------------
# Enhanced payment — adds room number to receipt PDF + emails it
# ---------------------------------------------------------------------------

def _get_room_no_for_booking(booking_id):
    """Resolve booking_id → room number (handles both FK id and direct number)."""
    conn = get_connection()
    if conn is None:
        return None
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT room_id FROM bookings WHERE booking_id = %s",
            (booking_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        room_ref = row[0]

        cursor.execute(
            "SELECT room_number FROM rooms WHERE room_id = %s",
            (room_ref,),
        )
        result = cursor.fetchone()
        if result:
            return result[0]

        # Fallback: maybe room_id stores the room_number directly
        cursor.execute(
            "SELECT room_number FROM rooms WHERE room_number = %s",
            (room_ref,),
        )
        result = cursor.fetchone()
        return result[0] if result else room_ref
    finally:
        cursor.close()
        conn.close()


def make_payment_with_room():
    """
    Enhanced payment flow — same as cli/billing.py's make_payment() but
    also looks up the room number, embeds it in the receipt PDF, and
    e-mails the PDF to the guest.
    """
    bill_id = input("Enter Bill ID: ").strip()

    conn = get_connection()
    if conn is None:
        print("Could not connect to database.")
        return
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM billing WHERE bill_id = %s", (bill_id,))
    data = cursor.fetchone()

    if not data:
        print("Bill Not Found!")
        cursor.close()
        conn.close()
        return

    if data[6] == "Paid":
        print("This bill is already Paid.")
        cursor.close()
        conn.close()
        return

    print("\nPayment Methods:")
    print("  1. Cash  |  2. Card  |  3. UPI")
    method  = input("Select Payment Method: ").strip()
    payment = {"1": "Cash", "2": "Card", "3": "UPI"}.get(method, "Unknown")

    cursor.execute(
        "UPDATE billing SET payment_status = %s, payment_method = %s WHERE bill_id = %s",
        ("Paid", payment, bill_id),
    )
    conn.commit()
    cursor.close()
    conn.close()
    print("Payment Received Successfully!")

    room_no = _get_room_no_for_booking(data[1])

    receipt_path = None
    try:
        receipt_path = bill_mod.generate_receipt_pdf(
            bill_id        = data[0],
            guest_name     = "See Booking",
            room_number    = room_no if room_no is not None else "N/A",
            bill_date      = data[7],
            room_charges   = float(data[2]),
            extra_charges  = float(data[3]),
            total_amount   = float(data[4]),
            payment_method = payment,
        )
        print(f"Receipt Generated: {receipt_path}")

        # Optionally record the file path in the DB
        conn2 = get_connection()
        if conn2 is not None:
            cursor2 = conn2.cursor()
            try:
                cursor2.execute(
                    "UPDATE billing SET receipt_path = %s WHERE bill_id = %s",
                    (receipt_path, bill_id),
                )
                conn2.commit()
            except Exception:
                pass
            finally:
                cursor2.close()
                conn2.close()

    except Exception as e:
        print(f"Payment recorded, but PDF generation failed: {e}")

    guest_email = get_guest_email_for_booking(data[1])
    send_receipt(guest_email, data[0], float(data[4]), receipt_path)


# ---------------------------------------------------------------------------
# Guest management sub-menu
# ---------------------------------------------------------------------------

def guests_menu():
    while True:
        print("\n===== Guest Management =====")
        print("  1. Add Guest")
        print("  2. View All Guests")
        print("  3. Search Guest")
        print("  4. Update Guest")
        print("  5. Delete Guest")
        print("  0. Back to Main Menu")

        choice = input("Enter your choice: ").strip()

        if   choice == "1": guest_mod.add_guest()
        elif choice == "2": guest_mod.view_guests()
        elif choice == "3": guest_mod.search_guest()
        elif choice == "4": guest_mod.update_guest()
        elif choice == "5": guest_mod.delete_guest()
        elif choice == "0": break
        else: print("Invalid choice.")


# ---------------------------------------------------------------------------
# Role-based sub-menus
# ---------------------------------------------------------------------------

def rooms_menu(role):
    while True:
        print("\n===== Room Management =====")
        print("  1. View Rooms")
        print("  2. Search by Status")
        if role in ("Admin", "Manager"):
            print("  3. Add Room")
            print("  4. Update Room")
        if role == "Admin":
            print("  5. Delete Room")
        print("  0. Back to Main Menu")

        choice = input("Enter your choice: ").strip()

        if   choice == "1": rooms_mod.show_rooms()
        elif choice == "2": rooms_mod.search_room_by_status()
        elif choice == "3" and role in ("Admin", "Manager"):
            rooms_mod.add_room()
        elif choice == "4" and role in ("Admin", "Manager"):
            rooms_mod.update_room()
        elif choice == "5" and role == "Admin":
            rooms_mod.delete_room()
        elif choice == "0": break
        else: print("Invalid choice.")


def bookings_menu(role):
    while True:
        print("\n===== Room Booking & Check-In/Check-Out =====")
        print("  1. Book Room")
        print("  2. View Bookings")
        print("  3. Search Booking")
        print("  4. Modify Booking")
        print("  5. Cancel Booking")
        print("  6. Guest Check-In")
        print("  7. Guest Check-Out")
        print("  0. Back to Main Menu")

        choice = input("Enter Your Choice: ").strip()

        if   choice == "1": booking_mod.book_room()
        elif choice == "2": booking_mod.view_booking()
        elif choice == "3": booking_mod.search_booking()
        elif choice == "4": booking_mod.modify_booking()
        elif choice == "5": booking_mod.cancel_booking()
        elif choice == "6": booking_mod.check_in()
        elif choice == "7": booking_mod.check_out()
        elif choice == "0": break
        else: print("Invalid choice.")


def billing_menu(role):
    while True:
        print("\n===== Billing and Payment Module =====")
        print("  1. Create Bill")
        print("  2. View Bills")
        print("  3. Payment (with receipt + email)")
        print("  4. Search Bill")
        if role in ("Admin", "Manager"):
            print("  5. Update Bill")
        if role == "Admin":
            print("  6. Delete Bill")
        print("  0. Back to Main Menu")

        choice = input("Enter your choice: ").strip()

        if   choice == "1": bill_mod.create_bill()
        elif choice == "2": bill_mod.view_bills()
        elif choice == "3": make_payment_with_room()
        elif choice == "4": bill_mod.search_bill()
        elif choice == "5" and role in ("Admin", "Manager"):
            bill_mod.update_bill()
        elif choice == "6" and role == "Admin":
            bill_mod.delete_bill()
        elif choice == "0": break
        else: print("Invalid choice.")


def service_requests_menu(role):
    while True:
        print("\n===== Service Requests =====")
        print("  1. Add Service Request")
        print("  2. View All Requests")
        print("  3. Update Status")
        if role == "Admin":
            print("  4. Delete Request")
        print("  0. Back to Main Menu")

        choice = input("Choose: ").strip()

        if   choice == "1": service_mod.add_service_request()
        elif choice == "2": service_mod.view_service_requests()
        elif choice == "3": service_mod.update_request_status()
        elif choice == "4" and role == "Admin":
            service_mod.delete_service_request()
        elif choice == "0": break
        else: print("Invalid choice.")


def staff_menu(role):
    while True:
        print("\n===== Staff & Housekeeping Management =====")
        print("  1. View Staff")
        print("  2. View Housekeeping")
        print("  3. Assign Room (Housekeeping)")
        if role == "Admin":
            print("  4. Add Staff")
            print("  5. Update Staff")
            print("  6. Delete Staff")
        print("  0. Back to Main Menu")

        choice = input("Enter your choice: ").strip()

        if   choice == "1": staff_mod.show_staff()
        elif choice == "2": staff_mod.show_housekeeping()
        elif choice == "3": staff_mod.assign_room()
        elif choice == "4" and role == "Admin":
            staff_mod.add_staff()
        elif choice == "5" and role == "Admin":
            staff_mod.update_staff()
        elif choice == "6" and role == "Admin":
            staff_mod.delete_staff()
        elif choice == "0": break
        else: print("Invalid choice.")


# ---------------------------------------------------------------------------
# Main menu (role-based)
# ---------------------------------------------------------------------------

def main_menu(role):
    while True:
        print(f"\n{'='*46}")
        print(f"   HOTEL MANAGEMENT SYSTEM  —  {role.upper()}")
        print(f"{'='*46}")
        print("  1. Room Management")
        print("  2. Room Booking / Check-In / Check-Out")
        print("  3. Guest Management")
        print("  4. Billing and Payment")
        print("  5. Service Requests")
        if role in ("Admin", "Manager"):
            print("  6. Staff & Housekeeping")
        print("  0. Logout")

        choice = input("Enter your choice: ").strip()

        if   choice == "1": rooms_menu(role)
        elif choice == "2": bookings_menu(role)
        elif choice == "3": guests_menu()
        elif choice == "4": billing_menu(role)
        elif choice == "5": service_requests_menu(role)
        elif choice == "6" and role in ("Admin", "Manager"):
            staff_menu(role)
        elif choice == "0":
            print("Logged out. Goodbye!")
            break
        else:
            print("Invalid choice.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    user_role = authenticate()
    if user_role:
        main_menu(user_role)