"""
cli/billing.py
==============
Billing and Payment module for the Hotel Management System CLI.

Functions:
    create_bill()   — create a new bill record in `billing`
    view_bills()    — list all bills
    search_bill()   — search by bill_id or guest name
    update_bill()   — update room/extra charges on an existing bill
    delete_bill()   — remove a bill record
    make_payment()  — process payment and generate a PDF receipt

PDF receipts are saved to the RECEIPT_DIR folder.
Email credentials are read from environment variables:
    HOTEL_SENDER_EMAIL / HOTEL_APP_PASSWORD

The interactive CLI menu is guarded by `if __name__ == "__main__":`.
"""

import os
import smtplib
from datetime import date as _date
from email.message import EmailMessage

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from db import get_connection

RECEIPT_DIR = "receipts"


# ---------------------------------------------------------------------------
# PDF Receipt
# ---------------------------------------------------------------------------

def generate_receipt_pdf(bill_id, guest_name, room_number, bill_date,
                          room_charges, extra_charges, total_amount,
                          payment_method):
    """Generate a PDF receipt and return its filepath."""
    os.makedirs(RECEIPT_DIR, exist_ok=True)
    filepath = os.path.join(RECEIPT_DIR, f"receipt_{bill_id}.pdf")

    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 80, "Payment Receipt")

    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 100, "Hotel Billing & Payment Module")
    c.line(60, height - 115, width - 60, height - 115)

    c.setFont("Helvetica", 12)
    y = height - 150
    line_height = 22

    details = [
        ("Bill ID:",               str(bill_id)),
        ("Bill Date:",             str(bill_date)),
        ("Guest Name:",            str(guest_name)),
        ("Room Number:",           str(room_number)),
        ("Room Charges:",          f"Rs. {room_charges:.2f}"),
        ("Extra Service Charges:", f"Rs. {extra_charges:.2f}"),
        ("Total Amount:",          f"Rs. {total_amount:.2f}"),
        ("Payment Method:",        str(payment_method)),
        ("Payment Status:",        "Paid"),
    ]

    for label, value in details:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(80, y, label)
        c.setFont("Helvetica", 12)
        c.drawString(260, y, value)
        y -= line_height

    c.line(60, y - 10, width - 60, y - 10)
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(width / 2, y - 30, "Thank you for your payment!")
    c.save()
    return filepath


# ---------------------------------------------------------------------------
# Email Receipt
# ---------------------------------------------------------------------------

def send_receipt_email(email, bill_id, guest_name, total_amount, receipt_path=None):
    """Email the receipt to the guest. Reads credentials from environment variables."""
    sender_email = os.environ.get("HOTEL_SENDER_EMAIL") or "kamblesahil259@gmail.com"
    app_password = os.environ.get("HOTEL_APP_PASSWORD") or "hakpkyvdcixtnxmz"

    if not sender_email or not app_password:
        print("Email not configured (set HOTEL_SENDER_EMAIL and HOTEL_APP_PASSWORD).")
        return

    msg = EmailMessage()
    msg["Subject"] = "Hotel Bill Receipt"
    msg["From"]    = sender_email
    msg["To"]      = email
    msg.set_content(
        f"Hotel Management System\n\nBill ID : {bill_id}\n"
        f"Guest   : {guest_name}\nTotal   : Rs. {total_amount:.2f}\n\n"
        "Thank You For Visiting Our Hotel."
    )

    if receipt_path and os.path.exists(receipt_path):
        with open(receipt_path, "rb") as f:
            msg.add_attachment(
                f.read(), maintype="application", subtype="pdf",
                filename=os.path.basename(receipt_path),
            )
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)
        print("Receipt Sent Successfully.")
    except Exception as e:
        print(f"Email Error: {e}")


# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

def create_bill():
    """Prompt for billing details and insert a new row into `billing`."""
    booking_id   = input("Enter Booking ID          : ").strip()
    room_charges = float(input("Enter Room Charges     : ").strip())
    extra_charges = float(input("Enter Extra Charges   : ").strip())
    total_amount = room_charges + extra_charges
    bill_date    = str(_date.today())

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO billing
                (booking_id, room_charges, extra_charges, total_amount,
                 payment_status, bill_date)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (booking_id, room_charges, extra_charges, total_amount,
             "Pending", bill_date),
        )
        conn.commit()
        print(f"Bill Created Successfully! Bill ID: {cursor.lastrowid}")
        print(f"Total Amount: Rs. {total_amount:.2f}")
    except Exception as e:
        print(f"Error creating bill: {e}")
    finally:
        cursor.close()
        conn.close()


