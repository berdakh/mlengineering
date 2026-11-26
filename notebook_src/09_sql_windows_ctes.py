# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/09_sql_windows_ctes.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 09 · Subqueries, CTEs and window functions
#
# **Week 3 · lesson · about 100 minutes**
#
# Last week you answered questions with `SELECT`, `GROUP BY` and `JOIN`. Real questions are often two or three
# questions stacked on top of each other: *"which products cost more than the average product?"*, *"what was each
# customer's most recent order?"*, *"what are the three best sellers in each category?"*. This notebook gives you
# the three tools that make such questions easy to write and easy to read.
#
# **What you will learn**
#
# - Put a query inside another query (a **subquery**) to compare against a computed value or list.
# - Break a long query into named steps with **CTEs** (`WITH ... AS (...)`).
# - Use **window functions** (`ROW_NUMBER`, `RANK`, `SUM(...) OVER`, `LAG`) to number, rank and accumulate rows
#   *without* collapsing them the way `GROUP BY` does.
# - Solve the classic "top N per group" and "running total" questions that appear in almost every data interview.
#
# **What you need:** notebooks 05-08 (SELECT, GROUP BY, JOIN on the shop database).
#
# **How grading works:** each exercise is a SQL string. The grader runs it on the course database *and* on a second,
# freshly generated shop database, and compares the rows with an answer it computes independently in pandas. So a
# query that only works by accident (or a hard-coded number) will not pass.

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
# We use the same helper as last week: `sql(query)` runs a query on the shop database and returns the result as a
# table. As a reminder of what is in the shop, here are the tables and the columns of `orders`.

# %%
from mlcourse.sql import sql, tables, schema

print(tables("shop"))
schema("shop", "orders")

# %% [markdown]
# ## 1. Subqueries: a query inside a query
#
# **Why.** A manager asks: *"which products are priced above our average product?"*. You could run one query to
# get the average (26.90), copy the number, and paste it into a second query. But next month the prices change and
# your pasted number is silently wrong. A subquery computes the number *inside* the query, every time.
#
# **Idea.** A **subquery** is a complete `SELECT` written in brackets inside another query. SQL runs the inner one
# first and uses its result. Two shapes cover most needs:
#
# | Shape | Inner query returns | Example |
# |---|---|---|
# | scalar subquery | one value | `WHERE price > (SELECT AVG(price) FROM products)` |
# | `IN` subquery | one column of values | `WHERE customer_id IN (SELECT customer_id FROM orders WHERE ...)` |
#
# Read them from the inside out: first "what is the average price?", then "which products beat it?".
#
# **See it.** The query below lists products that cost more than the cheapest Electronics product. Run it: you
# should see the products priced above 8.00 (the USB-C cable), most expensive first.

# %%
sql("""
SELECT name, category, price
FROM products
WHERE price > (SELECT MIN(price) FROM products WHERE category = 'Electronics')
ORDER BY price DESC
""")

# %% [markdown]
# **Try it.** Run the inner query on its own (copy the part in brackets into a new `sql("...")` call). Then change
# `MIN` to `MAX`: before running, predict how many products will be left. (Answer: none can beat the most expensive
# Electronics product, which is also the most expensive product overall.)

# %%
# Try it: run the inner query alone, then change MIN to MAX in the query above.
sql("SELECT MIN(price) FROM products WHERE category = 'Electronics'")

# %% [markdown]
# ### Exercise 1.1 · Products above the average price
#
# Write a query that returns the `name` and `price` of every product whose price is **greater than the average
# price of all products**. Do not type the average as a number: compute it with a subquery. Row order does not
# matter.

# %%
### BEGIN SOLUTION
query = """
SELECT name, price
FROM products
WHERE price > (SELECT AVG(price) FROM products)
"""
### STARTER
query = """
-- YOUR SQL HERE (replace the line below with your query)
SELECT 'not written yet' AS todo
"""
### END SOLUTION
sql(query)

# %%
grade("w03.above_average_products", query)

# %% [markdown]
# ### Exercise 1.2 · Customers who cancelled at least once
#
# Return `customer_id` and `name` of every customer who has **at least one order with status `'cancelled'`**. Each
# customer should appear once. Use an `IN (SELECT ...)` subquery (a JOIN would also work, but would give a customer
# with two cancellations two rows unless you add `DISTINCT`: one more reason the `IN` form is handy here).

