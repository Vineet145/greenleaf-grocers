from datetime import date, timedelta
import pandas as pd

def load(conn, start, end):
    sales = pd.read_sql_query(
        "SELECT sale_id, sale_date, total_amount FROM sales WHERE sale_date BETWEEN ? AND ?",
        conn, params=(start, end))
    items = pd.read_sql_query(
        """SELECT s.sale_id, s.sale_date, p.product_id, p.name, p.category, si.quantity,
                  si.quantity*si.price AS revenue
           FROM sale_items si JOIN sales s ON s.sale_id=si.sale_id
           JOIN products p ON p.product_id=si.product_id
           WHERE s.sale_date BETWEEN ? AND ?""", conn, params=(start, end))
    return sales, items

def daily(sales):
    return (sales.groupby("sale_date").agg(revenue=("total_amount", "sum"), bills=("sale_id", "count"))
            .round(2).reset_index())

def monthly(sales):
    s = sales.assign(month=sales["sale_date"].str[:7])
    return s.groupby("month").agg(revenue=("total_amount", "sum"), bills=("sale_id", "count")).round(2).reset_index()

def top_products(items, n=10):
    g = items.groupby("name").agg(quantity=("quantity", "sum"), revenue=("revenue", "sum")).round(2)
    return g.sort_values("quantity", ascending=False).head(n).reset_index()

def category_share(items):
    g = items.groupby("category").agg(quantity=("quantity", "sum"), revenue=("revenue", "sum")).round(2)
    total = g["revenue"].sum()
    g["share_pct"] = (g["revenue"] / total * 100).round(1) if total else 0
    return g.sort_values("revenue", ascending=False).reset_index()

def slow_moving(conn, days=30):
    since = (date.today() - timedelta(days=days)).isoformat()
    return pd.read_sql_query(
        """SELECT product_id, name, category, stock_qty FROM products WHERE product_id NOT IN
           (SELECT si.product_id FROM sale_items si JOIN sales s ON s.sale_id=si.sale_id
            WHERE s.sale_date >= ?) ORDER BY stock_qty DESC""", conn, params=(since,))

def low_stock(conn):
    return pd.read_sql_query(
        "SELECT name, category, stock_qty, reorder_level FROM products WHERE stock_qty <= reorder_level ORDER BY stock_qty",
        conn)

def expiring(conn, days=15):
    limit = (date.today() + timedelta(days=days)).isoformat()
    return pd.read_sql_query(
        "SELECT name, category, stock_qty, expiry_date FROM products WHERE expiry_date IS NOT NULL AND expiry_date <= ? ORDER BY expiry_date",
        conn, params=(limit,))

def kpis(conn, sales, items):
    total = float(sales["total_amount"].sum())
    bills = len(sales)
    stock = conn.execute("SELECT COALESCE(SUM(stock_qty),0) FROM products").fetchone()[0]
    sold = int(items["quantity"].sum()) if len(items) else 0
    cats = category_share(items)
    return {
        "Total Revenue": f"₹{total:,.2f}",
        "Average Bill Value": f"₹{total / bills:,.2f}" if bills else "₹0.00",
        "Stock Turnover": f"{sold / stock:.2f}" if stock else "0.00",
        "Low-Stock Items": len(low_stock(conn)),
        "Top Category Share": f"{cats.iloc[0]['share_pct']}% ({cats.iloc[0]['category']})" if len(cats) else "0%",
    }
