---
title: "Week 3 · Advanced SQL and pandas"
parent: Weekly plan
nav_order: 3
---

# Week 3 · Advanced SQL and pandas

**Goal:** use window functions and CTEs, do the same work in pandas, and clean messy data with quality checks.

Last week you learned to ask a database questions. This week you learn to ask harder ones (each customer's latest
order, the top three products per category, a running total), to do the same work in Python with pandas, and to
deal with what real exports look like: duplicates, missing-value codes, mixed date formats and prices in the wrong
unit. The week ends with a lab in which you clean a deliberately messy (synthetic) order export with a pipeline of
small functions and hand over a quality report. Everything runs in Google Colab.

| # | Notebook | Kind | Time | Open |
|---|---|---|---|---|
| 09 | Subqueries, CTEs and window functions | lesson | 100 min | [read](../notebooks/09_sql_windows_ctes.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/09_sql_windows_ctes.ipynb) |
| 10 | pandas essentials, side by side with SQL | lesson | 100 min | [read](../notebooks/10_pandas_essentials.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/10_pandas_essentials.ipynb) |
| 11 | Data cleaning and quality checks | lesson | 100 min | [read](../notebooks/11_data_cleaning_quality.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/11_data_cleaning_quality.ipynb) |
| 12 | Lab: clean a messy export and report its quality | lab | 90 min | [read](../notebooks/12_lab_clean_and_validate.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/12_lab_clean_and_validate.ipynb) |

## Before you start

* Week 2 (notebooks 05-08): `SELECT`, `WHERE`, `GROUP BY`, `HAVING` and `JOIN` on the shop database.
* Python functions, lists and dicts (Week 1, notebook 02). No pandas experience is assumed beyond having seen
  `read_csv`.

## What you will be able to do

* write subqueries and break long queries into readable steps with CTEs (`WITH ... AS`);
* number, rank and accumulate rows with window functions (`ROW_NUMBER`, `RANK`, `SUM(...) OVER`, `LAG`), and
  solve "top N per group" and "running total" questions;
* load tables into pandas and filter, sort, add columns, group, aggregate and merge them, knowing the SQL
  equivalent of each step;
* write vectorised pandas code and functions that return new tables without changing their input;
* inspect a new file, handle missing-value codes and duplicates, standardise text, units and mixed date formats,
  and flag outliers;
* tell cleaning from validation, and write quality checks as code that produce a report.

## Suggested pacing (6-8 hours)

| Session | Work | Time |
|---|---|---|
| 1 | Notebook 09, sections 1-3 (subqueries, CTEs, ROW_NUMBER and RANK) | 1 h |
| 2 | Notebook 09, sections 4-5 and quiz (top N per group, running totals, LAG) | 45 min |
| 3 | Notebook 10, sections 1-3 (DataFrames, filtering, new columns, vectorised code) | 50 min |
| 4 | Notebook 10, sections 4-6 and quiz (groupby, merge, dates) | 50 min |
| 5 | Notebook 11, sections 1-4 (inspection, missing values, duplicates, text and units) | 50 min |
| 6 | Notebook 11, sections 5-7 and quiz (dates, outliers, validation) | 50 min |
| 7 | Notebook 12, the lab, without looking at the solutions | 1.5 h |
| 8 | Review: redo any exercise you needed a hint for; skim the pandas cheat sheet | 30 min |

If a session runs long, stop at the end of a section: every notebook can be re-run from the top.

## Tool guides

* [pandas](../tools/pandas.html): the reference for notebooks 10-12, with the SQL-to-pandas translation table,
  common errors and a one-page cheat sheet.
* [SQL (SQLite)](../tools/sql.html): the Week 2 basics that notebook 09 builds on. For window functions, the
  recap of notebook 09 and SQLite's own page (<https://www.sqlite.org/windowfunctions.html>) are the reference.

## Data this week

* `data/course/shop.db`: the synthetic shop database from Week 2.
* `data/course/messy_orders.csv`: a **synthetic**, deliberately messy order export (1,236 rows) built by
  `data/course/make_messy_orders.py`. The lab's graders also generate a fresh file with a different seed, so your
  cleaning code has to work on any file of this kind.

Next week: [Week 4 · From data to features](week-4.html).
