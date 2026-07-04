from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlparse
import csv
import hashlib
import io
import json
import secrets
import shutil
import sqlite3
import sys
import time


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DB_PATH = BASE_DIR / "famai_motor.db"
BACKUP_DIR = BASE_DIR / "backups"
MODEL_PRICES_PATH = BASE_DIR / "yamaha_model_prices.json"
SESSIONS = {}


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now_text():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def row_to_dict(row):
    return dict(row) if row is not None else None


def init_db():
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS branches (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              username TEXT UNIQUE,
              password_hash TEXT,
              role TEXT NOT NULL CHECK (role IN ('admin', 'sales', 'stock', 'accounting', 'manager')),
              branch_id INTEGER REFERENCES branches(id)
            );

            CREATE TABLE IF NOT EXISTS customers (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              surname TEXT,
              nickname TEXT,
              how_to_call TEXT,
              phone TEXT,
              address TEXT,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS motorcycles (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              branch_id INTEGER NOT NULL REFERENCES branches(id),
              model_code TEXT,
              model TEXT NOT NULL,
              color_code TEXT,
              color TEXT,
              engine_no TEXT NOT NULL UNIQUE,
              frame_no TEXT NOT NULL UNIQUE,
              cost REAL NOT NULL DEFAULT 0,
              status TEXT NOT NULL CHECK (status IN ('available', 'hold', 'sold', 'written_off')) DEFAULT 'available',
              received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS model_prices (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              code TEXT NOT NULL UNIQUE,
              name TEXT NOT NULL,
              cc REAL,
              model_year INTEGER,
              cost REAL NOT NULL,
              vat REAL NOT NULL DEFAULT 0,
              total REAL NOT NULL DEFAULT 0,
              retail_price REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sales (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              motorcycle_id INTEGER NOT NULL UNIQUE REFERENCES motorcycles(id),
              customer_id INTEGER REFERENCES customers(id),
              sale_price REAL NOT NULL,
              payment_method TEXT NOT NULL DEFAULT 'cash',
              salesperson TEXT,
              finance_company TEXT,
              finance_status TEXT NOT NULL DEFAULT 'none',
              registration_status TEXT NOT NULL DEFAULT 'ขายแล้ว',
              sold_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS expenses (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              branch_id INTEGER NOT NULL REFERENCES branches(id),
              category TEXT NOT NULL,
              amount REAL NOT NULL,
              note TEXT,
              paid_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS stock_movements (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              motorcycle_id INTEGER REFERENCES motorcycles(id),
              branch_id INTEGER REFERENCES branches(id),
              movement_type TEXT NOT NULL,
              note TEXT,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS customer_cases (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              branch_id INTEGER NOT NULL REFERENCES branches(id),
              first_name TEXT NOT NULL,
              surname TEXT,
              nickname TEXT,
              how_to_call TEXT,
              phone TEXT NOT NULL,
              salesperson TEXT,
              case_status TEXT NOT NULL CHECK (case_status IN ('ปิดการขายได้', 'ลูกค้าสนใจ', 'ลูกค้าไม่สนใจ', 'ติด finance')),
              note TEXT,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS registration_records (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              sale_id INTEGER REFERENCES sales(id),
              branch_id INTEGER NOT NULL REFERENCES branches(id),
              first_name TEXT NOT NULL,
              surname TEXT,
              nickname TEXT,
              how_to_call TEXT,
              phone TEXT NOT NULL,
              registration_status TEXT NOT NULL CHECK (registration_status IN ('จดทะเบียน', 'รอจดทะเบียน')),
              submitted_at TEXT NOT NULL,
              registered_at TEXT,
              note TEXT,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS service_records (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              sale_id INTEGER REFERENCES sales(id),
              customer_id INTEGER REFERENCES customers(id),
              motorcycle_id INTEGER REFERENCES motorcycles(id),
              service_at TEXT,
              oil_change_at TEXT,
              note TEXT,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS receipt_prints (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              sale_id INTEGER NOT NULL REFERENCES sales(id),
              authorized_by INTEGER NOT NULL REFERENCES users(id),
              requested_by INTEGER REFERENCES users(id),
              printed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS parts_sales (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              branch_id INTEGER NOT NULL REFERENCES branches(id),
              part_name TEXT NOT NULL,
              part_code TEXT,
              quantity INTEGER NOT NULL DEFAULT 1,
              unit_price REAL NOT NULL DEFAULT 0,
              gross_amount REAL NOT NULL DEFAULT 0,
              discount_amount REAL NOT NULL DEFAULT 0,
              sale_total REAL NOT NULL DEFAULT 0,
              cost_total REAL NOT NULL DEFAULT 0,
              profit REAL NOT NULL DEFAULT 0,
              customer_name TEXT,
              salesperson TEXT,
              note TEXT,
              sold_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        for name in ["Famai Motor Group", "Famai Motor", "Famai Center Group"]:
            conn.execute("INSERT OR IGNORE INTO branches (name) VALUES (?)", (name,))

        if MODEL_PRICES_PATH.exists():
            model_prices = json.loads(MODEL_PRICES_PATH.read_text())
            for item in model_prices:
                conn.execute(
                    """
                    INSERT INTO model_prices (code, name, cc, model_year, cost, vat, total, retail_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(code) DO UPDATE SET
                      name = excluded.name,
                      cc = excluded.cc,
                      model_year = excluded.model_year,
                      cost = excluded.cost,
                      vat = excluded.vat,
                      total = excluded.total,
                      retail_price = excluded.retail_price
                    """,
                    (
                        item["code"],
                        item["name"],
                        item["cc"],
                        item["year"],
                        item["cost"],
                        item["vat"],
                        item["total"],
                        item["retail_price"],
                    ),
                )

        columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
        if "username" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN username TEXT")
        if "password_hash" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")

        customer_columns = {row["name"] for row in conn.execute("PRAGMA table_info(customers)")}
        if "surname" not in customer_columns:
            conn.execute("ALTER TABLE customers ADD COLUMN surname TEXT")
        if "nickname" not in customer_columns:
            conn.execute("ALTER TABLE customers ADD COLUMN nickname TEXT")
        if "how_to_call" not in customer_columns:
            conn.execute("ALTER TABLE customers ADD COLUMN how_to_call TEXT")

        motorcycle_columns = {row["name"] for row in conn.execute("PRAGMA table_info(motorcycles)")}
        if "model_code" not in motorcycle_columns:
            conn.execute("ALTER TABLE motorcycles ADD COLUMN model_code TEXT")
        if "color_code" not in motorcycle_columns:
            conn.execute("ALTER TABLE motorcycles ADD COLUMN color_code TEXT")

        sales_columns = {row["name"] for row in conn.execute("PRAGMA table_info(sales)")}
        if "salesperson" not in sales_columns:
            conn.execute("ALTER TABLE sales ADD COLUMN salesperson TEXT")
        if "finance_company" not in sales_columns:
            conn.execute("ALTER TABLE sales ADD COLUMN finance_company TEXT")
        if "finance_status" not in sales_columns:
            conn.execute("ALTER TABLE sales ADD COLUMN finance_status TEXT NOT NULL DEFAULT 'none'")
        if "registration_status" not in sales_columns:
            conn.execute("ALTER TABLE sales ADD COLUMN registration_status TEXT NOT NULL DEFAULT 'ขายแล้ว'")

        default_users = [
            ("Famai Admin", "admin", "admin", "admin123"),
            ("Sales Staff", "sales", "sales", "sales123"),
            ("Stock Staff", "stock", "stock", "stock123"),
            ("Accounting Staff", "accounting", "accounting", "accounting123"),
            ("Manager", "manager", "manager", "manager123"),
        ]
        for name, role, username, password in default_users:
            existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE users
                    SET name = ?, role = ?, password_hash = COALESCE(password_hash, ?)
                    WHERE username = ?
                    """,
                    (name, role, hash_password(password), username),
                )
            else:
                conn.execute(
                    "INSERT INTO users (name, role, username, password_hash) VALUES (?, ?, ?, ?)",
                    (name, role, username, hash_password(password)),
                )

        stock_exists = conn.execute("SELECT id FROM motorcycles LIMIT 1").fetchone()
        if not stock_exists:
            branch_ids = {row["name"]: row["id"] for row in conn.execute("SELECT id, name FROM branches")}
            starter_units = [
                ("Famai Motor Group", "NMAX", "Blue", "E-NMAX-001", "F-NMAX-001", 72000),
                ("Famai Motor Group", "Grand Filano", "White", "E-FIL-001", "F-FIL-001", 64500),
                ("Famai Motor", "Aerox", "Black", "E-AER-001", "F-AER-001", 68500),
                ("Famai Center Group", "Finn", "Red", "E-FIN-001", "F-FIN-001", 41000),
            ]
            for branch, model, color, engine_no, frame_no, cost in starter_units:
                cursor = conn.execute(
                    """
                    INSERT INTO motorcycles (branch_id, model_code, model, color_code, color, engine_no, frame_no, cost)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (branch_ids[branch], "", model, "", color, engine_no, frame_no, cost),
                )
                conn.execute(
                    """
                    INSERT INTO stock_movements (motorcycle_id, branch_id, movement_type, note)
                    VALUES (?, ?, 'receive', 'Opening stock')
                    """,
                    (cursor.lastrowid, branch_ids[branch]),
                )


def get_json(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    if length == 0:
        return {}
    raw = handler.rfile.read(length).decode("utf-8")
    return json.loads(raw)


def send_json(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def send_cookie_json(handler, status, payload, cookie=None):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    if cookie:
        handler.send_header("Set-Cookie", cookie)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def require_fields(data, fields):
    missing = [field for field in fields if data.get(field) in (None, "")]
    if missing:
        raise ValueError("Missing: " + ", ".join(missing))


def read_csv_rows(csv_text):
    text = csv_text.lstrip("\ufeff").strip()
    if not text:
        raise ValueError("CSV file is empty.")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV header row is missing.")
    return [{(key or "").strip(): (value or "").strip() for key, value in row.items()} for row in reader]


def pick(row, *names, default=""):
    for name in names:
        if row.get(name) not in (None, ""):
            return row[name]
    return default


def parse_money(value, default=0):
    if value in (None, ""):
        return default
    return float(str(value).replace(",", "").strip())


def public_user(user):
    if not user:
        return None
    return {
        "id": user["id"],
        "name": user["name"],
        "username": user["username"],
        "role": user["role"],
        "branch_id": user["branch_id"],
    }


def user_from_request(handler):
    cookie_header = handler.headers.get("Cookie", "")
    cookie = SimpleCookie()
    cookie.load(cookie_header)
    session_id = cookie.get("famai_session")
    if not session_id:
        return None
    user_id = SESSIONS.get(session_id.value)
    if not user_id:
        return None
    with connect() as conn:
        return conn.execute(
            "SELECT id, name, username, role, branch_id FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()


def require_login(handler):
    user = user_from_request(handler)
    if not user:
        raise PermissionError("Please log in first.")
    return user


def require_role(user, roles):
    if user["role"] not in roles:
        raise PermissionError("Your role cannot do this action.")


def list_branches(conn):
    return [row_to_dict(row) for row in conn.execute("SELECT id, name FROM branches ORDER BY id")]


def list_motorcycles(conn):
    rows = conn.execute(
        """
        SELECT m.id, b.name AS branch, m.branch_id, m.model, m.color_code, m.color, m.engine_no, m.frame_no,
               m.model_code, m.cost, m.status, m.received_at, m.updated_at
        FROM motorcycles m
        JOIN branches b ON b.id = m.branch_id
        ORDER BY m.status, b.name, m.model, m.engine_no
        """
    )
    return [row_to_dict(row) for row in rows]


def branch_id_by_name(conn, name):
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Branch name is missing.")
    row = conn.execute("SELECT id FROM branches WHERE name = ?", (clean_name,)).fetchone()
    if row:
        return row["id"]
    cursor = conn.execute("INSERT INTO branches (name) VALUES (?)", (clean_name,))
    return cursor.lastrowid


def list_model_prices(conn):
    rows = conn.execute(
        """
        SELECT id, code, name, cc, model_year, cost, vat, total, retail_price
        FROM model_prices
        ORDER BY model_year DESC, name, code
        """
    )
    return [row_to_dict(row) for row in rows]


def list_sold_sales(conn):
    rows = conn.execute(
        """
        SELECT s.id, b.id AS branch_id, b.name AS branch, m.model, m.engine_no, m.frame_no,
               c.id AS customer_id, c.name AS customer_name, c.surname, c.nickname,
               c.how_to_call, c.phone, s.sold_at,
               rr.registration_status AS latest_registration_status,
               rr.registered_at AS latest_registered_at
        FROM sales s
        JOIN motorcycles m ON m.id = s.motorcycle_id
        JOIN branches b ON b.id = m.branch_id
        LEFT JOIN customers c ON c.id = s.customer_id
        LEFT JOIN (
            SELECT r1.*
            FROM registration_records r1
            JOIN (
                SELECT sale_id, MAX(id) AS max_id
                FROM registration_records
                GROUP BY sale_id
            ) latest ON latest.max_id = r1.id
        ) rr ON rr.sale_id = s.id
        ORDER BY s.id DESC
        LIMIT 200
        """
    )
    return [row_to_dict(row) for row in rows]


def customer_dashboard(conn):
    sale_rows = conn.execute(
        """
        SELECT c.id AS customer_id, c.name, c.surname, c.nickname, c.how_to_call,
               c.phone, c.address, s.id AS sale_id, s.sold_at, b.name AS branch,
               m.id AS motorcycle_id, m.model, m.model_code, m.color_code, m.color,
               m.engine_no, m.frame_no,
               rr.registered_at
        FROM customers c
        LEFT JOIN sales s ON s.customer_id = c.id
        LEFT JOIN motorcycles m ON m.id = s.motorcycle_id
        LEFT JOIN branches b ON b.id = m.branch_id
        LEFT JOIN registration_records rr ON rr.sale_id = s.id
        ORDER BY c.id DESC, s.sold_at DESC
        """
    ).fetchall()
    service_rows = conn.execute(
        """
        SELECT sr.sale_id, sr.customer_id, sr.motorcycle_id, sr.service_at, sr.oil_change_at, sr.note
        FROM service_records sr
        ORDER BY COALESCE(sr.service_at, sr.oil_change_at, sr.created_at) DESC
        """
    ).fetchall()
    services_by_sale = {}
    services_by_customer = {}
    for row in service_rows:
        item = row_to_dict(row)
        if item["sale_id"]:
            services_by_sale.setdefault(item["sale_id"], []).append(item)
        if item["customer_id"]:
            services_by_customer.setdefault(item["customer_id"], []).append(item)

    customers = {}
    for row in sale_rows:
        item = row_to_dict(row)
        customer_id = item["customer_id"]
        customer = customers.setdefault(customer_id, {
            "customer_id": customer_id,
            "name": item["name"],
            "surname": item["surname"],
            "nickname": item["nickname"],
            "how_to_call": item["how_to_call"],
            "phone": item["phone"],
            "address": item["address"],
            "motorcycles": [],
            "services": services_by_customer.get(customer_id, []),
        })
        if item["sale_id"]:
            customer["motorcycles"].append({
                "sale_id": item["sale_id"],
                "branch": item["branch"],
                "model": item["model"],
                "model_code": item["model_code"],
                "color_code": item["color_code"],
                "color": item["color"],
                "engine_no": item["engine_no"],
                "frame_no": item["frame_no"],
                "sold_at": item["sold_at"],
                "registered_at": item["registered_at"],
                "services": services_by_sale.get(item["sale_id"], []),
            })
    return list(customers.values())


def summary(conn):
    motorcycle_sales_total = conn.execute("SELECT COALESCE(SUM(sale_price), 0) AS total FROM sales").fetchone()["total"]
    parts_sales_total = conn.execute("SELECT COALESCE(SUM(sale_total), 0) AS total FROM parts_sales").fetchone()["total"]
    parts_profit_total = conn.execute("SELECT COALESCE(SUM(profit), 0) AS total FROM parts_sales").fetchone()["total"]
    sales_total = motorcycle_sales_total + parts_sales_total
    expense_total = conn.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM expenses").fetchone()["total"]
    sold_count = conn.execute("SELECT COUNT(*) AS total FROM sales").fetchone()["total"]
    available_count = conn.execute("SELECT COUNT(*) AS total FROM motorcycles WHERE status = 'available'").fetchone()["total"]
    low_stock = conn.execute(
        """
        SELECT model, COUNT(*) AS qty
        FROM motorcycles
        WHERE status = 'available'
        GROUP BY model
        HAVING qty <= 1
        """
    ).fetchall()
    return {
        "sales_total": sales_total,
        "motorcycle_sales_total": motorcycle_sales_total,
        "parts_sales_total": parts_sales_total,
        "parts_profit_total": parts_profit_total,
        "expense_total": expense_total,
        "net_cash": sales_total - expense_total,
        "sold_count": sold_count,
        "available_count": available_count,
        "stock_risk_count": len(low_stock),
    }


def scalar(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()[0] or 0


def management_dashboard(conn):
    today = time.strftime("%Y-%m-%d")
    month = time.strftime("%Y-%m")
    today_like = today + "%"
    month_like = month + "%"

    def period_metrics(pattern):
        row = conn.execute(
            """
            SELECT COUNT(*) AS units,
                   COALESCE(SUM(s.sale_price), 0) AS revenue,
                   COALESCE(SUM(s.sale_price - m.cost), 0) AS gross_profit,
                   SUM(CASE WHEN s.payment_method = 'finance' THEN 1 ELSE 0 END) AS finance_deals,
                   SUM(CASE WHEN s.payment_method = 'cash' THEN 1 ELSE 0 END) AS cash_deals
            FROM sales s
            JOIN motorcycles m ON m.id = s.motorcycle_id
            WHERE s.sold_at LIKE ?
            """,
            (pattern,),
        ).fetchone()
        return row_to_dict(row)

    today_metrics = period_metrics(today_like)
    mtd_metrics = period_metrics(month_like)
    expense_today = scalar(conn, "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE paid_at LIKE ?", (today_like,))
    parts_today = conn.execute(
        """
        SELECT COALESCE(SUM(sale_total), 0) AS revenue,
               COALESCE(SUM(profit), 0) AS profit
        FROM parts_sales
        WHERE sold_at LIKE ?
        """,
        (today_like,),
    ).fetchone()
    parts_mtd = conn.execute(
        """
        SELECT COALESCE(SUM(sale_total), 0) AS revenue,
               COALESCE(SUM(profit), 0) AS profit
        FROM parts_sales
        WHERE sold_at LIKE ?
        """,
        (month_like,),
    ).fetchone()

    branch_rows = conn.execute(
        """
        SELECT b.name AS branch,
               COUNT(s.id) AS sales,
               COALESCE(SUM(s.sale_price), 0) AS revenue,
               COALESCE(SUM(s.sale_price - m.cost), 0) AS gross_profit
        FROM branches b
        LEFT JOIN motorcycles m ON m.branch_id = b.id
        LEFT JOIN sales s ON s.motorcycle_id = m.id AND s.sold_at LIKE ?
        GROUP BY b.id
        ORDER BY revenue DESC
        """,
        (month_like,),
    ).fetchall()
    branch_comparison = [row_to_dict(row) for row in branch_rows]
    if branch_comparison:
        max_revenue = max(row["revenue"] for row in branch_comparison)
        min_revenue = min(row["revenue"] for row in branch_comparison)
        for row in branch_comparison:
            row["rank_color"] = "green" if row["revenue"] == max_revenue and max_revenue > 0 else "red" if row["revenue"] == min_revenue and max_revenue > 0 else ""

    salesperson_rows = conn.execute(
        """
        SELECT COALESCE(NULLIF(s.salesperson, ''), 'Unknown') AS salesperson,
               COUNT(*) AS units,
               COALESCE(SUM(s.sale_price), 0) AS revenue,
               COALESCE(SUM(s.sale_price - m.cost), 0) AS gross_profit,
               ROUND(100.0 * SUM(CASE WHEN s.finance_status = 'approved' THEN 1 ELSE 0 END) /
                 NULLIF(SUM(CASE WHEN s.payment_method = 'finance' THEN 1 ELSE 0 END), 0), 1) AS finance_approval_rate
        FROM sales s
        JOIN motorcycles m ON m.id = s.motorcycle_id
        WHERE s.sold_at LIKE ?
        GROUP BY salesperson
        ORDER BY units DESC, revenue DESC
        LIMIT 10
        """,
        (month_like,),
    ).fetchall()

    registration_rows = conn.execute(
        """
        SELECT registration_status AS status, COUNT(*) AS count
        FROM sales
        GROUP BY registration_status
        ORDER BY count DESC
        """
    ).fetchall()

    aging_rows = conn.execute(
        """
        SELECT model,
               COUNT(*) AS qty,
               CAST(AVG(julianday('now') - julianday(received_at)) AS INTEGER) AS avg_days,
               SUM(CASE WHEN julianday('now') - julianday(received_at) <= 30 THEN 1 ELSE 0 END) AS d0_30,
               SUM(CASE WHEN julianday('now') - julianday(received_at) > 30 AND julianday('now') - julianday(received_at) <= 60 THEN 1 ELSE 0 END) AS d31_60,
               SUM(CASE WHEN julianday('now') - julianday(received_at) > 60 AND julianday('now') - julianday(received_at) <= 90 THEN 1 ELSE 0 END) AS d61_90,
               SUM(CASE WHEN julianday('now') - julianday(received_at) > 90 THEN 1 ELSE 0 END) AS d90_plus
        FROM motorcycles
        WHERE status = 'available'
        GROUP BY model
        ORDER BY avg_days DESC, qty DESC
        LIMIT 10
        """
    ).fetchall()

    finance_rows = conn.execute(
        """
        SELECT COALESCE(NULLIF(finance_company, ''), 'Other') AS company,
               COUNT(*) AS applications,
               SUM(CASE WHEN finance_status = 'approved' THEN 1 ELSE 0 END) AS approved,
               SUM(CASE WHEN finance_status = 'rejected' THEN 1 ELSE 0 END) AS rejected,
               SUM(CASE WHEN finance_status = 'pending' THEN 1 ELSE 0 END) AS pending,
               ROUND(100.0 * SUM(CASE WHEN finance_status = 'approved' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS approval_rate
        FROM sales
        WHERE payment_method = 'finance'
        GROUP BY company
        ORDER BY applications DESC
        """
    ).fetchall()

    top_models = conn.execute(
        """
        SELECT m.model, COUNT(*) AS units
        FROM sales s
        JOIN motorcycles m ON m.id = s.motorcycle_id
        WHERE s.sold_at LIKE ?
        GROUP BY m.model
        ORDER BY units DESC
        LIMIT 5
        """,
        (month_like,),
    ).fetchall()

    stock_alerts = conn.execute(
        """
        SELECT model, COUNT(*) AS qty
        FROM motorcycles
        WHERE status = 'available'
        GROUP BY model
        HAVING qty <= 2
        ORDER BY qty ASC, model
        LIMIT 10
        """
    ).fetchall()

    return {
        "today": today_metrics,
        "mtd": mtd_metrics,
        "parts_today": row_to_dict(parts_today),
        "parts_mtd": row_to_dict(parts_mtd),
        "snapshot": {
            "sales_today": today_metrics["revenue"] + parts_today["revenue"],
            "gross_profit": today_metrics["gross_profit"] + parts_today["profit"],
            "expenses": expense_today,
            "net_profit": today_metrics["gross_profit"] + parts_today["profit"] - expense_today,
        },
        "branch_comparison": branch_comparison,
        "salesperson_ranking": [row_to_dict(row) for row in salesperson_rows],
        "registration": [row_to_dict(row) for row in registration_rows],
        "aging_stock": [row_to_dict(row) for row in aging_rows],
        "finance": [row_to_dict(row) for row in finance_rows],
        "top_models": [row_to_dict(row) for row in top_models],
        "stock_alerts": [row_to_dict(row) for row in stock_alerts],
    }


def reports(conn):
    by_model = conn.execute(
        """
        SELECT model, status, COUNT(*) AS qty
        FROM motorcycles
        GROUP BY model, status
        ORDER BY model, status
        """
    ).fetchall()
    by_branch = conn.execute(
        """
        SELECT b.name AS branch,
               SUM(CASE WHEN m.status = 'available' THEN 1 ELSE 0 END) AS available,
               SUM(CASE WHEN m.status = 'sold' THEN 1 ELSE 0 END) AS sold,
               SUM(CASE WHEN m.status = 'hold' THEN 1 ELSE 0 END) AS hold_units
        FROM branches b
        LEFT JOIN motorcycles m ON m.branch_id = b.id
        GROUP BY b.id
        ORDER BY b.id
        """
    ).fetchall()
    recent_movements = conn.execute(
        """
        SELECT sm.created_at, sm.movement_type, sm.note, b.name AS branch,
               m.model, m.engine_no, m.frame_no
        FROM stock_movements sm
        LEFT JOIN motorcycles m ON m.id = sm.motorcycle_id
        LEFT JOIN branches b ON b.id = sm.branch_id
        ORDER BY sm.id DESC
        LIMIT 20
        """
    ).fetchall()
    recent_expenses = conn.execute(
        """
        SELECT e.paid_at, b.name AS branch, e.category, e.amount, e.note
        FROM expenses e
        JOIN branches b ON b.id = e.branch_id
        ORDER BY e.id DESC
        LIMIT 20
        """
    ).fetchall()
    recent_sales = conn.execute(
        """
        SELECT s.sold_at, b.name AS branch, m.model, m.engine_no, m.frame_no,
               c.name AS customer, s.sale_price, s.payment_method, s.salesperson,
               s.finance_company, s.finance_status, s.registration_status
        FROM sales s
        JOIN motorcycles m ON m.id = s.motorcycle_id
        JOIN branches b ON b.id = m.branch_id
        LEFT JOIN customers c ON c.id = s.customer_id
        ORDER BY s.id DESC
        LIMIT 20
        """
    ).fetchall()
    recent_parts_sales = conn.execute(
        """
        SELECT ps.sold_at, b.name AS branch, ps.part_name, ps.part_code, ps.quantity,
               ps.unit_price, ps.gross_amount, ps.discount_amount, ps.sale_total,
               ps.cost_total, ps.profit, ps.customer_name, ps.salesperson, ps.note
        FROM parts_sales ps
        JOIN branches b ON b.id = ps.branch_id
        ORDER BY ps.id DESC
        LIMIT 20
        """
    ).fetchall()
    recent_cases = conn.execute(
        """
        SELECT cc.created_at, b.name AS branch, cc.first_name, cc.surname,
               cc.nickname, cc.how_to_call, cc.phone, cc.salesperson,
               cc.case_status, cc.note
        FROM customer_cases cc
        JOIN branches b ON b.id = cc.branch_id
        ORDER BY cc.id DESC
        LIMIT 30
        """
    ).fetchall()
    recent_registrations = conn.execute(
        """
        SELECT rr.created_at, b.name AS branch, rr.first_name, rr.surname,
               rr.nickname, rr.how_to_call, rr.phone, rr.registration_status,
               rr.submitted_at, rr.registered_at, rr.note,
               m.model, m.engine_no, m.frame_no,
               CAST(julianday(COALESCE(rr.registered_at, date('now'))) - julianday(rr.submitted_at) AS INTEGER) AS days_count
        FROM registration_records rr
        JOIN branches b ON b.id = rr.branch_id
        LEFT JOIN sales s ON s.id = rr.sale_id
        LEFT JOIN motorcycles m ON m.id = s.motorcycle_id
        ORDER BY rr.id DESC
        LIMIT 30
        """
    ).fetchall()
    return {
        "by_model": [row_to_dict(row) for row in by_model],
        "by_branch": [row_to_dict(row) for row in by_branch],
        "recent_movements": [row_to_dict(row) for row in recent_movements],
        "recent_expenses": [row_to_dict(row) for row in recent_expenses],
        "recent_sales": [row_to_dict(row) for row in recent_sales],
        "recent_parts_sales": [row_to_dict(row) for row in recent_parts_sales],
        "recent_cases": [row_to_dict(row) for row in recent_cases],
        "recent_registrations": [row_to_dict(row) for row in recent_registrations],
    }


def dashboard_payload():
    with connect() as conn:
        return {
            "branches": list_branches(conn),
            "motorcycles": list_motorcycles(conn),
            "model_prices": list_model_prices(conn),
            "sold_sales": list_sold_sales(conn),
            "customer_dashboard": customer_dashboard(conn),
            "summary": summary(conn),
            "reports": reports(conn),
            "management": management_dashboard(conn),
        }


def login_user(data):
    require_fields(data, ["username", "password"])
    with connect() as conn:
        user = conn.execute(
            """
            SELECT id, name, username, role, branch_id, password_hash
            FROM users
            WHERE username = ?
            """,
            (data["username"].strip(),),
        ).fetchone()
        if not user or user["password_hash"] != hash_password(data["password"]):
            raise ValueError("Wrong username or password.")
    session_id = secrets.token_urlsafe(32)
    SESSIONS[session_id] = user["id"]
    cookie = f"famai_session={session_id}; HttpOnly; SameSite=Lax; Path=/"
    payload = dashboard_payload()
    payload["user"] = public_user(user)
    return payload, cookie


def logout_user(handler):
    cookie_header = handler.headers.get("Cookie", "")
    cookie = SimpleCookie()
    cookie.load(cookie_header)
    session_id = cookie.get("famai_session")
    if session_id:
        SESSIONS.pop(session_id.value, None)
    return "famai_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"


def backup_database():
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    destination = BACKUP_DIR / f"famai_motor_backup_{timestamp}.db"
    shutil.copy2(DB_PATH, destination)
    return {
        "backup_file": str(destination),
        "backup_name": destination.name,
        "created_at": now_text(),
    }


def receive_motorcycle(data, user):
    require_role(user, {"admin", "stock"})
    require_fields(data, ["branch_id", "model", "engine_no", "frame_no", "cost"])
    with connect() as conn:
        try:
            cursor = conn.execute(
                """
                INSERT INTO motorcycles (branch_id, model_code, model, color_code, color, engine_no, frame_no, cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(data["branch_id"]),
                    data.get("model_code", "").strip(),
                    data["model"].strip(),
                    data.get("color_code", "").strip(),
                    data.get("color", "").strip(),
                    data["engine_no"].strip(),
                    data["frame_no"].strip(),
                    float(data["cost"]),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Engine number or frame number already exists.") from exc
        conn.execute(
            """
            INSERT INTO stock_movements (motorcycle_id, branch_id, movement_type, note)
            VALUES (?, ?, 'receive', ?)
            """,
            (cursor.lastrowid, int(data["branch_id"]), data.get("note", "Received motorcycle")),
        )
    return dashboard_payload()


def adjust_motorcycle(data, user):
    require_role(user, {"admin", "stock"})
    require_fields(data, ["motorcycle_id", "action"])
    motorcycle_id = int(data["motorcycle_id"])
    action = data["action"]
    note = data.get("note", "").strip()
    with connect() as conn:
        unit = conn.execute("SELECT * FROM motorcycles WHERE id = ?", (motorcycle_id,)).fetchone()
        if not unit:
            raise ValueError("Motorcycle not found.")
        if unit["status"] == "sold":
            raise ValueError("Sold motorcycle cannot be adjusted.")
        if action == "transfer":
            require_fields(data, ["branch_id"])
            branch_id = int(data["branch_id"])
            conn.execute(
                "UPDATE motorcycles SET branch_id = ?, status = 'available', updated_at = ? WHERE id = ?",
                (branch_id, now_text(), motorcycle_id),
            )
            movement_type = "transfer"
        elif action in ("available", "hold", "written_off"):
            conn.execute(
                "UPDATE motorcycles SET status = ?, updated_at = ? WHERE id = ?",
                (action, now_text(), motorcycle_id),
            )
            branch_id = unit["branch_id"]
            movement_type = action
        else:
            raise ValueError("Unknown adjustment action.")
        conn.execute(
            """
            INSERT INTO stock_movements (motorcycle_id, branch_id, movement_type, note)
            VALUES (?, ?, ?, ?)
            """,
            (motorcycle_id, branch_id, movement_type, note),
        )
    return dashboard_payload()


def sell_motorcycle(data, user):
    require_role(user, {"admin", "sales"})
    require_fields(data, ["motorcycle_id", "customer_name", "sale_price", "payment_method"])
    motorcycle_id = int(data["motorcycle_id"])
    with connect() as conn:
        unit = conn.execute("SELECT * FROM motorcycles WHERE id = ?", (motorcycle_id,)).fetchone()
        if not unit or unit["status"] != "available":
            raise ValueError("Motorcycle is not available for sale.")
        customer = conn.execute(
            """
            INSERT INTO customers (name, surname, nickname, how_to_call, phone, address)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data["customer_name"].strip(),
                data.get("customer_surname", "").strip(),
                data.get("customer_nickname", "").strip(),
                data.get("customer_how_to_call", "").strip(),
                data.get("customer_phone", "").strip(),
                data.get("customer_address", "").strip(),
            ),
        )
        conn.execute(
            """
            INSERT INTO sales
              (motorcycle_id, customer_id, sale_price, payment_method, salesperson, finance_company, finance_status, registration_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                motorcycle_id,
                customer.lastrowid,
                float(data["sale_price"]),
                data["payment_method"],
                data.get("salesperson", "").strip(),
                data.get("finance_company", "").strip(),
                data.get("finance_status", "none"),
                data.get("registration_status", "ขายแล้ว"),
            ),
        )
        conn.execute(
            "UPDATE motorcycles SET status = 'sold', updated_at = ? WHERE id = ?",
            (now_text(), motorcycle_id),
        )
        conn.execute(
            """
            INSERT INTO stock_movements (motorcycle_id, branch_id, movement_type, note)
            VALUES (?, ?, 'sold', ?)
            """,
            (motorcycle_id, unit["branch_id"], "Sold to " + data["customer_name"].strip()),
        )
    return dashboard_payload()


def add_expense(data, user):
    require_role(user, {"admin", "accounting"})
    require_fields(data, ["branch_id", "category", "amount"])
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO expenses (branch_id, category, amount, note)
            VALUES (?, ?, ?, ?)
            """,
            (int(data["branch_id"]), data["category"], float(data["amount"]), data.get("note", "").strip()),
        )
    return dashboard_payload()


def add_parts_sale(data, user):
    require_role(user, {"admin", "sales"})
    require_fields(data, ["branch_id", "part_name", "quantity", "unit_price", "cost_total"])
    quantity = int(data["quantity"])
    if quantity <= 0:
        raise ValueError("Quantity must be more than 0.")
    unit_price = float(data["unit_price"])
    discount_amount = float(data.get("discount_amount") or 0)
    cost_total = float(data["cost_total"])
    gross_amount = quantity * unit_price
    sale_total = max(0, gross_amount - discount_amount)
    profit = sale_total - cost_total
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO parts_sales
              (branch_id, part_name, part_code, quantity, unit_price, gross_amount,
               discount_amount, sale_total, cost_total, profit, customer_name, salesperson, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(data["branch_id"]),
                data["part_name"].strip(),
                data.get("part_code", "").strip(),
                quantity,
                unit_price,
                gross_amount,
                discount_amount,
                sale_total,
                cost_total,
                profit,
                data.get("customer_name", "").strip(),
                data.get("salesperson", "").strip(),
                data.get("note", "").strip(),
            ),
        )
    return dashboard_payload()


def add_customer_case(data, user):
    require_role(user, {"admin", "sales"})
    require_fields(data, ["branch_id", "first_name", "phone", "case_status"])
    status = data["case_status"].strip()
    if status not in {"ปิดการขายได้", "ลูกค้าสนใจ", "ลูกค้าไม่สนใจ", "ติด finance"}:
        raise ValueError("Unknown case status.")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO customer_cases
              (branch_id, first_name, surname, nickname, how_to_call, phone, salesperson, case_status, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(data["branch_id"]),
                data["first_name"].strip(),
                data.get("surname", "").strip(),
                data.get("nickname", "").strip(),
                data.get("how_to_call", "").strip(),
                data["phone"].strip(),
                data.get("salesperson", "").strip(),
                status,
                data.get("note", "").strip(),
            ),
        )
    return dashboard_payload()


def add_registration_record(data, user):
    require_role(user, {"admin", "sales"})
    require_fields(data, ["branch_id", "first_name", "phone", "registration_status", "submitted_at"])
    status = data["registration_status"].strip()
    if status not in {"จดทะเบียน", "รอจดทะเบียน"}:
        raise ValueError("Unknown registration status.")
    registered_at = data.get("registered_at", "").strip()
    if status == "จดทะเบียน" and not registered_at:
        raise ValueError("Please enter received registration date.")
    if status == "รอจดทะเบียน":
        registered_at = ""
    sale_id_text = data.get("sale_id", "").strip()
    sale_id = int(sale_id_text) if sale_id_text else None
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO registration_records
              (sale_id, branch_id, first_name, surname, nickname, how_to_call, phone,
               registration_status, submitted_at, registered_at, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sale_id,
                int(data["branch_id"]),
                data["first_name"].strip(),
                data.get("surname", "").strip(),
                data.get("nickname", "").strip(),
                data.get("how_to_call", "").strip(),
                data["phone"].strip(),
                status,
                data["submitted_at"].strip(),
                registered_at or None,
                data.get("note", "").strip(),
            ),
        )
    return dashboard_payload()


def add_service_record(data, user):
    require_role(user, {"admin", "sales", "manager"})
    require_fields(data, ["sale_id"])
    service_at = data.get("service_at", "").strip()
    oil_change_at = data.get("oil_change_at", "").strip()
    if not service_at and not oil_change_at:
        raise ValueError("Enter service date or oil change date.")
    sale_id = int(data["sale_id"])
    with connect() as conn:
        sale = conn.execute(
            """
            SELECT s.id, s.customer_id, s.motorcycle_id
            FROM sales s
            WHERE s.id = ?
            """,
            (sale_id,),
        ).fetchone()
        if not sale:
            raise ValueError("Sale not found.")
        conn.execute(
            """
            INSERT INTO service_records (sale_id, customer_id, motorcycle_id, service_at, oil_change_at, note)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                sale_id,
                sale["customer_id"],
                sale["motorcycle_id"],
                service_at or None,
                oil_change_at or None,
                data.get("note", "").strip(),
            ),
        )
    return dashboard_payload()


def authorize_receipt_print(data, user):
    require_role(user, {"admin", "sales", "manager", "accounting"})
    require_fields(data, ["sale_id", "auth_username", "auth_password"])
    sale_id = int(data["sale_id"])
    with connect() as conn:
        authorizer = conn.execute(
            """
            SELECT id, name, username, role, password_hash
            FROM users
            WHERE username = ?
            """,
            (data["auth_username"].strip(),),
        ).fetchone()
        if not authorizer or authorizer["password_hash"] != hash_password(data["auth_password"]):
            raise PermissionError("Receipt authorization failed.")
        if authorizer["role"] not in {"admin", "manager", "accounting"}:
            raise PermissionError("This account cannot authorize receipt printing.")
        sale = conn.execute(
            """
            SELECT s.id, s.sale_price, s.payment_method, s.salesperson, s.sold_at,
                   b.name AS branch, m.model, m.model_code, m.color_code, m.color,
                   m.engine_no, m.frame_no, c.name AS customer_name, c.surname,
                   c.nickname, c.how_to_call, c.phone, c.address
            FROM sales s
            JOIN motorcycles m ON m.id = s.motorcycle_id
            JOIN branches b ON b.id = m.branch_id
            LEFT JOIN customers c ON c.id = s.customer_id
            WHERE s.id = ?
            """,
            (sale_id,),
        ).fetchone()
        if not sale:
            raise ValueError("Sale not found.")
        conn.execute(
            """
            INSERT INTO receipt_prints (sale_id, authorized_by, requested_by)
            VALUES (?, ?, ?)
            """,
            (sale_id, authorizer["id"], user["id"]),
        )
        print_count = conn.execute(
            "SELECT COUNT(*) AS total FROM receipt_prints WHERE sale_id = ?",
            (sale_id,),
        ).fetchone()["total"]
    payload = dashboard_payload()
    payload["receipt"] = row_to_dict(sale)
    payload["receipt"]["print_count"] = print_count
    payload["receipt"]["authorized_by"] = authorizer["name"]
    payload["receipt"]["authorized_role"] = authorizer["role"]
    payload["receipt"]["printed_at"] = now_text()
    return payload


def import_csv_data(data, user):
    require_role(user, {"admin"})
    require_fields(data, ["import_type", "csv_text"])
    import_type = data["import_type"]
    rows = read_csv_rows(data["csv_text"])
    imported = 0
    skipped = 0
    errors = []

    with connect() as conn:
        for line_number, row in enumerate(rows, start=2):
            try:
                if import_type == "motorcycles":
                    branch_id = branch_id_by_name(conn, pick(row, "branch"))
                    model = pick(row, "model")
                    engine_no = pick(row, "engine_no", "เลขเครื่อง")
                    frame_no = pick(row, "frame_no", "เลขถัง")
                    if not model or not engine_no or not frame_no:
                        raise ValueError("model, engine_no, and frame_no are required")
                    status = pick(row, "status", default="available") or "available"
                    if status not in {"available", "hold", "sold", "written_off"}:
                        raise ValueError("status must be available, hold, sold, or written_off")
                    cursor = conn.execute(
                        """
                        INSERT INTO motorcycles
                          (branch_id, model_code, model, color_code, color, engine_no, frame_no, cost, status, received_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            branch_id,
                            pick(row, "model_code", "code"),
                            model,
                            pick(row, "color_code"),
                            pick(row, "color"),
                            engine_no,
                            frame_no,
                            parse_money(pick(row, "cost"), 0),
                            status,
                            pick(row, "received_at", default=now_text()) or now_text(),
                            now_text(),
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO stock_movements (motorcycle_id, branch_id, movement_type, note, created_at)
                        VALUES (?, ?, 'import_motorcycle', ?, ?)
                        """,
                        (
                            cursor.lastrowid,
                            branch_id,
                            pick(row, "note", default="Imported old motorcycle data"),
                            pick(row, "received_at", default=now_text()) or now_text(),
                        ),
                    )
                    imported += 1

                elif import_type == "sales":
                    branch_id = branch_id_by_name(conn, pick(row, "branch"))
                    model = pick(row, "model")
                    engine_no = pick(row, "engine_no", "เลขเครื่อง")
                    frame_no = pick(row, "frame_no", "เลขถัง")
                    if not model or not engine_no or not frame_no:
                        raise ValueError("model, engine_no, and frame_no are required")
                    unit = conn.execute(
                        "SELECT id, status FROM motorcycles WHERE engine_no = ? OR frame_no = ?",
                        (engine_no, frame_no),
                    ).fetchone()
                    if unit and unit["status"] == "sold":
                        raise ValueError("motorcycle already sold")
                    if unit:
                        motorcycle_id = unit["id"]
                        conn.execute(
                            "UPDATE motorcycles SET status = 'sold', updated_at = ? WHERE id = ?",
                            (now_text(), motorcycle_id),
                        )
                    else:
                        cursor = conn.execute(
                            """
                            INSERT INTO motorcycles
                              (branch_id, model_code, model, color_code, color, engine_no, frame_no, cost, status, received_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'sold', ?, ?)
                            """,
                            (
                                branch_id,
                                pick(row, "model_code", "code"),
                                model,
                                pick(row, "color_code"),
                                pick(row, "color"),
                                engine_no,
                                frame_no,
                                parse_money(pick(row, "cost"), 0),
                                pick(row, "received_at", "sold_at", default=now_text()) or now_text(),
                                now_text(),
                            ),
                        )
                        motorcycle_id = cursor.lastrowid
                    customer = conn.execute(
                        "INSERT INTO customers (name, phone, address, created_at) VALUES (?, ?, ?, ?)",
                        (
                            pick(row, "customer_name", default="Imported customer"),
                            pick(row, "customer_phone", "phone"),
                            pick(row, "customer_address", "address"),
                            pick(row, "sold_at", default=now_text()) or now_text(),
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO sales
                          (motorcycle_id, customer_id, sale_price, payment_method, salesperson, finance_company, finance_status, registration_status, sold_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            motorcycle_id,
                            customer.lastrowid,
                            parse_money(pick(row, "sale_price", "price"), 0),
                            pick(row, "payment_method", default="cash") or "cash",
                            pick(row, "salesperson"),
                            pick(row, "finance_company"),
                            pick(row, "finance_status", default="none") or "none",
                            pick(row, "registration_status", default="ขายแล้ว") or "ขายแล้ว",
                            pick(row, "sold_at", default=now_text()) or now_text(),
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO stock_movements (motorcycle_id, branch_id, movement_type, note, created_at)
                        VALUES (?, ?, 'import_sale', ?, ?)
                        """,
                        (
                            motorcycle_id,
                            branch_id,
                            "Imported old sale",
                            pick(row, "sold_at", default=now_text()) or now_text(),
                        ),
                    )
                    imported += 1

                elif import_type == "expenses":
                    branch_id = branch_id_by_name(conn, pick(row, "branch"))
                    category = pick(row, "category")
                    amount = parse_money(pick(row, "amount"), 0)
                    if not category or amount <= 0:
                        raise ValueError("category and amount are required")
                    conn.execute(
                        """
                        INSERT INTO expenses (branch_id, category, amount, note, paid_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            branch_id,
                            category,
                            amount,
                            pick(row, "note"),
                            pick(row, "paid_at", default=now_text()) or now_text(),
                        ),
                    )
                    imported += 1
                else:
                    raise ValueError("Unknown import type.")
            except sqlite3.IntegrityError as exc:
                skipped += 1
                errors.append(f"Line {line_number}: duplicate engine/frame or sale record")
            except ValueError as exc:
                skipped += 1
                errors.append(f"Line {line_number}: {exc}")

    payload = dashboard_payload()
    payload["import_result"] = {
        "type": import_type,
        "imported": imported,
        "skipped": skipped,
        "errors": errors[:20],
    }
    return payload


class FamaiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/bootstrap":
            payload = dashboard_payload()
            payload["user"] = public_user(user_from_request(self))
            send_json(self, 200, payload)
            return
        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/login":
            try:
                payload, cookie = login_user(get_json(self))
                send_cookie_json(self, 200, payload, cookie)
            except ValueError as exc:
                send_json(self, 400, {"error": str(exc)})
            return
        if parsed.path == "/api/logout":
            cookie = logout_user(self)
            send_cookie_json(self, 200, {"ok": True}, cookie)
            return
        if parsed.path == "/api/backup":
            try:
                user = require_login(self)
                require_role(user, {"admin", "manager", "accounting"})
                backup = backup_database()
                payload = dashboard_payload()
                payload["user"] = public_user(user)
                payload["backup"] = backup
                send_json(self, 200, payload)
            except PermissionError as exc:
                send_json(self, 403, {"error": str(exc)})
            except Exception as exc:
                send_json(self, 500, {"error": "Backup failed", "detail": str(exc)})
            return
        routes = {
            "/api/receive": receive_motorcycle,
            "/api/adjust": adjust_motorcycle,
            "/api/sell": sell_motorcycle,
            "/api/case": add_customer_case,
            "/api/registration": add_registration_record,
            "/api/service": add_service_record,
            "/api/receipt/authorize": authorize_receipt_print,
            "/api/parts/sell": add_parts_sale,
            "/api/expense": add_expense,
            "/api/import": import_csv_data,
        }
        if parsed.path not in routes:
            send_json(self, 404, {"error": "Not found"})
            return
        try:
            user = require_login(self)
            payload = routes[parsed.path](get_json(self), user)
            payload["user"] = public_user(user)
            send_json(self, 200, payload)
        except PermissionError as exc:
            send_json(self, 403, {"error": str(exc)})
        except ValueError as exc:
            send_json(self, 400, {"error": str(exc)})
        except Exception as exc:
            send_json(self, 500, {"error": "Server error", "detail": str(exc)})


if __name__ == "__main__":
    init_db()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    server = ThreadingHTTPServer(("127.0.0.1", port), FamaiHandler)
    print(f"Famai Motor starter running at http://127.0.0.1:{port}")
    print(f"Database: {DB_PATH}")
    server.serve_forever()
