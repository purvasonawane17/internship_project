"""
cli/authentication.py
=====================
Authentication module for the Hotel Management System CLI.
Handles login with role-based password verification.

login() returns the role string ("Admin" / "Manager" / "Receptionist")
on success, or None on failure — so callers can route without stdout
capturing.

The interactive menu is guarded by `if __name__ == "__main__":` so
this module can be safely imported without launching a prompt loop.
"""

from db import get_connection

# Expected passwords per role (plaintext — matches the existing users table).
_ROLE_PASSWORDS = {
    "Admin":        "admin123",
    "Manager":      "manager123",
    "Receptionist": "reception123",
    "Reception":    "reception123",   # backward-compat alias
}


def login():
    """
    Authenticate a user against the `users` table.

    Prints a welcome message on success and returns the canonical role
    string. Returns None on any failure.
    """
    username = input("Enter Username : ").strip()
    password = input("Enter Password : ").strip()

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT role FROM users WHERE username = %s AND password = %s",
            (username, password),
        )
        result = cursor.fetchone()

        if not result:
            print("Invalid Username or Password")
            return None

        role = result[0]
        expected_password = _ROLE_PASSWORDS.get(role)

        if expected_password and password == expected_password:
            # Normalise "Reception" → "Receptionist" for consistent routing
            canonical = "Receptionist" if role == "Reception" else role
            print("Login Successful")
            print(f"Welcome {canonical}")
            return canonical
        else:
            print("Invalid Role or Password")
            return None

    except Exception as e:
        print(f"Login error: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    role = login()
    if role:
        print(f"Logged in as: {role}")
