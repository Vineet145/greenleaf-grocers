from datetime import datetime
from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(role=None):
    def deco(f):
        @wraps(f)
        def wrapper(*a, **k):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("Only admin can open that page.", "error")
                return redirect(url_for("billing_page"))
            return f(*a, **k)
        return wrapper
    return deco

def valid_date(s):
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False

def validate_product(d):
    """Return (clean_dict, error_message)."""
    try:
        name = (d.get("name") or "").strip()
        category = (d.get("category") or "").strip()
        price = float(d.get("unit_price"))
        stock = int(d.get("stock_qty"))
        reorder = int(d.get("reorder_level") or 10)
    except (TypeError, ValueError):
        return None, "Price must be a number; stock and reorder level must be whole numbers."
    expiry = (d.get("expiry_date") or "").strip() or None
    if not name or not category:
        return None, "Name and category are required."
    if price <= 0:
        return None, "Price must be greater than 0."
    if stock < 0 or reorder < 0:
        return None, "Stock and reorder level cannot be negative."
    if expiry and not valid_date(expiry):
        return None, "Expiry date must look like YYYY-MM-DD."
    return dict(name=name, category=category, unit_price=price, stock_qty=stock,
                reorder_level=reorder, expiry_date=expiry), None
