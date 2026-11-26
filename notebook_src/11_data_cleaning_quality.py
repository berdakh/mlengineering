# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/11_data_cleaning_quality.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 11 · Data cleaning and quality checks
#
# **Week 3 · lesson · about 100 minutes**
#
# The shop database you have used so far is tidy: one date format, no duplicates, prices in one currency. Real
# exports are not. A file arrives from another team or an old system, and before you can trust a single number
# computed from it you have to find out what is wrong with it, fix what you can, and *prove* the result is sound.
# In *Learning from Data* terms: the guarantees about $E_{out}$ assume your training data come from the same
# distribution as the data you will predict on. Duplicates, unit mix-ups and silently misread dates break that
# assumption before any model is trained.
#
# **What you will learn**
#
# - Inspect a new file: dtypes, missing values, and why a "number" column can arrive as text.
# - Handle missing values honestly, including codes such as `"N/A"`, `"-"` and `-1`, and why missingness itself
#   carries information.
# - Remove duplicates; standardise inconsistent text, units and date formats (including a classic date trap).
# - Flag outliers with the IQR rule, and decide what to do with them.
# - Tell **cleaning** (changing data) from **validation** (checking it), and write quality checks as code.
#
# **What you need:** notebook 10 (pandas essentials).
#
# **How grading works:** each exercise is a function. The grader runs it on small tables with planted problems
# (and on a file it writes itself), checks the result, and checks that your function did not change its input.

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
# ## The file for this week
#
# `data/course/messy_orders.csv` is a **synthetic** (generated, not real) order export that imitates a file
# exported by hand from an old shop system. It was built by `data/course/make_messy_orders.py`, which plants
# typical problems on purpose. Your job in this notebook is to learn the tools; in the lab (notebook 12) you will
# clean the whole file. Do not open the generator script yet: finding the problems yourself is the point.

# %%
import numpy as np
import pandas as pd

RAW = "data/course/messy_orders.csv"
raw = pd.read_csv(RAW)
print(raw.shape)
raw.head(8)

# %% [markdown]
# ## 1. Look before you clean: dtypes and missing values
#
# **Why.** Every cleaning mistake starts with an assumption about the data that nobody checked. Two minutes of
# looking saves hours of debugging a model that learned from garbage.
#
# **Idea.** Start with three questions.
#
# 1. **Are the types what I expect?** `raw.dtypes`. A column of numbers that pandas reads as text (dtype `object`,
#    or `str` in pandas 3) contains at least one value that is not a number: a stray `"-"`, a `"N/A"`.
# 2. **What is missing?** `raw.isna().sum()` counts missing values (`NaN`) per column. But pandas only recognises
#    some codes as missing (an empty field, `"N/A"`, `"NaN"`, `"null"` and a few others). Anything else a system
#    uses to mean "unknown" (`"-"`, `-1`, `999`) arrives as an ordinary value.
# 3. **What values occur?** `raw["col"].value_counts(dropna=False)` on every text column, and `.describe()` on
#    every number column. Look at the smallest and largest values: impossible ones jump out.
#
# **See it.** `discount` should be a number between 0 and 1, but look at its dtype.

# %%
print(raw.dtypes, "\n")
print(raw.isna().sum())

# %%
raw["discount"].value_counts(dropna=False)

# %% [markdown]
# There it is: besides the numbers and the `NaN`s (empty fields that pandas recognised), there is a `"-"`. One
# `"-"` is enough to make the whole column text, and then `raw["discount"].mean()` fails or makes no sense.
#
# **Try it.** Run `raw["quantity"].value_counts()` and `raw["unit_price"].describe()`. Write down anything that
# cannot be true for an order (we will come back to each one).

# %%
# Try it.
raw["quantity"].value_counts()

# %% [markdown]
# ### Exercise 1.1 · Count missing values
#
# Write `count_missing(df)` that returns a **Series**: for each column, the number of missing values, sorted from
# most to least missing. Every column must appear, even with 0. On an empty table every count is 0.