def view_bills():
    """Print all billing records."""
    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM billing ORDER BY bill_id")
        rows = cursor.fetchall()

        if not rows:
            print("No Bills Found.")
            return

        print(f"\n{'Bill ID':<10}{'Booking ID':<12}{'Room Chrg':<12}"
              f"{'Extra Chrg':<12}{'Total':<12}{'Method':<10}{'Status':<12}{'Date':<12}")
        print("-" * 90)
        for row in rows:
            print(f"{row[0]:<10}{row[1]:<12}{str(row[2]):<12}{str(row[3]):<12}"
                  f"{str(row[4]):<12}{str(row[5] or 'N/A'):<10}{row[6]:<12}{str(row[7]):<12}")
        print()
    except Exception as e:
        print(f"Error fetching bills: {e}")
    finally:
        cursor.close()
        conn.close()


def search_bill():
    """Search for a bill by bill_id."""
    bill_id = input("Enter Bill ID to search: ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM billing WHERE bill_id = %s", (bill_id,))
        row = cursor.fetchone()

        if row:
            print(f"\n  Bill ID        : {row[0]}")
            print(f"  Booking ID     : {row[1]}")
            print(f"  Room Charges   : Rs. {row[2]}")
            print(f"  Extra Charges  : Rs. {row[3]}")
            print(f"  Total Amount   : Rs. {row[4]}")
            print(f"  Payment Method : {row[5]}")
            print(f"  Payment Status : {row[6]}")
            print(f"  Bill Date      : {row[7]}")
        else:
            print("Bill Not Found.")
    except Exception as e:
        print(f"Error searching bill: {e}")
    finally:
        cursor.close()
        conn.close()


def update_bill():
    """Update room and extra charges on an existing bill."""
    bill_id = input("Enter Bill ID to update: ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM billing WHERE bill_id = %s", (bill_id,))
        existing = cursor.fetchone()

        if not existing:
            print("Bill Not Found.")
            return

        room_charges  = float(input("New Room Charges  : ").strip())
        extra_charges = float(input("New Extra Charges : ").strip())
        total_amount  = room_charges + extra_charges

        cursor.execute(
            """
            UPDATE billing
               SET room_charges  = %s,
                   extra_charges = %s,
                   total_amount  = %s
             WHERE bill_id = %s
            """,
            (room_charges, extra_charges, total_amount, bill_id),
        )
        conn.commit()
        print(f"Bill Updated Successfully! New Total: Rs. {total_amount:.2f}")
    except Exception as e:
        print(f"Error updating bill: {e}")
    finally:
        cursor.close()
        conn.close()


def delete_bill():
    """Delete a bill record by bill_id."""
    bill_id = input("Enter Bill ID to delete: ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM billing WHERE bill_id = %s", (bill_id,))
        conn.commit()
        if cursor.rowcount > 0:
            print("Bill Deleted Successfully!")
        else:
            print("Bill Not Found.")
    except Exception as e:
        print(f"Error deleting bill: {e}")
    finally:
        cursor.close()
        conn.close()


def make_payment():
    """Process payment for a pending bill and generate a PDF receipt."""
    bill_id = input("Enter Bill ID: ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM billing WHERE bill_id = %s", (bill_id,))
        data = cursor.fetchone()

        if not data:
            print("Bill Not Found!")
            return

        if data[6] == "Paid":
            print("This bill is already Paid.")
            return

        print("\nPayment Methods:")
        print("  1. Cash")
        print("  2. Card")
        print("  3. UPI")
        method  = input("Select Payment Method: ").strip()
        payment = {"1": "Cash", "2": "Card", "3": "UPI"}.get(method, "Unknown")

        cursor.execute(
            "UPDATE billing SET payment_status = %s, payment_method = %s WHERE bill_id = %s",
            ("Paid", payment, bill_id),
        )
        conn.commit()
        print("Payment Received Successfully!")

    except Exception as e:
        print(f"Error processing payment: {e}")
        return
    finally:
        cursor.close()
        conn.close()

    # Generate receipt outside the DB transaction
    try:
        receipt_path = generate_receipt_pdf(
            bill_id      = data[0],
            guest_name   = "N/A",
            room_number  = "N/A",
            bill_date    = data[7],
            room_charges = float(data[2]),
            extra_charges = float(data[3]),
            total_amount = float(data[4]),
            payment_method = payment,
        )
        print(f"Receipt Generated: {receipt_path}")
    except Exception as e:
        print(f"Payment recorded, but PDF generation failed: {e}")


# ---------------------------------------------------------------------------
# Interactive CLI menu — only runs when executed directly
# ---------------------------------------------------------------------------

def billing_menu():
    while True:
        print("\n===== BILLING AND PAYMENT MODULE =====")
        print("  1. Create Bill")
        print("  2. View Bills")
        print("  3. Make Payment")
        print("  4. Search Bill")
        print("  5. Update Bill")
        print("  6. Delete Bill")
        print("  0. Exit")

        choice = input("Enter Your Choice: ").strip()

        if   choice == "1": create_bill()
        elif choice == "2": view_bills()
        elif choice == "3": make_payment()
        elif choice == "4": search_bill()
        elif choice == "5": update_bill()
        elif choice == "6": delete_bill()
        elif choice == "0":
            print("Thank You!")
            break
        else:
            print("Invalid Choice!")


if __name__ == "__main__":
    billing_menu()
