---
title: "pandas"
parent: Tool guides
nav_order: 6
---

# pandas

pandas is the Python library for working with tables. If data is in a database, you use SQL to get it out; once
it is in Python, you use pandas to look at it, clean it, combine it and turn it into the features a model learns
from. This guide covers what pandas is, how to load data, the 20% of features you will use 80% of the time (each
with its SQL equivalent), the errors beginners meet most often, and a one-page cheat sheet. Notebooks 10-12 teach
the same material hands-on; this page is the reference to come back to.

## What pandas is, and why teams use it

A pandas **DataFrame** is a table held in memory: named columns, each with one data type (its **dtype**), and rows
labelled by an **index**. A single column is a **Series**. Almost every Python data tool speaks DataFrames:
scikit-learn accepts them, matplotlib plots them, and every file format you will meet (CSV, Excel, Parquet, JSON,
SQL results) can be read into one with a single call.

Teams use pandas because it makes the common steps of data work short and readable:

* **exploring**: how many rows, which values occur, what is missing;
* **cleaning**: fixing types, missing values, duplicates, inconsistent text and dates;
* **transforming**: new columns, filters, group summaries, joins;
* **handing over**: to a model (`model.fit(df[features], df[target])`), a plot, or a file.

Its limits are worth knowing early. pandas holds the whole table in memory, so it suits data up to a few million
rows on a laptop (or a Colab runtime). For larger data, teams filter and aggregate in the database with SQL first,
or use tools built for scale. And pandas code is easy to write in slow ways (row-by-row loops); the
[vectorised code](#vectorised-code-versus-loops-and-apply) section shows the fast way.

## Opening it

### In Google Colab

pandas is pre-installed. Import it with the conventional short name:

```python
import pandas as pd
import numpy as np    # pandas is built on NumPy; you will often want both
print(pd.__version__)
```

The course notebooks' setup cell also installs the course's `requirements.txt`, which asks for pandas 2.1 or newer.
Everything in this guide works on pandas 2.x and 3.x; where the two differ, the guide says so.

### On your own computer

In a terminal, inside the course folder and with your virtual environment active (Week 10 explains these steps):

```bash
python -m pip install -r requirements.txt     # installs pandas with the rest of the course
python -c "import pandas; print(pandas.__version__)"
```

In VS Code or Jupyter, a DataFrame as the last line of a cell is shown as a formatted table; `print(df)` gives a
plain-text version.

## The features you will use most

The examples use the course's shop database. Load the tables once:

```python
import pandas as pd
from mlcourse.sql import connect          # course helper: read-only connection to data/course/shop.db

with connect("shop") as con:
    orders = pd.read_sql_query("SELECT * FROM orders", con)
    items = pd.read_sql_query("SELECT * FROM order_items", con)
    products = pd.read_sql_query("SELECT * FROM products", con)
```

Outside the course, any database connection works the same way: `pd.read_sql_query(query, connection)`.

### Reading and writing files

```python
df = pd.read_csv("data.csv")                                   # comma-separated text
df = pd.read_csv("data.csv", na_values=["-", "N/A"])           # extra codes that mean "missing"
df = pd.read_csv("data.csv", dtype={"zip": str})               # keep a column as text (leading zeros!)
df = pd.read_csv("data.csv", parse_dates=["order_date"])       # parse a column of ISO dates while reading
df.to_csv("clean.csv", index=False)                            # write; index=False skips the row labels
```

`read_csv` treats an empty field, `"NA"`, `"N/A"`, `"NaN"`, `"null"` and a few other strings as missing by
default. Anything else a system uses for "unknown" (`"-"`, `"?"`, `-1`) must be declared with `na_values` or fixed
afterwards.

### First look at a table

```python
df.shape            # (rows, columns)
df.head()           # first 5 rows; df.tail(), df.sample(5) for others
df.dtypes           # type of each column
df.info()           # dtypes, non-missing counts and memory in one view
df.describe()       # count, mean, std, min, quartiles, max of numeric columns
df["status"].value_counts(dropna=False)    # how often each value occurs, including missing
df["customer_id"].nunique()                # number of distinct values
```

Run these on every new table before doing anything else. A numeric-looking column with dtype `object` (pandas 2) or
`str` (pandas 3) contains at least one value that is not a number.

### Selecting columns and filtering rows

| SQL | pandas |
|---|---|
| `SELECT a, b FROM t` | `t[["a", "b"]]` |
| `WHERE x > 3` | `t[t["x"] > 3]` |
| `WHERE x > 3 AND y = 'z'` | `t[(t["x"] > 3) & (t["y"] == "z")]` |
| `WHERE x = 1 OR x = 2` / `IN (1, 2)` | `t[t["x"].isin([1, 2])]` |
| `WHERE NOT ...` | `t[~(condition)]` |
| `WHERE x IS NULL` | `t[t["x"].isna()]` |
| `WHERE name LIKE '%cable%'` | `t[t["name"].str.contains("cable")]` |
| `WHERE x BETWEEN 1 AND 5` | `t[t["x"].between(1, 5)]` |

A condition such as `t["x"] > 3` produces a **boolean mask** (a Series of `True`/`False`); indexing with it keeps
the `True` rows. Combine masks with `&`, `|` and `~`, and put each condition in brackets: `&` binds more tightly
than `>`, so `t["x"] > 3 & t["y"] == "z"` is evaluated in the wrong order.

`.loc` selects rows and columns together and is the way to **change** a subset:

```python
recent = orders.loc[orders["order_date"] >= "2025-07-01", ["order_id", "status"]]
orders.loc[orders["status"] == "cancelled", "channel"] = "none"   # changes those cells in orders
```

`.iloc` selects by position: `df.iloc[0]` is the first row, `df.iloc[:10, :3]` the first ten rows and three columns.

### Sorting and the top rows

```python
products.sort_values("price", ascending=False).head(5)                          # ORDER BY price DESC LIMIT 5
products.sort_values(["category", "price"], ascending=[True, False])          # two keys
products.nlargest(3, "price")                                                   # shortcut for top values
```

Add a tie-breaking column (an id) when the order must be reproducible.

### New columns

```python
items["line_total"] = items["quantity"] * items["unit_price"] * (1 - items["discount"])   # in place
items2 = items.assign(big_discount=items["discount"] >= 0.1)                              # returns a new table
```

Use `df["c"] = ...` on your own working table, and `df.assign(c=...)` inside functions so the caller's table is not
changed. Conditional values: `np.where(cond, value_if_true, value_if_false)` (SQL's `CASE WHEN`), or
`series.where(cond, other)` which keeps values where `cond` is `True` and uses `other` elsewhere.

```python
items["size"] = np.where(items["quantity"] >= 3, "bulk", "single")
```

### Vectorised code versus loops and apply

Arithmetic and comparisons on whole columns run inside pandas' compiled code. A Python loop, `iterrows`, or
`df.apply(f, axis=1)` calls Python once per row and is many times slower (in notebook 10 the vectorised line
total was roughly 40-80 times faster than `apply` on 8,299 rows, and the gap grows with size). Reach for `apply`
only when no vectorised operation exists, which is rare: `.str` methods cover text, `.dt` covers dates, `np.where`
and `np.select` cover conditions.

### Missing values

```python
df.isna().sum()                       # missing per column
df["city"].fillna("Unknown")          # replace missing (SQL COALESCE)
df.dropna(subset=["quantity"])        # drop rows where quantity is missing
df["quantity"].mask(df["quantity"] == -1)   # turn a code into a real missing value
```

Missing numbers appear as `NaN`, missing dates as `NaT`, missing text as `NaN` or `None`. Any comparison with a
missing value is `False`, so `df[df["x"] > 0]` silently drops rows where `x` is missing. Before filling a gap,
decide what missing *means*, and write the decision down (notebook 11 discusses why).

### Duplicates

```python
df.duplicated().sum()                          # exact duplicate rows (copies after the first)
df.drop_duplicates().reset_index(drop=True)    # remove them and renumber the index
df["order_id"].duplicated().sum()              # repeated keys: investigate, do not just drop
df["order_id"].is_unique                       # True if no key repeats
```

### groupby and aggregation

`df.groupby("g")` splits the table by the values of `g`, applies a summary to each part, and combines the results:
SQL's `GROUP BY`.

```python
orders.groupby("channel").size()                         # COUNT(*) per channel (a Series)
orders.groupby("channel").size().reset_index(name="n")   # ... as a table with columns channel, n
items.groupby("product_id")["quantity"].sum()            # SUM(quantity) per product
orders.groupby("customer_id").agg(                       # several named summaries at once
    n_orders=("order_id", "nunique"),
    first_order=("order_date", "min"),
    last_order=("order_date", "max"),
).reset_index()
orders.groupby(["channel", "status"]).size().unstack(fill_value=0)   # a cross-table
```

Common functions in `agg`: `"count"` (non-missing values), `"size"` (rows), `"sum"`, `"mean"`, `"median"`, `"min"`,
`"max"`, `"nunique"`, `"std"`. The group columns end up in the index; `reset_index()` or `as_index=False` turns them
back into ordinary columns. To filter groups afterwards (SQL `HAVING`), filter the result:
`summary[summary["n_orders"] >= 5]`.

### merge (joins)

```python
items.merge(orders, on="order_id")                          # INNER JOIN on a shared column
items.merge(products, on="product_id", how="left")          # LEFT JOIN
customers.merge(orders, left_on="id", right_on="customer_id")   # different column names
customers[~customers["customer_id"].isin(orders["customer_id"])]   # anti-join: customers with no orders
```

`how` is `"inner"` (default), `"left"`, `"right"` or `"outer"`. Check the row count after every merge. If a key is
not unique on the side you expected, rows multiply (the "fan-out" from Week 2). `validate="many_to_one"` makes
pandas raise an error instead of silently multiplying: `items.merge(orders, on="order_id", validate="many_to_one")`.
To stack tables with the same columns on top of each other (SQL `UNION ALL`), use `pd.concat([a, b])`.

### Window-style operations

| SQL | pandas |
|---|---|
| `ROW_NUMBER() OVER (PARTITION BY g ORDER BY x)` | `df.sort_values("x").groupby("g").cumcount() + 1` |
| `RANK() OVER (ORDER BY x DESC)` | `df["x"].rank(method="min", ascending=False)` |
| `SUM(x) OVER (ORDER BY t)` | `df.sort_values("t")["x"].cumsum()` |
| `SUM(x) OVER (PARTITION BY g)` | `df.groupby("g")["x"].transform("sum")` |
| `LAG(x) OVER (ORDER BY t)` | `df.sort_values("t")["x"].shift(1)` |
| top N per group | `df.sort_values("x", ascending=False).groupby("g").head(N)` |

`transform` is the key idea: it returns one value per *original row* (like a window function), whereas `agg`
returns one value per group.

### Dates

```python
orders["order_date"] = pd.to_datetime(orders["order_date"])          # text -> datetime64
orders["order_date"].dt.year, orders["order_date"].dt.month         # parts
orders["order_date"].dt.day_name()                                   # "Monday", ...
orders["order_date"].dt.strftime("%Y-%m")                            # text "2025-03"
orders["order_date"].dt.to_period("M")                               # a monthly period
(orders["order_date"].max() - orders["order_date"]).dt.days          # days between dates
pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")                # one known format; others become NaT
```

Format codes: `%Y` year, `%m` month number, `%d` day, `%B` month name, `%H:%M` hours and minutes. When a column
mixes formats, parse each format explicitly with `errors="coerce"` and combine the attempts with `fillna`. Avoid
`format="mixed"` with `dayfirst=True` on such data: it reads ISO dates such as `2025-03-04` day first as well,
giving 3 April (notebook 11 shows this).

### Text

```python
s.str.strip()          # remove spaces at both ends
s.str.lower()          # also .upper(), .title()
s.str.replace("-", " ")
s.str.contains("cable", case=False)
s.str.split(" ").str[0]          # first word
s.str.len()
```

`.str` methods skip missing values, so `NaN` stays `NaN`.

### Writing data functions

From Week 3 on, write data steps as functions that take a DataFrame and return a **new** one:

```python
def delivered_revenue_by_category(items, orders, products):
    m = items.merge(orders, on="order_id").merge(products, on="product_id")
    m = m[m["status"] == "delivered"]
    m = m.assign(revenue=m["quantity"] * m["unit_price"] * (1 - m["discount"]))
    return m.groupby("category", as_index=False)["revenue"].sum()
```

Filtering, `sort_values`, `assign`, `merge`, `groupby` and `drop` all return new objects, so a function built from
them never changes its inputs. Such functions can be tested on small hand-made tables (Week 8) and chained into a
pipeline (the Week 3 lab).

## Common errors and how to read them

**`KeyError: 'Status'`.** No column has that exact name. Column names are case-sensitive and may contain spaces.
Check `df.columns.tolist()`.

**`ValueError: The truth value of a Series is ambiguous. Use a.empty, a.bool(), a.item(), a.any() or a.all().`**
You used `and`, `or`, `not` or an `if` on a whole column. Use `&`, `|`, `~` between conditions; use `.any()` or
`.all()` if you really need a single `True`/`False`.

**`TypeError: '>' not supported between instances of 'str' and 'int'`** (or a wrong result from `.mean()`). The
column is text, not numbers. Find the culprit with `df[pd.to_numeric(df["x"], errors="coerce").isna()]["x"]
.unique()`, then fix it with `na_values` or `pd.to_numeric(..., errors="coerce")`.

**`SettingWithCopyWarning` (pandas 2) or `ChainedAssignmentError` (pandas 3).** You assigned through two
indexing steps, such as `df[df["x"] > 0]["y"] = 1`. The value went into a temporary copy and `df` did not change.
Write it as one step: `df.loc[df["x"] > 0, "y"] = 1`. If you meant to work on a separate table, make it explicit
with `.copy()`: `sub = df[df["x"] > 0].copy()`.

**`MergeError` or a merge that has more rows than expected.** A key is duplicated on a side you assumed was unique.
Check with `df["key"].is_unique` and use `validate="many_to_one"` or `"one_to_one"` in `merge`.

**A merge with fewer rows than expected.** Keys did not match: different dtypes (`1` versus `"1"`), stray spaces,
or different case. Compare `left["key"].dtype` with `right["key"].dtype` and look at a few unmatched keys with an
anti-join.

**`DateParseError` / `ValueError: time data "04/03/2025" doesn't match format "%Y-%m-%d"`.** A date in a format you
did not expect. Use `errors="coerce"` to see which values fail (`NaT`), then handle each format.

**Columns become `float` after a merge or a fill.** Whole-number columns turn into `float64` as soon as they hold a
`NaN`, because the classic integer dtype cannot store missing values. This is normal. If you need integers with
gaps, use the nullable dtype: `df["x"].astype("Int64")`.

**`MemoryError` or a very slow notebook.** The table is too big for memory, or a loop/`apply` runs over many rows.
Filter and aggregate in SQL before loading, read only the columns you need (`usecols=`), and replace row-by-row
code with vectorised operations.

## Cheat sheet

```python
import pandas as pd, numpy as np

# load / save
df = pd.read_csv(path, na_values=["-"], parse_dates=["date"]);  df.to_csv(path, index=False)
df = pd.read_sql_query("SELECT ...", con)

# look
df.shape; df.head(); df.dtypes; df.info(); df.describe()
df["c"].value_counts(dropna=False); df["c"].nunique(); df.isna().sum()

# select / filter / sort
df[["a", "b"]]; df[df["x"] > 3]; df[(df.a > 1) & (df.b == "z")]; df[df["c"].isin([1, 2])]
df.loc[mask, ["a", "b"]]; df.iloc[:5]
df.sort_values(["a", "b"], ascending=[False, True]).head(10)

# new columns
df.assign(c=df["a"] * df["b"]); df["flag"] = df["x"] >= 0.1
np.where(cond, "yes", "no"); s.where(cond, other); s.mask(cond)

# missing / duplicates
df["c"].fillna(0); df.dropna(subset=["c"]); df.drop_duplicates().reset_index(drop=True)
df["id"].duplicated().sum(); df["id"].is_unique

# group
df.groupby("g").size().reset_index(name="n")
df.groupby("g", as_index=False).agg(total=("x", "sum"), n=("id", "nunique"))
df.groupby("g")["x"].transform("sum")            # group value on every row
df.sort_values("t").groupby("g").cumcount() + 1  # ROW_NUMBER
df.sort_values("x", ascending=False).groupby("g").head(3)   # top 3 per group

# combine
a.merge(b, on="k", how="left", validate="many_to_one"); pd.concat([a, b])
a[~a["k"].isin(b["k"])]                          # anti-join

# dates and text
pd.to_datetime(s, format="%Y-%m-%d", errors="coerce"); s.dt.strftime("%Y-%m"); s.dt.days
s.str.strip().str.title(); s.str.contains("x", case=False)

# checks (validation)
assert df["id"].is_unique
assert (df["price"] > 0).all()
assert df["status"].isin({"delivered", "shipped", "cancelled", "returned"}).all()
```

| SQL | pandas |
|---|---|
| `SELECT a, b` | `df[["a", "b"]]` |
| `WHERE` | `df[mask]` |
| `ORDER BY ... LIMIT n` | `sort_values(...).head(n)` |
| `GROUP BY` + aggregates | `groupby(...).agg(...)` |
| `HAVING` | filter the grouped result |
| `JOIN` / `LEFT JOIN` | `merge(how="inner" / "left")` |
| `UNION ALL` | `pd.concat` |
| `CASE WHEN` | `np.where`, `np.select` |
| `COALESCE` | `fillna` |
| `COUNT(DISTINCT x)` | `nunique` |
| window functions | `transform`, `cumsum`, `cumcount`, `shift`, `rank` |

## Where next

* "10 minutes to pandas", the official quick tour: <https://pandas.pydata.org/docs/user_guide/10min.html>.
* "Comparison with SQL", the official translation guide:
  <https://pandas.pydata.org/docs/getting_started/comparison/comparison_with_sql.html>.
* The user guide chapters on missing data, group by, merging and time series:
  <https://pandas.pydata.org/docs/user_guide/index.html>.
* Copy-on-Write (why chained assignment does not work in pandas 3):
  <https://pandas.pydata.org/docs/user_guide/copy_on_write.html>.
* In this course: notebook 10 (pandas essentials), notebook 11 (cleaning and validation), the Week 3 lab, and the
  [SQL (SQLite)](sql.html) guide for the database side.
