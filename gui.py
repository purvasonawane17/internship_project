import os
import secrets
from datetime import date, datetime, timedelta

import tkinter as tk
from tkinter import ttk, messagebox
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from db import get_connection

RECEIPT_DIR = "receipts"
RESET_TOKEN_VALID_MINUTES = 15

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
NAVY = "#1B2A4A"
NAVY_DARK = "#13203A"
GOLD = "#C9A24B"
CARD = "#EEF1F6"
WHITE = "#FFFFFF"
TEXT_DARK = "#1E2433"
TEXT_MUTED = "#5A6478"
GREEN = "#1E7A46"
RED = "#B0463C"


# ---------------------------------------------------------------------------
# Small DB helpers
# ---------------------------------------------------------------------------
def run_query(query, params=None, fetch=False, commit=False):
    """
    Open a connection, run one query, optionally fetch rows or commit,
    then always close the connection - mirrors how main.py/guest.py use
    get_connection() (a fresh connection per operation).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params or ())
        result = cursor.fetchall() if fetch else None
        if commit:
            conn.commit()
        return result, cursor.rowcount
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------------------------
# Reusable widgets
# ---------------------------------------------------------------------------
class FormField:
    """One label + entry (or combobox) pair, laid out in a grid row."""

    def __init__(self, parent, row, label, values=None, show=None, width=28):
        ttk.Label(parent, text=label, style="Field.TLabel").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )
        if values is not None:
            self.var = tk.StringVar()
            self.widget = ttk.Combobox(
                parent, textvariable=self.var, values=values, width=width - 2, state="readonly"
            )
        else:
            self.var = tk.StringVar()
            self.widget = ttk.Entry(parent, textvariable=self.var, width=width, show=show or "")
        self.widget.grid(row=row, column=1, sticky="w", pady=5)

    def get(self):
        return self.var.get().strip()

    def set(self, value):
        self.var.set("" if value is None else str(value))

    def clear(self):
        self.var.set("")


def make_tree(parent, columns, headings, widths=None):
    tree = ttk.Treeview(parent, columns=columns, show="headings", height=14)
    for i, col in enumerate(columns):
        tree.heading(col, text=headings[i])
        tree.column(col, width=(widths[i] if widths else 120), anchor="w")
    vsb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    return tree, vsb


def refresh_tree(tree, rows):
    tree.delete(*tree.get_children())
    for row in rows:
        tree.insert("", "end", values=row)


def selected_values(tree):
    sel = tree.selection()
    if not sel:
        return None
    return tree.item(sel[0], "values")


# ---------------------------------------------------------------------------
# Login window
# ---------------------------------------------------------------------------
class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Hotel Management System — Login")
        self.geometry("420x420")
        self.configure(bg=NAVY_DARK)
        self.resizable(False, False)
        self.role = None
        self.username = None

        card = tk.Frame(self, bg=NAVY_DARK)
        card.pack(expand=True)

        tk.Label(
            card, text="HOTEL MANAGEMENT SYSTEM", fg=WHITE, bg=NAVY_DARK,
            font=("Georgia", 16, "bold"),
        ).pack(pady=(40, 4))
        tk.Label(
            card, text="Sign in to continue", fg="#CADCFC", bg=NAVY_DARK,
            font=("Segoe UI", 10, "italic"),
        ).pack(pady=(0, 30))

        form = tk.Frame(card, bg=NAVY_DARK)
        form.pack()

        tk.Label(form, text="Username", fg="#CADCFC", bg=NAVY_DARK, font=("Segoe UI", 10)).grid(
            row=0, column=0, sticky="w", pady=6
        )
        self.username_var = tk.StringVar()
        tk.Entry(form, textvariable=self.username_var, width=28, font=("Segoe UI", 11)).grid(
            row=0, column=1, pady=6, padx=(10, 0)
        )

        tk.Label(form, text="Password", fg="#CADCFC", bg=NAVY_DARK, font=("Segoe UI", 10)).grid(
            row=1, column=0, sticky="w", pady=6
        )
        self.password_var = tk.StringVar()
        pw_entry = tk.Entry(
            form, textvariable=self.password_var, width=28, font=("Segoe UI", 11), show="*"
        )
        pw_entry.grid(row=1, column=1, pady=6, padx=(10, 0))
        pw_entry.bind("<Return>", lambda e: self.try_login())

        tk.Button(
            card, text="Login", command=self.try_login, bg=GOLD, fg=NAVY_DARK,
            activebackground="#DDBB66", font=("Segoe UI", 11, "bold"), relief="flat",
            width=20, pady=8, cursor="hand2",
        ).pack(pady=(30, 0))

        forgot_link = tk.Label(
            card, text="Forgot Password?", fg="#CADCFC", bg=NAVY_DARK,
            font=("Segoe UI", 9, "underline"), cursor="hand2",
        )
        forgot_link.pack(pady=(12, 0))
        forgot_link.bind("<Button-1>", lambda e: self.open_forgot_password())

        self.status_label = tk.Label(card, text="", fg="#F2A9A0", bg=NAVY_DARK, font=("Segoe UI", 9))
        self.status_label.pack(pady=(14, 0))

    def open_forgot_password(self):
        ForgotPasswordDialog(self)

    def try_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()

        if not username or not password:
            self.status_label.config(text="Enter both username and password.")
            return

        try:
            rows, _ = run_query(
                "SELECT username, password, role FROM users WHERE username = %s",
                (username,),
                fetch=True,
            )
        except Exception as e:
            self.status_label.config(text=f"Database error: {e}")
            return

        if not rows or rows[0][1] != password:
            self.status_label.config(text="Invalid username or password.")
            return

        self.role = rows[0][2]
        self.username = username
        self.destroy()


# ---------------------------------------------------------------------------
# Forgot / Reset password dialogs
# ---------------------------------------------------------------------------
class ForgotPasswordDialog(tk.Toplevel):
    """Step 1: user enters their email. If it matches a user row, a reset
    token is generated and written to reset_token / reset_token_expiry."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Forgot Password")
        self.geometry("360x220")
        self.configure(bg=WHITE)
        self.resizable(False, False)
        self.grab_set()

        tk.Label(
            self, text="Reset Your Password", bg=WHITE, fg=NAVY,
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=(20, 4))
        tk.Label(
            self, text="Enter the email linked to your account.",
            bg=WHITE, fg=TEXT_MUTED, font=("Segoe UI", 9),
        ).pack(pady=(0, 14))

        self.email_var = tk.StringVar()
        entry = tk.Entry(self, textvariable=self.email_var, width=32, font=("Segoe UI", 10))
        entry.pack()
        entry.focus_set()
        entry.bind("<Return>", lambda e: self.submit())

        self.status_label = tk.Label(self, text="", bg=WHITE, fg=RED, font=("Segoe UI", 9))
        self.status_label.pack(pady=(10, 0))

        btns = tk.Frame(self, bg=WHITE)
        btns.pack(pady=18)
        tk.Button(
            btns, text="Send Reset Token", command=self.submit, bg=GOLD, fg=NAVY_DARK,
            relief="flat", padx=14, pady=6, font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=6)
        tk.Button(btns, text="Cancel", command=self.destroy, relief="flat", padx=14, pady=6).pack(side="left")

    def submit(self):
        email = self.email_var.get().strip()
        if not email:
            self.status_label.config(text="Please enter an email address.")
            return

        try:
            rows, _ = run_query(
                "SELECT username FROM users WHERE email = %s",
                (email,),
                fetch=True,
            )
        except Exception as e:
            self.status_label.config(text=f"Database error: {e}")
            return

        # Same message whether or not the account exists, so we don't leak
        # which emails are registered.
        generic_msg = "If that email is registered, a reset token has been generated."

        if not rows:
            messagebox.showinfo("Forgot Password", generic_msg)
            self.destroy()
            return

        username = rows[0][0]
        token = secrets.token_urlsafe(16)
        expiry = datetime.now() + timedelta(minutes=RESET_TOKEN_VALID_MINUTES)

        try:
            run_query(
                "UPDATE users SET reset_token = %s, reset_token_expiry = %s WHERE username = %s",
                (token, expiry, username),
                commit=True,
            )
        except Exception as e:
            self.status_label.config(text=f"Database error: {e}")
            return

        self.destroy()
        # In production this token would be emailed, not shown on screen.
        # Since this is a dummy/offline setup, we show it directly and
        # jump straight into the reset dialog for convenience.
        messagebox.showinfo(
            "Reset Token Generated",
            f"{generic_msg}\n\nUsername: {username}\n"
            f"Token (valid {RESET_TOKEN_VALID_MINUTES} min): {token}",
        )
        ResetPasswordDialog(self.master, username=username, token=token)


