# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/07_sql_joins.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 07 · JOINs and the grain of a table
#
# **Week 2 · lesson · about 100 minutes**
#
# So far each query read one table. But the customer's name is in `customers`, the order date in `orders`, the
# product category in `products`. Answering "revenue per category" or "which customers never ordered" means
# **joining** tables. Joins are also where most wrong numbers in real analyses come from, so this notebook spends
# as much time on *checking* a join as on writing one.
#
# **What you will learn**
#
# - `INNER JOIN` and `LEFT JOIN`, and when each one silently drops or keeps rows;
# - joining three tables;
# - the **grain** of a result (what one row means) and **fan-out** (double counting after a join);
# - **anti-joins**: rows with *no* match, such as customers who never ordered;
# - a first subquery: aggregate, then filter the aggregate.
#
# **What you need:** notebooks 05 and 06.
#
# **How grading works:** each grader runs your query on two databases and also checks for the classic join
# mistakes (dropped rows, double counting) and names them if it finds them.

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
from mlcourse.sql import sql, tables, schema

# %% [markdown]
# ## 1. INNER JOIN: match rows by a key
#
# **Why.** An order row only says `customer_id = 17`. To show the customer's name next to the order, you need
# the matching row of `customers`.
#
# **Idea.** A join pairs rows of two tables whose keys match:
#
# ```sql
# SELECT o.order_id, o.order_date, c.name
# FROM orders AS o
# JOIN customers AS c ON c.customer_id = o.customer_id
# ```
#
# - `orders AS o` gives the table a short **alias**; `o.order_date` then means "the `order_date` of `orders`".
#   Aliases are needed whenever two tables have a column with the same name (both have `customer_id`).
# - `ON` states the matching rule: the foreign key `orders.customer_id` equals the primary key
#   `customers.customer_id` (look back at the ER diagram in notebook 05).
# - `JOIN` on its own means `INNER JOIN`: only pairs that match are kept.
#
# Every order has a customer, so this join returns exactly 4,744 rows, one per order.

# %%
sql("""
SELECT o.order_id, o.order_date, c.name, c.city
FROM orders AS o
JOIN customers AS c ON c.customer_id = o.customer_id
LIMIT 5
""")

# %% [markdown]
# **Try it.** Remove `o.` from `o.order_id` (it still works: only `orders` has that column). Then remove `c.`
# in front of `customer_id` in the `ON` line and read the error `ambiguous column name`.

# %%
sql("""
SELECT o.order_id, o.order_date, c.name, c.city
FROM orders AS o
JOIN customers AS c ON c.customer_id = o.customer_id
LIMIT 5
""")

# %% [markdown]
# ### Exercise 1 · Orders with names
#
# Return `order_id`, `order_date` and the customer's `name` for every order placed in **January 2025**.

# %%
### BEGIN SOLUTION
query = """
SELECT o.order_id, o.order_date, c.name
FROM orders AS o
JOIN customers AS c ON c.customer_id = o.customer_id
WHERE o.order_date BETWEEN '2025-01-01' AND '2025-01-31'
"""
### STARTER
# Write your query between the triple quotes, then run this cell and the next one.
query = """

"""
### END SOLUTION
sql(query) if query.strip() else print("(no query yet)")

# %%
grade("w02.orders_with_names", query)

# %% [markdown]
# ## 2. LEFT JOIN: keep everything on the left
#
# **Why.** "Orders per customer" must include customers with **zero** orders. An inner join drops them,
# because they have no matching row, and the report quietly loses 114 customers.
#
# **Idea.** `LEFT JOIN` keeps **every row of the left table** (the one after `FROM`). Where there is no match,
# the right table's columns are filled with NULL:
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c07-01.svg" alt="INNER JOIN keeps only customers who have orders; LEFT JOIN keeps every customer and fills the order columns with NULL for customers without orders" style="max-width:100%">
#
# `customers LEFT JOIN orders` returns 4,858 rows: 4,744 orders plus one NULL-filled row for each of the 114
# customers who never ordered.
#
# Counting after a LEFT JOIN has one trap. `COUNT(*)` counts that NULL-filled row as 1, so a customer with no
# orders would show 1. Count a column from the right table, `COUNT(o.order_id)`, which skips NULLs and gives 0.

