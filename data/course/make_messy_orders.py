"""Build data/course/messy_orders.csv: a SYNTHETIC, deliberately messy order export (Week 3).

    python data/course/make_messy_orders.py            # rebuild the committed file (seed 3)
    python data/course/make_messy_orders.py --check    # verify the committed file matches a rebuild

It imitates a CSV exported by hand from an old shop system. Planted problems, so students can find them:

* exact duplicate rows (the export was run twice for some days);
* three date formats in one column: 2025-03-04, 04/03/2025 (day first) and "March 4, 2025";
* text with stray spaces and mixed case in ``city`` and ``status``;
* ``unit_price`` sometimes recorded in cents instead of dollars (see ``price_unit``);
* missing values written as "N/A", "-" or an empty field; ``quantity`` uses -1 to mean "unknown";
* a few impossible values: negative quantities other than -1, and zero or negative prices.

The data is generated, not real. ``generate(seed, n_orders)`` returns the same table as a DataFrame so
graders can test student code on a fresh file with a different seed.
"""
from __future__ import annotations

import argparse
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent / "messy_orders.csv"
SEED = 3
CITIES = ["Almaty", "Astana", "Shymkent", "Karaganda", "Aktobe", "Taraz"]
STATUSES = ["delivered", "shipped", "cancelled", "returned"]
PRODUCTS = {"Headphones": 45.0, "USB-C cable": 8.0, "Kettle": 35.0, "Desk lamp": 25.0, "Yoga mat": 28.0,
            "Novel": 14.0, "Hand cream": 7.0, "Power bank": 30.0}
MISSING = ["N/A", "-", ""]


def _messy_text(rng: random.Random, value: str) -> str:
    style = rng.random()
    if style < 0.55:
        return value
    if style < 0.70:
        return value.lower()
    if style < 0.82:
        return value.upper()
    if style < 0.92:
        return " " + value
    return value + "  "


def _messy_date(rng: random.Random, d: date) -> str:
    style = rng.random()
    if style < 0.6:
        return d.isoformat()                      # 2025-03-04
    if style < 0.85:
        return d.strftime("%d/%m/%Y")             # 04/03/2025 (day first)
    return f"{d.strftime('%B')} {d.day}, {d.year}"  # March 4, 2025


def generate(seed: int = SEED, n_orders: int = 1200) -> pd.DataFrame:
    rng = random.Random(seed)
    start = date(2024, 1, 1)
    rows = []
    for order_id in range(1, n_orders + 1):
        d = start + timedelta(days=rng.randrange(0, 730))
        product = rng.choice(list(PRODUCTS))
        price = PRODUCTS[product]
        unit = "dollars"
        if rng.random() < 0.12:                   # recorded in cents
            price, unit = price * 100, "cents"
        quantity: object = rng.choices([1, 2, 3, 4], [0.6, 0.25, 0.1, 0.05])[0]
        r = rng.random()
        if r < 0.05:
            quantity = -1                         # the old system's code for "unknown"
        elif r < 0.07:
            quantity = rng.choice([-2, -3, -5])   # impossible
        if rng.random() < 0.015:
            price = rng.choice([0.0, -price])     # impossible price
        city: object = _messy_text(rng, rng.choice(CITIES))
        if rng.random() < 0.05:
            city = rng.choice(MISSING)
        discount: object = rng.choices([0.0, 0.05, 0.1, 0.2], [0.7, 0.1, 0.15, 0.05])[0]
        if rng.random() < 0.08:
            discount = rng.choice(MISSING)
        rows.append({
            "order_id": order_id,
            "customer_id": rng.randrange(1, 400),
            "order_date": _messy_date(rng, d),
            "city": city,
            "status": _messy_text(rng, rng.choices(STATUSES, [0.8, 0.08, 0.08, 0.04])[0]),
            "product": product,
            "quantity": quantity,
            "unit_price": round(price, 2),
            "price_unit": unit,
            "discount": discount,
        })
    for _ in range(int(n_orders * 0.03)):         # the export ran twice for some rows
        rows.insert(rng.randrange(0, len(rows)), dict(rng.choice(rows)))
    return pd.DataFrame(rows)


def write(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, lineterminator="\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    text = generate().to_csv(index=False, lineterminator="\n")
    if args.check:
        same = OUT.read_text() == text
        print("messy_orders.csv matches a rebuild" if same else "messy_orders.csv differs from a rebuild")
        return 0 if same else 1
    OUT.write_text(text)
    print(f"wrote {OUT.name}: {len(text.splitlines()) - 1} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