# %%
def count_missing(df):
    ### BEGIN SOLUTION
    return df.isna().sum().sort_values(ascending=False)
    ### END SOLUTION


count_missing(raw)

# %%
grade("w03.count_missing", count_missing)

# %% [markdown]
# ## 2. Missing values: codes, and why missingness matters
#
# **Why.** A model cannot learn from `"-"`, and a model trained on a column where `-1` secretly means "unknown"
# learns nonsense. Worse, *how* you fill gaps changes what the model learns.
#
# **Idea.** Two steps, in this order.
#
# **Step 1: make every "unknown" a real missing value**, as early as possible. `pd.read_csv(path,
# na_values=["-", "N/A"])` treats extra codes as missing while reading. A code that only means "unknown" in one
# column (like `quantity == -1`) is replaced later with `.where` or `.mask`:
# `df["quantity"].mask(df["quantity"] == -1)` gives `NaN` where the condition holds.
#
# **Step 2: decide what missing means, and write the decision down.** Options:
#
# | Option | When it is reasonable | The risk |
# |---|---|---|
# | leave it missing | most of the time, until you know more | some tools cannot handle `NaN` |
# | fill with a fixed value (`fillna(0)`) | when missing *means* that value (no discount recorded = no discount) | wrong if the assumption is wrong |
# | fill with mean or median | rarely, for a feature, together with a flag | invents data, shrinks the spread |
# | drop the row | the row is useless without it, and few rows are affected | can bias what remains |
#
# Why care: missingness is often **not random**. If customers who later churn are more likely to have no phone
# number on file, then "phone is missing" is itself a useful signal, and filling it with the most common value
# erases it. In week 4 you will add "is missing" flags as features for exactly this reason.
#
# **See it.** Read the file again, this time telling pandas about the extra code.

# %%
better = pd.read_csv(RAW, na_values=["-"])
print(better["discount"].dtype)
print(better[["city", "discount"]].isna().sum())

# %% [markdown]
# **Try it.** How many rows have `quantity == -1`? Turn them into missing values with
# `better["quantity"].mask(better["quantity"] == -1)` and check the new `.isna().sum()`.

# %%
# Try it.

# %% [markdown]
# ### Exercise 2.1 · Read with missing-value codes
#
# Write `read_with_missing_codes(path)` that reads a CSV file and returns a DataFrame in which the codes `"N/A"`,
# `"n/a"`, `"-"` and an empty field are all missing values (`NaN`). A numeric column that only contained those codes
# besides numbers should come out as numbers. The grader tests it on a small file it writes itself.

# %%
def read_with_missing_codes(path):
    ### BEGIN SOLUTION
    return pd.read_csv(path, na_values=["N/A", "n/a", "-", ""])
    ### END SOLUTION


read_with_missing_codes(RAW).isna().sum()

# %%
grade("w03.read_with_missing_codes", read_with_missing_codes)

# %% [markdown]
# ## 3. Duplicates
#
# **Why.** If an export ran twice for some days, every count, total and average computed from it is inflated, and
# a model sees those examples twice. Duplicates between training and test data also make test scores look better
# than they are (the model is "tested" on rows it has seen).
#
# **Idea.** Two different questions:
#
# - **Exact duplicates**: rows identical in every column. `df.duplicated()` marks every copy after the first;
#   `df.drop_duplicates()` removes them (keeping the first).
# - **Duplicate keys**: two *different* rows with the same `order_id`. That is not a copy, it is a conflict (which
#   version is right?), and it must be investigated, not silently dropped. `df["order_id"].duplicated().sum()`
#   counts them; `df[df["order_id"].duplicated(keep=False)]` shows all rows involved.
#
# After removing rows, `reset_index(drop=True)` renumbers the index 0, 1, 2, ... so later steps do not trip over
# gaps.
#
# **See it.** In this file the two counts happen to be equal: every repeated `order_id` is an exact copy.

