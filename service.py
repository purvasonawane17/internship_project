"""
cli/service.py
==============
Service Request module for the Hotel Management System CLI.

Functions:
    add_service_request()        — create a new service request record
    view_service_requests()      — list all requests (most recent first)
    update_request_status()      — change the status of a request
    delete_service_request()     — remove a service request
    view_requests_by_booking()   — helper: list requests for one booking_id

The interactive CLI menu is guarded by `if __name__ == "__main__":`.
"""

from db import get_connection


# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

def add_service_request():
    """Prompt for service details and insert a new request."""
    booking_id   = input("Booking ID                                          : ").strip()
    service_type = input("Service Type (Room Cleaning / Food Order / Laundry) : ").strip()
    details      = input("Details                                             : ").strip()

    conn = get_connection()
    if conn is None:
        print("Could not connect to database.")
        return

    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO service_requests (booking_id, service_type, details, status)
            VALUES (%s, %s, %s, %s)
            """,
            (booking_id, service_type, details, "Pending"),
        )
        conn.commit()
        print(f"Service Request Added! Request ID: {cursor.lastrowid}")
    except Exception as e:
        print(f"Error adding service request: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def view_service_requests():
    """Print all service requests ordered by most recent first."""
    conn = get_connection()
    if conn is None:
        print("Could not connect to database.")
        return

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM service_requests ORDER BY requested_at DESC")
        rows = cursor.fetchall()

        if not rows:
            print("No service requests found.")
            return

        print(f"\n{'ID':<6}{'Booking':<10}{'Service Type':<20}{'Details':<25}{'Status':<15}{'Requested At':<20}")
        print("-" * 96)
        for r in rows:
            print(f"{r['request_id']:<6}{r['booking_id']:<10}{r['service_type']:<20}"
                  f"{str(r['details'])[:22]:<25}{r['status']:<15}{str(r['requested_at']):<20}")
        print()
    except Exception as e:
        print(f"Error fetching service requests: {e}")
    finally:
        cursor.close()
        conn.close()


def update_request_status():
    """Change the status of a service request."""
    request_id = input("Request ID to update                              : ").strip()
    new_status = input("New Status (Pending/In Progress/Completed/Cancelled): ").strip()

    conn = get_connection()
    if conn is None:
        return

    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE service_requests SET status = %s WHERE request_id = %s",
            (new_status, request_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            print("No request found with that ID.")
        else:
            print(f"Request #{request_id} status updated to '{new_status}'.")
    except Exception as e:
        print(f"Error updating status: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def delete_service_request():
    """Delete a service request by request_id."""
    request_id = input("Request ID to delete: ").strip()

    conn = get_connection()
    if conn is None:
        return

    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM service_requests WHERE request_id = %s",
            (request_id,),
        )
        conn.commit()
        if cursor.rowcount == 0:
            print("No request found with that ID.")
        else:
            print(f"Request #{request_id} deleted.")
    except Exception as e:
        print(f"Error deleting request: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def view_requests_by_booking(booking_id):
    """Helper: print all service requests for a specific booking."""
    conn = get_connection()
    if conn is None:
        return

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM service_requests WHERE booking_id = %s ORDER BY requested_at DESC",
            (booking_id,),
        )
        rows = cursor.fetchall()
        for r in rows:
            print(f"  {r['request_id']} | {r['service_type']} | {r['details']} "
                  f"| {r['status']} | {r['requested_at']}")
    except Exception as e:
        print(f"Error fetching requests: {e}")
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------------------------
# Interactive CLI menu — only runs when executed directly
# ---------------------------------------------------------------------------

def service_menu():
    while True:
        print("\n===== SERVICE REQUESTS =====")
        print("  1. Add Service Request")
        print("  2. View All Requests")
        print("  3. Update Status")
        print("  4. Delete Request")
        print("  0. Exit")

        choice = input("Choose: ").strip()

        if   choice == "1": add_service_request()
        elif choice == "2": view_service_requests()
        elif choice == "3": update_request_status()
        elif choice == "4": delete_service_request()
        elif choice == "0": break
        else: print("Invalid choice.")


if __name__ == "__main__":
    service_menu()
