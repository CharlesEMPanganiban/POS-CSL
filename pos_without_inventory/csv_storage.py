"""
csv_storage.py
==============
Flat-file data layer for the POS system.

Files managed:
  - products.csv
  - users.csv
  - sales.csv
  - logs.csv

Operations supported per file:
  save, read, search, update, report
"""

import csv
import os
from datetime import datetime, date

# ── File paths ─────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
PRODUCTS_CSV  = os.path.join(BASE_DIR, "data", "products.csv")
USERS_CSV     = os.path.join(BASE_DIR, "data", "users.csv")
SALES_CSV     = os.path.join(BASE_DIR, "data", "sales.csv")
LOGS_CSV      = os.path.join(BASE_DIR, "data", "logs.csv")

# ── Field definitions ──────────────────────────────────────────────────────────
PRODUCTS_FIELDS = ["id", "name", "price", "category", "description", "image"]
USERS_FIELDS    = ["username", "password", "role"]
SALES_FIELDS    = ["id", "date", "items", "total"]
LOGS_FIELDS     = ["id", "username", "date", "timeIn", "timeOut"]


# ══════════════════════════════════════════════════════════════════════════════
# UTILITY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _ensure_file(filepath, fieldnames):
    """Create the CSV file with headers if it does not already exist."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if not os.path.exists(filepath):
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()


def _read_all(filepath, fieldnames):
    """Return every row in a CSV as a list of dicts."""
    _ensure_file(filepath, fieldnames)
    with open(filepath, "r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _write_all(filepath, fieldnames, rows):
    """Overwrite the CSV with a fresh set of rows."""
    _ensure_file(filepath, fieldnames)
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _next_id(rows):
    """Auto-increment integer ID based on current rows."""
    if not rows:
        return "1"
    try:
        return str(max(int(r["id"]) for r in rows if r.get("id", "").isdigit()) + 1)
    except ValueError:
        return str(len(rows) + 1)


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCTS
# ══════════════════════════════════════════════════════════════════════════════

def save_product(name, price, category, description="", image=""):
    """Add a new product. Returns the saved product dict."""
    rows = _read_all(PRODUCTS_CSV, PRODUCTS_FIELDS)
    product = {
        "id":          _next_id(rows),
        "name":        name,
        "price":       str(price),
        "category":    category,
        "description": description,
        "image":       image,
    }
    rows.append(product)
    _write_all(PRODUCTS_CSV, PRODUCTS_FIELDS, rows)
    return product


def read_products():
    """Return all products."""
    return _read_all(PRODUCTS_CSV, PRODUCTS_FIELDS)


def search_products(keyword="", category=""):
    """Search products by name keyword and/or category."""
    rows     = read_products()
    keyword  = keyword.lower()
    category = category.lower()
    result   = []
    for r in rows:
        name_match = keyword  in r["name"].lower()     if keyword  else True
        cat_match  = category in r["category"].lower() if category else True
        if name_match and cat_match:
            result.append(r)
    return result


def update_product(product_id, **kwargs):
    """Update fields of a product by id. Returns updated dict or None."""
    rows  = _read_all(PRODUCTS_CSV, PRODUCTS_FIELDS)
    found = None
    for r in rows:
        if r["id"] == str(product_id):
            for key, val in kwargs.items():
                if key in PRODUCTS_FIELDS:
                    r[key] = str(val)
            found = r
            break
    if found:
        _write_all(PRODUCTS_CSV, PRODUCTS_FIELDS, rows)
    return found


def delete_product(product_id):
    """Delete a product by id. Returns True if removed."""
    rows     = _read_all(PRODUCTS_CSV, PRODUCTS_FIELDS)
    new_rows = [r for r in rows if r["id"] != str(product_id)]
    if len(new_rows) < len(rows):
        _write_all(PRODUCTS_CSV, PRODUCTS_FIELDS, new_rows)
        return True
    return False


def delete_product_by_name(name):
    """Delete a product by name. Returns True if removed."""
    rows     = _read_all(PRODUCTS_CSV, PRODUCTS_FIELDS)
    new_rows = [r for r in rows if r["name"] != name]
    if len(new_rows) < len(rows):
        _write_all(PRODUCTS_CSV, PRODUCTS_FIELDS, new_rows)
        return True
    return False


def report_products_by_category():
    """Return {category: [product, ...]} for all products."""
    rows   = read_products()
    report = {}
    for r in rows:
        cat = r["category"]
        report.setdefault(cat, []).append(r)
    return report


# ══════════════════════════════════════════════════════════════════════════════
# USERS
# ══════════════════════════════════════════════════════════════════════════════

def save_user(username, password, role="employee"):
    """Register a new user. Returns None if username already exists."""
    _bootstrap_admin()
    rows = _read_all(USERS_CSV, USERS_FIELDS)
    if any(r["username"] == username for r in rows):
        return None
    user = {"username": username, "password": password, "role": role}
    rows.append(user)
    _write_all(USERS_CSV, USERS_FIELDS, rows)
    return user


def _bootstrap_admin():
    """Create the default admin account if it doesn't exist yet."""
    _ensure_file(USERS_CSV, USERS_FIELDS)
    rows = _read_all(USERS_CSV, USERS_FIELDS)
    if not any(r["username"] == "admin" for r in rows):
        rows.insert(0, {"username": "admin", "password": "admin123", "role": "admin"})
        _write_all(USERS_CSV, USERS_FIELDS, rows)


