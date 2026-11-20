# GreenLeaf Grocers: Inventory & Sales Management System

Flask + SQLite + pandas web app for products, billing, stock alerts and sales analytics.

## Features
- Login with roles (admin: everything, cashier: billing only), hashed passwords
- Product add / edit / delete / search / category filter, CSV import
- Multi-item billing with discount, automatic stock deduction, print/CSV bill
- Low-stock and near-expiry (15 days) alerts
- Reports (pandas): daily, monthly, top 10, category share, slow-moving, with date range, charts (revenue/quantity toggle) and CSV export
- KPIs: total revenue, average bill, stock turnover, low-stock count, top category share

## Run locally
```
python -m venv venv
venv\Scripts\activate        # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
python seed_data.py          # 56 products, 650 sales over 120 days
python app.py                # open http://127.0.0.1:5000
```
Logins: `admin / admin123`, `cashier / cashier123`

## Tests
`python -m pytest -v` (15 tests, uses a separate temporary database)

## Project structure
`app.py` routes | `database.py` schema | `billing.py` billing logic | `reports.py` pandas analytics | `utils.py` validation/auth | `seed_data.py` sample data | `templates/`, `static/` UI | `tests/`

## Deploy (Render.com, free)
Build: `pip install -r requirements.txt` | Start: `gunicorn wsgi:app` | Env var: `SECRET_KEY` = any long random text.
Free hosting resets the SQLite file on restart; the app re-seeds sample data automatically.

## Screenshots
Add your screenshots here (dashboard, billing, reports).
