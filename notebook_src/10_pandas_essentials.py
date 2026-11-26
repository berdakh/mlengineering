# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/10_pandas_essentials.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 10 · pandas essentials, side by side with SQL
#
# **Week 3 · lesson · about 100 minutes**
#
# SQL is how you get data *out* of a database. **pandas** is how you work with it once it is in Python: it is the
# library almost every data scientist and ML engineer uses to look at, reshape and prepare tables before they reach
# a model. The good news: you already know the ideas. Filtering is `WHERE`, grouping is `GROUP BY`, merging is
# `JOIN`. This notebook teaches pandas by translating what you know.
#
# **What you will learn**
#
# - What a `DataFrame` and a `Series` are, and how to load one from a database or a CSV file.
# - Select, filter and sort rows; add new columns with fast, **vectorised** code (and why loops and `apply` are slow).
# - Group and aggregate with `groupby` and `agg`; combine tables with `merge`.
# - Work with dates: parse them and group by month.
# - Write small functions that take a DataFrame and return a new one, without changing their input.
#
# **What you need:** notebooks 05-09 (SQL). Basic Python: functions, lists, dicts.
#
# **How grading works:** each exercise is a function that takes one or more DataFrames and returns a DataFrame. The
# grader calls it on the real shop tables, on small hand-made tables and on empty tables, and checks that your
# function did not modify its input.

# %%
# --- Setup: works in Google Colab AND on your own computer. Safe to re-run. ---
# In Colab this downloads the course (about 30 s) and installs what it needs (about a minute, once
# per session). On your computer it just finds the course folder.
import os, sys, subprocess
from pathlib import Path

if "google.colab" in sys.modules and not Path("/content/mlengineering").exists():
    subprocess.run(["git", "clone", "--depth", "1",
                    "https://github.com/berdakh/mlengineering.git", "/content/mlengineering"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r",
                    "/content/mlengineering/requirements.txt"], check=True)
REPO_ROOT = Path("/content/mlengineering") if "google.colab" in sys.modules else next(
    p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src" / "mlcourse").is_dir())
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "src"))
from mlcourse.grader import grade, quiz
print("Ready. Course folder:", REPO_ROOT)

# %% [markdown]
# ## 1. DataFrames: a table in Python
#
# **Why.** A SQL result disappears once you have looked at it. To clean data, build features or train a model you
# need the table *in Python*, where you can keep it in a variable, change it step by step and hand it to
# scikit-learn.
#
# **Idea.** pandas has two objects:
#
# - a **`DataFrame`** is a table: named columns, and rows labelled by an **index** (by default 0, 1, 2, ...);
# - a **`Series`** is one column: values of a single type (its **dtype**, for example `int64`, `float64`, text or
#   datetime) plus the same index.
#
# You get a DataFrame by reading something: `pd.read_sql_query(query, connection)` for a database,
# `pd.read_csv(path)` for a file. By convention pandas is imported as `pd`. Four things to run on every new table:
# `.shape` (rows, columns), `.head()` (first rows), `.dtypes` (type of each column), `.describe()` (summary numbers).
#
# **See it.** Load the shop's four main tables. `connect("shop")` from the course helper opens the database
# read-only; `pd.read_sql_query` turns any query result into a DataFrame. You should see 4744 orders and 8299
# order items.

# %%
import pandas as pd
from mlcourse.sql import connect

with connect("shop") as con:
    orders = pd.read_sql_query("SELECT * FROM orders", con)
    items = pd.read_sql_query("SELECT * FROM order_items", con)
    products = pd.read_sql_query("SELECT * FROM products", con)
    customers = pd.read_sql_query("SELECT * FROM customers", con)

print(orders.shape, items.shape, products.shape, customers.shape)
orders.head()

# %%
orders.dtypes

# %%
items.describe()

# %% [markdown]
# **Try it.** A single column is a Series: run `orders["status"]` and then `orders["status"].value_counts()`. Which
# status is most common? Then run `type(orders)` and `type(orders["status"])`.

# %%
# Try it.
orders["status"].value_counts()