def authenticate_user(username, password):
    """Return user dict if credentials match, else None."""
    _bootstrap_admin()
    rows = _read_all(USERS_CSV, USERS_FIELDS)
    for r in rows:
        if r["username"] == username and r["password"] == password:
            return r
    return None


def read_users():
    """Return all users."""
    return _read_all(USERS_CSV, USERS_FIELDS)


# ══════════════════════════════════════════════════════════════════════════════
# SALES
# ══════════════════════════════════════════════════════════════════════════════

def _parse_items(raw):
    """Parse 'name|price|qty;name|price|qty' string into list of dicts."""
    if not raw:
        return []
    result = []
    for part in raw.split(";"):
        bits = part.split("|")
        if len(bits) >= 2:
            result.append({
                "name":  bits[0],
                "price": bits[1],
                "qty":   bits[2] if len(bits) > 2 else "1",
            })
    return result


def save_sale(items, total):
    """Record a new sale. items is a list of {name, price, qty}."""
    rows = _read_all(SALES_CSV, SALES_FIELDS)
    sale = {
        "id":    _next_id(rows),
        "date":  datetime.now().isoformat(),
        "items": ";".join(
            f"{i.get('name','')}|{i.get('price',0)}|{i.get('qty',1)}"
            for i in items
        ),
        "total": str(total),
    }
    rows.append(sale)
    _write_all(SALES_CSV, SALES_FIELDS, rows)
    result = dict(sale)
    result["items"] = _parse_items(result["items"])
    return result


def read_sales():
    """Return all sales with items parsed."""
    rows = _read_all(SALES_CSV, SALES_FIELDS)
    for r in rows:
        r["items"] = _parse_items(r.get("items", ""))
    return rows


def search_sales(date_str="", product_name=""):
    """Search sales by date prefix or product name substring."""
    rows   = read_sales()
    result = []
    for r in rows:
        date_match = date_str in r["date"]                                   if date_str    else True
        item_names = " ".join(i["name"].lower() for i in r["items"])
        prod_match = product_name.lower() in item_names                      if product_name else True
        if date_match and prod_match:
            result.append(r)
    return result


def update_sale(sale_id, items=None, total=None):
    """Update a sale by id. Returns updated dict or None."""
    rows  = _read_all(SALES_CSV, SALES_FIELDS)
    found = None
    for r in rows:
        if r["id"] == str(sale_id):
            if items is not None:
                r["items"] = ";".join(
                    f"{i.get('name','')}|{i.get('price',0)}|{i.get('qty',1)}"
                    for i in items
                )
            if total is not None:
                r["total"] = str(total)
            found = dict(r)
            found["items"] = _parse_items(found["items"])
            break
    if found:
        _write_all(SALES_CSV, SALES_FIELDS, rows)
    return found


