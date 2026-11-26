---
title: "SQL (SQLite)"
parent: Tool guides
nav_order: 5
---

# SQL (SQLite)

SQL (Structured Query Language) is how you ask a relational database a question. This guide covers the SQL you
need for Weeks 2 and 3 and for most of a first job: reading tables, filtering, summarising and joining. It uses
**SQLite**, the database engine built into Python, so it works in Google Colab with nothing to install.

## What SQL is, and why every data team uses it

A **relational database** stores data in **tables**: each row is one record (a customer, an order), each column
one attribute with a type (a number, a text, a date). Tables are linked by **keys**:

* a **primary key** identifies a row uniquely (`customers.customer_id`);
* a **foreign key** points to a row of another table (`orders.customer_id` says which customer placed an order).

Almost every company keeps its important data this way: sales, users, events, payments. SQL is the shared
language for it. An analyst uses it to build reports, a data engineer to move data, and an ML engineer to build
training sets, check labels and investigate a strange prediction. The core of SQL has barely changed in 40 years,
so what you learn here keeps paying off.

You *describe* the result you want (which rows, which columns, which totals), and the database works out how to
compute it. That is different from Python, where you write the steps.

### The course database

`data/course/shop.db` is a synthetic (made-up) online shop. Its tables:

| Table | One row is | Key columns |
|---|---|---|
| `customers` | a customer | `customer_id` (PK), `name`, `city`, `signup_date`, `segment`, `email` |
| `products` | a product | `product_id` (PK), `name`, `category`, `price` |
| `orders` | an order | `order_id` (PK), `customer_id` (FK), `order_date`, `status`, `channel` |
| `order_items` | one product line of an order | `order_id` (FK), `product_id` (FK), `quantity`, `unit_price`, `discount` |
| `payments` | a payment | `payment_id` (PK), `order_id` (FK), `amount`, `method`, `paid_at` |
| `support_tickets` | a help request | `ticket_id` (PK), `customer_id` (FK), `opened_at`, `topic`, `resolved_at` |

Dates are text in `YYYY-MM-DD` form. Order `status` is one of `delivered`, `shipped`, `cancelled`, `returned`.

## Opening it

### In Google Colab (the course default)

Run a notebook's setup cell, then:

```python
from mlcourse.sql import sql, tables, schema
tables("shop")                          # list the tables
schema("shop", "orders")                # columns, types, primary key
sql("SELECT * FROM products LIMIT 5")   # run a query; returns a pandas DataFrame
```

`sql(query, db="shop")` opens the database **read-only**, so you cannot damage it. Write longer queries in
triple quotes:

```python
sql("""
SELECT status, COUNT(*) AS n
FROM orders
GROUP BY status
""")
```

Without the course helpers, the standard library does the same:

```python
import sqlite3, pandas as pd
con = sqlite3.connect("data/course/shop.db")
pd.read_sql_query("SELECT * FROM products", con)
```

### On your own computer with VS Code

1. Clone the course repository (see the Git guide) and open the folder in VS Code.
2. In the Extensions panel, install **SQLite Viewer** (to browse tables) or **SQLTools** plus its
   **SQLTools SQLite** driver (to write and run queries with autocomplete).
3. For SQLTools: open the SQLTools panel, *Add new connection*, choose SQLite, and point it to
   `data/course/shop.db`. Open a new `.sql` file, write a query, and run it with the *Run on active connection*
   command. Results appear in a side panel.

### From the command line

Many systems include the `sqlite3` program: `sqlite3 data/course/shop.db`, then type queries ending with `;`.
`.tables` lists tables, `.schema orders` shows a table definition, `.mode column` and `.headers on` make output
readable, `.quit` exits.

### DuckDB (optional)

DuckDB is a fast analytical database that runs inside Python, popular for working with large files. After
`pip install duckdb` it can read the course database directly:

```python
import duckdb
duckdb.sql("INSTALL sqlite; LOAD sqlite;")
duckdb.sql("SELECT status, COUNT(*) FROM sqlite_scan('data/course/shop.db', 'orders') GROUP BY status")
```