# %% [markdown]
# Here is the translation table you will use for the rest of the notebook. Keep it open; every row has an example
# below.
#
# | SQL | pandas |
# |---|---|
# | `SELECT a, b FROM t` | `t[["a", "b"]]` |
# | `WHERE x > 3 AND y = 'z'` | `t[(t["x"] > 3) & (t["y"] == "z")]` |
# | `WHERE x IN (1, 2)` | `t[t["x"].isin([1, 2])]` |
# | `ORDER BY x DESC LIMIT 5` | `t.sort_values("x", ascending=False).head(5)` |
# | `SELECT a * b AS c` | `t.assign(c=t["a"] * t["b"])` or `t["c"] = t["a"] * t["b"]` |
# | `GROUP BY g` with `COUNT(*)` | `t.groupby("g").size()` |
# | `GROUP BY g` with `SUM(x), AVG(y)` | `t.groupby("g").agg(total=("x", "sum"), avg=("y", "mean"))` |
# | `JOIN u ON t.k = u.k` | `t.merge(u, on="k")` |
# | `LEFT JOIN` | `t.merge(u, on="k", how="left")` |
# | `x IS NULL` | `t["x"].isna()` |
# | `COALESCE(x, 'n/a')` | `t["x"].fillna("n/a")` |
# | `COUNT(DISTINCT x)` | `t["x"].nunique()` |
# | `ROW_NUMBER() OVER (PARTITION BY g ORDER BY x)` | `t.sort_values("x").groupby("g").cumcount() + 1` |
# | `SUM(x) OVER (ORDER BY t)` | `t.sort_values("t")["x"].cumsum()` |
# | `LAG(x) OVER (ORDER BY t)` | `t.sort_values("t")["x"].shift(1)` |

# %% [markdown]
# ## 2. Select, filter, sort
#
# **Why.** Nearly every analysis starts with "only the rows that matter, only the columns I need, in a useful order".
#
# **Idea.**
#
# - **Columns:** `df[["a", "b"]]` (a list inside the brackets gives a DataFrame; `df["a"]` gives a Series).
# - **Rows:** write a condition on a column. `orders["status"] == "delivered"` is a Series of `True`/`False`, one
#   per row (a **boolean mask**). `orders[mask]` keeps the rows where it is `True`. That is SQL's `WHERE`.
#   Combine conditions with `&` (and), `|` (or), `~` (not), and **put each condition in brackets**:
#   `(a > 1) & (b < 2)`. Python's `and`/`or` do not work on whole columns.
# - **Sort:** `df.sort_values("price", ascending=False)`; for several keys pass lists:
#   `sort_values(["price", "product_id"], ascending=[False, True])`.
# - `df.loc[mask, ["a", "b"]]` does rows and columns in one step; you will use `.loc` to *change* values too.
#
# **See it.** Mobile-app orders that were delivered in 2025, newest first. Dates are stored as text like
# `2025-03-14`, so comparing them as text works because the format is year-month-day.

# %%
mask = (orders["channel"] == "mobile_app") & (orders["status"] == "delivered") & (orders["order_date"] >= "2025-01-01")
recent_app = orders.loc[mask, ["order_id", "customer_id", "order_date"]].sort_values("order_date", ascending=False)
print(len(recent_app), "rows")
recent_app.head()

# %% [markdown]
# **Try it.** Change the mask to also keep `"shipped"` orders: replace the status condition with
# `orders["status"].isin(["delivered", "shipped"])`. Predict: more rows or fewer?

# %%
# Try it.

# %% [markdown]
# ### How the exercises look
#
# In this notebook each exercise is a **function**: it receives a DataFrame and returns a new one. This is how you
# will write data code from now on, because a function can be tested on any table (the grader does exactly that).
# One rule: **never change the input**. Return a new table instead (filtering, `sort_values` and `assign` all
# return new tables, so this is easy if you avoid assigning into the input).
#
# ### Exercise 2.1 · Delivered orders
#
# Write `delivered_orders(orders)` that returns only the rows whose `status` is `"delivered"`, with all columns, in
# the original order. On an empty table it should return an empty table.

# %%
def delivered_orders(orders):
    ### BEGIN SOLUTION
    return orders[orders["status"] == "delivered"]
    ### END SOLUTION


delivered_orders(orders).head()

# %%
grade("w03.delivered_orders", delivered_orders)