# %%
### BEGIN SOLUTION
query = """
SELECT customer_id, name
FROM customers
WHERE customer_id IN (SELECT customer_id FROM orders WHERE status = 'cancelled')
"""
### STARTER
query = """
-- YOUR SQL HERE (replace the line below with your query)
SELECT 'not written yet' AS todo
"""
### END SOLUTION
sql(query).head()

# %%
grade("w03.customers_with_cancellations", query)

# %% [markdown]
# ## 2. CTEs: name each step
#
# **Why.** Subqueries nest. After two or three levels a query reads like a sentence with brackets inside brackets,
# and nobody (including you, next week) can check it. Analysts and ML engineers write long queries every day:
# the fix is to give each step a name.
#
# **Idea.** A **CTE** (common table expression) is a named, temporary result that exists only while one query runs.
# You write the steps first, after the word `WITH`, and then a final `SELECT` that uses them like tables:
#
# ```sql
# WITH step_one AS (
#     SELECT ...            -- any query
# ),
# step_two AS (
#     SELECT ... FROM step_one ...   -- later steps can use earlier ones
# )
# SELECT ... FROM step_two;
# ```
#
# A CTE does not store anything and is not faster than a subquery; it is about **readability**. Each step can be
# run and checked on its own, which is exactly how you should build a long query: one step at a time.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c09-02.svg" alt="A long query as a chain of CTEs: line totals, order totals, ranking, final filter" style="max-width:100%">
#
# **See it.** In the shop, the value of one order item is `quantity * unit_price * (1 - discount)`. The query below
# computes order totals in a CTE and then asks *"how many orders are above 100, per status?"*.

# %%
sql("""
WITH order_totals AS (
    SELECT o.order_id, o.status,
           SUM(i.quantity * i.unit_price * (1 - i.discount)) AS total
    FROM orders AS o
    JOIN order_items AS i ON i.order_id = o.order_id
    GROUP BY o.order_id, o.status
)
SELECT status, COUNT(*) AS n_orders, ROUND(AVG(total), 2) AS avg_total
FROM order_totals
WHERE total > 100
GROUP BY status
ORDER BY n_orders DESC
""")

# %% [markdown]
# **Try it.** Build it the way a professional would: copy only the CTE's inner `SELECT` into the cell below and run
# it alone. Check that it has one row per order (compare the row count with `SELECT COUNT(*) FROM orders`). Then put
# it back inside `WITH`.

# %%
# Try it: run the inner query of the CTE on its own and look at its grain (one row per ...?).
sql("SELECT COUNT(*) AS n_orders FROM orders")

# %% [markdown]
# ### Exercise 2.1 · Big delivered orders
#
# Return `order_id` and `total` for **delivered** orders whose total value (sum of
# `quantity * unit_price * (1 - discount)` over the order's items) is **greater than 500**. Use a CTE for the totals.
# Do not round. Row order does not matter.

# %%
### BEGIN SOLUTION
query = """
WITH totals AS (
    SELECT o.order_id, SUM(i.quantity * i.unit_price * (1 - i.discount)) AS total
    FROM orders AS o
    JOIN order_items AS i ON i.order_id = o.order_id
    WHERE o.status = 'delivered'
    GROUP BY o.order_id
)
SELECT order_id, total
FROM totals
WHERE total > 500
"""
### STARTER
query = """
-- YOUR SQL HERE (replace the line below with your query)
SELECT 'not written yet' AS todo
"""
### END SOLUTION
sql(query)

# %%
grade("w03.delivered_order_totals", query)

# %% [markdown]
# ### Exercise 2.2 · Average order value per channel
#
# "Average order value" is a standard business metric: the average of order **totals**, not of item prices. Return
# `channel` and `avg_order_value` for each sales channel, leaving out **cancelled** orders. You need two steps:
# first total each order (a CTE with one row per order, keeping its channel), then average those totals per channel.
#
# *Watch out:* averaging the item values directly would give the average *item* value, which is a different number.

