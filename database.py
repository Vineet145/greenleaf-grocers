import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  user_id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('admin','cashier')));
CREATE TABLE IF NOT EXISTS suppliers(
  supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, phone TEXT, email TEXT);
CREATE TABLE IF NOT EXISTS products(
  product_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, category TEXT NOT NULL,
  unit_price REAL NOT NULL CHECK(unit_price > 0),
  stock_qty INTEGER NOT NULL CHECK(stock_qty >= 0),
  reorder_level INTEGER NOT NULL DEFAULT 10 CHECK(reorder_level >= 0),
  expiry_date TEXT,
  supplier_id INTEGER REFERENCES suppliers(supplier_id));
CREATE TABLE IF NOT EXISTS sales(
  sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
  sale_date TEXT NOT NULL, sale_time TEXT NOT NULL,
  user_id INTEGER NOT NULL REFERENCES users(user_id),
  discount REAL NOT NULL DEFAULT 0,
  total_amount REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sale_items(
  sale_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
  sale_id INTEGER NOT NULL REFERENCES sales(sale_id),
  product_id INTEGER NOT NULL REFERENCES products(product_id),
  quantity INTEGER NOT NULL CHECK(quantity > 0),
  price REAL NOT NULL);
"""

def get_conn(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db(path):
    conn = get_conn(path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