# %% [markdown]
# ### Exercise 2.2 · The n most expensive products
#
# Write `top_n_expensive(products, n)` that returns the `n` most expensive products (all columns), most expensive
# first; when two products have the same price, the one with the **smaller `product_id`** comes first. If `n` is
# larger than the table, return all products.

# %%
def top_n_expensive(products, n):
    ### BEGIN SOLUTION
    return products.sort_values(["price", "product_id"], ascending=[False, True]).head(n)
    ### END SOLUTION


top_n_expensive(products, 3)

# %%
grade("w03.top_n_expensive", top_n_expensive)

# %% [markdown]
# ## 3. New columns, and why you should not loop
#
# **Why.** Features for a model are mostly new columns computed from old ones: a line total, a flag, a ratio. You
# will write thousands of them, so it matters that they are correct *and* fast.
#
# **Idea.** Arithmetic on columns works **element by element** over the whole column at once:
# `items["quantity"] * items["unit_price"]` multiplies row by row and returns a new Series. This is called
# **vectorised** code: the loop runs inside pandas' compiled code, not in Python.
#
# Two ways to add a column:
#
# - `df["c"] = ...` changes `df` in place (fine for your own working table);
# - `df.assign(c=...)` returns a **new** table and leaves `df` alone (what you want inside a function).
#
# You will also meet `df.apply(f, axis=1)`, which calls a Python function once per row. It is flexible but slow,
# and almost never needed for arithmetic or comparisons.
#
# **See it.** The same line total, computed with a vectorised expression and with `apply`. Both give identical
# numbers; look at the timings printed below (on our machine the vectorised version was about 40 to 80 times faster
# on these 8299 rows, and the gap grows with the table).

# %%
import time

t0 = time.perf_counter()
fast = items["quantity"] * items["unit_price"] * (1 - items["discount"])
t1 = time.perf_counter()
slow = items.apply(lambda row: row["quantity"] * row["unit_price"] * (1 - row["discount"]), axis=1)
t2 = time.perf_counter()

print("same result:", bool((fast - slow).abs().max() < 1e-9))
print(f"vectorised: {(t1 - t0) * 1000:.2f} ms   apply: {(t2 - t1) * 1000:.2f} ms")

# %% [markdown]
# **Try it.** Comparisons are vectorised too: `items["quantity"] >= 3` is a boolean column. How many order items
# have a quantity of 3 or more? (Hint: `True` counts as 1, so `.sum()` counts them.)

# %%
# Try it.
(items["quantity"] >= 3).sum()

# %% [markdown]
# A word on changing values in part of a table. To set a value only where a condition holds, use **one** `.loc`:
# `df.loc[df["status"] == "cancelled", "channel"] = "none"`. Writing it in two steps,
# `df[df["status"] == "cancelled"]["channel"] = "none"`, changes a temporary copy and leaves `df` untouched (pandas
# prints a warning). If you see that warning, rewrite the line with `.loc`.
#
# ### Exercise 3.1 · Line totals
#
# Write `add_line_total(items)` that returns a copy of the items table with a new column `line_total` equal to
# `quantity * unit_price * (1 - discount)`. Use vectorised code (no loop, no `apply`), and do not change `items`.

# %%
def add_line_total(items):
    ### BEGIN SOLUTION
    return items.assign(line_total=items["quantity"] * items["unit_price"] * (1 - items["discount"]))
    ### END SOLUTION


add_line_total(items).head()

# %%
grade("w03.add_line_total", add_line_total)

# %% [markdown]
# ### Exercise 3.2 · A boolean flag
#
# Write `big_discount_flag(items)` that returns a copy of the table with a new column `big_discount`: `True` when
# `discount` is **at least 0.1**, else `False`. It must be a real boolean column (not the strings "yes"/"no").

# %%
def big_discount_flag(items):
    ### BEGIN SOLUTION
    return items.assign(big_discount=items["discount"] >= 0.1)
    ### END SOLUTION


big_discount_flag(items)["big_discount"].mean()

# %%
grade("w03.big_discount_flag", big_discount_flag)

# %% [markdown]
# ### Exercise 3.3 · Missing values in a column
#
# Some customers have no city: the value is missing (`None` in the database, shown as `None` or `NaN` in pandas).
# `customers["city"].isna().sum()` counts them. Write `fill_missing_city(customers)` that returns a copy where a
# missing `city` is replaced by the text `"Unknown"` (SQL's `COALESCE(city, 'Unknown')`) and every other column is
# unchanged. Do not change `customers`.