# %%
### BEGIN SOLUTION
query = """
WITH order_totals AS (
    SELECT o.order_id, o.channel, SUM(i.quantity * i.unit_price * (1 - i.discount)) AS total
    FROM orders AS o
    JOIN order_items AS i ON i.order_id = o.order_id
    WHERE o.status <> 'cancelled'
    GROUP BY o.order_id, o.channel
)
SELECT channel, AVG(total) AS avg_order_value
FROM order_totals
GROUP BY channel
"""
### STARTER
query = """
-- YOUR SQL HERE (replace the line below with your query)
SELECT 'not written yet' AS todo
"""
### END SOLUTION
sql(query)

# %%
grade("w03.avg_order_value_by_channel", query)

# %% [markdown]
# ## 3. Window functions: compute across rows, keep every row
#
# **Why.** *"What was each customer's most recent order?"* sounds like `GROUP BY customer_id` with `MAX(order_date)`.
# But that gives you the date, not the rest of the order (its id, its channel). You need to compare rows within a
# group *and still keep the rows*. That is what window functions do, and they are among the most useful (and most
# interviewed) parts of SQL.
#
# **Idea.** A **window function** computes a value for every row, looking at a *window* of related rows. Its shape:
#
# ```sql
# function(...) OVER (PARTITION BY <group columns> ORDER BY <order columns>)
# ```
#
# - `PARTITION BY` splits the rows into groups (like `GROUP BY`), **but the rows are not collapsed**.
# - `ORDER BY` inside `OVER` sets the order within each group.
# - `ROW_NUMBER()` numbers the rows 1, 2, 3, ... inside each group.
# - `RANK()` is the same, but tied rows share a rank and the next rank is skipped (1, 1, 3).
#   `DENSE_RANK()` does not skip (1, 1, 2).
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c09-01.svg" alt="GROUP BY returns one row per customer; a window function keeps every order and adds a number per customer" style="max-width:100%">
#
# **See it.** Number each customer's orders from the earliest. Customer 1 has five orders, numbered 1 to 5 by date;
# customer 2 has two.

# %%
sql("""
SELECT customer_id, order_id, order_date,
       ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date) AS order_number
FROM orders
WHERE customer_id IN (1, 2)
ORDER BY customer_id, order_number
""")

# %% [markdown]
# **Try it.** Change `ORDER BY order_date` (inside `OVER`) to `ORDER BY order_date DESC`. Which order now gets
# number 1? Then delete `PARTITION BY customer_id`: what happens to the numbering?

# %%
# Try it: edit the window and re-run.
sql("""
SELECT customer_id, order_id, order_date,
       ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date) AS order_number
FROM orders
WHERE customer_id IN (1, 2)
ORDER BY customer_id, order_number
""")

# %% [markdown]
# One rule to remember: **window functions are computed after `WHERE`**, so you cannot write
# `WHERE ROW_NUMBER() OVER (...) = 1`. Compute the number in a CTE, then filter in the final query. This
# "CTE + window + filter" pattern solves a huge range of questions.
#
# ### Exercise 3.1 · Each customer's latest order
#
# Return one row per customer who has orders, with `customer_id`, `order_id` and `order_date` of their **most recent**
# order. If a customer has two orders on the same latest date, take the one with the **larger `order_id`**.
# (Customers without orders do not appear.)

# %%
### BEGIN SOLUTION
query = """
WITH numbered AS (
    SELECT customer_id, order_id, order_date,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC, order_id DESC) AS rn
    FROM orders
)
SELECT customer_id, order_id, order_date
FROM numbered
WHERE rn = 1
"""
### STARTER
query = """
-- YOUR SQL HERE (replace the line below with your query)
SELECT 'not written yet' AS todo
"""
### END SOLUTION
sql(query).head()

# %%
grade("w03.latest_order_per_customer", query)

# %% [markdown]
# ### Exercise 3.2 · Rank products by revenue
#
# Using **delivered** orders only, compute each product's `revenue` (sum of `quantity * unit_price * (1 - discount)`)
# and its `revenue_rank` with `RANK()`, where rank 1 is the highest revenue. Return `product_id`, `revenue`,
# `revenue_rank`. Products with no delivered sales do not appear.
#
# *Tip:* a window can be applied to an aggregated result: compute revenue per product in a CTE, then rank.

