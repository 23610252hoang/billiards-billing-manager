# Billiards Billing Manager

A desktop billing and operations app for a billiards club. The app was rebuilt
as a clean portfolio version from an older local executable, with private
business data removed.

## Features

- Table session management: start, stop, and calculate play time.
- Automatic billing based on hourly rate, player count, prepaid amount, and discount.
- Service menu management for drinks or add-on items.
- Customer management with points tracking.
- Receipt export as text files.
- Daily revenue report from the SQLite database.
- Local-first storage using SQLite.

## Tech Stack

- Python 3.10+
- Tkinter desktop UI
- SQLite database
- Standard library only

## How to Run

```bash
python run_app.py
```

The app creates local runtime data in:

- `data/billiards_app.db`
- `reports/`

These generated files are ignored by Git.

## Project Structure

```text
src/billiards_manager/
  app.py       # Tkinter UI and user workflows
  database.py  # SQLite schema and data access
  __main__.py  # App entry point
run_app.py     # Convenient local launcher
```

## Why This Project

This project demonstrates a practical desktop application for a real business
workflow: tracking billiards table usage, calculating fees, saving history, and
exporting receipts. It is intentionally small, readable, and runnable without
external services.

## Notes

The old executable, real database, and generated reports are not included in
this repository because they may contain private shop information. This repo
contains only clean source code suitable for public review.