# %%
print("missing cities:", customers["city"].isna().sum())


def fill_missing_city(customers):
    ### BEGIN SOLUTION
    return customers.assign(city=customers["city"].fillna("Unknown"))
    ### END SOLUTION


fill_missing_city(customers)["city"].value_counts().head(8)

# %%
grade("w03.fill_missing_city", fill_missing_city)

# %% [markdown]
# ## 4. groupby: split, apply, combine
#
# **Why.** "How many orders per channel?", "revenue per category?", "spend per customer?": most features and most
# reports are group summaries.
#
# **Idea.** `df.groupby("g")` **splits** the table into one piece per value of `g`, **applies** a summary to each
# piece, and **combines** the results into one row per group. That is exactly SQL's `GROUP BY`.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c10-01.svg" alt="groupby splits orders by channel, counts each piece, and combines the counts into one row per channel" style="max-width:100%">
#
# - `df.groupby("g").size()` counts rows per group (`COUNT(*)`); the result is a Series indexed by `g`.
# - `df.groupby("g")["x"].sum()` sums one column per group.
# - `df.groupby("g").agg(total=("x", "sum"), n=("id", "nunique"))` computes several named summaries at once: each
#   is `new_name=(column, function)`, with functions such as `"sum"`, `"mean"`, `"count"`, `"nunique"`, `"max"`.
# - The group column ends up in the **index**. `.reset_index()` (or `as_index=False`) turns it back into a normal
#   column, which is what you want before merging or saving. `reset_index(name="n")` names a Series' values.
#
# **See it.** Orders and number of distinct customers per status.

# %%
by_status = orders.groupby("status").agg(n_orders=("order_id", "count"),
                                         n_customers=("customer_id", "nunique")).reset_index()
by_status

# %% [markdown]
# **Try it.** Group by **two** columns: `orders.groupby(["channel", "status"]).size()`. Then add
# `.unstack()` at the end: it turns the inner group into columns, a quick cross-table.

# %%
# Try it.

# %% [markdown]
# ### Exercise 4.1 · Orders per channel
#
# Write `orders_per_channel(orders)` that returns a DataFrame with columns `channel` and `n_orders` (number of
# orders), one row per channel, sorted by `n_orders` from largest to smallest (and by `channel` alphabetically
# when two counts are equal).

# %%
def orders_per_channel(orders):
    ### BEGIN SOLUTION
    counts = orders.groupby("channel").size().reset_index(name="n_orders")
    return counts.sort_values(["n_orders", "channel"], ascending=[False, True])
    ### END SOLUTION


orders_per_channel(orders)

# %%
grade("w03.orders_per_channel", orders_per_channel)

# %% [markdown]
# ## 5. merge: JOIN in pandas
#
# **Why.** The information you need is spread over tables: the price is on the item, the category on the product,
# the status on the order. Before you can summarise, you combine.
#
# **Idea.** `left.merge(right, on="key")` matches rows with equal `key` values, like `JOIN ... ON left.key =
# right.key`. The `how=` argument picks the join type: `"inner"` (default, only matches), `"left"` (keep every row
# of the left table, missing values where there is no match), `"right"`, `"outer"`.
#
# Two habits from last week still apply. Know the **grain** of each table (one row per *what*?), and check the row
# count after a merge: merging items (one row per order item) with orders (one row per order) gives one row per
# order item, the same count as `items`. If the count grows unexpectedly, a key was not unique.
#
# Anti-joins ("customers *without* orders") are easiest with `isin` and `~`:
# `customers[~customers["customer_id"].isin(orders["customer_id"])]`.
#
# **See it.** Item rows with their order's status and the product's category; the row count stays 8299.

# %%
full = items.merge(orders, on="order_id").merge(products[["product_id", "name", "category"]], on="product_id")
print(len(items), len(full))
full.head(3)

# %% [markdown]
# **Try it.** Merge `customers` with `orders` using `how="left"`. How many rows have a missing `order_id`? Those
# are customers with no orders. Check that the number matches the anti-join below.

# %%
# Try it.
customers[~customers["customer_id"].isin(orders["customer_id"])].shape