# %%
### BEGIN SOLUTION
query = """
WITH revenue AS (
    SELECT i.product_id, SUM(i.quantity * i.unit_price * (1 - i.discount)) AS revenue
    FROM order_items AS i
    JOIN orders AS o ON o.order_id = i.order_id
    WHERE o.status = 'delivered'
    GROUP BY i.product_id
)
SELECT product_id, revenue, RANK() OVER (ORDER BY revenue DESC) AS revenue_rank
FROM revenue
"""
### STARTER
query = """
-- YOUR SQL HERE (replace the line below with your query)
SELECT 'not written yet' AS todo
"""
### END SOLUTION
sql(query).head()

# %%
grade("w03.product_revenue_rank", query)

# %% [markdown]
# ## 4. Top N per group
#
# **Why.** "The three best-selling products in each category", "each user's five most recent sessions", "the top
# customer in each city": this is the single most common shape of an analytics question, and a favourite interview
# question. `LIMIT 3` does not work: it keeps three rows in total, not three per group.
#
# **Idea.** Combine the pieces you already have:
#
# 1. a CTE that computes the measure per item (here: units sold per product, with its category);
# 2. a CTE that numbers the items inside each group with `ROW_NUMBER() OVER (PARTITION BY group ORDER BY measure DESC)`;
# 3. a final `SELECT ... WHERE rn <= N`.
#
# Always add a **tie-breaker** to the window's `ORDER BY` (for example `product_id`). Without one, two products with
# the same units can swap places between runs, and your "top 3" changes for no reason.
#
# **See it.** The single most expensive product in each category:

# %%
sql("""
WITH ranked AS (
    SELECT category, name, price,
           ROW_NUMBER() OVER (PARTITION BY category ORDER BY price DESC, product_id) AS rn
    FROM products
)
SELECT category, name, price
FROM ranked
WHERE rn = 1
ORDER BY category
""")

# %% [markdown]
# **Try it.** Change `rn = 1` to `rn <= 2`. How many rows do you expect? (Five categories, so ten.)

# %%
# Try it: top 2 per category.

# %% [markdown]
# ### Exercise 4.1 · Top 3 products per category by units sold
#
# Count `units` sold per product (sum of `quantity`) over orders that are **not cancelled**. Return the **top 3
# products in each category** by units, with columns `category`, `name`, `units`. Break ties by the smaller
# `product_id`. Row order does not matter.

# %%
### BEGIN SOLUTION
query = """
WITH units AS (
    SELECT p.product_id, p.category, p.name, SUM(i.quantity) AS units
    FROM order_items AS i
    JOIN orders AS o ON o.order_id = i.order_id
    JOIN products AS p ON p.product_id = i.product_id
    WHERE o.status <> 'cancelled'
    GROUP BY p.product_id, p.category, p.name
),
ranked AS (
    SELECT category, name, units,
           ROW_NUMBER() OVER (PARTITION BY category ORDER BY units DESC, product_id) AS rn
    FROM units
)
SELECT category, name, units
FROM ranked
WHERE rn <= 3
"""
### STARTER
query = """
-- YOUR SQL HERE (replace the line below with your query)
SELECT 'not written yet' AS todo
"""
### END SOLUTION
sql(query)

# %%
grade("w03.top3_per_category", query)

# %% [markdown]
# ## 5. Running totals, previous values and shares
#
# **Why.** Dashboards and time-series features are full of *"so far this year"*, *"compared with last month"* and
# *"as a share of the total"*. In week 4 you will build model features like *"customer's spend in the previous 30
# days"*; they rest on exactly these ideas.
#
# **Idea.** Aggregate functions become window functions when you add `OVER`:
#
# | You write | You get on each row |
# |---|---|
# | `SUM(x) OVER (ORDER BY month)` | the **running total** of `x` up to this month |
# | `SUM(x) OVER ()` | the **grand total** (empty window = all rows) |
# | `LAG(x) OVER (ORDER BY month)` | `x` from the **previous** row (NULL on the first row) |
# | `LEAD(x) OVER (ORDER BY month)` | `x` from the **next** row (NULL on the last row) |
#
# Months are easy in this database because dates are stored as text like `2025-03-14`: `substr(order_date, 1, 7)`
# gives `2025-03`.
#
# **See it.** Monthly order counts, the previous month's count and a running count. Look at the first row: its
# `prev_month` is empty (`None`), because there is no earlier month.