Almost all queries in this course run unchanged in DuckDB; date functions differ (see below).

## The features you will use most

### SELECT, FROM, WHERE

```sql
SELECT name, price          -- which columns (* = all)
FROM products               -- which table
WHERE price < 15            -- which rows
```

Conditions: `=`, `!=`, `<`, `<=`, `>`, `>=`; combine with `AND`, `OR`, `NOT`. `AND` binds before `OR`, so use
parentheses when mixing them. Shortcuts:

```sql
WHERE city IN ('Almaty', 'Astana')
WHERE price BETWEEN 10 AND 20             -- inclusive at both ends
WHERE name LIKE 'A%'                      -- % = any text, _ = exactly one character
WHERE order_date >= '2025-01-01'          -- works because dates are YYYY-MM-DD text
```

Text values use single quotes. Keywords are case-insensitive; column and table names are not, in some databases,
so keep them exactly as defined.

### ORDER BY, LIMIT, DISTINCT

```sql
SELECT name, price FROM products ORDER BY price DESC, name LIMIT 5;
SELECT DISTINCT category FROM products;
```

`ORDER BY` sorts (`ASC` by default); without it, rows come back in no guaranteed order, so `LIMIT` alone returns
arbitrary rows. `LIMIT n OFFSET k` skips `k` rows first.

### NULL

`NULL` means unknown or missing. Comparisons with NULL are *unknown*, and `WHERE` keeps only rows where the
condition is *true*. Therefore:

```sql
WHERE email IS NULL                        -- right
WHERE email = NULL                         -- always returns nothing
WHERE city != 'Almaty' OR city IS NULL     -- != alone silently drops NULL cities
COALESCE(city, 'unknown')                  -- replace NULL with a value
```

### Computed columns and AS

```sql
SELECT order_id,
       quantity * unit_price * (1 - discount) AS line_total,
       name || ' (' || city || ')'             AS label
FROM ...
```

Whole-number division truncates in SQLite: `7 / 2` is `3`. Use `7 / 2.0` or `x * 1.0 / y`.
`ROUND(x, 2)` rounds.

### Dates in SQLite

| Expression | Result |
|---|---|
| `date('2025-03-14', '+7 days')` | `'2025-03-21'` |
| `date('2025-03-14', 'start of month')` | `'2025-03-01'` |
| `strftime('%Y-%m', '2025-03-14')` | `'2025-03'` (`%Y` year, `%m` month, `%d` day, `%w` weekday, 0 = Sunday) |
| `julianday('2025-03-14') - julianday('2025-03-01')` | `13.0` (days between) |
| `date('now')` | today |

In PostgreSQL and DuckDB the equivalents are `order_date + INTERVAL 7 DAY`, `strftime(order_date, '%Y-%m')` or
`date_trunc('month', order_date)`, and `order_date - other_date`.

### Aggregates and GROUP BY

```sql
SELECT channel,
       COUNT(*)            AS n_orders,     -- rows
       COUNT(DISTINCT customer_id) AS n_customers
FROM orders
WHERE status != 'cancelled'                 -- filters rows, before grouping
GROUP BY channel
HAVING COUNT(*) > 1000                      -- filters groups, after grouping
ORDER BY n_orders DESC;
```

`COUNT(*)` counts rows; `COUNT(col)`, `SUM`, `AVG`, `MIN`, `MAX` skip NULLs. Every selected column must be
in `GROUP BY` or inside an aggregate. The logical order of a query is
`FROM → WHERE → GROUP BY → HAVING → SELECT → DISTINCT → ORDER BY → LIMIT`, which explains why `WHERE` cannot use
`COUNT(*)` and why `ORDER BY` can use a column alias.

### CASE WHEN

```sql
SELECT CASE WHEN price < 15 THEN 'cheap'
            WHEN price < 40 THEN 'mid'
            ELSE 'premium' END AS band,
       COUNT(*)
FROM products
GROUP BY band;

-- conditional counts, side by side
SELECT channel,
       SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS n_cancelled
FROM orders GROUP BY channel;
```