class ResetPasswordDialog(tk.Toplevel):
    """Step 2: user supplies username + token + new password."""

    def __init__(self, parent, username="", token=""):
        super().__init__(parent)
        self.title("Reset Password")
        self.geometry("380x320")
        self.configure(bg=WHITE)
        self.resizable(False, False)
        self.grab_set()

        tk.Label(
            self, text="Set a New Password", bg=WHITE, fg=NAVY,
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=(20, 14))

        form = tk.Frame(self, bg=WHITE)
        form.pack()

        tk.Label(form, text="Username", bg=WHITE, font=("Segoe UI", 9)).grid(
            row=0, column=0, sticky="w", pady=6
        )
        self.username_var = tk.StringVar(value=username)
        tk.Entry(form, textvariable=self.username_var, width=26, font=("Segoe UI", 10)).grid(
            row=0, column=1, pady=6, padx=(10, 0)
        )

        tk.Label(form, text="Reset Token", bg=WHITE, font=("Segoe UI", 9)).grid(
            row=1, column=0, sticky="w", pady=6
        )
        self.token_var = tk.StringVar(value=token)
        tk.Entry(form, textvariable=self.token_var, width=26, font=("Segoe UI", 10)).grid(
            row=1, column=1, pady=6, padx=(10, 0)
        )

        tk.Label(form, text="New Password", bg=WHITE, font=("Segoe UI", 9)).grid(
            row=2, column=0, sticky="w", pady=6
        )
        self.new_pw_var = tk.StringVar()
        tk.Entry(form, textvariable=self.new_pw_var, width=26, font=("Segoe UI", 10), show="*").grid(
            row=2, column=1, pady=6, padx=(10, 0)
        )

        tk.Label(form, text="Confirm Password", bg=WHITE, font=("Segoe UI", 9)).grid(
            row=3, column=0, sticky="w", pady=6
        )
        self.confirm_pw_var = tk.StringVar()
        tk.Entry(form, textvariable=self.confirm_pw_var, width=26, font=("Segoe UI", 10), show="*").grid(
            row=3, column=1, pady=6, padx=(10, 0)
        )

        self.status_label = tk.Label(self, text="", bg=WHITE, fg=RED, font=("Segoe UI", 9))
        self.status_label.pack(pady=(12, 0))

        btns = tk.Frame(self, bg=WHITE)
        btns.pack(pady=16)
        tk.Button(
            btns, text="Reset Password", command=self.submit, bg=GOLD, fg=NAVY_DARK,
            relief="flat", padx=14, pady=6, font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=6)
        tk.Button(btns, text="Cancel", command=self.destroy, relief="flat", padx=14, pady=6).pack(side="left")

    def submit(self):
        username = self.username_var.get().strip()
        token = self.token_var.get().strip()
        new_pw = self.new_pw_var.get()
        confirm_pw = self.confirm_pw_var.get()

        if not (username and token and new_pw):
            self.status_label.config(text="All fields are required.")
            return
        if new_pw != confirm_pw:
            self.status_label.config(text="Passwords do not match.")
            return

        try:
            rows, _ = run_query(
                "SELECT reset_token, reset_token_expiry FROM users WHERE username = %s",
                (username,),
                fetch=True,
            )
        except Exception as e:
            self.status_label.config(text=f"Database error: {e}")
            return

        if not rows or rows[0][0] != token:
            self.status_label.config(text="Invalid username or reset token.")
            return

        expiry = rows[0][1]
        if expiry is None or datetime.now() > expiry:
            self.status_label.config(text="This reset token has expired.")
            return

        try:
            run_query(
                "UPDATE users SET password = %s, reset_token = NULL, reset_token_expiry = NULL "
                "WHERE username = %s",
                (new_pw, username),
                commit=True,
            )
        except Exception as e:
            self.status_label.config(text=f"Database error: {e}")
            return

        messagebox.showinfo("Success", "Password reset successful. You can now log in.")
        self.destroy()


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------
class MainApp(tk.Tk):
    def __init__(self, role, username):
        super().__init__()
        self.role = role
        self.username = username
        self.title(f"Hotel Management System — {role}")
        self.geometry("1180x680")
        self.configure(bg=WHITE)

        self._setup_style()
        self._build_header()

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.build_rooms_tab(notebook)
        self.build_guests_tab(notebook)
        self.build_bookings_tab(notebook)
        self.build_billing_tab(notebook)
        self.build_service_tab(notebook)
        if self.role in ("Admin", "Manager"):
            self.build_staff_tab(notebook)

    # -- chrome -------------------------------------------------------
    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=WHITE, borderwidth=0)
        style.configure(
            "TNotebook.Tab", padding=(16, 10), font=("Segoe UI", 10, "bold"),
            background=CARD, foreground=TEXT_DARK,
        )
        style.map("TNotebook.Tab", background=[("selected", NAVY)], foreground=[("selected", WHITE)])
        style.configure("Treeview", rowheight=26, font=("Segoe UI", 10), fieldbackground=WHITE)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background=NAVY, foreground=WHITE)
        style.map("Treeview.Heading", background=[("active", NAVY)])
        style.configure("Field.TLabel", font=("Segoe UI", 10), foreground=TEXT_DARK, background=WHITE)
        style.configure("Card.TFrame", background=CARD)
        style.configure("TFrame", background=WHITE)

    def _build_header(self):
        header = tk.Frame(self, bg=NAVY_DARK, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header, text="HOTEL MANAGEMENT SYSTEM", fg=WHITE, bg=NAVY_DARK,
            font=("Georgia", 14, "bold"),
        ).pack(side="left", padx=20)

        tk.Label(
            header, text=f"{self.username}  ·  {self.role}", fg=GOLD, bg=NAVY_DARK,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="right", padx=(0, 12))

        tk.Button(
            header, text="Logout", command=self.logout, bg=NAVY, fg=WHITE,
            activebackground="#24304E", relief="flat", font=("Segoe UI", 9, "bold"),
            padx=12, cursor="hand2",
        ).pack(side="right", padx=(0, 12))

    def logout(self):
        self.destroy()
        start_app()

    def _action_bar(self, parent):
        bar = tk.Frame(parent, bg=WHITE)
        bar.pack(fill="x", pady=(10, 0))
        return bar

    def _add_button(self, bar, text, command, side="left", enabled=True):
        state = "normal" if enabled else "disabled"
        btn = tk.Button(
            bar, text=text, command=command, bg=NAVY, fg=WHITE, activebackground="#24304E",
            relief="flat", font=("Segoe UI", 9, "bold"), padx=14, pady=6, cursor="hand2",
            state=state,
        )
        btn.pack(side=side, padx=(0, 8))
        return btn

    # -- ROOMS ----------------------------------------------------------
    def build_rooms_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Rooms")

        can_write = self.role in ("Admin", "Manager")
        can_delete = self.role == "Admin"

        left = tk.Frame(tab, bg=WHITE)
        left.pack(side="left", fill="both", expand=True, padx=(12, 6), pady=12)
        right = tk.Frame(tab, bg=CARD, width=300)
        right.pack(side="right", fill="y", padx=(6, 12), pady=12)
        right.pack_propagate(False)

        columns = ("room_id", "room_number", "room_type", "price", "status")
        headings = ("ID", "Room No.", "Type", "Price/Night", "Status")
        tree, vsb = make_tree(left, columns, headings, widths=(50, 90, 100, 100, 100))
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def load_rooms(status_filter=None):
            if status_filter:
                rows, _ = run_query(
                    "SELECT room_id, room_number, room_type, price_per_night, status "
                    "FROM rooms WHERE status = %s ORDER BY room_id",
                    (status_filter,), fetch=True,
                )
            else:
                rows, _ = run_query(
                    "SELECT room_id, room_number, room_type, price_per_night, status "
                    "FROM rooms ORDER BY room_id",
                    fetch=True,
                )
            refresh_tree(tree, rows)

        tk.Label(right, text="ROOM DETAILS", bg=CARD, fg=GOLD, font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 10)
        )
        form = tk.Frame(right, bg=CARD)
        form.grid(row=1, column=0, columnspan=2, padx=16, sticky="w")

        f_number = FormField(form, 0, "Room No.")
        f_type = FormField(form, 1, "Type", values=["Single", "Double", "Deluxe", "Suite"])
        f_price = FormField(form, 2, "Price/Night")
        f_status = FormField(form, 3, "Status", values=["Available", "Booked", "Maintenance"])

        def clear_form():
            for f in (f_number, f_type, f_price, f_status):
                f.clear()
            tree.selection_remove(tree.selection())

        def on_select(_event):
            values = selected_values(tree)
            if not values:
                return
            f_number.set(values[1])
            f_type.set(values[2])
            f_price.set(values[3])
            f_status.set(values[4])

        tree.bind("<<TreeviewSelect>>", on_select)

        def add_room():
            if not (f_number.get() and f_type.get() and f_price.get() and f_status.get()):
                messagebox.showwarning("Missing info", "Fill in all room fields.")
                return
            try:
                run_query(
                    "INSERT INTO rooms (room_number, room_type, price_per_night, status) "
                    "VALUES (%s, %s, %s, %s)",
                    (f_number.get(), f_type.get(), f_price.get(), f_status.get()),
                    commit=True,
                )
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return
            messagebox.showinfo("Success", "Room added.")
            clear_form()
            load_rooms()

        def update_room():
            values = selected_values(tree)
            if not values:
                messagebox.showwarning("No selection", "Select a room to update.")
                return
            try:
                run_query(
                    "UPDATE rooms SET room_number=%s, room_type=%s, price_per_night=%s, status=%s "
                    "WHERE room_id=%s",
                    (f_number.get(), f_type.get(), f_price.get(), f_status.get(), values[0]),
                    commit=True,
                )
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return
            messagebox.showinfo("Success", "Room updated.")
            clear_form()
            load_rooms()

        def delete_room():
            values = selected_values(tree)
            if not values:
                messagebox.showwarning("No selection", "Select a room to delete.")
                return
            if not messagebox.askyesno("Confirm", f"Delete room {values[1]}?"):
                return
            run_query("DELETE FROM rooms WHERE room_id=%s", (values[0],), commit=True)
            clear_form()
            load_rooms()

        btn_row = tk.Frame(right, bg=CARD)
        btn_row.grid(row=2, column=0, columnspan=2, padx=16, pady=16, sticky="w")
        self._add_button(btn_row, "Add", add_room, enabled=can_write)
        self._add_button(btn_row, "Update", update_room, enabled=can_write)
        self._add_button(btn_row, "Delete", delete_room, enabled=can_delete)
        self._add_button(btn_row, "Clear", clear_form)

        filter_bar = self._action_bar(left)
        self._add_button(filter_bar, "All", lambda: load_rooms())
        self._add_button(filter_bar, "Available", lambda: load_rooms("Available"))
        self._add_button(filter_bar, "Booked", lambda: load_rooms("Booked"))
        self._add_button(filter_bar, "Maintenance", lambda: load_rooms("Maintenance"))
        self._add_button(filter_bar, "Refresh", lambda: load_rooms(), side="right")

        load_rooms()

    # -- GUESTS -----------------------------------------------------------
    def build_guests_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Guests")

        can_delete = self.role == "Admin"

        left = tk.Frame(tab, bg=WHITE)
        left.pack(side="left", fill="both", expand=True, padx=(12, 6), pady=12)
        right = tk.Frame(tab, bg=CARD, width=320)
        right.pack(side="right", fill="y", padx=(6, 12), pady=12)
        right.pack_propagate(False)

        columns = ("guest_id", "full_name", "gender", "phone", "email")
        headings = ("ID", "Full Name", "Gender", "Phone", "Email")
        tree, vsb = make_tree(left, columns, headings, widths=(50, 160, 80, 110, 180))
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def load_guests():
            rows, _ = run_query(
                "SELECT guest_id, full_name, gender, phone, email FROM guests ORDER BY guest_id",
                fetch=True,
            )
            refresh_tree(tree, rows)

        tk.Label(right, text="GUEST DETAILS", bg=CARD, fg=GOLD, font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 10)
        )
        form = tk.Frame(right, bg=CARD)
        form.grid(row=1, column=0, columnspan=2, padx=16, sticky="w")

        f_name = FormField(form, 0, "Full Name")
        f_gender = FormField(form, 1, "Gender", values=["Male", "Female", "Other"])
        f_phone = FormField(form, 2, "Phone")
        f_email = FormField(form, 3, "Email")
        f_address = FormField(form, 4, "Address")
        f_proof = FormField(form, 5, "ID Proof Type")
        f_proof_no = FormField(form, 6, "ID Proof Number")

        def clear_form():
            for f in (f_name, f_gender, f_phone, f_email, f_address, f_proof, f_proof_no):
                f.clear()
            tree.selection_remove(tree.selection())

        def on_select(_event):
            values = selected_values(tree)
            if not values:
                return
            rows, _ = run_query(
                "SELECT full_name, gender, phone, email, address, id_proof, id_proof_number "
                "FROM guests WHERE guest_id=%s",
                (values[0],), fetch=True,
            )
            if not rows:
                return
            data = rows[0]
            for field, val in zip((f_name, f_gender, f_phone, f_email, f_address, f_proof, f_proof_no), data):
                field.set(val)

        tree.bind("<<TreeviewSelect>>", on_select)

        def add_guest():
            if not (f_name.get() and f_phone.get()):
                messagebox.showwarning("Missing info", "Full name and phone are required.")
                return
            try:
                run_query(
                    "INSERT INTO guests (full_name, gender, phone, email, address, id_proof, id_proof_number) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (f_name.get(), f_gender.get(), f_phone.get(), f_email.get(),
                     f_address.get(), f_proof.get(), f_proof_no.get()),
                    commit=True,
                )
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return
            messagebox.showinfo("Success", "Guest added.")
            clear_form()
            load_guests()

        def update_guest():
            values = selected_values(tree)
            if not values:
                messagebox.showwarning("No selection", "Select a guest to update.")
                return
            try:
                run_query(
                    "UPDATE guests SET full_name=%s, gender=%s, phone=%s, email=%s, "
                    "address=%s, id_proof=%s, id_proof_number=%s WHERE guest_id=%s",
                    (f_name.get(), f_gender.get(), f_phone.get(), f_email.get(),
                     f_address.get(), f_proof.get(), f_proof_no.get(), values[0]),
                    commit=True,
                )
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return
            messagebox.showinfo("Success", "Guest updated.")
            clear_form()
            load_guests()

        def delete_guest():
            values = selected_values(tree)
            if not values:
                messagebox.showwarning("No selection", "Select a guest to delete.")
                return
            if not messagebox.askyesno("Confirm", f"Delete guest {values[1]}?"):
                return
            run_query("DELETE FROM guests WHERE guest_id=%s", (values[0],), commit=True)
            clear_form()
            load_guests()

        def search_guest():
            term = SearchDialog(self, "Search Guests", "Guest name or phone contains:").result
            if term is None:
                return
            rows, _ = run_query(
                "SELECT guest_id, full_name, gender, phone, email FROM guests "
                "WHERE full_name LIKE %s OR phone LIKE %s ORDER BY guest_id",
                (f"%{term}%", f"%{term}%"), fetch=True,
            )
            refresh_tree(tree, rows)

        btn_row = tk.Frame(right, bg=CARD)
        btn_row.grid(row=2, column=0, columnspan=2, padx=16, pady=16, sticky="w")
        self._add_button(btn_row, "Add", add_guest)
        self._add_button(btn_row, "Update", update_guest)
        self._add_button(btn_row, "Delete", delete_guest, enabled=can_delete)
        self._add_button(btn_row, "Clear", clear_form)

        filter_bar = self._action_bar(left)
        self._add_button(filter_bar, "Search", search_guest)
        self._add_button(filter_bar, "Refresh", load_guests, side="right")

        load_guests()

    # -- BOOKINGS -----------------------------------------------------
    def build_bookings_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Bookings")

        left = tk.Frame(tab, bg=WHITE)
        left.pack(side="left", fill="both", expand=True, padx=(12, 6), pady=12)
        right = tk.Frame(tab, bg=CARD, width=320)
        right.pack(side="right", fill="y", padx=(6, 12), pady=12)
        right.pack_propagate(False)

        columns = ("booking_id", "guest_name", "room_id", "check_in", "check_out", "status")
        headings = ("ID", "Guest", "Room ID", "Check-In", "Check-Out", "Status")
        tree, vsb = make_tree(left, columns, headings, widths=(50, 140, 70, 100, 100, 100))
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def load_bookings():
            rows, _ = run_query(
                "SELECT booking_id, guest_name, room_id, check_in, check_out, booking_status "
                "FROM bookings ORDER BY booking_id DESC",
                fetch=True,
            )
            refresh_tree(tree, rows)

        tk.Label(right, text="BOOKING DETAILS", bg=CARD, fg=GOLD, font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 10)
        )
        form = tk.Frame(right, bg=CARD)
        form.grid(row=1, column=0, columnspan=2, padx=16, sticky="w")

        f_guest_name = FormField(form, 0, "Guest Name")
        f_guest_id = FormField(form, 1, "Guest ID")
        f_room_id = FormField(form, 2, "Room ID")
        f_checkin = FormField(form, 3, "Check-In (YYYY-MM-DD)")
        f_checkout = FormField(form, 4, "Check-Out (YYYY-MM-DD)")
        f_adults = FormField(form, 5, "Adults")
        f_children = FormField(form, 6, "Children")
        f_status = FormField(
            form, 7, "Status",
            values=["Confirmed", "Checked In", "Checked Out", "Cancelled"],
        )

        def clear_form():
            for f in (f_guest_name, f_guest_id, f_room_id, f_checkin, f_checkout,
                      f_adults, f_children, f_status):
                f.clear()
            tree.selection_remove(tree.selection())

        def on_select(_event):
            values = selected_values(tree)
            if not values:
                return
            rows, _ = run_query(
                "SELECT guest_name, guest_id, room_id, check_in, check_out, adults, "
                "children, booking_status FROM bookings WHERE booking_id=%s",
                (values[0],), fetch=True,
            )
            if not rows:
                return
            data = rows[0]
            for field, val in zip(
                (f_guest_name, f_guest_id, f_room_id, f_checkin, f_checkout, f_adults, f_children, f_status),
                data,
            ):
                field.set(val)

        tree.bind("<<TreeviewSelect>>", on_select)

        def book_room():
            required = (f_guest_name.get(), f_room_id.get(), f_checkin.get(), f_checkout.get())
            if not all(required):
                messagebox.showwarning("Missing info", "Guest name, room, and dates are required.")
                return
            try:
                run_query(
                    "INSERT INTO bookings (guest_name, guest_id, room_id, check_in, check_out, "
                    "adults, children, booking_status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (f_guest_name.get(), f_guest_id.get() or None, f_room_id.get(),
                     f_checkin.get(), f_checkout.get(), f_adults.get() or 1,
                     f_children.get() or 0, f_status.get() or "Confirmed"),
                    commit=True,
                )
                run_query("UPDATE rooms SET status='Booked' WHERE room_id=%s", (f_room_id.get(),), commit=True)
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return
            messagebox.showinfo("Success", "Room booked.")
            clear_form()
            load_bookings()

        def modify_booking():
            values = selected_values(tree)
            if not values:
                messagebox.showwarning("No selection", "Select a booking to modify.")
                return
            try:
                run_query(
                    "UPDATE bookings SET guest_name=%s, guest_id=%s, room_id=%s, check_in=%s, "
                    "check_out=%s, adults=%s, children=%s, booking_status=%s WHERE booking_id=%s",
                    (f_guest_name.get(), f_guest_id.get() or None, f_room_id.get(), f_checkin.get(),
                     f_checkout.get(), f_adults.get() or 1, f_children.get() or 0,
                     f_status.get(), values[0]),
                    commit=True,
                )
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return
            messagebox.showinfo("Success", "Booking updated.")
            clear_form()
            load_bookings()

        def cancel_booking():
            values = selected_values(tree)
            if not values:
                messagebox.showwarning("No selection", "Select a booking to cancel.")
                return
            run_query(
                "UPDATE bookings SET booking_status='Cancelled' WHERE booking_id=%s",
                (values[0],), commit=True,
            )
            clear_form()
            load_bookings()

        def check_in():
            values = selected_values(tree)
            if not values:
                messagebox.showwarning("No selection", "Select a booking to check in.")
                return
            run_query(
                "UPDATE bookings SET booking_status='Checked In' WHERE booking_id=%s",
                (values[0],), commit=True,
            )
            clear_form()
            load_bookings()

        def check_out():
            values = selected_values(tree)
            if not values:
                messagebox.showwarning("No selection", "Select a booking to check out.")
                return
            run_query(
                "UPDATE bookings SET booking_status='Checked Out' WHERE booking_id=%s",
                (values[0],), commit=True,
            )
            run_query(
                "UPDATE rooms SET status='Available' WHERE room_id=%s",
                (values[2],), commit=True,
            )
            clear_form()
            load_bookings()

        def search_booking():
            term = SearchDialog(self, "Search Bookings", "Guest name contains:").result
            if term is None:
                return
            rows, _ = run_query(
                "SELECT booking_id, guest_name, room_id, check_in, check_out, booking_status "
                "FROM bookings WHERE guest_name LIKE %s ORDER BY booking_id DESC",
                (f"%{term}%",), fetch=True,
            )
            refresh_tree(tree, rows)

        row1 = tk.Frame(right, bg=CARD)
        row1.grid(row=2, column=0, columnspan=2, padx=16, pady=(12, 4), sticky="w")
        self._add_button(row1, "Book", book_room)
        self._add_button(row1, "Modify", modify_booking)
        self._add_button(row1, "Cancel", cancel_booking)

        row2 = tk.Frame(right, bg=CARD)
        row2.grid(row=3, column=0, columnspan=2, padx=16, pady=(0, 4), sticky="w")
        self._add_button(row2, "Check-In", check_in)
        self._add_button(row2, "Check-Out", check_out)
        self._add_button(row2, "Clear", clear_form)

        filter_bar = self._action_bar(left)
        self._add_button(filter_bar, "Search", search_booking)
        self._add_button(filter_bar, "Refresh", load_bookings, side="right")

        load_bookings()

    # -- BILLING --------------------------------------------------------
    def build_billing_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Billing")

        can_update = self.role in ("Admin", "Manager")
        can_delete = self.role == "Admin"

        left = tk.Frame(tab, bg=WHITE)
        left.pack(side="left", fill="both", expand=True, padx=(12, 6), pady=12)
        right = tk.Frame(tab, bg=CARD, width=320)
        right.pack(side="right", fill="y", padx=(6, 12), pady=12)
        right.pack_propagate(False)

        columns = ("bill_id", "booking_id", "room_charges", "extra_charges", "total", "method", "status", "date")
        headings = ("ID", "Booking", "Room ₹", "Extra ₹", "Total ₹", "Method", "Status", "Date")
        tree, vsb = make_tree(left, columns, headings, widths=(45, 65, 80, 80, 80, 80, 90, 100))
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def load_bills():
            rows, _ = run_query(
                "SELECT bill_id, booking_id, room_charges, extra_charges, total_amount, "
                "payment_method, payment_status, bill_date FROM billing ORDER BY bill_id DESC",
                fetch=True,
            )
            refresh_tree(tree, rows)

        tk.Label(right, text="BILL DETAILS", bg=CARD, fg=GOLD, font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 10)
        )
        form = tk.Frame(right, bg=CARD)
        form.grid(row=1, column=0, columnspan=2, padx=16, sticky="w")

        f_booking_id = FormField(form, 0, "Booking ID")
        f_room_charges = FormField(form, 1, "Room Charges")
        f_extra_charges = FormField(form, 2, "Extra Charges")
        f_method = FormField(form, 3, "Payment Method", values=["Cash", "Card", "UPI"])
        f_status = FormField(form, 4, "Payment Status", values=["Pending", "Paid"])

        def clear_form():
            for f in (f_booking_id, f_room_charges, f_extra_charges, f_method, f_status):
                f.clear()
            tree.selection_remove(tree.selection())

        def on_select(_event):
            values = selected_values(tree)
            if not values:
                return
            f_booking_id.set(values[1])
            f_room_charges.set(values[2])
            f_extra_charges.set(values[3])
            f_method.set(values[5])
            f_status.set(values[6])

        tree.bind("<<TreeviewSelect>>", on_select)

        def create_bill():
            if not (f_booking_id.get() and f_room_charges.get()):
                messagebox.showwarning("Missing info", "Booking ID and room charges are required.")
                return
            room_charges = float(f_room_charges.get() or 0)
            extra_charges = float(f_extra_charges.get() or 0)
            total = room_charges + extra_charges
            try:
                run_query(
                    "INSERT INTO billing (booking_id, room_charges, extra_charges, total_amount, "
                    "payment_method, payment_status, bill_date) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (f_booking_id.get(), room_charges, extra_charges, total,
                     f_method.get() or "Cash", f_status.get() or "Pending", date.today().isoformat()),
                    commit=True,
                )
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return
            messagebox.showinfo("Success", "Bill created.")
            clear_form()
            load_bills()

        def update_bill():
            values = selected_values(tree)
            if not values:
                messagebox.showwarning("No selection", "Select a bill to update.")
                return
            room_charges = float(f_room_charges.get() or 0)
            extra_charges = float(f_extra_charges.get() or 0)
            total = room_charges + extra_charges
            run_query(
                "UPDATE billing SET room_charges=%s, extra_charges=%s, total_amount=%s, "
                "payment_method=%s, payment_status=%s WHERE bill_id=%s",
                (room_charges, extra_charges, total, f_method.get(), f_status.get(), values[0]),
                commit=True,
            )
            clear_form()
            load_bills()

        def delete_bill():
            values = selected_values(tree)
            if not values:
                messagebox.showwarning("No selection", "Select a bill to delete.")
                return
            if not messagebox.askyesno("Confirm", f"Delete bill #{values[0]}?"):
                return
            run_query("DELETE FROM billing WHERE bill_id=%s", (values[0],), commit=True)
            clear_form()
            load_bills()

        def get_room_no_for_booking(booking_id):
            rows, _ = run_query("SELECT room_id FROM bookings WHERE booking_id=%s", (booking_id,), fetch=True)
            if not rows:
                return None
            room_ref = rows[0][0]
            rows, _ = run_query("SELECT room_number FROM rooms WHERE room_id=%s", (room_ref,), fetch=True)
            if rows:
                return rows[0][0]
            rows, _ = run_query("SELECT room_number FROM rooms WHERE room_number=%s", (room_ref,), fetch=True)
            return rows[0][0] if rows else room_ref

        def generate_receipt(bill_id, booking_id, room_no, room_charges, extra_charges,
                              total_amount, payment_method, bill_date):
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
            details = [
                ("Bill ID:", str(bill_id)),
                ("Booking ID:", str(booking_id)),
                ("Room No:", str(room_no)),
                ("Bill Date:", str(bill_date)),
                ("Room Charges:", f"{room_charges:.2f}"),
                ("Extra Service Charges:", f"{extra_charges:.2f}"),
                ("Total Amount:", f"{total_amount:.2f}"),
                ("Payment Method:", str(payment_method)),
                ("Payment Status:", "Paid"),
            ]
            for label, value in details:
                c.setFont("Helvetica-Bold", 12)
                c.drawString(80, y, label)
                c.setFont("Helvetica", 12)
                c.drawString(260, y, value)
                y -= 22
            c.line(60, y - 10, width - 60, y - 10)
            c.setFont("Helvetica-Oblique", 10)
            c.drawCentredString(width / 2, y - 30, "Thank you for your payment!")
            c.save()
            return filepath

        def make_payment():
            values = selected_values(tree)
            if not values:
                messagebox.showwarning("No selection", "Select a bill to pay.")
                return
            if values[6] == "Paid":
                messagebox.showinfo("Already paid", "This bill is already Paid.")
                return

            method = PaymentDialog(self).result
            if method is None:
                return

            run_query(
                "UPDATE billing SET payment_status=%s, payment_method=%s WHERE bill_id=%s",
                ("Paid", method, values[0]),
                commit=True,
            )
            room_no = get_room_no_for_booking(values[1])
            try:
                path = generate_receipt(
                    bill_id=values[0], booking_id=values[1],
                    room_no=room_no if room_no is not None else "N/A",
                    room_charges=float(values[2]), extra_charges=float(values[3]),
                    total_amount=float(values[4]), payment_method=method, bill_date=values[7],
                )
                messagebox.showinfo("Payment received", f"Receipt saved to:\n{path}")
            except Exception as e:
                messagebox.showwarning("Payment recorded", f"Payment saved, but PDF failed: {e}")
            clear_form()
            load_bills()

        def search_bill():
            term = SearchDialog(self, "Search Bills", "Bill ID or Booking ID:").result
            if term is None:
                return
            rows, _ = run_query(
                "SELECT bill_id, booking_id, room_charges, extra_charges, total_amount, "
                "payment_method, payment_status, bill_date FROM billing "
                "WHERE bill_id=%s OR booking_id=%s",
                (term, term), fetch=True,
            )
            refresh_tree(tree, rows)

        row1 = tk.Frame(right, bg=CARD)
        row1.grid(row=2, column=0, columnspan=2, padx=16, pady=(12, 4), sticky="w")
        self._add_button(row1, "Create", create_bill)
        self._add_button(row1, "Pay", make_payment)

        row2 = tk.Frame(right, bg=CARD)
        row2.grid(row=3, column=0, columnspan=2, padx=16, pady=(0, 4), sticky="w")
        self._add_button(row2, "Update", update_bill, enabled=can_update)
        self._add_button(row2, "Delete", delete_bill, enabled=can_delete)
        self._add_button(row2, "Clear", clear_form)

        filter_bar = self._action_bar(left)
        self._add_button(filter_bar, "Search", search_bill)
        self._add_button(filter_bar, "Refresh", load_bills, side="right")

        load_bills()

    # -- SERVICE REQUESTS -------------------------------------------------
    def build_service_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Service Requests")

        can_delete = self.role == "Admin"

        left = tk.Frame(tab, bg=WHITE)
        left.pack(side="left", fill="both", expand=True, padx=(12, 6), pady=12)
        right = tk.Frame(tab, bg=CARD, width=320)
        right.pack(side="right", fill="y", padx=(6, 12), pady=12)
        right.pack_propagate(False)

        columns = ("request_id", "booking_id", "service_type", "details", "status")
        headings = ("ID", "Booking", "Service", "Details", "Status")
        tree, vsb = make_tree(left, columns, headings, widths=(45, 65, 120, 260, 100))
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def load_requests():
            rows, _ = run_query(
                "SELECT request_id, booking_id, service_type, details, status "
                "FROM service_requests ORDER BY request_id DESC",
                fetch=True,
            )
            refresh_tree(tree, rows)

        tk.Label(right, text="REQUEST DETAILS", bg=CARD, fg=GOLD, font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 10)
        )
        form = tk.Frame(right, bg=CARD)
        form.grid(row=1, column=0, columnspan=2, padx=16, sticky="w")

        f_booking_id = FormField(form, 0, "Booking ID")
        f_service_type = FormField(
            form, 1, "Service Type",
            values=["Housekeeping", "Room Service", "Laundry", "Wake-up Call", "Maintenance", "Other"],
        )
        f_details = FormField(form, 2, "Details")
        f_status = FormField(form, 3, "Status", values=["Pending", "In Progress", "Completed", "Cancelled"])

        def clear_form():
            for f in (f_booking_id, f_service_type, f_details, f_status):
                f.clear()
            tree.selection_remove(tree.selection())

        def on_select(_event):
            values = selected_values(tree)
            if not values:
                return
            f_booking_id.set(values[1])
            f_service_type.set(values[2])
            f_details.set(values[3])
            f_status.set(values[4])

        tree.bind("<<TreeviewSelect>>", on_select)

        def add_request():
            if not (f_booking_id.get() and f_service_type.get()):
                messagebox.showwarning("Missing info", "Booking ID and service type are required.")
                return
            try:
                run_query(
                    "INSERT INTO service_requests (booking_id, service_type, details, status) "
                    "VALUES (%s,%s,%s,%s)",
                    (f_booking_id.get(), f_service_type.get(), f_details.get(), f_status.get() or "Pending"),
                    commit=True,
                )
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return
            messagebox.showinfo("Success", "Service request added.")
            clear_form()
            load_requests()

        def update_status():
            values = selected_values(tree)
            if not values:
                messagebox.showwarning("No selection", "Select a request to update.")
                return
            run_query(
                "UPDATE service_requests SET status=%s WHERE request_id=%s",
                (f_status.get(), values[0]), commit=True,
            )
            clear_form()
            load_requests()

        def delete_request():
            values = selected_values(tree)
            if not values:
                messagebox.showwarning("No selection", "Select a request to delete.")
                return
            if not messagebox.askyesno("Confirm", "Delete this service request?"):
                return
            run_query("DELETE FROM service_requests WHERE request_id=%s", (values[0],), commit=True)
            clear_form()
            load_requests()

        btn_row = tk.Frame(right, bg=CARD)
        btn_row.grid(row=2, column=0, columnspan=2, padx=16, pady=16, sticky="w")
        self._add_button(btn_row, "Add", add_request)
        self._add_button(btn_row, "Update Status", update_status)
        self._add_button(btn_row, "Delete", delete_request, enabled=can_delete)
        self._add_button(btn_row, "Clear", clear_form)

        filter_bar = self._action_bar(left)
        self._add_button(filter_bar, "Refresh", load_requests, side="right")

        load_requests()

    # -- STAFF & HOUSEKEEPING (Admin/Manager only tab) -------------------
    def build_staff_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Staff & Housekeeping")

        can_manage_staff = self.role == "Admin"

        inner = ttk.Notebook(tab)
        inner.pack(fill="both", expand=True, padx=12, pady=12)

        staff_tab = ttk.Frame(inner)
        house_tab = ttk.Frame(inner)
        inner.add(staff_tab, text="Staff Directory")
        inner.add(house_tab, text="Housekeeping")

        # --- Staff directory ---
        left = tk.Frame(staff_tab, bg=WHITE)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=12)
        right = tk.Frame(staff_tab, bg=CARD, width=320)
        right.pack(side="right", fill="y", padx=(6, 0), pady=12)
        right.pack_propagate(False)

        columns = ("staff_id", "full_name", "designation", "phone", "email", "salary")
        headings = ("ID", "Full Name", "Designation", "Phone", "Email", "Salary")
        tree, vsb = make_tree(left, columns, headings, widths=(45, 140, 110, 100, 170, 90))
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def load_staff():
            rows, _ = run_query(
                "SELECT staff_id, full_name, designation, phone, email, salary "
                "FROM staff ORDER BY staff_id",
                fetch=True,
            )
            refresh_tree(tree, rows)

        tk.Label(right, text="STAFF DETAILS", bg=CARD, fg=GOLD, font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 10)
        )
        form = tk.Frame(right, bg=CARD)
        form.grid(row=1, column=0, columnspan=2, padx=16, sticky="w")

        f_name = FormField(form, 0, "Full Name")
        f_designation = FormField(form, 1, "Designation")
        f_phone = FormField(form, 2, "Phone")
        f_email = FormField(form, 3, "Email")
        f_salary = FormField(form, 4, "Salary")
        f_joining = FormField(form, 5, "Joining Date (YYYY-MM-DD)")

        def clear_form():
            for f in (f_name, f_designation, f_phone, f_email, f_salary, f_joining):
                f.clear()
            tree.selection_remove(tree.selection())

        def on_select(_event):
            values = selected_values(tree)
            if not values:
                return
            f_name.set(values[1])
            f_designation.set(values[2])
            f_phone.set(values[3])
            f_email.set(values[4])
            f_salary.set(values[5])

        tree.bind("<<TreeviewSelect>>", on_select)

        def add_staff():
            if not (f_name.get() and f_designation.get()):
                messagebox.showwarning("Missing info", "Name and designation are required.")
                return
            try:
                run_query(
                    "INSERT INTO staff (full_name, designation, phone, email, salary, joining_date) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (f_name.get(), f_designation.get(), f_phone.get(), f_email.get(),
                     f_salary.get() or 0, f_joining.get() or date.today().isoformat()),
                    commit=True,
                )
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return
            messagebox.showinfo("Success", "Staff added.")
            clear_form()
            load_staff()

        def update_staff():
            values = selected_values(tree)
            if not values:
                messagebox.showwarning("No selection", "Select a staff member to update.")
                return
            run_query(
                "UPDATE staff SET full_name=%s, designation=%s, phone=%s, email=%s, salary=%s "
                "WHERE staff_id=%s",
                (f_name.get(), f_designation.get(), f_phone.get(), f_email.get(),
                 f_salary.get() or 0, values[0]),
                commit=True,
            )
            clear_form()
            load_staff()

        def delete_staff():
            values = selected_values(tree)
            if not values:
                messagebox.showwarning("No selection", "Select a staff member to delete.")
                return
            if not messagebox.askyesno("Confirm", f"Delete staff member {values[1]}?"):
                return
            run_query("DELETE FROM staff WHERE staff_id=%s", (values[0],), commit=True)
            clear_form()
            load_staff()

        btn_row = tk.Frame(right, bg=CARD)
        btn_row.grid(row=2, column=0, columnspan=2, padx=16, pady=16, sticky="w")
        self._add_button(btn_row, "Add", add_staff, enabled=can_manage_staff)
        self._add_button(btn_row, "Update", update_staff, enabled=can_manage_staff)
        self._add_button(btn_row, "Delete", delete_staff, enabled=can_manage_staff)
        self._add_button(btn_row, "Clear", clear_form)

        filter_bar = self._action_bar(left)
        self._add_button(filter_bar, "Refresh", load_staff, side="right")
        load_staff()

        # --- Housekeeping ---
        hleft = tk.Frame(house_tab, bg=WHITE)
        hleft.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=12)
        hright = tk.Frame(house_tab, bg=CARD, width=300)
        hright.pack(side="right", fill="y", padx=(6, 0), pady=12)
        hright.pack_propagate(False)

        hcolumns = ("room_no", "assigned_staff", "status")
        hheadings = ("Room No.", "Assigned Staff", "Status")
        htree, hvsb = make_tree(hleft, hcolumns, hheadings, widths=(100, 180, 120))
        htree.pack(side="left", fill="both", expand=True)
        hvsb.pack(side="right", fill="y")

        def load_housekeeping():
            rows, _ = run_query(
                "SELECT room_no, assigned_staff, status FROM housekeeping ORDER BY room_no",
                fetch=True,
            )
            refresh_tree(htree, rows)

        tk.Label(hright, text="ASSIGN HOUSEKEEPING", bg=CARD, fg=GOLD, font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 10)
        )
        hform = tk.Frame(hright, bg=CARD)
        hform.grid(row=1, column=0, columnspan=2, padx=16, sticky="w")

        h_room = FormField(hform, 0, "Room No.")
        h_staff = FormField(hform, 1, "Assigned Staff")
        h_status = FormField(hform, 2, "Status", values=["Clean", "Dirty", "In Progress"])

        def hclear():
            for f in (h_room, h_staff, h_status):
                f.clear()
            htree.selection_remove(htree.selection())

        def hon_select(_event):
            values = selected_values(htree)
            if not values:
                return
            h_room.set(values[0])
            h_staff.set(values[1])
            h_status.set(values[2])

        htree.bind("<<TreeviewSelect>>", hon_select)

        def assign_room():
            if not h_room.get():
                messagebox.showwarning("Missing info", "Room number is required.")
                return
            try:
                run_query(
                    "INSERT INTO housekeeping (room_no, assigned_staff, status) VALUES (%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE assigned_staff=VALUES(assigned_staff), status=VALUES(status)",
                    (h_room.get(), h_staff.get(), h_status.get() or "Dirty"),
                    commit=True,
                )
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return
            messagebox.showinfo("Success", "Housekeeping assignment saved.")
            hclear()
            load_housekeeping()

        hbtn_row = tk.Frame(hright, bg=CARD)
        hbtn_row.grid(row=2, column=0, columnspan=2, padx=16, pady=16, sticky="w")
        self._add_button(hbtn_row, "Assign / Update", assign_room)
        self._add_button(hbtn_row, "Clear", hclear)

        hfilter_bar = self._action_bar(hleft)
        self._add_button(hfilter_bar, "Refresh", load_housekeeping, side="right")
        load_housekeeping()