# %% [markdown]
# ### Exercise 5.1 · Customers without orders
#
# Write `customers_without_orders(customers, orders)` that returns the rows of `customers` (all columns) whose
# `customer_id` never appears in `orders`. If `orders` is empty, every customer qualifies.

# %%
def customers_without_orders(customers, orders):
    ### BEGIN SOLUTION
    return customers[~customers["customer_id"].isin(orders["customer_id"])]
    ### END SOLUTION


len(customers_without_orders(customers, orders))

# %%
grade("w03.customers_without_orders", customers_without_orders)

# %% [markdown]
# ### Exercise 5.2 · Revenue by category
#
# Write `revenue_by_category(items, orders, products)` returning columns `category` and `revenue`: the sum of
# `quantity * unit_price * (1 - discount)` over items of **delivered** orders, one row per category. (Categories
# with no delivered sales do not appear.) Row order does not matter.

# %%
def revenue_by_category(items, orders, products):
    ### BEGIN SOLUTION
    m = items.merge(orders, on="order_id").merge(products, on="product_id")
    m = m[m["status"] == "delivered"]
    m = m.assign(revenue=m["quantity"] * m["unit_price"] * (1 - m["discount"]))
    return m.groupby("category", as_index=False)["revenue"].sum()
    ### END SOLUTION


revenue_by_category(items, orders, products)

# %%
grade("w03.revenue_by_category", revenue_by_category)

# %% [markdown]
# ### Exercise 5.3 · A customer summary
#
# This is the shape of a typical feature table: one row per customer. Write `customer_summary(orders, items)`
# returning columns `customer_id`, `n_orders` (number of **distinct** orders) and `total_spent` (sum of
# `quantity * unit_price * (1 - discount)`), counting only orders that are **not cancelled**. Customers whose
# every order was cancelled do not appear. Row order does not matter.
#
# *Watch out:* after merging items with orders there is one row per item, so counting rows would count items, not
# orders. Which aggregation counts distinct values?

# %%
def customer_summary(orders, items):
    ### BEGIN SOLUTION
    m = items.merge(orders, on="order_id")
    m = m[m["status"] != "cancelled"]
    m = m.assign(spent=m["quantity"] * m["unit_price"] * (1 - m["discount"]))
    return m.groupby("customer_id", as_index=False).agg(n_orders=("order_id", "nunique"),
                                                        total_spent=("spent", "sum"))
    ### END SOLUTION


customer_summary(orders, items).head()

# %%
grade("w03.customer_summary", customer_summary)

# %% [markdown]
# ## 6. Dates
#
# **Why.** Time is in almost every business table, and many model features are "in the last 30 days" or "per
# month". Text that *looks* like a date cannot be subtracted or grouped by month; a real date can.
#
# **Idea.** `pd.to_datetime(column)` turns text into a **datetime** column (dtype `datetime64`). Then the `.dt`
# accessor gives parts and formats: `.dt.year`, `.dt.month`, `.dt.day_name()`, `.dt.strftime("%Y-%m")` (text like
# `2025-03`). Subtracting two dates gives a duration; `.dt.days` turns it into a number of days. If a value cannot be
# parsed, `errors="coerce"` turns it into `NaT` ("not a time", the date version of a missing value) instead of
# failing. Notebook 11 deals with columns that mix several date formats.
#
# **See it.** Parse the order date and look at orders per weekday.

# %%
order_dates = pd.to_datetime(orders["order_date"])
print(order_dates.dtype, order_dates.min(), order_dates.max())
order_dates.dt.day_name().value_counts()

# %% [markdown]
# **Try it.** How many days passed between each customer's first and last order? Try
# `orders.assign(d=order_dates).groupby("customer_id")["d"].agg(["min", "max"])`, then subtract the two columns and
# use `.dt.days`.

# %%
# Try it.

# %% [markdown]
# ### Exercise 6.1 · Orders per month
#
# Write `monthly_orders(orders)` returning columns `month` (text like `"2025-03"`) and `n_orders`, one row per month
# that has orders, sorted by month from oldest to newest. Parse `order_date` with `pd.to_datetime` rather than
# cutting the text, so the function also works on dates stored in other formats.

# %%
def monthly_orders(orders):
    ### BEGIN SOLUTION
    month = pd.to_datetime(orders["order_date"]).dt.strftime("%Y-%m")
    counts = orders.assign(month=month).groupby("month").size().reset_index(name="n_orders")
    return counts.sort_values("month")
    ### END SOLUTION