# %%
sql("""
SELECT c.customer_id, c.name, o.order_id
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id
WHERE c.customer_id <= 12
""")

# %% [markdown]
# **Try it.** Change `LEFT JOIN` to `JOIN`. Which customers disappear? (Look for rows where `order_id` was
# empty.)

# %%
sql("""
SELECT c.customer_id, c.name, o.order_id
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id
WHERE c.customer_id <= 12
""")

# %% [markdown]
# ### Exercise 2 · Orders per customer
#
# Return `customer_id`, `name` and the **number of orders** of **every** customer, including those with none
# (they should show 0).

# %%
### BEGIN SOLUTION
query = """
SELECT c.customer_id, c.name, COUNT(o.order_id) AS n_orders
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.name
"""
### STARTER
# Write your query between the triple quotes, then run this cell and the next one.
query = """

"""
### END SOLUTION
sql(query) if query.strip() else print("(no query yet)")

# %%
grade("w02.orders_per_customer", query)

# %% [markdown]
# ## 3. Anti-joins: rows with no match
#
# **Why.** "Customers who signed up but never ordered", "orders that were never paid", "products nobody bought":
# finding what is *missing* is a daily task, and the reason for many marketing e-mails.
#
# **Idea.** An **anti-join** keeps the left rows that have **no** match. The safest way to write it is a LEFT JOIN
# followed by a test that the right side is NULL:
#
# ```sql
# SELECT c.customer_id
# FROM customers AS c
# LEFT JOIN orders AS o ON o.customer_id = c.customer_id
# WHERE o.order_id IS NULL
# ```
#
# Test a column that is never NULL in a real match, such as the right table's primary key.
#
# You will also see `WHERE customer_id NOT IN (SELECT customer_id FROM orders)`. It works here (it also returns
# 114), but it has a trap: if the list inside the parentheses contains a single NULL, `NOT IN` is never true and
# the query returns **nothing**, for the same reason `= NULL` never matches (notebook 05). The LEFT JOIN form has
# no such trap.

# %%
sql("""
SELECT COUNT(*) AS n_never_ordered
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id
WHERE o.order_id IS NULL
""")

# %% [markdown]
# **Try it.** See the `NOT IN` trap for yourself: run the cell below, which adds a NULL to the list with
# `UNION SELECT NULL`. It returns 0 rows even though 114 customers never ordered.

# %%
sql("""
SELECT COUNT(*) AS n
FROM customers
WHERE customer_id NOT IN (SELECT customer_id FROM orders UNION SELECT NULL)
""")

# %% [markdown]
# ### Exercise 3 · Customers who never ordered
#
# Return `customer_id` and `name` of customers who have **no orders at all**.

# %%
### BEGIN SOLUTION
query = """
SELECT c.customer_id, c.name
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id
WHERE o.order_id IS NULL
"""
### STARTER
# Write your query between the triple quotes, then run this cell and the next one.
query = """

"""
### END SOLUTION
sql(query) if query.strip() else print("(no query yet)")

# %%
grade("w02.never_ordered", query)

# %% [markdown]
# ## 4. Joining three tables
#
# **Why.** Revenue per category needs the line amounts (`order_items`), the category (`products`) and the order
# status (`orders`): three tables.
#
# **Idea.** Chain joins. Each `JOIN ... ON` adds one table, matched on its key:
#
# ```sql
# FROM order_items AS oi
# JOIN products AS p ON p.product_id = oi.product_id
# JOIN orders   AS o ON o.order_id   = oi.order_id
# ```
#
# Start from the table whose rows you want to count or sum (here, order lines), then join "outwards" to the
# tables that describe them. Each `products` row and each `orders` row matches many lines, but each line matches
# exactly one product and one order, so the result still has one row per line: 8,299 rows.
#
# Throughout this notebook, a line's amount is `quantity * unit_price * (1 - discount)`, as in notebook 05.

