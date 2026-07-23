"""
reports.py — Analytics/reporting module for the Hotel Management System.

Uses matplotlib to turn live data from db.py (rooms, billing, bookings)
into charts saved under reports/. Drop this file next to db.py, Rooms.py,
bill.py, etc., and call generate_reports() from your CLI menu or GUI.
"""

import os
import matplotlib
matplotlib.use("Agg")  # safe for headless/CLI use; remove if only used inside gui.py
import matplotlib.pyplot as plt

from db import get_connection

REPORT_DIR = "reports"


def _ensure_dir():
    os.makedirs(REPORT_DIR, exist_ok=True)


# ---------------------------------------------------------------------
# 1. Room status breakdown (pie chart) — from `rooms` table
# ---------------------------------------------------------------------
def chart_room_status():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) FROM rooms GROUP BY status")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No room data to chart.")
        return None

    labels = [r[0] for r in rows]
    counts = [r[1] for r in rows]

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(counts, labels=labels, autopct="%1.0f%%", startangle=90)
    ax.set_title("Room Status Breakdown")

    _ensure_dir()
    path = os.path.join(REPORT_DIR, "room_status.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")
    return path


# ---------------------------------------------------------------------
# 2. Revenue over time (line chart) — from `billing` table
# ---------------------------------------------------------------------
def chart_revenue_by_date():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT bill_date, SUM(total_amount)
        FROM billing
        WHERE payment_status = 'Paid'
        GROUP BY bill_date
        ORDER BY bill_date
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No billing data to chart.")
        return None

    dates = [str(r[0]) for r in rows]
    totals = [float(r[1]) for r in rows]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(dates, totals, marker="o", color="#4C72B0")
    ax.set_title("Revenue by Date (Paid Bills)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Revenue")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()

    _ensure_dir()
    path = os.path.join(REPORT_DIR, "revenue_by_date.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")
    return path


# ---------------------------------------------------------------------
# 3. Bookings per room type (bar chart) — joins `bookings` + `rooms`
# ---------------------------------------------------------------------
def chart_bookings_by_room_type():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.room_type, COUNT(*)
        FROM bookings b
        JOIN rooms r ON b.room_id = r.room_id
        GROUP BY r.room_type
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No booking data to chart.")
        return None

    room_types = [r[0] for r in rows]
    counts = [r[1] for r in rows]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(room_types, counts, color="#C44E52")
    ax.set_title("Bookings by Room Type")
    ax.set_ylabel("Number of Bookings")
    fig.tight_layout()

    _ensure_dir()
    path = os.path.join(REPORT_DIR, "bookings_by_room_type.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")
    return path


def generate_reports():
    """Run all charts in one go — call this from main.py's menu."""
    chart_room_status()
    chart_revenue_by_date()
    chart_bookings_by_room_type()
    print("\nAll reports generated in the 'reports/' folder.")


if __name__ == "__main__":
    generate_reports()