monthly_orders(orders).head()

# %%
grade("w03.monthly_orders", monthly_orders)

# %% [markdown]
# ## Quiz
#
# **Q1.** Which description of a DataFrame is right?
#
# - a) Every cell of a DataFrame must have the same type.
# - b) A table of named columns; each column is a Series with its own dtype, and rows share an index.
# - c) A connection to a database table that updates automatically.
# - d) Another name for a Series.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"
### END SOLUTION
quiz("w03.10_q1", answer)

# %% [markdown]
# **Q2.** You want every customer, with their orders where they have any (customers without orders kept, with
# missing values). Which call?
#
# - a) `customers.merge(orders, on="customer_id", how="inner")`
# - b) `pd.concat([customers, orders])`
# - c) `customers.groupby("customer_id")`
# - d) `customers.merge(orders, on="customer_id", how="left")`

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"
### END SOLUTION
quiz("w03.10_q2", answer)

# %% [markdown]
# **Q3.** `orders[orders["channel"] == "web"]` corresponds to which part of SQL?
#
# - a) `WHERE channel = 'web'`
# - b) `SELECT channel`
# - c) `ORDER BY channel`
# - d) `GROUP BY channel`

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"
### END SOLUTION
quiz("w03.10_q3", answer)

# %% [markdown]
# **Q4.** Why is `df["a"] * df["b"]` preferred over `df.apply(lambda r: r["a"] * r["b"], axis=1)`?
#
# - a) `apply` is the fastest way to work row by row.
# - b) They give different numbers.
# - c) The vectorised version runs in compiled code over the whole column, so it is much faster and shorter.
# - d) `iterrows` would be faster than both.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"
### END SOLUTION
quiz("w03.10_q4", answer)

# %% [markdown]
# **Q5.** You run `orders[orders["status"] == "cancelled"]["channel"] = "none"`. What happens to `orders`?
#
# - a) The cancelled rows now have channel `"none"`.
# - b) Nothing: the value is set on a temporary copy (pandas warns). Use `orders.loc[mask, "channel"] = "none"`.
# - c) pandas raises an error and deletes the cancelled rows.
# - d) A new row is added.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"
### END SOLUTION
quiz("w03.10_q5", answer)

# %% [markdown]
# ## Recap
#
# - A **DataFrame** is a table of **Series** (columns), each with one dtype; check `.shape`, `.head()`, `.dtypes`,
#   `.describe()` on every new table.
# - Filtering is a **boolean mask** (`df[cond]`, with `&`, `|`, `~` and brackets); sorting is `sort_values`.
# - New columns come from **vectorised** expressions; avoid loops and `apply` for arithmetic.
# - `groupby(...).agg(name=(column, function))` is `GROUP BY`; `reset_index()` brings the group back as a column.
# - `merge(..., how=...)` is `JOIN`; check the row count after every merge.
# - `pd.to_datetime` and `.dt` turn text into real dates you can group and subtract.
# - Write data code as **functions that return a new table** and never change their input.
#
# ## On the job
#
# A typical day for an ML engineer: a SQL query pulls raw rows out of the warehouse, and pandas turns them into a
# feature table (one row per customer, per day or per machine) that a model can learn from. The functions you
# wrote today (filter, add a column, summarise per customer, count per month) are the building blocks of every
# feature pipeline you will write in week 4, and the habit of returning new tables is what makes them testable
# in week 8.
#
# ## Going further
#
# - Tool guide: [pandas](../docs/tools/pandas.md), with a one-page cheat sheet.
# - The official "10 minutes to pandas": <https://pandas.pydata.org/docs/user_guide/10min.html> and the comparison
#   with SQL: <https://pandas.pydata.org/docs/getting_started/comparison/comparison_with_sql.html>.
# - Next: [11 · Data cleaning and quality checks](11_data_cleaning_quality.ipynb).

# %% [markdown]
# ## Record your progress
#
# Flags: `reading`, `guided` (you passed the graded exercises), `independent` (you solved them without hints or
# solutions), `review` (come back to this).

# %%
from mlcourse.progress import mark

# mark("10", "reading")
# mark("10", "guided")