The first true `WHEN` wins; without `ELSE`, unmatched rows get NULL.

### JOINs

```sql
-- INNER JOIN: only matching pairs
SELECT o.order_id, c.name
FROM orders AS o
JOIN customers AS c ON c.customer_id = o.customer_id;

-- LEFT JOIN: every left row; NULLs where there is no match
SELECT c.customer_id, COUNT(o.order_id) AS n_orders    -- count a right-side column, not *
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id
GROUP BY c.customer_id;

-- anti-join: left rows with no match
SELECT c.customer_id
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id
WHERE o.order_id IS NULL;
```

Chain joins to combine three or more tables. Start from the table whose rows you are counting or summing.

### Grain and fan-out

The **grain** of a result is what one row means. Joining a table to one with *several* matches per key
(an order to its lines) repeats the first table's values once per match, so `SUM` and `COUNT(*)` over them are
inflated. In the shop, payments total 286,986.75, but 636,496.65 after joining `order_items`. Defences: compare
row counts before and after each join, aggregate to the right grain first (in a subquery), and use
`COUNT(DISTINCT ...)` when counting entities.

### Subqueries

```sql
SELECT customer_id, total
FROM (SELECT customer_id, COUNT(*) AS total FROM orders GROUP BY customer_id)
WHERE total >= 5;
```

A subquery in parentheses can stand where a table stands.

### CTEs: naming a step with WITH

A **CTE** (common table expression) is a subquery with a name, written first. It reads top to bottom like a
recipe, and you can check each step on its own by selecting from it.

```sql
WITH monthly AS (
  SELECT strftime('%Y-%m', order_date) AS month, COUNT(*) AS n_orders
  FROM orders
  GROUP BY month
)
SELECT month, n_orders FROM monthly ORDER BY n_orders DESC LIMIT 3;
```

In the shop this gives 2025-12 (615 orders), 2025-11 (558) and 2025-10 (443). Several CTEs are separated by
commas (`WITH a AS (...), b AS (SELECT ... FROM a) SELECT ...`), and a later one may use an earlier one.

### Window functions: a value per row, computed over a group

`GROUP BY` collapses each group to one row. A **window function** keeps every row and adds a column computed
over related rows, its *window*. `OVER (PARTITION BY ... ORDER BY ...)` says which rows (the partition) and in
what order.

```sql
SELECT customer_id, order_date,
       ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date) AS nth_order,
       LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date) AS previous_order
FROM orders
WHERE customer_id = 1;
```

| customer_id | order_date | nth_order | previous_order |
|---|---|---|---|
| 1 | 2025-05-20 | 1 | NULL |
| 1 | 2025-06-20 | 2 | 2025-05-20 |
| 1 | 2025-07-01 | 3 | 2025-06-20 |
| 1 | 2025-08-09 | 4 | 2025-07-01 |
| 1 | 2025-08-29 | 5 | 2025-08-09 |

The functions you will use most:

| Function | Gives | Typical use |
|---|---|---|
| `ROW_NUMBER()` | 1, 2, 3 ... within the partition, no ties | first or latest row per customer |
| `RANK()` / `DENSE_RANK()` | rank with ties (`RANK` skips numbers after a tie) | top 3 products per category |
| `LAG(x)` / `LEAD(x)` | `x` from the previous / next row | days since the previous order |
| `SUM(x) OVER (ORDER BY ...)` | running total | cumulative revenue by month |
| `AVG(x) OVER (... ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)` | moving average | 3-month smoothed trend |

**Latest row per group**, the pattern you will write most often: number the rows in a CTE, then keep row 1.
Window functions cannot go in `WHERE` (they are computed after it), which is why the CTE is needed.

```sql
WITH ranked AS (
  SELECT customer_id, order_id, order_date,
         ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS rn
  FROM orders
)
SELECT customer_id, order_id, order_date FROM ranked WHERE rn = 1;
```

