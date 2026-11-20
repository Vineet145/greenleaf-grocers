import csv, io, os
from datetime import date, timedelta
from flask import (Flask, render_template, request, redirect, url_for, session,
                   flash, Response)
from werkzeug.security import check_password_hash
from database import get_conn, init_db
from utils import login_required, valid_date, validate_product
import billing, reports

def create_app(db_path=None, seed=False):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["DB_PATH"] = db_path or os.environ.get("DB_PATH", "greenleaf.db")
    init_db(app.config["DB_PATH"])
    if seed:
        import seed_data
        seed_data.seed(app.config["DB_PATH"], only_if_empty=True)

    def db():
        return get_conn(app.config["DB_PATH"])

    def dates():
        end, start = date.today().isoformat(), (date.today() - timedelta(days=29)).isoformat()
        s, e = request.args.get("start", start), request.args.get("end", end)
        if not (valid_date(s) and valid_date(e)) or s > e:
            flash("Invalid date range, showing the last 30 days.", "error")
            return start, end
        return s, e

    @app.errorhandler(404)
    def nf(_):
        return render_template("message.html", msg="Page not found."), 404

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            conn = db()
            u = conn.execute("SELECT * FROM users WHERE username=?",
                             (request.form.get("username", "").strip(),)).fetchone()
            conn.close()
            if u and check_password_hash(u["password_hash"], request.form.get("password", "")):
                session.clear()
                session.update(user_id=u["user_id"], username=u["username"], role=u["role"])
                return redirect(url_for("index"))
            flash("Wrong username or password.", "error")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    @login_required()
    def index():
        if session["role"] != "admin":
            return redirect(url_for("billing_page"))
        conn = db()
        s, e = dates()
        sales, items = reports.load(conn, s, e)
        ctx = dict(kpis=reports.kpis(conn, sales, items),
                   low=reports.low_stock(conn).to_dict("records"),
                   exp=reports.expiring(conn).to_dict("records"))
        conn.close()
        return render_template("dashboard.html", **ctx)

    # ---------- products ----------
    @app.route("/products")
    @login_required("admin")
    def products():
        q, cat = request.args.get("q", "").strip(), request.args.get("category", "")
        sql, args = "SELECT * FROM products WHERE name LIKE ?", [f"%{q}%"]
        if cat:
            sql += " AND category=?"
            args.append(cat)
        conn = db()
        rows = conn.execute(sql + " ORDER BY name", args).fetchall()
        cats = [r[0] for r in conn.execute("SELECT DISTINCT category FROM products ORDER BY 1")]
        conn.close()
        return render_template("products.html", rows=rows, cats=cats, q=q, cat=cat, today=date.today().isoformat())

    @app.route("/products/new", methods=["GET", "POST"])
    @app.route("/products/<int:pid>/edit", methods=["GET", "POST"])
    @login_required("admin")
    def product_form(pid=None):
        conn = db()
        p = conn.execute("SELECT * FROM products WHERE product_id=?", (pid,)).fetchone() if pid else None
        if pid and not p:
            conn.close()
            return render_template("message.html", msg="Product not found."), 404
        if request.method == "POST":
            data, err = validate_product(request.form)
            if err:
                flash(err, "error")
                p = request.form
            else:
                if pid:
                    conn.execute("""UPDATE products SET name=:name, category=:category, unit_price=:unit_price,
                        stock_qty=:stock_qty, reorder_level=:reorder_level, expiry_date=:expiry_date
                        WHERE product_id=:id""", {**data, "id": pid})
                else:
                    conn.execute("""INSERT INTO products(name,category,unit_price,stock_qty,reorder_level,expiry_date)
                        VALUES(:name,:category,:unit_price,:stock_qty,:reorder_level,:expiry_date)""", data)
                conn.commit()
                conn.close()
                flash("Product saved.", "ok")
                return redirect(url_for("products"))
        conn.close()
        return render_template("product_form.html", p=p)

    @app.route("/products/<int:pid>/delete", methods=["POST"])
    @login_required("admin")
    def product_delete(pid):
        conn = db()
        used = conn.execute("SELECT 1 FROM sale_items WHERE product_id=?", (pid,)).fetchone()
        if used:
            flash("This product has sales history, so it can't be deleted. Set its stock to 0 instead.", "error")
        else:
            conn.execute("DELETE FROM products WHERE product_id=?", (pid,))
            conn.commit()
            flash("Product deleted.", "ok")
        conn.close()
        return redirect(url_for("products"))

    @app.route("/products/import", methods=["POST"])
    @login_required("admin")
    def product_import():
        f = request.files.get("file")
        if not f or not f.filename.lower().endswith(".csv"):
            flash("Choose a .csv file.", "error")
            return redirect(url_for("products"))
        ok = bad = 0
        conn = db()
        try:
            for row in csv.DictReader(io.StringIO(f.read().decode("utf-8-sig"))):
                data, err = validate_product(row)
                if err:
                    bad += 1
                    continue
                conn.execute("""INSERT INTO products(name,category,unit_price,stock_qty,reorder_level,expiry_date)
                    VALUES(:name,:category,:unit_price,:stock_qty,:reorder_level,:expiry_date)""", data)
                ok += 1
            conn.commit()
        except (UnicodeDecodeError, csv.Error):
            flash("Could not read that file.", "error")
        conn.close()
        flash(f"Imported {ok} products, skipped {bad} invalid rows.", "ok" if ok else "error")
        return redirect(url_for("products"))

    # ---------- billing ----------
    @app.route("/billing", methods=["GET", "POST"])
    @login_required()
    def billing_page():
        conn = db()
        if request.method == "POST":
            try:
                lines = [(int(p), int(q)) for p, q in
                         zip(request.form.getlist("product_id"), request.form.getlist("qty")) if p]
                disc = float(request.form.get("discount") or 0)
                sid = billing.create_bill(conn, session["user_id"], lines, disc)
                conn.close()
                return redirect(url_for("bill_view", sid=sid))
            except (ValueError, billing.BillError) as ex:
                flash(str(ex) if isinstance(ex, billing.BillError) else "Enter valid numbers.", "error")
        prods = conn.execute("SELECT * FROM products WHERE stock_qty>0 ORDER BY name").fetchall()
        conn.close()
        return render_template("billing.html", prods=prods)

    def get_bill(sid):
        conn = db()
        sale = conn.execute("SELECT s.*, u.username FROM sales s JOIN users u USING(user_id) WHERE sale_id=?", (sid,)).fetchone()
        items = conn.execute("""SELECT p.name, si.quantity, si.price FROM sale_items si
            JOIN products p USING(product_id) WHERE sale_id=?""", (sid,)).fetchall()
        conn.close()
        return sale, items

    @app.route("/bill/<int:sid>")
    @login_required()
    def bill_view(sid):
        sale, items = get_bill(sid)
        if not sale:
            return render_template("message.html", msg="Bill not found."), 404
        return render_template("bill.html", sale=sale, items=items)

    @app.route("/bill/<int:sid>/download")
    @login_required()
    def bill_download(sid):
        sale, items = get_bill(sid)
        if not sale:
            return render_template("message.html", msg="Bill not found."), 404
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["item", "quantity", "price", "amount"])
        for i in items:
            w.writerow([i["name"], i["quantity"], i["price"], i["quantity"] * i["price"]])
        w.writerow(["discount %", sale["discount"]])
        w.writerow(["total", sale["total_amount"]])
        return Response(out.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename=bill_{sid}.csv"})

    # ---------- reports ----------
    @app.route("/reports")
    @login_required("admin")
    def reports_page():
        s, e = dates()
        conn = db()
        sales, items = reports.load(conn, s, e)
        top, cats = reports.top_products(items), reports.category_share(items)
        ctx = dict(start=s, end=e, kpis=reports.kpis(conn, sales, items),
                   daily=reports.daily(sales).to_dict("records"),
                   monthly=reports.monthly(sales).to_dict("records"),
                   top=top.to_dict("records"), cats=cats.to_dict("records"),
                   slow=reports.slow_moving(conn).to_dict("records"),
                   low=reports.low_stock(conn).to_dict("records"),
                   exp=reports.expiring(conn).to_dict("records"))
        conn.close()
        return render_template("reports.html", **ctx)

    @app.route("/export/<name>")
    @login_required("admin")
    def export(name):
        s, e = dates()
        conn = db()
        sales, items = reports.load(conn, s, e)
        table = {"daily": lambda: reports.daily(sales), "monthly": lambda: reports.monthly(sales),
                 "top": lambda: reports.top_products(items), "category": lambda: reports.category_share(items),
                 "slow": lambda: reports.slow_moving(conn), "lowstock": lambda: reports.low_stock(conn),
                 "expiry": lambda: reports.expiring(conn)}.get(name)
        if not table:
            conn.close()
            return render_template("message.html", msg="Unknown report."), 404
        df = table()
        conn.close()
        return Response(df.to_csv(index=False), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={name}_report.csv"})

    return app

if __name__ == "__main__":
    create_app(seed=True).run(debug=True)