# %%
sql("""
WITH monthly AS (
    SELECT substr(order_date, 1, 7) AS month, COUNT(*) AS n_orders
    FROM orders
    GROUP BY month
)
SELECT month, n_orders,
       LAG(n_orders) OVER (ORDER BY month) AS prev_month,
       SUM(n_orders) OVER (ORDER BY month) AS running_orders,
       SUM(n_orders) OVER ()               AS all_orders
FROM monthly
ORDER BY month
""").head(6)

# %% [markdown]
# **Try it.** Replace `LAG(n_orders)` with `LEAD(n_orders)` and look at the *last* row (`.tail()` instead of
# `.head(6)`). Then add a column `n_orders * 1.0 / SUM(n_orders) OVER ()`: what does it mean? (The `* 1.0` makes
# SQLite divide as decimals instead of whole numbers.)

# %%
# Try it: LEAD, and the share of all orders per month.

# %% [markdown]
# ### Exercise 5.1 · Monthly revenue with a running total
#
# For **delivered** orders, compute `revenue` per `month` (format `YYYY-MM`, revenue = sum of
# `quantity * unit_price * (1 - discount)`), and a `running_revenue` that adds up revenue from the first month to
# this one. Return `month`, `revenue`, `running_revenue`, **ordered by month** (order matters here).

# %%
### BEGIN SOLUTION
query = """
WITH monthly AS (
    SELECT substr(o.order_date, 1, 7) AS month,
           SUM(i.quantity * i.unit_price * (1 - i.discount)) AS revenue
    FROM orders AS o
    JOIN order_items AS i ON i.order_id = o.order_id
    WHERE o.status = 'delivered'
    GROUP BY month
)
SELECT month, revenue, SUM(revenue) OVER (ORDER BY month) AS running_revenue
FROM monthly
ORDER BY month
"""
### STARTER
query = """
-- YOUR SQL HERE (replace the line below with your query)
SELECT 'not written yet' AS todo
"""
### END SOLUTION
sql(query).tail()

# %%
grade("w03.monthly_running_revenue", query)

# %% [markdown]
# ### Exercise 5.2 · Month-over-month change
#
# Same monthly delivered revenue. Return `month`, `revenue`, `prev_revenue` (last month's revenue, empty for the
# first month) and `change` (`revenue - prev_revenue`, also empty for the first month), **ordered by month**.
#
# *Note:* subtracting from NULL gives NULL in SQL. That is the honest answer here: there is no change to report
# for the first month. Do not replace it with 0.

# %%
### BEGIN SOLUTION
query = """
WITH monthly AS (
    SELECT substr(o.order_date, 1, 7) AS month,
           SUM(i.quantity * i.unit_price * (1 - i.discount)) AS revenue
    FROM orders AS o
    JOIN order_items AS i ON i.order_id = o.order_id
    WHERE o.status = 'delivered'
    GROUP BY month
),
with_prev AS (
    SELECT month, revenue, LAG(revenue) OVER (ORDER BY month) AS prev_revenue
    FROM monthly
)
SELECT month, revenue, prev_revenue, revenue - prev_revenue AS change
FROM with_prev
ORDER BY month
"""
### STARTER
query = """
-- YOUR SQL HERE (replace the line below with your query)
SELECT 'not written yet' AS todo
"""
### END SOLUTION
sql(query).head()

# %%
grade("w03.month_over_month", query)

# %% [markdown]
# ### Exercise 5.3 · Each category's share of revenue
#
# For **delivered** orders, return `category`, its `revenue`, and `share` = category revenue divided by the revenue
# of all categories together (a number between 0 and 1; the shares add up to 1). Use `SUM(...) OVER ()` for the
# total. Row order does not matter.

# %%
### BEGIN SOLUTION
query = """
WITH by_category AS (
    SELECT p.category, SUM(i.quantity * i.unit_price * (1 - i.discount)) AS revenue
    FROM order_items AS i
    JOIN orders AS o ON o.order_id = i.order_id
    JOIN products AS p ON p.product_id = i.product_id
    WHERE o.status = 'delivered'
    GROUP BY p.category
)
SELECT category, revenue, revenue / SUM(revenue) OVER () AS share
FROM by_category
"""
### STARTER
query = """
-- YOUR SQL HERE (replace the line below with your query)
SELECT 'not written yet' AS todo
"""
### END SOLUTION
sql(query)

# %%
grade("w03.category_revenue_share", query)