def report_sales_summary():
    """Return total_revenue, daily_revenue, top_product, by_date, total_transactions."""
    rows          = read_sales()
    today_str     = date.today().isoformat()
    total_revenue = 0.0
    daily_revenue = 0.0
    product_qty   = {}
    by_date       = {}

    for r in rows:
        amt            = float(r["total"] or 0)
        total_revenue += amt
        sale_date      = r["date"][:10]
        by_date[sale_date] = by_date.get(sale_date, 0.0) + amt
        if sale_date == today_str:
            daily_revenue += amt
        for item in r["items"]:
            name = item["name"]
            qty  = int(item.get("qty", 1))
            product_qty[name] = product_qty.get(name, 0) + qty

    top_product = max(product_qty, key=product_qty.get) if product_qty else "None"

    return {
        "total_revenue":      round(total_revenue, 2),
        "total_transactions": len(rows),
        "daily_revenue":      round(daily_revenue, 2),
        "top_product":        top_product,
        "by_date":            by_date,
    }


def report_sales_by_period(period="daily"):
    """Filter sales by period: daily | weekly | monthly | yearly."""
    from datetime import timedelta
    rows   = read_sales()
    now    = datetime.now()
    result = []
    for r in rows:
        try:
            sale_dt = datetime.fromisoformat(r["date"])
        except ValueError:
            continue
        if   period == "daily"   and sale_dt.date() == now.date():
            result.append(r)
        elif period == "weekly"  and (now - sale_dt).days <= 7:
            result.append(r)
        elif period == "monthly" and sale_dt.month == now.month and sale_dt.year == now.year:
            result.append(r)
        elif period == "yearly"  and sale_dt.year == now.year:
            result.append(r)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE LOGS
# ══════════════════════════════════════════════════════════════════════════════

def save_log(username):
    """Record a time-in for a user."""
    rows = _read_all(LOGS_CSV, LOGS_FIELDS)
    log  = {
        "id":       _next_id(rows),
        "username": username,
        "date":     date.today().isoformat(),
        "timeIn":   datetime.now().strftime("%I:%M:%S %p"),
        "timeOut":  "",
    }
    rows.append(log)
    _write_all(LOGS_CSV, LOGS_FIELDS, rows)
    return log


def read_logs():
    """Return all logs."""
    return _read_all(LOGS_CSV, LOGS_FIELDS)


def search_logs(username="", date_str=""):
    """Search logs by username and/or date."""
    rows   = _read_all(LOGS_CSV, LOGS_FIELDS)
    result = []
    for r in rows:
        u_match = username in r["username"] if username else True
        d_match = date_str in r["date"]     if date_str else True
        if u_match and d_match:
            result.append(r)
    return result


def update_log_timeout(log_id, username=""):
    """Set timeOut for an open log. Matches by id or open username log."""
    rows  = _read_all(LOGS_CSV, LOGS_FIELDS)
    found = None
    for r in rows:
        id_match   = r["id"] == str(log_id)   if log_id   else False
        user_match = r["username"] == username if username else False
        if (id_match or user_match) and not r.get("timeOut"):
            r["timeOut"] = datetime.now().strftime("%I:%M:%S %p")
            found = r
            break
    if found:
        _write_all(LOGS_CSV, LOGS_FIELDS, rows)
    return found


def clear_logs():
    """Delete all log records."""
    _write_all(LOGS_CSV, LOGS_FIELDS, [])


def report_employee_hours():
    """Return {username: total_hours} for all users."""
    rows    = read_logs()
    summary = {}
    for r in rows:
        if not r.get("timeOut"):
            continue
        try:
            fmt  = "%I:%M:%S %p"
            tin  = datetime.strptime(r["timeIn"],  fmt)
            tout = datetime.strptime(r["timeOut"], fmt)
            hrs  = (tout - tin).seconds / 3600
            summary[r["username"]] = round(summary.get(r["username"], 0) + hrs, 2)
        except ValueError:
            continue
    return summary