# %%
print("exact duplicate rows:", raw.duplicated().sum())
print("repeated order_id:   ", raw["order_id"].duplicated().sum())
raw[raw["order_id"].duplicated(keep=False)].sort_values("order_id").head(6)

# %% [markdown]
# **Try it.** Pick one repeated `order_id` from the output and compare its two rows column by column. Are they
# really identical?

# %%
# Try it.

# %% [markdown]
# ### Exercise 3.1 · Drop exact duplicates
#
# Write `drop_exact_duplicates(df)` that returns a new table without exact duplicate rows (keep the first copy),
# with the index reset to 0, 1, 2, .... Do not change `df`.

# %%
def drop_exact_duplicates(df):
    ### BEGIN SOLUTION
    return df.drop_duplicates().reset_index(drop=True)
    ### END SOLUTION


print(len(raw), "->", len(drop_exact_duplicates(raw)))

# %%
grade("w03.drop_exact_duplicates", drop_exact_duplicates)

# %% [markdown]
# ## 4. Inconsistent text and units
#
# **Why.** To a computer, `"Almaty"`, `"almaty"` and `" Almaty"` are three different cities. Group by city before
# fixing that and you get three half-sized groups; one-hot encode it for a model and you get three useless features.
# Units are worse: a price recorded in cents is a hundred times too big, and nothing about the number tells you so.
#
# **Idea.** Text columns have a `.str` accessor with vectorised string methods: `.str.strip()` removes spaces at both
# ends, `.str.lower()`, `.str.upper()` and `.str.title()` fix the case (`title` gives `"Almaty"`), `.str.replace(a, b)`
# swaps text. Missing values stay missing through all of them.
#
# For units, look for a column that tells you the unit (here: `price_unit`) and convert everything to **one** unit,
# then drop the unit column so nobody can misread it. `series.where(cond, other)` keeps values where `cond` is
# `True` and takes `other` elsewhere: `price.where(unit != "cents", price / 100)`.
#
# **See it.** How many different spellings does `city` have before and after cleaning?

# %%
print("before:", raw["city"].nunique(), "spellings")
print("after: ", raw["city"].str.strip().str.title().nunique(), "spellings")
raw["city"].str.strip().str.title().value_counts(dropna=False)

# %% [markdown]
# There is still a `"-"` among the cities: that is a missing-value code, not a city. Cleaning steps interact; the
# lab puts them in a sensible order.
#
# **Try it.** Do the same for `status` (lower case is the convention there). How many distinct statuses remain?
# Then look at `raw.groupby("price_unit")["unit_price"].median()`: what does it tell you?

# %%
# Try it.

# %% [markdown]
# ### Exercise 4.1 · Standardise text
#
# Write `standardise_text(s)` that takes a **Series** of text and returns a new Series with spaces removed at both
# ends and title case (`"  ALMATY"` becomes `"Almaty"`). Missing values must stay missing.

# %%
def standardise_text(s):
    ### BEGIN SOLUTION
    return s.str.strip().str.title()
    ### END SOLUTION


standardise_text(raw["city"]).value_counts().head(3)

# %%
grade("w03.standardise_text", standardise_text)

# %% [markdown]
# ### Exercise 4.2 · Convert cents to dollars
#
# Write `convert_cents(df)` that takes a table with columns `unit_price` and `price_unit` (`"dollars"` or `"cents"`)
# and returns a new table where every `unit_price` is in **dollars** and the `price_unit` column is **dropped**. Keep
# all other columns. Do not change `df`.

# %%
def convert_cents(df):
    ### BEGIN SOLUTION
    price = df["unit_price"].where(df["price_unit"] != "cents", df["unit_price"] / 100)
    return df.assign(unit_price=price).drop(columns="price_unit")
    ### END SOLUTION


convert_cents(raw)["unit_price"].describe()

# %%
grade("w03.convert_cents", convert_cents)

