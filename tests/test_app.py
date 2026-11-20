import io, os, sys, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from werkzeug.security import generate_password_hash
from app import create_app
from database import get_conn
import billing
from utils import validate_product

@pytest.fixture
def app(tmp_path):
    a = create_app(str(tmp_path / "test.db"))  # separate test database
    c = get_conn(a.config["DB_PATH"])
    c.execute("INSERT INTO users(username,password_hash,role) VALUES('admin',?, 'admin')", (generate_password_hash("pw"),))
    c.execute("INSERT INTO users(username,password_hash,role) VALUES('cash',?, 'cashier')", (generate_password_hash("pw"),))
    c.execute("INSERT INTO products(name,category,unit_price,stock_qty,reorder_level) VALUES('Milk','Dairy',50,10,5)")
    c.execute("INSERT INTO products(name,category,unit_price,stock_qty,reorder_level) VALUES('Rice','Grains',100,3,5)")
    c.commit(); c.close()
    return a

def login(app, user):
    cl = app.test_client()
    cl.post("/login", data={"username": user, "password": "pw"})
    return cl

def stock(app, pid):
    c = get_conn(app.config["DB_PATH"]); s = c.execute("SELECT stock_qty FROM products WHERE product_id=?", (pid,)).fetchone()[0]; c.close(); return s

def test_login_ok(app):
    assert login(app, "admin").get("/").status_code == 200

def test_login_wrong_password(app):
    r = app.test_client().post("/login", data={"username": "admin", "password": "bad"})
    assert b"Wrong username or password" in r.data

def test_password_is_hashed(app):
    c = get_conn(app.config["DB_PATH"]); h = c.execute("SELECT password_hash FROM users").fetchone()[0]; c.close()
    assert h != "pw"

def test_cashier_cannot_open_products(app):
    r = login(app, "cash").get("/products")
    assert r.status_code == 302 and "/billing" in r.location

def test_billing_total_and_discount(app):
    c = get_conn(app.config["DB_PATH"])
    sid = billing.create_bill(c, 1, [(1, 2)], discount=10)
    assert c.execute("SELECT total_amount FROM sales WHERE sale_id=?", (sid,)).fetchone()[0] == 90.0
    c.close()

def test_stock_deducted_after_sale(app):
    c = get_conn(app.config["DB_PATH"]); billing.create_bill(c, 1, [(1, 4)]); c.close()
    assert stock(app, 1) == 6

def test_duplicate_lines_are_merged(app):
    c = get_conn(app.config["DB_PATH"]); billing.create_bill(c, 1, [(1, 2), (1, 3)]); c.close()
    assert stock(app, 1) == 5

def test_cannot_sell_more_than_stock(app):
    c = get_conn(app.config["DB_PATH"])
    with pytest.raises(billing.BillError): billing.create_bill(c, 1, [(2, 99)])
    c.close(); assert stock(app, 2) == 3

def test_negative_quantity_rejected(app):
    c = get_conn(app.config["DB_PATH"])
    with pytest.raises(billing.BillError): billing.create_bill(c, 1, [(1, -1)])
    c.close()

def test_bad_discount_rejected(app):
    c = get_conn(app.config["DB_PATH"])
    with pytest.raises(billing.BillError): billing.create_bill(c, 1, [(1, 1)], discount=150)
    c.close()

def test_product_validation():
    assert validate_product({"name": "A", "category": "B", "unit_price": "-5", "stock_qty": "1"})[1]
    assert validate_product({"name": "A", "category": "B", "unit_price": "5", "stock_qty": "1", "expiry_date": "31-12-2026"})[1]
    assert validate_product({"name": "A", "category": "B", "unit_price": "5", "stock_qty": "1"})[1] is None

def test_add_edit_delete_product(app):
    cl = login(app, "admin")
    cl.post("/products/new", data={"name": "Tea", "category": "Beverages", "unit_price": "80", "stock_qty": "20", "reorder_level": "5"})
    assert b"Tea" in cl.get("/products?q=Tea").data
    cl.post("/products/3/edit", data={"name": "Tea Gold", "category": "Beverages", "unit_price": "90", "stock_qty": "20", "reorder_level": "5"})
    assert b"Tea Gold" in cl.get("/products").data
    cl.post("/products/3/delete")
    assert b"Tea Gold" not in cl.get("/products").data

def test_billing_via_web_and_bad_input(app):
    cl = login(app, "cash")
    assert cl.post("/billing", data={"product_id": "1", "qty": "2", "discount": "0"}).status_code == 302
    assert b"Enter valid numbers" in cl.post("/billing", data={"product_id": "1", "qty": "abc"}).data

def test_reports_and_invalid_dates(app):
    cl = login(app, "admin")
    c = get_conn(app.config["DB_PATH"]); billing.create_bill(c, 1, [(1, 1)]); c.close()
    assert cl.get("/reports").status_code == 200
    assert b"Invalid date range" in cl.get("/reports?start=oops&end=2026-01-01").data
    assert cl.get("/export/daily").mimetype == "text/csv"

def test_csv_import(app):
    cl = login(app, "admin")
    data = b"name,category,unit_price,stock_qty,reorder_level,expiry_date\nSoap,Household,30,40,10,\nBad,Household,-1,5,5,\n"
    r = cl.post("/products/import", data={"file": (io.BytesIO(data), "p.csv")}, follow_redirects=True)
    assert b"Imported 1 products, skipped 1" in r.data
