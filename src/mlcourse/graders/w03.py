"""Week 3 graders: advanced SQL (09), pandas (10), data cleaning (11), lab (12).

SQL answers are run on the course shop database AND on a freshly generated shop database with a
different seed, then compared with results computed independently in pandas. Function answers are run
on real tables, on small hand-made tables and on empty tables.
"""
from __future__ import annotations

import importlib.util
import math
import sqlite3
import tempfile
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from mlcourse.grader import exercise, register_quiz
from mlcourse.paths import repo_root

# ----------------------------------------------------------------------------- shared helpers


def _load_module(name: str):
    path = repo_root() / "data" / "course" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_course_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@lru_cache(maxsize=None)
def _db_paths() -> tuple[str, str]:
    """The shipped shop.db and a fresh one built with a different seed (cached for the session)."""
    shipped = str(repo_root() / "data" / "course" / "shop.db")
    shop = _load_module("make_shop")
    shop.SEED = 777
    fresh = Path(tempfile.mkdtemp()) / "shop_fresh.db"
    shop.build(fresh)
    con = sqlite3.connect(fresh)   # also change the catalogue prices, so numbers copied from the course db fail
    con.execute("UPDATE products SET price = ROUND(price * 1.15 + (product_id % 4), 2)")
    con.commit()
    con.close()
    return shipped, str(fresh)


def _query(sql: str, path: str) -> pd.DataFrame:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return pd.read_sql_query(sql, con)
    finally:
        con.close()


def _tables(path: str) -> dict[str, pd.DataFrame]:
    return {t: _query(f"SELECT * FROM {t}", path)
            for t in ["customers", "products", "orders", "order_items", "payments", "support_tickets"]}


def _check_sql(sql: str, expected_fn, columns: list[str], ordered: bool = False, rtol: float = 1e-6) -> None:
    assert isinstance(sql, str) and sql.strip(), "the answer should be a SQL query string"
    for label, path in zip(("the course database", "a second, freshly generated database"), _db_paths()):
        try:
            got = _query(sql, path)
        except Exception as err:  # noqa: BLE001
            raise AssertionError(f"the query fails on {label}: {err}") from None
        expected = expected_fn(_tables(path))
        _compare(got, expected, columns, ordered, rtol, label)


def _compare(got: pd.DataFrame, expected: pd.DataFrame, columns: list[str], ordered: bool, rtol: float,
             label: str) -> None:
    got_cols = [c.lower() for c in got.columns]
    missing = [c for c in columns if c not in got_cols]
    assert not missing, f"the result needs the columns {columns}; missing {missing} (got {list(got.columns)})"
    got = got.rename(columns=str.lower)[columns].reset_index(drop=True)
    expected = expected[columns].reset_index(drop=True)
    assert len(got) == len(expected), f"on {label}: expected {len(expected)} rows, got {len(got)}"
    if not ordered:
        got = got.sort_values(columns).reset_index(drop=True)
        expected = expected.sort_values(columns).reset_index(drop=True)
    for col in columns:
        a, b = got[col], expected[col]
        if pd.api.types.is_numeric_dtype(b) and not pd.api.types.is_bool_dtype(b):
            ok = np.isclose(pd.to_numeric(a, errors="coerce").astype(float), b.astype(float),
                            rtol=rtol, atol=1e-6, equal_nan=True)
            if not ok.all():
                i = int(np.argmin(ok))
                raise AssertionError(f"on {label}: column '{col}' differs (row {i}: expected {_v(b.iloc[i])}, "
                                     f"got {_v(a.iloc[i])})" + ("" if ordered else " after sorting"))
        else:
            same = (a.isna().values & b.isna().values) | (a.astype(str).values == b.astype(str).values)
            if not same.all():
                i = int(np.argmin(same))
                raise AssertionError(f"on {label}: column '{col}' differs (row {i}: expected {_v(b.iloc[i])}, "
                                     f"got {_v(a.iloc[i])})")


def _v(x):
    """A value as a student would write it (no numpy type names)."""
    x = x.item() if hasattr(x, "item") else x
    return repr(round(x, 4) if isinstance(x, float) else x)