# %% [markdown]
# ## 5. Dates in several formats, and a trap
#
# **Why.** A date column that mixes formats is one of the most common problems in exported files, and one of the
# most dangerous: a wrongly parsed date does not cause an error, it silently becomes a *different, valid* date.
# Every "last 30 days" feature computed from it is then wrong.
#
# **Idea.** This file has three formats in `order_date`: `2025-03-04` (ISO: year-month-day), `04/03/2025` (day
# first, as in most of the world: 4 March) and `March 4, 2025`. The tempting shortcut is to let pandas guess:
# `pd.to_datetime(s, format="mixed", dayfirst=True)`. Watch what it does to an ISO date.

# %%
sample = pd.Series(["2025-03-04", "04/03/2025", "March 4, 2025"])
pd.to_datetime(sample, format="mixed", dayfirst=True)

# %% [markdown]
# All three strings mean 4 March 2025, but the first one comes out as **3 April**: with `dayfirst=True` pandas read
# the ISO date day first too. (Without `dayfirst`, the second one would be read as 3 April instead.) No single
# global rule is right for a file that mixes conventions.
#
# The safe approach: parse **each known format explicitly**, with `errors="coerce"` so that values in other
# formats become `NaT`, and combine the attempts with `fillna`:
#
# ```python
# iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
# dmy = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
# result = iso.fillna(dmy)
# ```
#
# Format codes: `%Y` four-digit year, `%m` month number, `%d` day, `%B` full month name. Finally, check that **no**
# value is left as `NaT`: if one is, there is a format you have not seen yet.
#
# **Try it.** Run the snippet above on `sample` (after defining `s = sample`). Which value is still `NaT`, and which
# format string would catch it?

# %%
# Try it.

# %% [markdown]
# ### Exercise 5.1 · Parse mixed dates
#
# Write `parse_mixed_dates(s)` that takes a Series of date strings in the three formats above (possibly with spaces
# around them) and returns a datetime Series with every date parsed correctly. Remember `04/03/2025` is 4 March.

# %%
def parse_mixed_dates(s):
    ### BEGIN SOLUTION
    s = s.astype(str).str.strip()
    out = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    out = out.fillna(pd.to_datetime(s, format="%d/%m/%Y", errors="coerce"))
    return out.fillna(pd.to_datetime(s, format="%B %d, %Y", errors="coerce"))
    ### END SOLUTION


parsed = parse_mixed_dates(raw["order_date"])
print("unparsed:", parsed.isna().sum(), "| range:", parsed.min().date(), "to", parsed.max().date())

# %%
grade("w03.parse_mixed_dates", parse_mixed_dates)

# %% [markdown]
# ## 6. Outliers: flag first, decide second
#
# **Why.** One price of 4500 in a column of 7-to-45 prices moves the mean and dominates a squared-error loss. But an
# extreme value is not automatically an error: a bulk order of 400 units is unusual and real. You need a quick way to
# find candidates, and then judgement.
#
# **Idea.** The **IQR rule** is a simple screen. The **quartiles** $Q_1$ and $Q_3$ are the values below which 25%
# and 75% of the data lie; the **interquartile range** is $IQR = Q_3 - Q_1$. A value is flagged when it is below
# $Q_1 - 1.5\,IQR$ or above $Q_3 + 1.5\,IQR$. It uses quartiles rather than the mean and standard deviation, so the
# outliers themselves barely move the fences.
#
# Then, for each kind of flagged value, ask: **impossible** (a negative quantity: fix or remove), **an error with a
# known cause** (a price in cents: convert), or **rare but real** (keep, maybe cap for some models)?
#
# **See it.** On the raw prices, the rule flags many values. Most are the cents prices from section 4: an "outlier"
# that is really a unit problem.

# %%
price = raw["unit_price"]
q1, q3 = price.quantile([0.25, 0.75])
iqr = q3 - q1
flag = (price < q1 - 1.5 * iqr) | (price > q3 + 1.5 * iqr)
print(f"Q1 = {q1}, Q3 = {q3}, fences = [{q1 - 1.5 * iqr}, {q3 + 1.5 * iqr}], flagged = {flag.sum()}")
raw.loc[flag, "price_unit"].value_counts()

