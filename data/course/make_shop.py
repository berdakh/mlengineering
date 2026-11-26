"""Build data/course/shop.db: a SYNTHETIC online shop used from Week 2 (SQL) to Week 7 (models).

    python data/course/make_shop.py           # rebuild (deterministic: same seed, same database)
    python data/course/make_shop.py --check   # verify the committed file matches a rebuild

Tables (one row per ...):
  customers(customer_id, name, city, signup_date, segment, email)          one customer
  products(product_id, name, category, price)                               one product
  orders(order_id, customer_id, order_date, status, channel)                one order
  order_items(order_id, product_id, quantity, unit_price, discount)         one product line in an order
  payments(payment_id, order_id, amount, method, paid_at)                   one payment (some orders: none)
  support_tickets(ticket_id, customer_id, opened_at, topic, resolved_at)    one ticket (resolved_at may be NULL)

Realistic on purpose: some customers never order, some orders have no payment yet, some emails and
cities are missing (NULL), some tickets are unresolved. All names are generated, not real people.
"""
from __future__ import annotations

import argparse
import hashlib
import random
import sqlite3
import tempfile
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent / "shop.db"
SEED = 20261126
CITIES = ["Almaty", "Astana", "Shymkent", "Karaganda", "Aktobe", "Taraz", "Pavlodar", "Oskemen"]
FIRST = ["Aru", "Dana", "Timur", "Aigerim", "Nurlan", "Madina", "Yerlan", "Saule", "Ali", "Zarina",
         "Daniyar", "Kamila", "Arman", "Dina", "Bekzat", "Aliya", "Ruslan", "Asel", "Marat", "Gulnara"]
LAST = ["Sadykov", "Akhmetova", "Iskakov", "Nurlanova", "Bekov", "Omarova", "Tulegenov", "Kassymova",
        "Zhakupov", "Serikova", "Abenov", "Mukanova"]
CATALOG = {
    "Electronics": [("Headphones", 45), ("USB-C cable", 8), ("Power bank", 30), ("Smartwatch", 120), ("Keyboard", 55)],
    "Home": [("Desk lamp", 25), ("Kettle", 35), ("Cushion", 15), ("Storage box", 12), ("Coffee mug", 9)],
    "Books": [("Python notebook", 22), ("Statistics primer", 30), ("Novel", 14), ("Cookbook", 26)],
    "Sports": [("Yoga mat", 28), ("Water bottle", 11), ("Running socks", 9), ("Dumbbells", 48)],
    "Beauty": [("Hand cream", 7), ("Shampoo", 10), ("Face mask", 6)],
}