def _line_totals(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    items = t["order_items"].merge(t["orders"], on="order_id")
    items["line_total"] = items.quantity * items.unit_price * (1 - items.discount)
    return items


# ----------------------------------------------------------------------------- 09: SQL windows and CTEs


@exercise("w03.above_average_products", hint="Compute the average price in a subquery inside WHERE.")
def _(sql):
    def exp(t):
        p = t["products"]
        return p[p.price > p.price.mean()][["name", "price"]]
    _check_sql(sql, exp, ["name", "price"])


@exercise("w03.customers_with_cancellations", hint="WHERE customer_id IN (SELECT ... FROM orders WHERE ...).")
def _(sql):
    def exp(t):
        o = t["orders"]
        ids = sorted(o[o.status == "cancelled"].customer_id.unique())
        return t["customers"][t["customers"].customer_id.isin(ids)][["customer_id", "name"]]
    _check_sql(sql, exp, ["customer_id", "name"])


@exercise("w03.delivered_order_totals",
          hint="A CTE (WITH totals AS (...)) that sums quantity * unit_price * (1 - discount) per order.")
def _(sql):
    def exp(t):
        items = _line_totals(t)
        items = items[items.status == "delivered"]
        return (items.groupby("order_id", as_index=False).line_total.sum()
                .rename(columns={"line_total": "total"}).query("total > 500"))
    _check_sql(sql, exp, ["order_id", "total"], rtol=1e-4)


@exercise("w03.avg_order_value_by_channel",
          hint="First total each order (CTE), then average those totals per channel. Leave out cancelled orders.")
def _(sql):
    def exp(t):
        items = _line_totals(t)
        items = items[items.status != "cancelled"]
        totals = items.groupby(["order_id", "channel"], as_index=False).line_total.sum()
        return (totals.groupby("channel", as_index=False).line_total.mean()
                .rename(columns={"line_total": "avg_order_value"}))
    _check_sql(sql, exp, ["channel", "avg_order_value"], rtol=1e-4)


@exercise("w03.latest_order_per_customer",
          hint="ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC, order_id DESC), keep row 1.")
def _(sql):
    def exp(t):
        o = t["orders"].sort_values(["customer_id", "order_date", "order_id"], ascending=[True, False, False])
        return o.groupby("customer_id").head(1)[["customer_id", "order_id", "order_date"]]
    _check_sql(sql, exp, ["customer_id", "order_id", "order_date"])


@exercise("w03.product_revenue_rank",
          hint="Revenue per product in a CTE, then RANK() OVER (ORDER BY revenue DESC). Delivered orders only.")
def _(sql):
    def exp(t):
        items = _line_totals(t)
        items = items[items.status == "delivered"]
        rev = items.groupby("product_id", as_index=False).line_total.sum().rename(columns={"line_total": "revenue"})
        rev["revenue_rank"] = rev.revenue.rank(method="min", ascending=False).astype(int)
        return rev
    _check_sql(sql, exp, ["product_id", "revenue", "revenue_rank"], rtol=1e-4)


@exercise("w03.top3_per_category",
          hint="Units per product, then ROW_NUMBER() OVER (PARTITION BY category ORDER BY units DESC, product_id).")
def _(sql):
    def exp(t):
        items = _line_totals(t)
        items = items[items.status != "cancelled"].merge(t["products"][["product_id", "name", "category"]],
                                                         on="product_id")
        units = items.groupby(["category", "product_id", "name"], as_index=False).quantity.sum()
        units = units.rename(columns={"quantity": "units"}).sort_values(["category", "units", "product_id"],
                                                                        ascending=[True, False, True])
        return units.groupby("category").head(3)[["category", "name", "units"]]
    _check_sql(sql, exp, ["category", "name", "units"])


@exercise("w03.monthly_running_revenue",
          hint="Monthly revenue (substr(order_date, 1, 7)) in a CTE, then SUM(revenue) OVER (ORDER BY month).")
def _(sql):
    def exp(t):
        items = _line_totals(t)
        items = items[items.status == "delivered"].copy()
        items["month"] = items.order_date.str[:7]
        m = items.groupby("month", as_index=False).line_total.sum().rename(columns={"line_total": "revenue"})
        m = m.sort_values("month")
        m["running_revenue"] = m.revenue.cumsum()
        return m
    _check_sql(sql, exp, ["month", "revenue", "running_revenue"], ordered=True, rtol=1e-4)


@exercise("w03.month_over_month",
          hint="LAG(revenue) OVER (ORDER BY month) gives last month's value; the first month has NULL.")
def _(sql):
    def exp(t):
        items = _line_totals(t)
        items = items[items.status == "delivered"].copy()
        items["month"] = items.order_date.str[:7]
        m = items.groupby("month", as_index=False).line_total.sum().rename(columns={"line_total": "revenue"})
        m = m.sort_values("month")
        m["prev_revenue"] = m.revenue.shift(1)
        m["change"] = m.revenue - m.prev_revenue
        return m
    _check_sql(sql, exp, ["month", "revenue", "prev_revenue", "change"], ordered=True, rtol=1e-4)


@exercise("w03.category_revenue_share",
          hint="SUM(revenue) OVER () is the grand total on every row; divide by it.")
def _(sql):
    def exp(t):
        items = _line_totals(t)
        items = items[items.status == "delivered"].merge(t["products"][["product_id", "category"]], on="product_id")
        c = items.groupby("category", as_index=False).line_total.sum().rename(columns={"line_total": "revenue"})
        c["share"] = c.revenue / c.revenue.sum()
        return c
    _check_sql(sql, exp, ["category", "revenue", "share"], rtol=1e-4)


register_quiz("w03.09_q1", "c",
              "A window function adds a value to every row without collapsing rows; GROUP BY returns one row per group.",
              {"a": "Both can sum; the difference is what happens to the rows.",
               "b": "Window functions work in SQLite (since 3.25) and every major database.",
               "d": "Window functions do not filter rows; you filter their result in an outer query or CTE."})
register_quiz("w03.09_q2", "b",
              "RANK gives tied rows the same rank and then skips (1, 1, 3); ROW_NUMBER always gives 1, 2, 3.",
              {"a": "That is ROW_NUMBER's behaviour, not RANK's.",
               "c": "DENSE_RANK is the one that does not skip numbers (1, 1, 2).",
               "d": "Both depend on the ORDER BY inside OVER (...)."})
register_quiz("w03.09_q3", "a",
              "A CTE is a named subquery that makes a long query readable step by step; it is not stored anywhere.",
              {"b": "A CTE exists only while that one query runs.",
               "c": "SQLite and most databases treat a CTE like a subquery; it is about readability, not speed.",
               "d": "You can use CTEs with any SELECT."})
register_quiz("w03.09_q4", "d",
              "You cannot use a window function's result in WHERE of the same query: compute it in a CTE, then filter.",
              {"a": "LIMIT 3 would keep 3 rows overall, not 3 per category.",
               "b": "WHERE runs before window functions are computed, so this is an error.",
               "c": "GROUP BY category returns one row per category, not three."})
register_quiz("w03.09_q5", "c",
              "LAG looks one row back in the window's order; on the first row there is nothing before, so it is NULL.",
              {"a": "LAG returns NULL, not zero; deciding that missing means zero is your choice to make explicitly.",
               "b": "It returns NULL rather than raising an error.",
               "d": "Rows are not dropped by LAG."})

# ----------------------------------------------------------------------------- 10: pandas essentials


def _shop() -> dict[str, pd.DataFrame]:
    return _tables(_db_paths()[0])


def _small_orders() -> pd.DataFrame:
    return pd.DataFrame({
        "order_id": [1, 2, 3, 4, 5],
        "customer_id": [10, 10, 11, 12, 12],
        "order_date": ["2025-01-05", "2025-02-11", "2025-02-20", "2025-02-28", "2025-03-01"],
        "status": ["delivered", "cancelled", "delivered", "shipped", "delivered"],
        "channel": ["web", "web", "mobile_app", "web", "marketplace"],
    })


def _small_items() -> pd.DataFrame:
    return pd.DataFrame({
        "order_id": [1, 1, 2, 3, 4, 5],
        "product_id": [100, 101, 100, 102, 101, 102],
        "quantity": [1, 2, 1, 3, 1, 2],
        "unit_price": [10.0, 5.0, 10.0, 4.0, 5.0, 4.0],
        "discount": [0.0, 0.1, 0.0, 0.0, 0.5, 0.0],
    })


def _small_products() -> pd.DataFrame:
    return pd.DataFrame({"product_id": [100, 101, 102, 103], "name": ["A", "B", "C", "D"],
                         "category": ["x", "y", "x", "y"], "price": [10.0, 5.0, 4.0, 10.0]})


def _frame_equal(got, expected: pd.DataFrame, columns: list[str], label: str, ordered: bool = True) -> None:
    assert isinstance(got, pd.DataFrame), f"the function should return a DataFrame, got {type(got).__name__}"
    _compare(got, expected, columns, ordered, 1e-6, label)


def _unchanged(fn, *frames):
    copies = [f.copy() if isinstance(f, pd.DataFrame) else f for f in frames]
    out = fn(*frames)
    for before, after in zip(copies, frames):
        assert not isinstance(after, pd.DataFrame) or before.equals(after), "your function changed its input DataFrame; work on a copy instead"
    return out


@exercise("w03.delivered_orders", hint="Boolean filtering: df[df['status'] == 'delivered'].")
def _(fn):
    for label, o in (("a small table", _small_orders()), ("the shop orders", _shop()["orders"]),
                     ("an empty table", _small_orders().iloc[0:0])):
        got = _unchanged(fn, o)
        exp = o[o.status == "delivered"]
        _frame_equal(got, exp, list(o.columns), label)


@exercise("w03.add_line_total", hint="Columns can be combined element-wise: a * b * (1 - c). Do not loop.")
def _(fn):
    for label, items in (("a small table", _small_items()), ("the shop order_items", _shop()["order_items"])):
        got = _unchanged(fn, items)
        exp = items.assign(line_total=items.quantity * items.unit_price * (1 - items.discount))
        _frame_equal(got, exp, list(exp.columns), label)


@exercise("w03.top_n_expensive",
          hint="sort_values(['price', 'product_id'], ascending=[False, True]).head(n)")
def _(fn):
    for label, p, n in (("a small table", _small_products(), 2), ("the shop products", _shop()["products"], 5),
                        ("n larger than the table", _small_products(), 10)):
        got = _unchanged(fn, p, n)
        exp = p.sort_values(["price", "product_id"], ascending=[False, True]).head(n)
        _frame_equal(got, exp, list(p.columns), label)


@exercise("w03.orders_per_channel",
          hint="groupby('channel').size(), then reset_index(name='n_orders') and sort by count (desc), channel.")
def _(fn):
    for label, o in (("a small table", _small_orders()), ("the shop orders", _shop()["orders"])):
        got = _unchanged(fn, o)
        exp = (o.groupby("channel").size().reset_index(name="n_orders")
               .sort_values(["n_orders", "channel"], ascending=[False, True]))
        _frame_equal(got, exp, ["channel", "n_orders"], label)


@exercise("w03.revenue_by_category",
          hint="merge items with orders and products, keep delivered orders, then groupby('category').")
def _(fn):
    cases = (("small tables", _small_items(), _small_orders(), _small_products()),
             ("the shop tables", _shop()["order_items"], _shop()["orders"], _shop()["products"]))
    for label, items, orders, products in cases:
        got = _unchanged(fn, items, orders, products)
        m = items.merge(orders, on="order_id").merge(products, on="product_id")
        m = m[m.status == "delivered"]
        exp = (m.assign(revenue=m.quantity * m.unit_price * (1 - m.discount))
               .groupby("category", as_index=False).revenue.sum().sort_values("revenue", ascending=False))
        _frame_equal(got, exp, ["category", "revenue"], label, ordered=False)


@exercise("w03.customers_without_orders",
          hint="Keep customers whose customer_id is not in orders.customer_id (isin with ~).")
def _(fn):
    cust_small = pd.DataFrame({"customer_id": [10, 11, 12, 13, 14], "name": list("VWXYZ")})
    for label, c, o in (("small tables", cust_small, _small_orders()),
                        ("the shop tables", _shop()["customers"], _shop()["orders"]),
                        ("no orders at all", cust_small, _small_orders().iloc[0:0])):
        got = _unchanged(fn, c, o)
        exp = c[~c.customer_id.isin(o.customer_id)]
        _frame_equal(got, exp, ["customer_id"], label, ordered=False)


@exercise("w03.monthly_orders",
          hint="pd.to_datetime, then .dt.strftime('%Y-%m') or .dt.to_period('M').astype(str); count per month.")
def _(fn):
    for label, o in (("a small table", _small_orders()), ("the shop orders", _shop()["orders"])):
        got = _unchanged(fn, o)
        month = pd.to_datetime(o.order_date).dt.strftime("%Y-%m")
        exp = o.assign(month=month).groupby("month").size().reset_index(name="n_orders").sort_values("month")
        _frame_equal(got, exp, ["month", "n_orders"], label)


@exercise("w03.customer_summary",
          hint="Line totals per item, merge with orders, drop cancelled, then groupby customer with agg(...).")
def _(fn):
    for label, o, items in (("small tables", _small_orders(), _small_items()),
                            ("the shop tables", _shop()["orders"], _shop()["order_items"])):
        got = _unchanged(fn, o, items)
        m = items.merge(o, on="order_id")
        m = m[m.status != "cancelled"].assign(spent=lambda d: d.quantity * d.unit_price * (1 - d.discount))
        exp = m.groupby("customer_id", as_index=False).agg(n_orders=("order_id", "nunique"),
                                                           total_spent=("spent", "sum"))
        _frame_equal(got, exp, ["customer_id", "n_orders", "total_spent"], label, ordered=False)


@exercise("w03.fill_missing_city",
          hint="Return df.assign(city=df['city'].fillna('Unknown')) so the original is untouched.")
def _(fn):
    small = pd.DataFrame({"customer_id": [1, 2, 3], "city": ["Almaty", None, "Astana"]})
    for label, c in (("a small table", small), ("the shop customers", _shop()["customers"])):
        got = _unchanged(fn, c)
        exp = c.assign(city=c.city.fillna("Unknown"))
        _frame_equal(got, exp, list(c.columns), label)


@exercise("w03.big_discount_flag", hint="A comparison on a whole column gives a boolean column: df['discount'] >= 0.1")
def _(fn):
    for label, items in (("a small table", _small_items()), ("the shop order_items", _shop()["order_items"])):
        got = _unchanged(fn, items)
        assert isinstance(got, pd.DataFrame) and "big_discount" in got.columns, "add a column called big_discount"
        assert pd.api.types.is_bool_dtype(got.big_discount), "big_discount should be True/False (a boolean column)"
        exp = items.assign(big_discount=items.discount >= 0.1)
        _frame_equal(got, exp, list(exp.columns), label)


register_quiz("w03.10_q1", "b",
              "A DataFrame is a table of named columns; each column is a Series with one dtype.",
              {"a": "Rows of a DataFrame can mix types across columns; within one column the dtype is shared.",
               "c": "pandas keeps the table in memory, not in a database.",
               "d": "A Series is one column (or one row), not a whole table."})
register_quiz("w03.10_q2", "d",
              "merge(..., how='left') keeps every row of the left table, like LEFT JOIN.",
              {"a": "how='inner' keeps only matching rows.",
               "b": "concat stacks tables; it does not match keys.",
               "c": "groupby aggregates; it does not join."})
register_quiz("w03.10_q3", "a",
              "df[df.x > 3] keeps rows where the condition is True; it is SQL's WHERE.",
              {"b": "Selecting columns is df[['a', 'b']], SQL's SELECT list.",
               "c": "Sorting is sort_values, SQL's ORDER BY.",
               "d": "Grouping is groupby, SQL's GROUP BY."})
register_quiz("w03.10_q4", "c",
              "Vectorised column arithmetic runs in compiled code; a Python loop or apply over rows is much slower.",
              {"a": "apply calls Python once per row; it is convenient but rarely the fast option.",
               "b": "Both give the same numbers; the difference is speed and clarity.",
               "d": "iterrows is the slowest of these options."})
register_quiz("w03.10_q5", "b",
              "df[mask]['col'] = v sets values on a temporary copy; the original is unchanged. Use df.loc[mask, 'col'] = v.",
              {"a": "That is what you intended, but the first [mask] already made a separate (temporary) table.",
               "c": "pandas warns, but it does not raise an error or delete anything.",
               "d": "Nothing is added to the table."})

# ----------------------------------------------------------------------------- 11: cleaning and quality

MISSING_CODES = ["N/A", "n/a", "-", ""]
ISO, DMY, LONG = "%Y-%m-%d", "%d/%m/%Y", "%B %d, %Y"


def _ref_parse_dates(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip()
    out = pd.to_datetime(s, format=ISO, errors="coerce")
    out = out.fillna(pd.to_datetime(s, format=DMY, errors="coerce"))
    return out.fillna(pd.to_datetime(s, format=LONG, errors="coerce"))


def _ref_standardise(s: pd.Series) -> pd.Series:
    return s.str.strip().str.title()


@exercise("w03.count_missing",
          hint="df.isna().sum() counts missing values per column; sort the result from most to least.")
def _(fn):
    df = pd.DataFrame({"a": [1, None, 3, None], "b": ["x", "y", None, "z"], "c": [1.0, 2.0, 3.0, 4.0]})
    for label, d in (("a small table", df), ("an empty table", df.iloc[0:0])):
        got = fn(d)
        exp = d.isna().sum().sort_values(ascending=False)
        assert isinstance(got, pd.Series), "return a Series: column name -> number missing"
        assert dict(got) == dict(exp), f"on {label}: expected {dict(exp)}, got {dict(got)}"
        if label == "a small table":
            assert list(got.index)[0] in ("a", "b") and list(got.index)[-1] == "c", "sort from most to least missing"


@exercise("w03.read_with_missing_codes",
          hint="pd.read_csv(path, na_values=[...]) turns those strings into NaN while reading.")
def _(fn):
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "x.csv"
        p.write_text("id,city,discount\n1,Almaty,0.1\n2,N/A,-\n3,-,\n4,Astana,0.0\n")
        got = fn(str(p))
        assert isinstance(got, pd.DataFrame), "return the DataFrame read from the file"
        assert int(got.city.isna().sum()) == 2, "both 'N/A' and '-' in city should become missing (NaN)"
        assert int(got.discount.isna().sum()) == 2, "'-' and an empty field in discount should become missing"
        assert pd.api.types.is_numeric_dtype(got.discount), \
            "once '-' is treated as missing, discount should be read as numbers"


@exercise("w03.drop_exact_duplicates",
          hint="df.drop_duplicates() keeps the first copy; reset_index(drop=True) tidies the index.")
def _(fn):
    df = pd.DataFrame({"id": [1, 2, 2, 3, 3, 3], "v": ["a", "b", "b", "c", "c", "d"]})
    got = _unchanged(fn, df)
    exp = df.drop_duplicates().reset_index(drop=True)
    _frame_equal(got, exp, ["id", "v"], "a small table")
    assert list(got.index) == list(range(len(got))), "reset the index so it runs 0, 1, 2, ..."


@exercise("w03.parse_mixed_dates",
          hint="Try each known format with errors='coerce', and fill the gaps of one with the next (fillna).")
def _(fn):
    s = pd.Series(["2025-03-04", "04/03/2025", "March 4, 2025", " 2024-12-31", "31/12/2024", "December 31, 2024"])
    got = fn(s)
    exp = _ref_parse_dates(s)
    assert isinstance(got, pd.Series), "return a Series of dates"
    assert pd.api.types.is_datetime64_any_dtype(got), "the result should have a datetime dtype"
    got_s, exp_s = got.dt.strftime("%Y-%m-%d").tolist(), exp.dt.strftime("%Y-%m-%d").tolist()
    for raw, g, e in zip(s, got_s, exp_s):
        assert g == e, f"'{raw.strip()}' should be {e}, got {g} (careful: 04/03/2025 is day first, i.e. 4 March)"


@exercise("w03.standardise_text", hint="Chain .str.strip() and .str.title(); missing values stay missing.")
def _(fn):
    s = pd.Series([" almaty", "ALMATY", "Almaty  ", None, "astana"])
    got = fn(s)
    exp = _ref_standardise(s)
    assert isinstance(got, pd.Series), "return a Series"
    assert got.isna().tolist() == exp.isna().tolist(), "missing values must stay missing (not the text 'None')"
    assert got.dropna().tolist() == exp.dropna().tolist(), f"expected {exp.dropna().tolist()}, got {got.dropna().tolist()}"


@exercise("w03.convert_cents",
          hint="Where price_unit == 'cents', divide unit_price by 100; then drop price_unit.")
def _(fn):
    df = pd.DataFrame({"unit_price": [45.0, 4500.0, 8.0, 800.0], "price_unit": ["dollars", "cents", "dollars", "cents"]})
    got = _unchanged(fn, df)
    assert "price_unit" not in got.columns, "drop the price_unit column once every price is in dollars"
    assert np.allclose(got.unit_price, [45.0, 45.0, 8.0, 8.0]), f"prices should all be in dollars: got {got.unit_price.tolist()}"


@exercise("w03.flag_outliers_iqr",
          hint="q1, q3 = s.quantile([0.25, 0.75]); flag values below q1 - 1.5*IQR or above q3 + 1.5*IQR.")
def _(fn):
    rng = np.random.default_rng(0)
    for label, s in (("a small series", pd.Series([10, 11, 12, 11, 10, 95, -40, 12.0])),
                     ("a random series", pd.Series(rng.normal(0, 1, 500)))):
        got = fn(s)
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        exp = (s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)
        assert isinstance(got, pd.Series) and pd.api.types.is_bool_dtype(got), "return a boolean Series"
        assert got.tolist() == exp.tolist(), f"on {label}: {int(exp.sum())} outliers expected, you flagged {int(got.sum())}"


@exercise("w03.quality_checks",
          hint="Return a dict of named booleans, each one a single check on the whole table.")
def _(fn):
    good = pd.DataFrame({"order_id": [1, 2, 3], "quantity": [1, 2, 1], "unit_price": [5.0, 8.0, 1.5],
                         "status": ["delivered", "shipped", "cancelled"]})
    got = fn(good)
    keys = {"unique_order_ids", "quantities_positive", "prices_positive", "statuses_valid"}
    assert isinstance(got, dict) and keys <= set(got), f"return a dict with the keys {sorted(keys)}"
    assert all(bool(got[k]) for k in keys), "every check should pass on a clean table"
    bad_cases = {
        "unique_order_ids": good.assign(order_id=[1, 1, 3]),
        "quantities_positive": good.assign(quantity=[1, 0, 1]),
        "prices_positive": good.assign(unit_price=[5.0, -8.0, 1.5]),
        "statuses_valid": good.assign(status=["delivered", "lost", "cancelled"]),
    }
    for key, bad in bad_cases.items():
        res = fn(bad)
        assert not bool(res[key]), f"'{key}' should be False when the table breaks that rule"
        others = [k for k in keys if k != key and not bool(res[k])]
        assert not others, f"a table that breaks only '{key}' made {others} fail too"


register_quiz("w03.11_q1", "c",
              "Cleaning changes data so it is usable; validation checks it and stops the pipeline if a rule is broken.",
              {"a": "Validation should not silently change data; that hides problems.",
               "b": "Both are needed: you clean once you understand a problem, and validate every time new data arrives.",
               "d": "Validation is about data, not model accuracy."})
register_quiz("w03.11_q2", "b",
              "Filling with the mean pretends you know the value and shrinks the spread; missingness itself may carry information.",
              {"a": "Every fill choice changes the data; the question is whether the change is honest.",
               "c": "It does not affect duplicates.",
               "d": "Many models can be given an 'is missing' flag together with a filled value; that is often better."})
register_quiz("w03.11_q3", "d",
              "-1 is a code meaning 'unknown' in that system, so it must become a missing value, not a number to average.",
              {"a": "Taking the absolute value invents a quantity of 1.",
               "b": "Dropping every row with -1 may throw away valid orders whose quantity was simply not recorded.",
               "c": "Averaging -1 with real quantities biases every statistic."})
register_quiz("w03.11_q4", "a",
              "With dayfirst=True pandas reads 2025-03-04 as 3 April. Parse each known format explicitly.",
              {"b": "ISO dates are year-month-day; reading them day first is the bug.",
               "c": "Both formats exist in this file, so one global rule cannot be right for both.",
               "d": "The problem is not time zones."})
register_quiz("w03.11_q5", "c",
              "An outlier rule flags values to inspect; whether to drop them depends on whether they are errors or real.",
              {"a": "Real extreme values (a bulk order) are information, not errors.",
               "b": "The IQR rule is a screening heuristic, not proof of an error.",
               "d": "Outliers matter for many models, not only linear ones."})

# ----------------------------------------------------------------------------- 12: lab


@lru_cache(maxsize=None)
def _lab_files() -> tuple[str, str]:
    shipped = str(repo_root() / "data" / "course" / "messy_orders.csv")
    mod = _load_module("make_messy_orders")
    fresh = Path(tempfile.mkdtemp()) / "messy_orders_fresh.csv"
    mod.write(mod.generate(seed=41, n_orders=900), fresh)
    return shipped, str(fresh)


def _ref_load(path: str) -> pd.DataFrame:
    return pd.read_csv(path, na_values=MISSING_CODES)


def _ref_dedupe(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates().reset_index(drop=True)


def _ref_dates(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(order_date=_ref_parse_dates(df.order_date))


def _ref_text(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(city=_ref_standardise(df.city), status=df.status.str.strip().str.lower())


def _ref_prices(df: pd.DataFrame) -> pd.DataFrame:
    price = df.unit_price.where(df.price_unit != "cents", df.unit_price / 100).round(2)
    return df.assign(unit_price=price).drop(columns="price_unit")


def _ref_impossible(df: pd.DataFrame) -> pd.DataFrame:
    df = df.assign(quantity=df.quantity.where(df.quantity != -1))
    keep = ~(df.quantity < 0) & (df.unit_price > 0)
    return df[keep].assign(discount=df.discount.fillna(0.0)).reset_index(drop=True)


ALLOWED = {"delivered", "shipped", "cancelled", "returned"}


def _ref_report(df: pd.DataFrame) -> dict:
    return {
        "rows": int(len(df)),
        "duplicate_order_ids": int(df.order_id.duplicated().sum()),
        "missing_quantity": int(df.quantity.isna().sum()),
        "missing_city": int(df.city.isna().sum()),
        "dates_in_range": bool(df.order_date.between("2024-01-01", "2025-12-31").all()),
        "prices_positive": bool((df.unit_price > 0).all()),
        "statuses_valid": bool(df.status.isin(ALLOWED).all()),
    }


_STEPS = [_ref_load, _ref_dedupe, _ref_dates, _ref_text, _ref_prices, _ref_impossible]


def _input_for(step: int, path: str):
    """The correct input to lab step `step` (0 = load): earlier steps are done by the reference."""
    data = path
    for fn in _STEPS[:step]:
        data = fn(data)
    return data


def _lab_step(step: int, fn, columns_check=None) -> None:
    for label, path in zip(("the course file", "a freshly generated file"), _lab_files()):
        inp = _input_for(step, path)
        before = inp.copy() if isinstance(inp, pd.DataFrame) else None
        got = fn(inp)
        if before is not None:
            assert before.equals(inp), "your function changed its input DataFrame; return a new one"
        exp = _STEPS[step](inp)
        assert isinstance(got, pd.DataFrame), f"return a DataFrame (got {type(got).__name__})"
        assert list(got.columns) == list(exp.columns), \
            f"on {label}: columns should be {list(exp.columns)}, got {list(got.columns)}"
        assert len(got) == len(exp), f"on {label}: expected {len(exp)} rows, got {len(got)}"
        if columns_check:
            columns_check(got, exp, label)
        cols = list(exp.columns)
        g = got.reset_index(drop=True).copy()
        e = exp.reset_index(drop=True).copy()
        for c in cols:
            if pd.api.types.is_datetime64_any_dtype(e[c]):
                assert pd.api.types.is_datetime64_any_dtype(g[c]), f"'{c}' should have a datetime dtype"
                g[c], e[c] = g[c].dt.strftime("%Y-%m-%d"), e[c].dt.strftime("%Y-%m-%d")
        _compare(g, e, cols, True, 1e-6, label)


@exercise("w03.lab_load", hint="read_csv with na_values for the three missing-value codes in this file.")
def _(fn):
    _lab_step(0, fn)


@exercise("w03.lab_dedupe", hint="Exact duplicate rows only; keep the first; reset the index.")
def _(fn):
    _lab_step(1, fn)


@exercise("w03.lab_dates", hint="Reuse your parse_mixed_dates idea from notebook 11 on the order_date column.")
def _(fn):
    _lab_step(2, fn)


@exercise("w03.lab_text", hint="city: strip + title case. status: strip + lower case. Missing stays missing.")
def _(fn):
    _lab_step(3, fn)


@exercise("w03.lab_prices", hint="Cents to dollars where price_unit says so, round to 2 decimals, drop price_unit.")
def _(fn):
    _lab_step(4, fn)


@exercise("w03.lab_impossible",
          hint="-1 means unknown (make it NaN); drop rows with other negative quantities or prices <= 0; missing "
               "discount means no discount (0.0); reset the index.")
def _(fn):
    _lab_step(5, fn)


@exercise("w03.lab_report", hint="One entry per key, each computed on the cleaned table; use plain int and bool values.")
def _(fn):
    keys = ["rows", "duplicate_order_ids", "missing_quantity", "missing_city", "dates_in_range",
            "prices_positive", "statuses_valid"]
    for label, path in zip(("the course file", "a freshly generated file"), _lab_files()):
        clean = _input_for(6, path)
        got = fn(clean.copy())
        exp = _ref_report(clean)
        assert isinstance(got, dict), "return a dict"
        missing = [k for k in keys if k not in got]
        assert not missing, f"the report is missing the keys {missing}"
        for k in keys:
            g = got[k]
            assert (bool(g) == exp[k]) if isinstance(exp[k], bool) else (int(g) == exp[k]), \
                f"on {label}: '{k}' should be {exp[k]}, got {g}"
        bad = clean.copy()
        bad.loc[0, "unit_price"] = -1.0
        assert not bool(fn(bad)["prices_positive"]), "prices_positive must turn False when a price is not positive"


register_quiz("w03.12_q1", "b",
              "Write each cleaning step as a function of its input: you can test it, reorder it and rerun it on next month's file.",
              {"a": "Editing the CSV by hand cannot be repeated or reviewed.",
               "c": "A single giant cell is hard to test or reuse.",
               "d": "Saving over the raw file destroys the evidence of what was changed."})
register_quiz("w03.12_q2", "c",
              "Duplicates must go before counting anything; otherwise every count and total is inflated.",
              {"a": "Parsing dates first does not change duplicate detection, but counting before deduplicating does.",
               "b": "The order matters for every downstream number.",
               "d": "Dropping impossible values first can hide that two copies of a row existed."})
register_quiz("w03.12_q3", "a",
              "A quality report is evidence: it records what the data looked like after cleaning, so a reviewer can trust or question it.",
              {"b": "It does not fix anything by itself.",
               "c": "It is for every dataset that feeds a model, not only big ones.",
               "d": "It complements cleaning; it does not replace it."})
register_quiz("w03.12_q4", "d",
              "Filling a missing discount with 0 is a business assumption: write it down so others can disagree with it.",
              {"a": "No fill value is automatically correct.",
               "b": "Dropping those rows would lose real orders.",
               "c": "The mean discount invents a discount that was probably never given."})