# %% [markdown]
# **Try it.** Apply the same rule to `convert_cents(raw)["unit_price"]`. How many values are flagged now, and what
# are they?

# %%
# Try it.

# %% [markdown]
# ### Exercise 6.1 · Flag outliers with the IQR rule
#
# Write `flag_outliers_iqr(s)` that takes a numeric Series and returns a **boolean** Series of the same length:
# `True` where the value is below $Q_1 - 1.5\,IQR$ or above $Q_3 + 1.5\,IQR$ (use pandas' default `quantile`).

# %%
def flag_outliers_iqr(s):
    ### BEGIN SOLUTION
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    return (s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)
    ### END SOLUTION


flag_outliers_iqr(raw["unit_price"]).sum()

# %%
grade("w03.flag_outliers_iqr", flag_outliers_iqr)

# %% [markdown]
# ## 7. Cleaning versus validation
#
# **Why.** You will clean this file once. But next month a new export arrives, and it may have a new problem you
# have never seen. Cleaning code does not notice new problems; it just runs. You need a second kind of code whose
# only job is to **check**.
#
# **Idea.**
#
# - **Cleaning** *changes* data: it fixes problems you know about (codes to `NaN`, duplicates removed, units
#   converted).
# - **Validation** *checks* data against rules that must hold, and changes nothing. If a rule fails, the pipeline
#   should stop and a person should look, rather than quietly train a model on broken data.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c11-01.svg" alt="Raw data goes through cleaning functions, then validation checks; if a check fails, stop and investigate" style="max-width:100%">
#
# Write validation as small, named checks, each a single `True`/`False` about the whole table, collected in a dict
# (a **quality report**). Then a pipeline can do `assert all(report.values())`, and a person can read which rule
# broke. Useful checks: keys are unique (`df["id"].is_unique`), values in a range (`(df["x"] > 0).all()`), values from
# an allowed set (`df["s"].isin(allowed).all()`), no missing values where none are allowed
# (`df["x"].notna().all()`).
#
# **See it.** Two checks on the raw file. Both fail, as they should.

# %%
report = {
    "unique_order_ids": bool(raw["order_id"].is_unique),
    "no_missing_city": bool(raw["city"].notna().all()),
}
print(report)
failed = [name for name, ok in report.items() if not ok]
print("failed checks:", failed)

# %% [markdown]
# **Try it.** Run the same two checks on `drop_exact_duplicates(raw)`. Which one passes now? Should the other one
# be "fixed" by cleaning, or is missing city acceptable? (That is a business decision, not a coding one.)

# %%
# Try it.

# %% [markdown]
# ### Exercise 7.1 · Quality checks as code
#
# Write `quality_checks(df)` for an order table with columns `order_id`, `quantity`, `unit_price`, `status`. Return
# a dict with exactly these boolean checks:
#
# - `"unique_order_ids"`: no `order_id` appears twice;
# - `"quantities_positive"`: every `quantity` is greater than 0;
# - `"prices_positive"`: every `unit_price` is greater than 0;
# - `"statuses_valid"`: every `status` is one of `"delivered"`, `"shipped"`, `"cancelled"`, `"returned"`.
#
# Do not clean anything inside this function: it only looks. The grader breaks one rule at a time and checks that
# exactly that check fails.

# %%
def quality_checks(df):
    ### BEGIN SOLUTION
    allowed = {"delivered", "shipped", "cancelled", "returned"}
    return {
        "unique_order_ids": bool(df["order_id"].is_unique),
        "quantities_positive": bool((df["quantity"] > 0).all()),
        "prices_positive": bool((df["unit_price"] > 0).all()),
        "statuses_valid": bool(df["status"].isin(allowed).all()),
    }
    ### END SOLUTION


quality_checks(raw)

# %%
grade("w03.quality_checks", quality_checks)