def build(path: Path) -> None:
    rng = random.Random(SEED)
    con = sqlite3.connect(path)
    con.executescript("""
    CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT NOT NULL, city TEXT,
        signup_date TEXT NOT NULL, segment TEXT NOT NULL, email TEXT);
    CREATE TABLE products (product_id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
        price REAL NOT NULL);
    CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers,
        order_date TEXT NOT NULL, status TEXT NOT NULL, channel TEXT NOT NULL);
    CREATE TABLE order_items (order_id INTEGER NOT NULL REFERENCES orders, product_id INTEGER NOT NULL
        REFERENCES products, quantity INTEGER NOT NULL, unit_price REAL NOT NULL, discount REAL NOT NULL,
        PRIMARY KEY (order_id, product_id));
    CREATE TABLE payments (payment_id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders,
        amount REAL NOT NULL, method TEXT NOT NULL, paid_at TEXT NOT NULL);
    CREATE TABLE support_tickets (ticket_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL
        REFERENCES customers, opened_at TEXT NOT NULL, topic TEXT NOT NULL, resolved_at TEXT);
    """)
    products, pid = [], 1
    for cat, items in CATALOG.items():
        for name, price in items:
            products.append((pid, name, cat, float(price)))
            pid += 1
    con.executemany("INSERT INTO products VALUES (?,?,?,?)", products)
    start, end = date(2024, 1, 1), date(2025, 12, 31)
    span = (end - start).days
    customers = []
    for cid in range(1, 1201):
        signup = start + timedelta(days=rng.randrange(0, span - 30))
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        city = None if rng.random() < 0.04 else rng.choice(CITIES)
        segment = rng.choices(["consumer", "small_business", "student"], [0.7, 0.2, 0.1])[0]
        email = None if rng.random() < 0.06 else f"user{cid}@example.com"
        customers.append((cid, name, city, signup.isoformat(), segment, email))
    con.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?)", customers)
    oid = pay_id = tid = 1
    orders, items, payments, tickets = [], [], [], []
    for cid, _, _, signup_s, segment, _ in customers:
        signup = date.fromisoformat(signup_s)
        activity = rng.choices([0, 1, 2, 4, 8, 15], [0.12, 0.25, 0.25, 0.2, 0.13, 0.05])[0]
        if segment == "small_business":
            activity += 3
        for _ in range(activity):
            d = signup + timedelta(days=rng.randrange(0, max(1, (end - signup).days)))
            status = rng.choices(["delivered", "shipped", "cancelled", "returned"], [0.8, 0.08, 0.08, 0.04])[0]
            channel = rng.choices(["web", "mobile_app", "marketplace"], [0.5, 0.35, 0.15])[0]
            orders.append((oid, cid, d.isoformat(), status, channel))
            total = 0.0
            for prod in rng.sample(products, rng.choices([1, 2, 3, 4], [0.5, 0.3, 0.15, 0.05])[0]):
                qty = rng.choices([1, 2, 3, 5], [0.7, 0.2, 0.07, 0.03])[0]
                disc = rng.choices([0.0, 0.05, 0.1, 0.2], [0.75, 0.1, 0.1, 0.05])[0]
                items.append((oid, prod[0], qty, prod[3], disc))
                total += qty * prod[3] * (1 - disc)
            if status != "cancelled" and rng.random() > 0.03:
                method = rng.choices(["card", "cash_on_delivery", "bank_transfer"], [0.7, 0.2, 0.1])[0]
                payments.append((pay_id, oid, round(total, 2), method, (d + timedelta(days=rng.randrange(0, 3))).isoformat()))
                pay_id += 1
            oid += 1
        for _ in range(rng.choices([0, 1, 2, 3], [0.6, 0.25, 0.1, 0.05])[0]):
            opened = signup + timedelta(days=rng.randrange(0, max(1, (end - signup).days)))
            topic = rng.choice(["delivery", "refund", "account", "product_question", "payment"])
            resolved = None if rng.random() < 0.15 else (opened + timedelta(days=rng.randrange(0, 10))).isoformat()
            tickets.append((tid, cid, opened.isoformat(), topic, resolved))
            tid += 1
    con.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", orders)
    con.executemany("INSERT INTO order_items VALUES (?,?,?,?,?)", items)
    con.executemany("INSERT INTO payments VALUES (?,?,?,?,?)", payments)
    con.executemany("INSERT INTO support_tickets VALUES (?,?,?,?,?)", tickets)
    con.commit()
    con.execute("VACUUM")
    con.close()


def digest(path: Path) -> str:
    """Hash the table contents (not the file bytes, which vary with the SQLite version)."""
    con = sqlite3.connect(path)
    h = hashlib.sha256()
    for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        for row in con.execute(f"SELECT * FROM {table} ORDER BY 1, 2"):
            h.update(repr(row).encode())
    con.close()
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        with tempfile.TemporaryDirectory() as tmp:
            fresh = Path(tmp) / "shop.db"
            build(fresh)
            same = digest(fresh) == digest(OUT)
        print("shop.db matches a rebuild" if same else "shop.db differs from a rebuild")
        return 0 if same else 1
    OUT.unlink(missing_ok=True)
    build(OUT)
    con = sqlite3.connect(OUT)
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}
    print(f"wrote {OUT.name} ({OUT.stat().st_size / 1e6:.1f} MB): {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
