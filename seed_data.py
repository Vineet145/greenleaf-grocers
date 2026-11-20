import random
from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash
from database import get_conn, init_db

CATALOG = {
 "Dairy": ["Milk 1L","Curd 500g","Butter 100g","Cheese Slices","Paneer 200g","Ghee 500ml","Fresh Cream","Buttermilk"],
 "Vegetables": ["Potato 1kg","Onion 1kg","Tomato 1kg","Carrot 500g","Spinach Bunch","Cauliflower","Capsicum","Cucumber"],
 "Fruits": ["Apple 1kg","Banana Dozen","Orange 1kg","Mango 1kg","Grapes 500g","Papaya","Pomegranate","Watermelon"],
 "Grains": ["Basmati Rice 5kg","Wheat Flour 5kg","Toor Dal 1kg","Moong Dal 1kg","Chana Dal 1kg","Poha 500g","Oats 1kg","Sugar 1kg"],
 "Snacks": ["Potato Chips","Namkeen Mix","Biscuits","Cookies","Popcorn","Chocolate Bar","Peanuts","Nachos"],
 "Beverages": ["Green Tea","Tea Powder","Coffee Jar","Fruit Juice 1L","Cola 2L","Mineral Water 1L","Coconut Water","Lemon Soda"],
 "Household": ["Detergent 1kg","Dish Soap","Floor Cleaner","Tissue Pack","Garbage Bags","Toothpaste","Hand Wash","Bath Soap"],
}
PERISHABLE = {"Dairy", "Vegetables", "Fruits"}

def seed(path, only_if_empty=False, n_sales=650, days=120):
    init_db(path)
    conn = get_conn(path)
    if only_if_empty and conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        conn.close()
        return
    rnd = random.Random(42)
    today = date.today()
    conn.executemany("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)", [
        ("admin", generate_password_hash("admin123"), "admin"),
        ("cashier", generate_password_hash("cashier123"), "cashier")])
    conn.executemany("INSERT INTO suppliers(name,phone,email) VALUES(?,?,?)", [
        ("Fresh Farms", "9876500001", "farms@example.com"),
        ("Daily Dairy Co", "9876500002", "dairy@example.com"),
        ("Home Needs Traders", "9876500003", "home@example.com")])
    pid = 0
    for cat, names in CATALOG.items():
        for name in names:
            pid += 1
            stock = rnd.randint(30, 200)
            if pid % 9 == 0:
                stock = rnd.randint(1, 8)  # low stock
            if cat in PERISHABLE:
                exp = today + timedelta(days=rnd.randint(3, 12) if pid % 7 == 0 else rnd.randint(20, 60))
            elif cat == "Household":
                exp = None
            else:
                exp = today + timedelta(days=rnd.randint(150, 365))
            conn.execute("INSERT INTO products(name,category,unit_price,stock_qty,reorder_level,expiry_date,supplier_id) VALUES(?,?,?,?,?,?,?)",
                         (name, cat, round(rnd.uniform(10, 450), 2), stock, rnd.randint(10, 30),
                          exp.isoformat() if exp else None, rnd.randint(1, 3)))
    prices = {r[0]: r[1] for r in conn.execute("SELECT product_id, unit_price FROM products")}
    slow = set(rnd.sample(list(prices), 8))  # these don't sell in the last 30 days
    for _ in range(n_sales):
        d = today - timedelta(days=rnd.randint(0, days - 1))
        pool = [p for p in prices if not (p in slow and (today - d).days < 30)]
        picks = rnd.sample(pool, rnd.randint(1, 4))
        disc = rnd.choice([0, 0, 0, 5, 10])
        lines = [(p, rnd.randint(1, 5)) for p in picks]
        total = round(sum(prices[p] * q for p, q in lines) * (1 - disc / 100), 2)
        sid = conn.execute("INSERT INTO sales(sale_date,sale_time,user_id,discount,total_amount) VALUES(?,?,?,?,?)",
                           (d.isoformat(), f"{rnd.randint(8,21):02d}:{rnd.randint(0,59):02d}:00", rnd.randint(1, 2), disc, total)).lastrowid
        conn.executemany("INSERT INTO sale_items(sale_id,product_id,quantity,price) VALUES(?,?,?,?)",
                         [(sid, p, q, prices[p]) for p, q in lines])
    conn.commit()
    conn.close()

if __name__ == "__main__":
    seed("greenleaf.db", only_if_empty=True)
    print("Done. Logins: admin/admin123 and cashier/cashier123")