# %% [markdown]
# ## Quiz
#
# **Q1.** What is the difference between cleaning and validation?
#
# - a) Validation should fix any problem it finds, so the pipeline never stops.
# - b) You only need one of them: cleaning if the data is small, validation if it is large.
# - c) Cleaning changes data to fix known problems; validation only checks rules and stops the pipeline when one fails.
# - d) Validation means measuring the model's accuracy on a validation set.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"
### END SOLUTION
quiz("w03.11_q1", answer)

# %% [markdown]
# **Q2.** 30% of customers have no `income` value. Why is filling those with the mean income risky?
#
# - a) It is not risky: filling with the mean never changes the data.
# - b) It invents values, shrinks the spread, and erases the signal in *who* is missing (which may relate to the target).
# - c) It creates duplicate rows.
# - d) Models cannot use filled values at all.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"
### END SOLUTION
quiz("w03.11_q2", answer)

# %% [markdown]
# **Q3.** The old system wrote `quantity = -1` when the quantity was unknown. What should cleaning do with these?
#
# - a) Take the absolute value, so they become 1.
# - b) Drop every such row immediately.
# - c) Keep -1, so averages include it.
# - d) Turn -1 into a missing value, then decide (and document) how to handle missing quantities.

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"
### END SOLUTION
quiz("w03.11_q3", answer)

# %% [markdown]
# **Q4.** A column contains both `2025-03-04` and `04/03/2025`. Why is `pd.to_datetime(s, format="mixed",
# dayfirst=True)` a bad idea here?
#
# - a) It reads the ISO date `2025-03-04` day first too, giving 3 April; parse each known format explicitly instead.
# - b) ISO dates should be read day first, so it is correct.
# - c) One global setting is fine because both formats put the day first.
# - d) It converts the dates to a different time zone.

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"
### END SOLUTION
quiz("w03.11_q4", answer)

# %% [markdown]
# **Q5.** The IQR rule flags 12 order quantities as outliers. What next?
#
# - a) Delete them: outliers are errors.
# - b) The rule proves they are wrong, so replace them with the median.
# - c) Inspect them: impossible values get fixed or removed, known-cause errors get converted, rare but real values stay.
# - d) Ignore them; outliers only matter for linear models.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"
### END SOLUTION
quiz("w03.11_q5", answer)

# %% [markdown]
# ## Recap
#
# - Inspect first: `dtypes`, `isna().sum()`, `value_counts(dropna=False)`, `describe()`. A text dtype on a number
#   column means a non-number is hiding in it.
# - Turn every "unknown" code into a real missing value (`na_values=`, `.mask`), then decide what missing means and
#   **write the decision down**. Missingness can carry information.
# - Exact duplicates are removed; duplicate **keys** with different values are investigated.
# - Standardise text with `.str.strip()` and a case method; convert every value to one unit and drop the unit column.
# - Parse mixed date formats explicitly, one format at a time; `format="mixed"` with `dayfirst` can silently swap
#   day and month.
# - The IQR rule flags outliers to **inspect**; decide per cause.
# - Cleaning changes data; validation only checks, and stops the pipeline when a rule breaks.
#
# ## On the job
#
# A large part of an ML engineer's time goes into data that is almost right. The habits from today (look before
# touching, keep the raw file, write each fix as a function, write validation checks that run on every new batch)
# are what keep a model from quietly degrading when an upstream system changes a format. In week 11 you will see the
# same idea at production scale: input checks and drift monitoring on live data.
#
# ## Going further
#
# - Tool guide: [pandas](../docs/tools/pandas.md), sections on missing data and dates.
# - pandas user guide on missing data: <https://pandas.pydata.org/docs/user_guide/missing_data.html>.
# - Next: [12 · Lab: clean a messy export and report its quality](12_lab_clean_and_validate.ipynb).

# %% [markdown]
# ## Record your progress
#
# Flags: `reading`, `guided` (you passed the graded exercises), `independent` (you solved them without hints or
# solutions), `review` (come back to this).

# %%
from mlcourse.progress import mark

# mark("11", "reading")
# mark("11", "guided")