# %%
sql("""
SELECT oi.order_id, o.order_date, o.status, p.name, p.category, oi.quantity
FROM order_items AS oi
JOIN products AS p ON p.product_id = oi.product_id
JOIN orders   AS o ON o.order_id   = oi.order_id
LIMIT 6
""")

# %% [markdown]
# **Try it.** Add `c.name AS customer` by joining a fourth table: `JOIN customers AS c ON c.customer_id =
# o.customer_id`.

# %%
sql("""
SELECT oi.order_id, o.order_date, o.status, p.name, p.category, oi.quantity
FROM order_items AS oi
JOIN products AS p ON p.product_id = oi.product_id
JOIN orders   AS o ON o.order_id   = oi.order_id
LIMIT 6
""")

# %% [markdown]
# ### Exercise 4 · Order lines with product names
#
# For orders placed in **December 2025**, return `order_id`, the product `name` and the `quantity` of each line.

# %%
### BEGIN SOLUTION
query = """
SELECT oi.order_id, p.name, oi.quantity
FROM order_items AS oi
JOIN products AS p ON p.product_id = oi.product_id
JOIN orders   AS o ON o.order_id   = oi.order_id
WHERE o.order_date BETWEEN '2025-12-01' AND '2025-12-31'
"""
### STARTER
# Write your query between the triple quotes, then run this cell and the next one.
query = """

"""
### END SOLUTION
sql(query) if query.strip() else print("(no query yet)")

# %%
grade("w02.order_lines_named", query)

# %% [markdown]
# ### Exercise 5 · Revenue per category
#
# Return each product `category` and the **sum of line amounts** in it, **excluding cancelled orders**.

# %%
### BEGIN SOLUTION
query = """
SELECT p.category, SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) AS revenue
FROM order_items AS oi
JOIN products AS p ON p.product_id = oi.product_id
JOIN orders   AS o ON o.order_id   = oi.order_id
WHERE o.status != 'cancelled'
GROUP BY p.category
"""
### STARTER
# Write your query between the triple quotes, then run this cell and the next one.
query = """

"""
### END SOLUTION
sql(query) if query.strip() else print("(no query yet)")

# %%
grade("w02.revenue_by_category", query)

# %% [markdown]
# ## 5. The grain of a result, and fan-out
#
# **Why.** This is the single most expensive SQL mistake in industry: a join quietly repeats rows, a `SUM` adds
# the repeats, and a report shows revenue twice as high as the truth. Nobody gets an error.
#
# **Idea.** The **grain** of a table or result is *what one row means*: "one customer", "one order", "one order
# line". Before you aggregate, say the grain out loud.
#
# When you join a table to another that has **several** matching rows per key, the result takes the finer grain,
# and every value from the coarser table is **repeated** once per match. That is **fan-out**:
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c07-02.svg" alt="Fan-out: one payment of 30 joined to an order with three order lines becomes three rows, so SUM(amount) counts 90 instead of 30" style="max-width:100%">
#
# On our data, payments total 286,986.75. Join payments to `order_items` (to get "more detail") and
# `SUM(amount)` becomes 636,496.65, more than double, because each payment now appears once per line of its order.
#
# The defence is a habit, not a trick:
#
# 1. Write down the grain you want in the result.
# 2. **Compare row counts** before and after each join. If the count grows when you did not expect it, you fanned out.
# 3. Aggregate at the right grain: per order first, then per channel; or use `COUNT(DISTINCT ...)`.

# %%
# Each (SELECT ...) in parentheses is a small query that returns one number; section 6 explains this.
sql("""
SELECT
  (SELECT COUNT(*) FROM payments)                                   AS payment_rows,
  (SELECT COUNT(*) FROM payments p JOIN order_items oi ON oi.order_id = p.order_id) AS after_join,
  (SELECT SUM(amount) FROM payments)                                AS true_total,
  (SELECT SUM(p.amount) FROM payments p JOIN order_items oi ON oi.order_id = p.order_id) AS fanned_total
""")

# %% [markdown]
# **Try it.** In the cell below, `COUNT(*)` counts joined rows (one per order, so per-city order
# counts). Change it to `COUNT(DISTINCT c.customer_id)` and compare: now you count customers.

