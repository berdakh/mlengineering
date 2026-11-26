---
title: "Week 2 · SQL from zero"
parent: Weekly plan
nav_order: 2
---

# Week 2 · SQL from zero

**Goal:** answer business questions from a relational database with `SELECT`, `GROUP BY` and `JOIN`.

You start from "what is a database?" and end the week answering a product manager's questions about revenue,
repeat customers, payment gaps and support times, with numbers you have checked yourself. Everything runs in
Google Colab on a small synthetic shop database; nothing needs installing.

| # | Notebook | Kind | Time | Open |
|---|---|---|---|---|
| 05 | Databases and SELECT | lesson | 90 min | [read](../notebooks/05_sql_select.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/05_sql_select.ipynb) |
| 06 | Aggregation: GROUP BY, HAVING, CASE | lesson | 90 min | [read](../notebooks/06_sql_aggregation.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/06_sql_aggregation.ipynb) |
| 07 | JOINs and the grain of a table | lesson | 100 min | [read](../notebooks/07_sql_joins.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/07_sql_joins.ipynb) |
| 08 | Lab: business questions in SQL | lab | 90 min | [read](../notebooks/08_lab_sql_business_questions.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/08_lab_sql_business_questions.ipynb) |

## Before you start

* Week 1, at least notebook 01 (how Colab and the graders work) and notebook 02 (Python functions and strings).
* No SQL or database experience is assumed.

## What you will be able to do

* explain tables, rows, columns, primary and foreign keys, and read an entity-relationship diagram;
* filter, sort and compute columns with `SELECT`, `WHERE`, `ORDER BY`, `LIMIT`, and handle `NULL` correctly;
* summarise with `COUNT`, `SUM`, `AVG`, `GROUP BY`, `HAVING` and `CASE WHEN`, including per month;
* combine tables with `INNER` and `LEFT JOIN`, find rows with no match, and spot double counting (fan-out);
* turn a vague question into a definition, a query and a reconciled number.

## Suggested pacing (6-8 hours)

| Session | Work | Time |
|---|---|---|
| 1 | Notebook 05, sections 1-4 (tables, SELECT, WHERE, ORDER BY) | 1 h |
| 2 | Notebook 05, sections 5-6 and quiz (NULL, computed columns, dates) | 45 min |
| 3 | Notebook 06 (aggregates, GROUP BY, HAVING, CASE, time) | 1.5 h |
| 4 | Notebook 07, sections 1-4 (inner, left and anti-joins, three tables) | 1 h |
| 5 | Notebook 07, sections 5-6 and quiz (grain, fan-out, subqueries) | 45 min |
| 6 | Notebook 08, the lab, without looking at the solutions | 1.5 h |
| 7 | Review: redo any exercise you needed a hint for; skim the SQL tool guide's cheat sheet | 30 min |

If a session runs long, stop at the end of a section: every notebook can be re-run from the top.

## Tool guides

* [SQL (SQLite)](../tools/sql.html): reference for everything this week, including running the same SQL in VS Code
  and DuckDB, common error messages and a one-page cheat sheet.
* [Google Colab](../tools/colab.html), from Week 1, if anything about running notebooks is unclear.

Next week: [Week 3 · Advanced SQL and pandas](week-3.html).