This returns 1,086 rows, one for each customer who has ordered, which is a quick check that it worked:
`SELECT COUNT(DISTINCT customer_id) FROM orders` also gives 1,086.

For machine learning, window functions are how you build "as of" features (the number of orders before each
order, days since the previous one) without looking into the future: the `ORDER BY` inside `OVER` plus a frame
that ends at the current row only sees the past.

## Common errors and how to read them

| Message | What it means | Fix |
|---|---|---|
| `no such table: order` | table name misspelt | check with `tables()`; here it is `orders` |
| `no such column: colour` | column name misspelt, or a text value without quotes | check with `schema()`; quote text: `'Almaty'` |
| `ambiguous column name: customer_id` | two joined tables have that column | prefix it: `o.customer_id` |
| `misuse of aggregate: COUNT()` | an aggregate in `WHERE` | move the condition to `HAVING` |
| `near "FROM": syntax error` | usually a missing or extra comma just before | read the line before the word named |
| `incomplete input` | unclosed quote or parenthesis | count your quotes and brackets |
| no error, but 0 rows | `= NULL`, a typo in a text value (`'Delivered'` vs `'delivered'`), or `NOT IN` with a NULL | test each condition on its own |
| no error, numbers too big | fan-out after a join | compare row counts before and after the join |

When a query surprises you, take it apart: run the `FROM` and joins with `SELECT *` and `LIMIT 20`, check the
row count, then add one clause at a time.

## Cheat sheet

```sql
-- read
SELECT col1, col2 AS alias, expr AS name
FROM table AS t
WHERE cond1 AND (cond2 OR cond3)
ORDER BY col DESC, col2
LIMIT 10 OFFSET 0;

-- filter helpers
x IN (a, b)   x BETWEEN a AND b   x LIKE 'A%'   x IS NULL   x IS NOT NULL   NOT cond

-- summarise
SELECT key, COUNT(*), COUNT(col), COUNT(DISTINCT col), SUM(col), AVG(col), MIN(col), MAX(col)
FROM t WHERE row_cond GROUP BY key HAVING group_cond;

-- categories and conditional counts
CASE WHEN c1 THEN v1 WHEN c2 THEN v2 ELSE v3 END
SUM(CASE WHEN cond THEN 1 ELSE 0 END)

-- combine
FROM a JOIN b ON b.k = a.k            -- only matches
FROM a LEFT JOIN b ON b.k = a.k       -- all of a
... LEFT JOIN b ... WHERE b.k IS NULL -- rows of a with no match

-- dates (SQLite)
strftime('%Y-%m', d)   date(d, '+7 days')   julianday(d2) - julianday(d1)

-- NULL and numbers
COALESCE(x, 0)   ROUND(x, 2)   x * 1.0 / y

-- steps and windows
WITH step1 AS (SELECT ...), step2 AS (SELECT ... FROM step1) SELECT ... FROM step2;
ROW_NUMBER() OVER (PARTITION BY k ORDER BY d DESC)        -- then WHERE rn = 1 in an outer query
LAG(x) OVER (PARTITION BY k ORDER BY d)   SUM(x) OVER (ORDER BY d)   RANK() OVER (ORDER BY x DESC)
```

Query order to remember: **FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT**.

Before you trust a number: state the grain, state the definition, check the row count, reconcile the total.

## Where next

* Course notebooks: [05 · Databases and SELECT](../notebooks/05_sql_select.html),
  [06 · Aggregation](../notebooks/06_sql_aggregation.html), [07 · JOINs](../notebooks/07_sql_joins.html),
  [08 · Lab](../notebooks/08_lab_sql_business_questions.html); [09 · Subqueries, CTEs and window functions](../notebooks/09_sql_windows_ctes.html).
* SQLite documentation: <https://www.sqlite.org/lang.html> (the SQL language) and
  <https://www.sqlite.org/lang_datefunc.html> (date functions).
* DuckDB documentation: <https://duckdb.org/docs/>.
* PostgreSQL tutorial, for the database you are most likely to meet at work:
  <https://www.postgresql.org/docs/current/tutorial.html>.