# %%
sql("""
SELECT c.city, COUNT(*) AS n
FROM customers AS c
JOIN orders AS o ON o.customer_id = c.customer_id
WHERE c.city IS NOT NULL
GROUP BY c.city
""")

# %% [markdown]
# ### Exercise 6 · Customers with orders, per city
#
# For each `city` (skip unknown cities), return the city and the **number of customers** there who placed at
# least one order.

# %%
### BEGIN SOLUTION
query = """
SELECT c.city, COUNT(DISTINCT c.customer_id) AS n_customers
FROM customers AS c
JOIN orders AS o ON o.customer_id = c.customer_id
WHERE c.city IS NOT NULL
GROUP BY c.city
"""
### STARTER
# Write your query between the triple quotes, then run this cell and the next one.
query = """

"""
### END SOLUTION
sql(query) if query.strip() else print("(no query yet)")

# %%
grade("w02.customers_per_city_with_orders", query)

# %% [markdown]
# ### Exercise 7 · Order values
#
# Change the grain from *line* to *order*: return `order_id` and the **total amount of the order** (the sum of its
# line amounts), one row per order that has lines.

# %%
### BEGIN SOLUTION
query = """
SELECT order_id, SUM(quantity * unit_price * (1 - discount)) AS order_value
FROM order_items
GROUP BY order_id
"""
### STARTER
# Write your query between the triple quotes, then run this cell and the next one.
query = """

"""
### END SOLUTION
sql(query) if query.strip() else print("(no query yet)")

# %%
grade("w02.order_values", query)

# %% [markdown]
# ### Exercise 8 · Average order value per channel
#
# For each `channel`, return the **average value of an order** (not of an order line), **excluding cancelled
# orders**. An order's value is the sum of its line amounts.

# %%
### BEGIN SOLUTION
query = """
SELECT o.channel,
       SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) / COUNT(DISTINCT o.order_id) AS avg_order_value
FROM order_items AS oi
JOIN orders AS o ON o.order_id = oi.order_id
WHERE o.status != 'cancelled'
GROUP BY o.channel
"""
### STARTER
# Write your query between the triple quotes, then run this cell and the next one.
query = """

"""
### END SOLUTION
sql(query) if query.strip() else print("(no query yet)")

# %%
grade("w02.avg_order_value_by_channel", query)

# %% [markdown]
# ### Exercise 9 · Money received per channel
#
# Return each order `channel` and the **total amount of payments** for orders from that channel.

# %%
### BEGIN SOLUTION
query = """
SELECT o.channel, SUM(p.amount) AS paid
FROM payments AS p
JOIN orders AS o ON o.order_id = p.order_id
GROUP BY o.channel
"""
### STARTER
# Write your query between the triple quotes, then run this cell and the next one.
query = """

"""
### END SOLUTION
sql(query) if query.strip() else print("(no query yet)")

# %%
grade("w02.paid_per_channel", query)

# %% [markdown]
# ## 6. Aggregate first, then filter: a subquery
#
# **Why.** "Customers who spent more than 1,000" needs a per-customer total, then a filter on it. `HAVING` can do
# it, but often you want to treat the totals as a table of their own: join it, filter it, average it.
#
# **Idea.** A query in parentheses can stand where a table stands. The inner query builds a table at the grain you
# need (one row per customer); the outer query uses it:
#
# ```sql
# SELECT customer_id, total
# FROM (
#     SELECT o.customer_id, SUM(...) AS total
#     FROM ...
#     GROUP BY o.customer_id
# )
# WHERE total > 1000
# ```
#
# This "build the right grain, then use it" pattern is how you avoid fan-out in bigger queries. In Week 3 you
# will write the same thing more readably with `WITH` (a CTE).

# %%
sql("""
SELECT COUNT(*) AS n_customers, AVG(n_orders) AS avg_orders
FROM (
    SELECT customer_id, COUNT(*) AS n_orders
    FROM orders
    GROUP BY customer_id
)
""")

