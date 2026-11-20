from datetime import datetime

class BillError(ValueError):
    pass

def create_bill(conn, user_id, lines, discount=0):
    """lines = [(product_id, qty), ...]. Saves the sale and reduces stock."""
    if not lines:
        raise BillError("Add at least one item.")
    if not 0 <= discount <= 100:
        raise BillError("Discount must be between 0 and 100.")
    merged = {}
    for pid, qty in lines:
        if qty <= 0:
            raise BillError("Quantity must be at least 1.")
        merged[pid] = merged.get(pid, 0) + qty
    rows, subtotal = [], 0.0
    for pid, qty in merged.items():
        p = conn.execute("SELECT * FROM products WHERE product_id=?", (pid,)).fetchone()
        if not p:
            raise BillError("Product not found.")
        if qty > p["stock_qty"]:
            raise BillError(f"Only {p['stock_qty']} of {p['name']} left in stock.")
        rows.append((p, qty))
        subtotal += p["unit_price"] * qty
    total = round(subtotal * (1 - discount / 100), 2)
    now = datetime.now()
    cur = conn.execute(
        "INSERT INTO sales(sale_date,sale_time,user_id,discount,total_amount) VALUES(?,?,?,?,?)",
        (now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), user_id, discount, total))
    sid = cur.lastrowid
    for p, qty in rows:
        conn.execute("INSERT INTO sale_items(sale_id,product_id,quantity,price) VALUES(?,?,?,?)",
                     (sid, p["product_id"], qty, p["unit_price"]))
        conn.execute("UPDATE products SET stock_qty=stock_qty-? WHERE product_id=?",
                     (qty, p["product_id"]))
    conn.commit()
    return sid