# ---------------------------------------------------------------------------
# Small helper dialogs
# ---------------------------------------------------------------------------
class SearchDialog(tk.Toplevel):
    def __init__(self, parent, title, prompt):
        super().__init__(parent)
        self.title(title)
        self.geometry("320x140")
        self.configure(bg=WHITE)
        self.result = None
        self.grab_set()

        tk.Label(self, text=prompt, bg=WHITE, font=("Segoe UI", 10)).pack(pady=(20, 8))
        self.var = tk.StringVar()
        entry = tk.Entry(self, textvariable=self.var, width=30, font=("Segoe UI", 10))
        entry.pack()
        entry.focus_set()
        entry.bind("<Return>", lambda e: self._submit())

        btns = tk.Frame(self, bg=WHITE)
        btns.pack(pady=16)
        tk.Button(btns, text="Search", command=self._submit, bg=NAVY, fg=WHITE,
                  relief="flat", padx=14, pady=4).pack(side="left", padx=6)
        tk.Button(btns, text="Cancel", command=self.destroy, relief="flat", padx=14, pady=4).pack(side="left")

        self.wait_window(self)

    def _submit(self):
        self.result = self.var.get().strip()
        self.destroy()


class PaymentDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Select Payment Method")
        self.geometry("300x160")
        self.configure(bg=WHITE)
        self.result = None
        self.grab_set()

        tk.Label(self, text="Payment Method", bg=WHITE, font=("Segoe UI", 10, "bold")).pack(pady=(20, 8))
        self.var = tk.StringVar(value="Cash")
        combo = ttk.Combobox(self, textvariable=self.var, values=["Cash", "Card", "UPI"],
                              state="readonly", width=20)
        combo.pack()

        btns = tk.Frame(self, bg=WHITE)
        btns.pack(pady=20)
        tk.Button(btns, text="Confirm Payment", command=self._submit, bg=GOLD, fg=NAVY_DARK,
                  relief="flat", padx=14, pady=6, font=("Segoe UI", 9, "bold")).pack(side="left", padx=6)
        tk.Button(btns, text="Cancel", command=self.destroy, relief="flat", padx=14, pady=6).pack(side="left")

        self.wait_window(self)

    def _submit(self):
        self.result = self.var.get()
        self.destroy()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def start_app():
    login = LoginWindow()
    login.mainloop()
    if login.role:
        app = MainApp(login.role, login.username)
        app.mainloop()


if __name__ == "__main__":
    start_app()