# %% [markdown]
# ## Quiz
#
# Set `answer` to the letter you choose and run the cell. A wrong answer explains the misconception behind it.
#
# **Q1.** What is the essential difference between `SUM(x) OVER (PARTITION BY g)` and `SUM(x) ... GROUP BY g`?
#
# - a) Only `GROUP BY` can add numbers up.
# - b) Window functions do not work in SQLite.
# - c) The window version keeps every row and puts the group's sum on each; `GROUP BY` returns one row per group.
# - d) The window version removes rows that are not in the group.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"
### END SOLUTION
quiz("w03.09_q1", answer)

# %% [markdown]
# **Q2.** Three products have revenue 90, 90 and 70. What does `RANK() OVER (ORDER BY revenue DESC)` give them?
#
# - a) 1, 2, 3
# - b) 1, 1, 3
# - c) 1, 1, 2
# - d) It depends on the product ids.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"
### END SOLUTION
quiz("w03.09_q2", answer)

# %% [markdown]
# **Q3.** Which statement about CTEs (`WITH name AS (...)`) is true?
#
# - a) A CTE names a step of a query so the query can be read and checked step by step.
# - b) A CTE creates a table that stays in the database after the query.
# - c) A CTE always makes a query run faster than the same subquery.
# - d) CTEs can only be used together with window functions.

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"
### END SOLUTION
quiz("w03.09_q3", answer)

# %% [markdown]
# **Q4.** You want the 3 most expensive products **in each category**. Which approach works?
#
# - a) `SELECT ... FROM products ORDER BY price DESC LIMIT 3`
# - b) `SELECT ... FROM products WHERE ROW_NUMBER() OVER (PARTITION BY category ORDER BY price DESC) <= 3`
# - c) `SELECT category, MAX(price) FROM products GROUP BY category`
# - d) Number the rows per category in a CTE with `ROW_NUMBER() OVER (PARTITION BY category ...)`, then keep `rn <= 3`.

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"
### END SOLUTION
quiz("w03.09_q4", answer)

# %% [markdown]
# **Q5.** In a monthly table ordered by month, what does `LAG(revenue) OVER (ORDER BY month)` return on the first
# month?
#
# - a) 0
# - b) An error, because there is no previous row.
# - c) NULL (a missing value).
# - d) The first month's row is dropped from the result.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"
### END SOLUTION
quiz("w03.09_q5", answer)

# %% [markdown]
# ## Recap
#
# - A **subquery** computes a value or a list inside a query, so the query stays correct when the data changes.
# - A **CTE** (`WITH step AS (...)`) names each step of a long query; build and check one step at a time.
# - A **window function** (`... OVER (PARTITION BY ... ORDER BY ...)`) computes across related rows **without
#   collapsing them**.
# - `ROW_NUMBER` numbers rows; `RANK` shares ranks on ties and skips; `DENSE_RANK` shares and does not skip.
# - **Top N per group** = CTE + `ROW_NUMBER() OVER (PARTITION BY group ORDER BY measure DESC, tie_breaker)` +
#   `WHERE rn <= N`.
# - `SUM(x) OVER (ORDER BY t)` is a running total, `SUM(x) OVER ()` a grand total, `LAG`/`LEAD` look one row back or
#   forward.
# - Window results cannot be used in `WHERE` of the same query: compute them in a CTE first.
#
# ## On the job
#
# Most data an ML engineer touches is first pulled out of a warehouse with a query like the ones you just wrote:
# "each customer's latest order", "spend in the previous month", "rank of this product in its category". When a
# model's features are computed in SQL, a missing tie-breaker or a running total that accidentally includes the
# future becomes a silent bug in the model. Reading and writing these queries carefully is part of the job.
#
# ## Going further
#
# - Tool guide: [SQL (SQLite)](../docs/tools/sql.md), with a cheat sheet of
#   window functions.
# - SQLite's own page on window functions: <https://www.sqlite.org/windowfunctions.html> (frames such as
#   `ROWS BETWEEN 2 PRECEDING AND CURRENT ROW` give moving averages).
# - Next: [10 · pandas essentials, side by side with SQL](10_pandas_essentials.ipynb).

# %% [markdown]
# ## Record your progress
#
# Flags: `reading`, `guided` (you passed the graded exercises), `independent` (you solved them without hints or
# solutions), `review` (come back to this).

# %%
from mlcourse.progress import mark

# mark("09", "reading")
# mark("09", "guided")
