"""Week 2 graders: SQL from zero (notebooks 05-08).

Every SQL exercise is graded the same way: the student's query runs against the course shop database AND
against a second copy generated with a different random seed, and each result is compared with an expected
result computed independently in pandas. Rows are compared as a set unless the task asks for an order.
Column names are not graded (only their order and contents), so aliases are free.
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

REVENUE_STATUSES = ("delivered", "shipped")


# --------------------------------------------------------------------------- databases
@lru_cache(maxsize=None)
def _databases() -> tuple[Path, Path]:
    """The course database and a variant built with another seed (catches hard-coded answers)."""
    main = repo_root() / "data" / "course" / "shop.db"
    spec = importlib.util.spec_from_file_location("_make_shop", repo_root() / "data" / "course" / "make_shop.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.SEED = mod.SEED + 101
    variant = Path(tempfile.mkdtemp(prefix="mlcourse_w02_")) / "shop_variant.db"
    mod.build(variant)
    # Make the copy differ in size and prices too, so counts and orderings cannot be hard-coded.
    with sqlite3.connect(variant) as con:
        gone = "SELECT customer_id FROM customers WHERE customer_id % 13 = 0"
        con.execute(f"DELETE FROM payments WHERE order_id IN (SELECT order_id FROM orders WHERE customer_id IN ({gone}))")
        con.execute(f"DELETE FROM order_items WHERE order_id IN (SELECT order_id FROM orders WHERE customer_id IN ({gone}))")
        con.execute(f"DELETE FROM orders WHERE customer_id IN ({gone})")
        con.execute(f"DELETE FROM support_tickets WHERE customer_id IN ({gone})")
        con.execute(f"DELETE FROM customers WHERE customer_id IN ({gone})")
        con.execute("UPDATE products SET price = ROUND(price * (0.8 + (product_id % 5) * 0.1), 2)")
    return main, variant


@lru_cache(maxsize=None)
def _tables(path: Path) -> dict[str, pd.DataFrame]:
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as con:
        names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {n: pd.read_sql_query(f"SELECT * FROM {n}", con) for n in names}


def _run(query, path: Path) -> pd.DataFrame:
    if not isinstance(query, str):
        raise AssertionError("the answer should be a SQL query written as a Python string")
    text = query.strip().rstrip(";").strip()
    if not text:
        raise NotImplementedError
    if ";" in text:
        raise AssertionError("write exactly one query (there is a ';' in the middle of your answer)")
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as con:
            return pd.read_sql_query(text, con)
    except Exception as err:  # SQL syntax or name errors: report SQLite's own message
        msg = str(err).split("\n")[0]
        raise AssertionError(f"SQLite could not run your query: {msg}") from None


# --------------------------------------------------------------------------- comparison
def _norm(v):
    if v is None:
        return None
    if isinstance(v, (bool, np.bool_)):
        return float(v)
    if isinstance(v, (int, float, np.integer, np.floating)):
        return None if math.isnan(float(v)) else float(v)
    return str(v)


def _rows(df: pd.DataFrame) -> list[tuple]:
    return [tuple(_norm(v) for v in row) for row in df.itertuples(index=False, name=None)]


def _sort_key(row: tuple, decimals: int):
    return tuple((0, "") if v is None else (1, f"{round(v, decimals):.{decimals}f}") if isinstance(v, float)
                 else (2, v) for v in row)


def _matches(got: pd.DataFrame, exp: pd.DataFrame, ordered: bool, decimals: int) -> bool:
    if got.shape != exp.shape:
        return False
    a, b = _rows(got), _rows(exp)
    if not ordered:
        a, b = sorted(a, key=lambda r: _sort_key(r, decimals)), sorted(b, key=lambda r: _sort_key(r, decimals))
    tol = 10 ** -decimals * 1.01
    for ra, rb in zip(a, b):
        for va, vb in zip(ra, rb):
            if isinstance(va, float) and isinstance(vb, float):
                if abs(va - vb) > tol:
                    return False
            elif va != vb:
                return False
    return True


def _check(query, expected, *, ordered: bool = False, decimals: int = 2, mistakes=()):
    """Grade one query. `expected(T)` and each mistake function take the dict of tables and return a DataFrame."""
    main, variant = _databases()
    for path in (main, variant):
        got = _run(query, path)
        T = _tables(path)
        exp = expected(T)
        if _matches(got, exp, ordered, decimals):
            continue
        for wrong, message in mistakes:
            if _matches(got, wrong(T), ordered, decimals):
                raise AssertionError(message)
        cols = ", ".join(exp.columns)
        if got.shape[1] != exp.shape[1]:
            raise AssertionError(f"expected {exp.shape[1]} column(s) ({cols}), your query returns {got.shape[1]}")
        if path == variant:
            raise AssertionError("your query gives the right answer on this database but not on a second, "
                                 "differently generated copy: it probably hard-codes values (ids, counts, names) "
                                 "instead of computing them from the tables")
        if len(got) != len(exp):
            raise AssertionError(f"expected {len(exp)} row(s), your query returns {len(got)}")
        if ordered and _matches(got, exp, False, decimals):
            raise AssertionError("the right rows, but in the wrong order: check your ORDER BY")
        raise AssertionError("the right number of rows and columns, but some values differ: "
                             "check your conditions and calculations")


def _df(rows, columns) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=columns)


def _line_totals(T) -> pd.DataFrame:
    it = T["order_items"].copy()
    it["line_total"] = it["quantity"] * it["unit_price"] * (1 - it["discount"])
    return it


# =========================================================================== notebook 05: SELECT
@exercise("w02.all_products", hint="SELECT * returns every column.")
def _(q):
    _check(q, lambda T: T["products"])


@exercise("w02.customer_names_cities", hint="List the two columns after SELECT, separated by a comma.")
def _(q):
    _check(q, lambda T: T["customers"][["name", "city"]])


@exercise("w02.cheap_products", hint="A WHERE clause with a < comparison.")
def _(q):
    _check(q, lambda T: T["products"].loc[T["products"]["price"] < 15, ["name", "price"]],
           mistakes=[(lambda T: T["products"].loc[T["products"]["price"] <= 15, ["name", "price"]],
                      "you included products that cost exactly 15: the task says *less than* 15")])


@exercise("w02.books_over_20", hint="Two conditions that must both hold: join them with AND.")
def _(q):
    p = lambda T: T["products"]  # noqa: E731
    _check(q, lambda T: p(T).loc[(p(T)["category"] == "Books") & (p(T)["price"] > 20), ["name", "price"]],
           mistakes=[(lambda T: p(T).loc[(p(T)["category"] == "Books") | (p(T)["price"] > 20), ["name", "price"]],
                      "too many rows: with OR a product needs only ONE of the two conditions")])


@exercise("w02.students_two_cities", hint="IN ('Almaty', 'Astana') keeps the logic simple.")
def _(q):
    def exp(T):
        c = T["customers"]
        return c.loc[(c["segment"] == "student") & c["city"].isin(["Almaty", "Astana"]), ["customer_id", "name"]]

    def precedence(T):
        c = T["customers"]
        return c.loc[((c["segment"] == "student") & (c["city"] == "Almaty")) | (c["city"] == "Astana"),
                     ["customer_id", "name"]]
    _check(q, exp, mistakes=[(precedence, "you included non-students from Astana: AND binds tighter than OR, "
                                          "so add parentheses or use IN")])


@exercise("w02.march_2025_orders", hint="Dates are text in 'YYYY-MM-DD' form, so BETWEEN works on them.")
def _(q):
    def exp(T):
        o = T["orders"]
        return o.loc[(o["order_date"] >= "2025-03-01") & (o["order_date"] <= "2025-03-31"), ["order_id", "order_date"]]
    _check(q, exp)


@exercise("w02.names_starting_a", hint="LIKE with the % wildcard.")
def _(q):
    _check(q, lambda T: T["customers"].loc[T["customers"]["name"].str.upper().str.startswith("A"),
                                           ["customer_id", "name"]])


@exercise("w02.top5_expensive", hint="ORDER BY two columns, then LIMIT.")
def _(q):
    def exp(T):
        p = T["products"].sort_values(["price", "name"], ascending=[False, True])
        return p[["name", "price"]].head(5)
    _check(q, exp, ordered=True)


@exercise("w02.distinct_categories", hint="SELECT DISTINCT, then ORDER BY.")
def _(q):
    _check(q, lambda T: pd.DataFrame({"category": sorted(T["products"]["category"].unique())}), ordered=True)


@exercise("w02.missing_email", hint="Missing values are tested with IS NULL, never with = NULL.")
def _(q):
    def exp(T):
        c = T["customers"]
        return c.loc[c["email"].isna(), ["customer_id", "name"]]
    _check(q, exp, mistakes=[(lambda T: _df([], ["customer_id", "name"]),
                              "your query returns no rows: `email = NULL` is never true in SQL; use IS NULL")])


@exercise("w02.not_almaty", hint="Customers with an unknown city (NULL) must be included too.")
def _(q):
    def exp(T):
        c = T["customers"]
        return c.loc[c["city"].ne("Almaty") | c["city"].isna(), ["customer_id"]]

    def dropped_nulls(T):
        c = T["customers"]
        return c.loc[c["city"].notna() & c["city"].ne("Almaty"), ["customer_id"]]
    _check(q, exp, mistakes=[(dropped_nulls, "you lost the customers whose city is unknown: `city != 'Almaty'` "
                                             "is not true for NULL, so add `OR city IS NULL`")])


@exercise("w02.line_totals", hint="quantity * unit_price * (1 - discount), named with AS.")
def _(q):
    _check(q, lambda T: _line_totals(T)[["order_id", "product_id", "line_total"]],
           mistakes=[(lambda T: T["order_items"].assign(t=lambda d: d.quantity * d.unit_price)[["order_id", "product_id", "t"]],
                      "the totals ignore the discount: multiply by (1 - discount)")])


@exercise("w02.signups_2025", hint="strftime('%Y-%m', signup_date) gives the month as text.")
def _(q):
    def exp(T):
        c = T["customers"]
        c = c.loc[c["signup_date"].str.startswith("2025")].copy()
        c["signup_month"] = c["signup_date"].str[:7]
        return c[["customer_id", "signup_date", "signup_month"]]
    _check(q, exp)


register_quiz("w02.05_q1", "b", "A primary key identifies exactly one row: no two rows share it and it is never NULL.",
              {"a": "Being the first column does not make a column a key.",
               "c": "Keys are about identity, not about sorting; ORDER BY decides the order of a result.",
               "d": "Many columns are mandatory without being keys; the key's job is uniqueness."})
register_quiz("w02.05_q2", "c", "orders.customer_id is a foreign key: it holds the primary key of a row in customers.",
              {"a": "order_id identifies the order itself: it is the primary key of orders.",
               "b": "order_date is an ordinary column; it does not point to another table.",
               "d": "status describes the order; it does not refer to another table."})
register_quiz("w02.05_q3", "d", "Any comparison with NULL gives NULL (unknown), which WHERE treats as false. Use IS NULL.",
              {"a": "NULL is not equal to NULL in SQL: the comparison is unknown, not true.",
               "b": "There is no error: the query runs and silently returns nothing.",
               "c": "The comparison is never true for any row, so no rows come back."})
register_quiz("w02.05_q4", "a", "Without ORDER BY, SQL promises no order, so LIMIT 5 returns some 5 rows, not the 'first' ones.",
              {"b": "Tables have no meaningful order in SQL; insertion order is not guaranteed.",
               "c": "LIMIT does not sort; only ORDER BY sorts.",
               "d": "The query is valid; LIMIT works with or without ORDER BY."})
register_quiz("w02.05_q5", "b", "'A%' means: starts with A, followed by anything (including nothing).",
              {"a": "% matches any number of characters, not exactly one; '_' matches exactly one.",
               "c": "That would be '%A'.",
               "d": "That would be '%A%'."})


# =========================================================================== notebook 06: aggregation
@exercise("w02.count_customers", hint="COUNT(*) counts rows.")
def _(q):
    _check(q, lambda T: _df([[len(T["customers"])]], ["n"]))


@exercise("w02.count_emails", hint="COUNT(column) skips NULLs.")
def _(q):
    _check(q, lambda T: _df([[int(T["customers"]["email"].notna().sum())]], ["n"]),
           mistakes=[(lambda T: _df([[len(T["customers"])]], ["n"]),
                      "that is the number of all customers: COUNT(*) counts rows, COUNT(email) counts known emails")])


@exercise("w02.count_cities", hint="COUNT(DISTINCT ...) counts different values; NULL is not a value.")
def _(q):
    _check(q, lambda T: _df([[T["customers"]["city"].nunique()]], ["n"]),
           mistakes=[(lambda T: _df([[int(T["customers"]["city"].notna().sum())]], ["n"]),
                      "that counts customers with a city, not different cities: add DISTINCT")])


@exercise("w02.price_stats", hint="Three aggregate functions in one SELECT.")
def _(q):
    _check(q, lambda T: _df([[T["products"]["price"].min(), T["products"]["price"].max(),
                              T["products"]["price"].mean()]], ["min_price", "max_price", "avg_price"]))


@exercise("w02.orders_per_status", hint="GROUP BY status, then COUNT(*).")
def _(q):
    _check(q, lambda T: T["orders"].groupby("status").size().reset_index(name="n"))


@exercise("w02.units_per_product", hint="SUM(quantity) for each product_id.")
def _(q):
    _check(q, lambda T: T["order_items"].groupby("product_id")["quantity"].sum().reset_index(),
           mistakes=[(lambda T: T["order_items"].groupby("product_id").size().reset_index(name="n"),
                      "that counts order lines, not units: sum the quantity")])


@exercise("w02.busy_channels", hint="Filter rows with WHERE before grouping; filter groups with HAVING after.")
def _(q):
    def counts(T, keep_cancelled):
        o = T["orders"] if keep_cancelled else T["orders"].loc[T["orders"]["status"] != "cancelled"]
        g = o.groupby("channel").size().reset_index(name="n_orders")
        return g.loc[g["n_orders"] > 1000]
    _check(q, lambda T: counts(T, False),
           mistakes=[(lambda T: counts(T, True), "cancelled orders are included: exclude them with WHERE")])


@exercise("w02.products_over_500_units", hint="HAVING SUM(quantity) > 500.")
def _(q):
    def exp(T):
        g = T["order_items"].groupby("product_id")["quantity"].sum().reset_index(name="units")
        return g.loc[g["units"] > 500]
    _check(q, exp)


def _band(price):
    return "cheap" if price < 15 else "mid" if price < 40 else "premium"


@exercise("w02.price_bands", hint="CASE WHEN ... THEN ... END inside SELECT, then GROUP BY that band.")
def _(q):
    _check(q, lambda T: T["products"].assign(band=T["products"]["price"].map(_band))
           .groupby("band").size().reset_index(name="n_products"))


@exercise("w02.status_by_channel", hint="SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) counts the delivered ones.")
def _(q):
    def exp(T):
        o = T["orders"]
        return (o.assign(d=o["status"].eq("delivered").astype(int), c=o["status"].eq("cancelled").astype(int))
                .groupby("channel")[["d", "c"]].sum().reset_index())
    _check(q, exp)


@exercise("w02.orders_per_month_2025", hint="strftime('%Y-%m', order_date) as the month; ORDER BY month.")
def _(q):
    def exp(T):
        o = T["orders"].loc[T["orders"]["order_date"].str.startswith("2025")]
        return o.assign(month=o["order_date"].str[:7]).groupby("month").size().reset_index(name="n_orders")
    _check(q, exp, ordered=True)


@exercise("w02.avg_resolution_days", hint="julianday(resolved_at) - julianday(opened_at) is a number of days; AVG skips NULL.")
def _(q):
    def exp(T):
        t = T["support_tickets"].dropna(subset=["resolved_at"]).copy()
        t["days"] = (pd.to_datetime(t["resolved_at"]) - pd.to_datetime(t["opened_at"])).dt.days
        return t.groupby("topic")["days"].mean().reset_index()
    _check(q, exp, decimals=1)


register_quiz("w02.06_q1", "c", "COUNT(*) counts rows; COUNT(email) counts rows where email is not NULL.",
              {"a": "They differ whenever some emails are NULL.",
               "b": "It is the other way round: COUNT(*) counts every row.",
               "d": "COUNT(email) does not count distinct values unless you write COUNT(DISTINCT email)."})
register_quiz("w02.06_q2", "b", "WHERE filters rows before grouping; HAVING filters groups after the aggregates exist.",
              {"a": "WHERE cannot use aggregates like COUNT(*): they do not exist yet when WHERE runs.",
               "c": "They are not interchangeable: one acts on rows, the other on groups.",
               "d": "HAVING works with any aggregate, not only COUNT."})
register_quiz("w02.06_q3", "a", "Every SELECT column must be grouped or aggregated; otherwise the value per group is ambiguous.",
              {"b": "SQLite may let it run, but it then picks an arbitrary value: the result is not meaningful.",
               "c": "GROUP BY does not sort the result in any guaranteed way.",
               "d": "Aggregates are exactly what makes grouped queries useful."})
register_quiz("w02.06_q4", "d", "AVG ignores NULLs: it averages only the known values.",
              {"a": "NULLs are not treated as zero by AVG.",
               "b": "AVG does not fail on NULL; it skips it.",
               "c": "One NULL does not make the whole average NULL (only all-NULL input does)."})
register_quiz("w02.06_q5", "c", "CASE returns the THEN value of the first true WHEN, else the ELSE value (NULL if absent).",
              {"a": "CASE stops at the first true condition, even if later ones are also true.",
               "b": "Without ELSE, unmatched rows get NULL, not an error.",
               "d": "CASE works in SELECT, WHERE, GROUP BY and ORDER BY."})


# =========================================================================== notebook 07: joins
@exercise("w02.orders_with_names", hint="JOIN customers ON customers.customer_id = orders.customer_id.")
def _(q):
    def exp(T):
        o = T["orders"].loc[T["orders"]["order_date"].str.startswith("2025-01")]
        return o.merge(T["customers"], on="customer_id")[["order_id", "order_date", "name"]]
    _check(q, exp)


@exercise("w02.orders_per_customer", hint="LEFT JOIN from customers, and COUNT a column of orders, not *.")
def _(q):
    def counts(T):
        n = T["orders"].groupby("customer_id").size()
        c = T["customers"][["customer_id", "name"]].copy()
        c["n_orders"] = c["customer_id"].map(n).fillna(0).astype(int)
        return c

    def inner(T):
        c = counts(T)
        return c.loc[c["n_orders"] > 0]

    def count_star(T):
        c = counts(T)
        c["n_orders"] = c["n_orders"].clip(lower=1)
        return c
    _check(q, counts, mistakes=[
        (inner, "customers with no orders are missing: an inner JOIN drops them, use LEFT JOIN"),
        (count_star, "customers with no orders show 1, not 0: COUNT(*) counts the NULL-filled row; "
                     "count a column from orders instead")])


@exercise("w02.never_ordered", hint="LEFT JOIN orders, then keep rows where the order side IS NULL.")
def _(q):
    def exp(T):
        c = T["customers"]
        return c.loc[~c["customer_id"].isin(T["orders"]["customer_id"]), ["customer_id", "name"]]
    _check(q, exp)


@exercise("w02.order_lines_named", hint="Three tables: order_items JOIN products JOIN orders.")
def _(q):
    def exp(T):
        o = T["orders"].loc[T["orders"]["order_date"].str.startswith("2025-12")]
        m = T["order_items"].merge(o[["order_id"]], on="order_id").merge(T["products"], on="product_id")
        return m[["order_id", "name", "quantity"]]
    _check(q, exp)


def _revenue_lines(T, statuses=None):
    it = _line_totals(T).merge(T["orders"], on="order_id")
    if statuses is not None:
        it = it.loc[it["status"].isin(statuses)]
    return it


@exercise("w02.revenue_by_category", hint="Join order_items to products (for category) and to orders (for status).")
def _(q):
    def rev(T, exclude_cancelled):
        it = _revenue_lines(T).merge(T["products"][["product_id", "category"]], on="product_id")
        if exclude_cancelled:
            it = it.loc[it["status"] != "cancelled"]
        return it.groupby("category")["line_total"].sum().reset_index()
    _check(q, lambda T: rev(T, True),
           mistakes=[(lambda T: rev(T, False), "cancelled orders are included: they are not revenue")])


@exercise("w02.customers_per_city_with_orders", hint="COUNT(DISTINCT customers.customer_id): after the join there is one row per order.")
def _(q):
    def exp(T, distinct=True):
        m = T["customers"].merge(T["orders"], on="customer_id").dropna(subset=["city"])
        g = m.groupby("city")["customer_id"]
        return (g.nunique() if distinct else g.size()).reset_index()
    _check(q, exp, mistakes=[(lambda T: exp(T, False), "these are numbers of orders, not of customers: after the join "
                                                        "each customer appears once per order; count DISTINCT customers")])


@exercise("w02.order_values", hint="Group order_items by order_id and sum the line totals.")
def _(q):
    _check(q, lambda T: _line_totals(T).groupby("order_id")["line_total"].sum().reset_index())


@exercise("w02.avg_order_value_by_channel",
          hint="Average per ORDER: total of the lines divided by the number of distinct orders.")
def _(q):
    def exp(T, per_line=False):
        it = _revenue_lines(T)
        it = it.loc[it["status"] != "cancelled"]
        if per_line:
            return it.groupby("channel")["line_total"].mean().reset_index()
        per_order = it.groupby(["channel", "order_id"])["line_total"].sum().reset_index()
        return per_order.groupby("channel")["line_total"].mean().reset_index()
    _check(q, exp, mistakes=[(lambda T: exp(T, True), "that is the average order LINE, not the average order: after "
                                                       "joining order_items there is one row per line")])


@exercise("w02.paid_per_channel", hint="payments already has one row per payment: join only what you need (orders).")
def _(q):
    def exp(T):
        return T["payments"].merge(T["orders"], on="order_id").groupby("channel")["amount"].sum().reset_index()

    def fanned(T):
        m = T["payments"].merge(T["orders"], on="order_id").merge(T["order_items"], on="order_id")
        return m.groupby("channel")["amount"].sum().reset_index()
    _check(q, exp, mistakes=[(fanned, "the totals are too large: joining order_items repeats each payment once per "
                                      "order line (fan-out); leave order_items out")])


@exercise("w02.top_spenders_subquery", hint="Put the per-customer totals in a subquery in FROM, then filter it.")
def _(q):
    def exp(T):
        per = _revenue_lines(T, REVENUE_STATUSES).groupby("customer_id")["line_total"].sum()
        return per.loc[per > 1000].reset_index()
    _check(q, exp)


register_quiz("w02.07_q1", "b", "A LEFT JOIN keeps every row of the left table; unmatched right-side columns become NULL.",
              {"a": "That describes an INNER JOIN.",
               "c": "LEFT JOIN keeps unmatched LEFT rows, not unmatched right rows.",
               "d": "Neither join removes duplicates; each match produces a row."})
register_quiz("w02.07_q2", "c", "A customer with 3 orders appears in 3 joined rows, so per-customer values are repeated.",
              {"a": "The join adds rows when one side has several matches.",
               "b": "Customers without orders disappear in an inner join; they are not doubled.",
               "d": "SQL does not de-duplicate joined rows unless you ask for DISTINCT."})
register_quiz("w02.07_q3", "a", "The grain is what one row means; summing a per-order amount at per-line grain repeats it.",
              {"b": "The number of columns does not change what one row represents.",
               "c": "Grain is not about sorting.",
               "d": "Grain matters for every aggregate, not only averages."})
register_quiz("w02.07_q4", "d", "If the subquery returns any NULL, `x NOT IN (...)` is never true, so the result is empty.",
              {"a": "NOT IN is valid SQL; the problem is NULLs in the list.",
               "b": "Duplicates in the list do not change NOT IN.",
               "c": "The result is not 'all rows': a NULL in the list makes every comparison unknown."})
register_quiz("w02.07_q5", "b", "Comparing row counts before and after a join is the cheapest test for unwanted fan-out.",
              {"a": "Speed tells you nothing about correctness.",
               "c": "Column names do not reveal duplicated rows.",
               "d": "Joins on a key can still fan out when the key repeats on one side."})


# =========================================================================== notebook 08: lab
def _revenue_orders(T):
    return T["orders"].loc[T["orders"]["status"].isin(REVENUE_STATUSES)]


@exercise("w02.lab_monthly_revenue", hint="Revenue = lines of delivered or shipped orders; group by strftime('%Y-%m').")
def _(q):
    def exp(T, statuses=REVENUE_STATUSES):
        it = _revenue_lines(T, statuses)
        it = it.loc[it["order_date"].str.startswith("2025")]
        return it.assign(month=it["order_date"].str[:7]).groupby("month")["line_total"].sum().reset_index()
    _check(q, exp, ordered=True,
           mistakes=[(lambda T: exp(T, ("delivered", "shipped", "cancelled", "returned")),
                      "cancelled and returned orders are not revenue: keep only delivered and shipped")])


@exercise("w02.lab_top_customers", hint="Join to customers for the name; ORDER BY revenue DESC, customer_id; LIMIT 10.")
def _(q):
    def exp(T):
        per = _revenue_lines(T, REVENUE_STATUSES).groupby("customer_id")["line_total"].sum().reset_index(name="revenue")
        per = per.merge(T["customers"][["customer_id", "name"]], on="customer_id")
        return per.sort_values(["revenue", "customer_id"], ascending=[False, True]).head(10)[["customer_id", "name", "revenue"]]
    _check(q, exp, ordered=True)


@exercise("w02.lab_repeat_rate", hint="Count revenue orders per customer in a subquery, then average (n >= 2).")
def _(q):
    def exp(T):
        n = _revenue_orders(T).groupby("customer_id").size()
        return _df([[float((n >= 2).mean())]], ["repeat_rate"])
    _check(q, exp, decimals=3)


@exercise("w02.lab_unpaid_orders", hint="Revenue orders with no matching payment: LEFT JOIN payments ... IS NULL.")
def _(q):
    def exp(T):
        o = _revenue_orders(T)
        return o.loc[~o["order_id"].isin(T["payments"]["order_id"]), ["order_id", "customer_id", "order_date"]]
    _check(q, exp)


@exercise("w02.lab_ticket_resolution", hint="COUNT(*), COUNT(resolved_at), and AVG of the day difference, per topic.")
def _(q):
    def exp(T):
        t = T["support_tickets"].copy()
        t["days"] = (pd.to_datetime(t["resolved_at"]) - pd.to_datetime(t["opened_at"])).dt.days
        return t.groupby("topic").agg(n_tickets=("ticket_id", "size"), n_resolved=("resolved_at", "count"),
                                      avg_days=("days", "mean")).reset_index()
    _check(q, exp, decimals=1)


@exercise("w02.lab_category_channel", hint="Three tables; group by two columns.")
def _(q):
    def exp(T):
        it = _revenue_lines(T, REVENUE_STATUSES).merge(T["products"][["product_id", "category"]], on="product_id")
        return it.groupby(["category", "channel"])["line_total"].sum().reset_index()
    _check(q, exp)


@exercise("w02.lab_inactive_2024_signups", hint="Signed up in 2024 AND no order at all (anti-join), counted per segment.")
def _(q):
    def exp(T):
        c = T["customers"]
        c = c.loc[c["signup_date"].str.startswith("2024") & ~c["customer_id"].isin(T["orders"]["customer_id"])]
        return c.groupby("segment").size().reset_index(name="n_customers")
    _check(q, exp)


register_quiz("w02.08_q1", "c", "Write down the grain and the revenue definition before the query; most errors are there.",
              {"a": "Speed is rarely the problem with an analysis query; correctness is.",
               "b": "Pretty output does not make a wrong number right.",
               "d": "Running it first and reasoning later is how double counting goes unnoticed."})
register_quiz("w02.08_q2", "a", "A share needs the right denominator: customers who bought at least once.",
              {"b": "Including customers who never bought changes the question to 'share of all customers'.",
               "c": "Counting orders instead of customers answers a different question.",
               "d": "Excluding one-time buyers makes the rate 100% by construction."})
register_quiz("w02.08_q3", "d", "Check a total two ways: the per-month revenue should add up to the yearly revenue.",
              {"a": "A plausible-looking number is the usual disguise of a wrong one.",
               "b": "A different database would not tell you whether this query is right.",
               "c": "Row counts help, but only a reconciliation of totals checks the numbers themselves."})
register_quiz("w02.08_q4", "b", "Stating the definition (which statuses count as revenue) lets others check and reuse your number.",
              {"a": "Definitions belong next to the number, not hidden in the query.",
               "c": "Rounding hides nothing important here; the definition is what changes the result.",
               "d": "A chart without the definition repeats the ambiguity."})
