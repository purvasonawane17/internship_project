# Hotel Management System (HMS)

A dual-interface (CLI + GUI) hotel management application built with Python and MySQL.

## Quick Start

```bash
# Install dependencies
pip install mysql-connector-python reportlab matplotlib

# CLI mode
python main.py

# GUI mode  
python gui.py
```

## Project Structure

```
HMS_Project/
├── main.py        ← CLI entry point
├── gui.py         ← Tkinter GUI entry point
├── db.py          ← Shared MySQL connection
├── guest.py       ← Guest CRUD module
├── reports.py     ← Analytics charts
│
├── cli/           ← All CLI business-logic modules
│   ├── authentication.py
│   ├── rooms.py
│   ├── booking.py
│   ├── billing.py
│   ├── service.py
│   ├── staff.py
│   └── guest.py
│
├── docs/          ← Project documentation
├── legacy/        ← Superseded/draft files (reference only)
├── receipts/      ← Generated PDF receipts
└── reports/       ← Generated analytics charts
```

## Roles

| Role | Default Password |
|---|---|
| Admin | `admin123` |
| Manager | `manager123` |
| Receptionist | `reception123` |

## Email Receipts

Set environment variables before running:
```bash
set HOTEL_SENDER_EMAIL=your@gmail.com
set HOTEL_APP_PASSWORD=your_gmail_app_password
```

See `docs/project_description.md` for the full architecture and role access map.