# %% [markdown]
# **Try it.** Add `WHERE n_orders >= 5` after the closing parenthesis. How many customers placed five or
# more orders?

# %%
sql("""
SELECT COUNT(*) AS n_customers, AVG(n_orders) AS avg_orders
FROM (
    SELECT customer_id, COUNT(*) AS n_orders
    FROM orders
    GROUP BY customer_id
)
""")

# %% [markdown]
# ### Exercise 10 · Big spenders
#
# Count only **delivered or shipped** orders. Return `customer_id` and `total` (the sum of their line amounts)
# for customers whose total is **greater than 1,000**.

# %%
### BEGIN SOLUTION
query = """
SELECT customer_id, total
FROM (
    SELECT o.customer_id, SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) AS total
    FROM order_items AS oi
    JOIN orders AS o ON o.order_id = oi.order_id
    WHERE o.status IN ('delivered', 'shipped')
    GROUP BY o.customer_id
)
WHERE total > 1000
"""
### STARTER
# Write your query between the triple quotes, then run this cell and the next one.
query = """

"""
### END SOLUTION
sql(query) if query.strip() else print("(no query yet)")

# %%
grade("w02.top_spenders_subquery", query)

# %% [markdown]
# ## Quiz
#
# **Q1.** What does `customers LEFT JOIN orders` return?
# (a) only customers who have orders (b) every customer; order columns are NULL for customers without orders
# (c) every order, even those without a customer (d) one row per customer, duplicates removed

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w02.07_q1", answer)

# %% [markdown]
# **Q2.** Imagine `customers` had a `credit_limit` column. You join `customers` to `orders` and compute `SUM(c.credit_limit)`. Why is the result too large?
# (a) the join removes customers (b) customers without orders are counted twice (c) a customer with 3 orders
# appears in 3 rows, so their value is added 3 times (d) SUM always double counts after a join

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w02.07_q2", answer)

# %% [markdown]
# **Q3.** What is the "grain" of a result?
# (a) what one row represents, e.g. one order or one order line (b) how many columns it has (c) how it is sorted
# (d) a setting that only matters for averages

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w02.07_q3", answer)

# %% [markdown]
# **Q4.** `WHERE id NOT IN (SELECT id FROM t)` returns no rows at all, although you expected some. The most
# likely reason:
# (a) NOT IN is not valid SQL (b) `t` has duplicate ids (c) it returns every row instead (d) the subquery
# returns a NULL

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w02.07_q4", answer)

# %% [markdown]
# **Q5.** What is the quickest way to notice fan-out after a join?
# (a) check whether the query got slower (b) compare the number of rows before and after the join
# (c) look at the column names (d) nothing: joins on keys never fan out

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w02.07_q5", answer)

# %% [markdown]
# ## Recap
#
# - `JOIN ... ON a.key = b.key` pairs matching rows; aliases (`orders AS o`) keep column names clear.
# - `INNER JOIN` drops rows without a match; `LEFT JOIN` keeps every left row and fills NULLs.
# - After a LEFT JOIN, count a right-side column (`COUNT(o.order_id)`), not `*`.
# - Anti-join: `LEFT JOIN ... WHERE right.key IS NULL`; avoid `NOT IN` when the list can contain NULL.
# - Chain joins from the table whose rows you aggregate, outwards to the tables that describe them.
# - Know the **grain**; compare row counts before and after joins; fan-out makes sums silently too big.
# - Build a table at the grain you need in a subquery, then filter or join it.
#
# **On the job.** Building a training set is mostly joins: one row per customer (the grain of the label), with
# features aggregated from orders, tickets and payments. A fan-out there does not raise an error; it gives your
# model wrong features and inflated labels. "What is the grain, and did the row count change?" is the question
# senior engineers ask first in a code review.
#
# **Going further.** The [SQL tool guide](../docs/tools/sql.md) summarises joins and lists common errors. Next:
# the Week 2 lab, notebook 08, where you answer a product manager's questions end to end.

# %%
# Record your progress (optional; stored in progress/progress.json):
from mlcourse.progress import mark
# mark("07", "reading")
# mark("07", "guided")
