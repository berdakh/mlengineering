# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/30_testing_with_pytest.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 30 · Testing with pytest
#
# **Week 8 · lesson · about 100 minutes**
#
# You have been *graded* by tests all course. Today you write them. A **test** is a small piece of code that runs your
# code on an input where you know the right answer, and complains loudly if the answer is wrong. With a good test
# suite you can change code on Friday afternoon without fear, because a mistake shows up in seconds, not in next
# month's dashboard.
#
# **What you will learn**
#
# - Write tests as plain functions with `assert`, and run them with **pytest**.
# - Read a pytest failure report and find the cause quickly.
# - Compare numbers, arrays and DataFrames with tolerances.
# - Use **fixtures**, **parametrize** and the `tmp_path` folder to keep tests short and independent.
# - Decide what to test in ML code (transforms, features, splits, leakage) and what not to unit-test (accuracy).
#
# **What you need:** notebook 29 (modules and `%%writefile`).
#
# **How grading works (this is new).** Your answers are *test files*. The grader runs them twice: on the correct code,
# where they must **pass**, and on copies of the code with one realistic bug planted each, where they must **fail**.
# A test that passes on buggy code would not protect you, so it does not pass the grader.

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
# ### The code under test
#
# All of today's tests check one module, `featurekit.py`: eight small feature functions for the shop data, all
# **correct**. The next cell writes it into a project folder `T` (inside your working folder) and prints it. Read it
# once now; you will come back to each function when you test it.

# %%
import numpy as np
import pandas as pd
from mlcourse.graders.w08 import work_dir, load_module, FEATUREKIT

T = work_dir() / "testing"
(T / "tests").mkdir(parents=True, exist_ok=True)
(T / "featurekit.py").write_text(FEATUREKIT)
sys.path.insert(0, str(T))
print(FEATUREKIT)

# %% [markdown]
# ## 1. A test is a function with an `assert`
#
# **Why.** You change `clean_city` to also handle tabs. Did you break the capitalisation? Without a test you find out
# when a report shows "almaty" and "Almaty" as two cities.
#
# **Idea.** `assert condition` does nothing when the condition is true and raises `AssertionError` when it is false.
# A **test** is a function whose name starts with `test_` and which follows three steps:
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c30-01.svg" alt="Arrange a small input with a known answer, act by calling the function once, assert that the result equals the known answer" style="max-width:100%">
#
# 1. **Arrange**: build a small input whose correct answer you know *without* running the code (work it out on paper).
# 2. **Act**: call the function.
# 3. **Assert**: compare the result with the known answer.
#
# Good tests are **small** (one behaviour each), **fast** (milliseconds), **independent** (no test relies on
# another one running first) and **deterministic** (same result every time). Their names say what they check, so a
# failure report reads like a sentence: `test_blank_city_becomes_none FAILED`.
#
# **See it.** Two asserts, one true and one false. The second raises an error, which a test runner reports as a
# failed test.

# %%
from featurekit import clean_city

assert clean_city("  almaty ") == "Almaty"      # true: nothing happens
try:
    assert clean_city("astana") == "astana", "expected the name unchanged"
except AssertionError as err:
    print("AssertionError:", err)

# %% [markdown]
# **Try it.** Predict what `clean_city("NEW   york")` returns, then check.

# %%
clean_city("NEW   york")

# %% [markdown]
# ### Running tests with pytest
#
# **pytest** is the standard test runner for Python. Run in a terminal, `python -m pytest` looks for files named
# `test_*.py`, runs every function named `test_*` in them, and reports. Useful options: `-q` (quiet: one character
# per test), `-x` (stop at the first failure), `-k word` (only tests whose name contains *word*), `-v` (one line per
# test).
#
# In a notebook, `!cd "{T}" && python -m pytest tests/test_demo.py -q` means: go into the project folder, then run
# pytest on one file. Running from the project folder is what lets the tests `import featurekit`.

# %%
%%writefile {T}/tests/test_demo.py
from featurekit import clean_city


def test_spaces_are_removed():
    assert clean_city("  Almaty  ") == "Almaty"


def test_missing_value_stays_missing():
    assert clean_city(None) is None

# %%
!cd "{T}" && python -m pytest tests/test_demo.py -q

# %% [markdown]
# Two dots and `2 passed`: each dot is a passing test.
#
# ### Exercise 1 · your first test file
#
# Write `tests/test_clean_city.py` with **at least two** test functions for `clean_city`: one showing that a
# lower-case name comes back in Title Case, and one showing that an empty (or blank) name becomes `None`.
# Run it with the cell below before grading. Compare with `is None`, not `== None`.

# %%
%%writefile {T}/tests/test_clean_city.py
from featurekit import clean_city

### BEGIN SOLUTION

def test_lower_case_becomes_title_case():
    assert clean_city("almaty") == "Almaty"


def test_blank_becomes_none():
    assert clean_city("") is None
    assert clean_city("   ") is None
### STARTER

def test_clean_city():
    # YOUR CODE HERE
    raise NotImplementedError()
### END SOLUTION

# %%
!cd "{T}" && python -m pytest tests/test_clean_city.py -q

# %%
grade("w08.test_clean_city", T / "tests" / "test_clean_city.py")

# %% [markdown]
# ## 2. Reading a failure report
#
# **Why.** When a test fails, pytest tells you *which* test, *which line* and *what the values were*. Engineers who
# read this report carefully fix bugs in minutes; those who skim it start guessing.
#
# **Idea.** A failure report has four parts, top to bottom:
#
# 1. the summary line of dots and `F`s;
# 2. a section per failed test, headed `____ test_name ____`, showing the test's code with `>` on the failing line;
# 3. under it, `E` lines: the assertion with the **actual** values filled in. `assert 110.0 == 90.0` means the code
#    returned 110.0 where the test expected 90.0; a `where 110.0 = apply_discount(100.0, 0.1)` line says where the
#    left value came from;
# 4. the final summary: `FAILED tests/file.py::test_name - assert ...` and the counts.
#
# **See it.** A small pricing module with a bug, and its tests. Run them and read the report from the bottom up.

# %%
%%writefile {T}/discounts.py
def apply_discount(price, rate):
    """Price after a discount; rate is a fraction, so 0.1 means 10% off."""
    return round(price * (1 + rate), 2)


def add_tax(price, tax_rate=0.12):
    return round(price * (1 + tax_rate), 2)

# %%
%%writefile {T}/tests/test_discounts.py
from discounts import add_tax, apply_discount


def test_no_discount_keeps_price():
    assert apply_discount(50.0, 0.0) == 50.0


def test_ten_percent_off():
    assert apply_discount(100.0, 0.1) == 90.0


def test_tax_is_added():
    assert add_tax(100.0) == 112.0

# %%
!cd "{T}" && python -m pytest tests/test_discounts.py -q

# %% [markdown]
# ### Exercise 2 · what failed?
#
# From the report above, fill in the dictionary: the name of the failing test, the value the test **expected**, and
# the value the function actually returned (**got**). Then look at `discounts.py` and find the bug (you do not need
# to fix it).

# %%
### BEGIN SOLUTION
failure = {"test": "test_ten_percent_off", "expected": 90.0, "got": 110.0}
### STARTER
failure = {"test": None, "expected": None, "got": None}  # YOUR CODE HERE
### END SOLUTION

# %%
grade("w08.read_failure", failure)

# %% [markdown]
# ## 3. Comparing numbers, arrays and tables
#
# **Why.** Most ML code returns floats, arrays and DataFrames. Comparing them with `==` gives false alarms.
#
# **Idea.** Computers store most decimals approximately, so `0.1 + 0.2 == 0.3` is `False` (the left side is
# `0.30000000000000004`). Compare floats with a **tolerance**:
#
# | what you compare | tool |
# |---|---|
# | one float, or a list of floats | `assert x == pytest.approx(0.3)` (relative tolerance 1e-6 by default; `abs=1e-9` for values near 0) |
# | NumPy arrays | `np.testing.assert_allclose(actual, expected)` |
# | missing values | `np.isnan(x)`; never `x == np.nan`, which is always `False` |
# | DataFrames / Series | `pd.testing.assert_frame_equal(actual, expected)` / `assert_series_equal`: checks values, column names, index and dtypes, with a float tolerance |
#
# **See it.**

# %%
import pytest

print(0.1 + 0.2 == 0.3, "|", 0.1 + 0.2 == pytest.approx(0.3))
print(np.nan == np.nan, "|", np.isnan(np.nan))
np.testing.assert_allclose(np.array([1.0, 2.0]) / 3, [0.333333333, 0.666666667], rtol=1e-6)
pd.testing.assert_series_equal(pd.Series([1.0, 2.0]) * 0.1, pd.Series([0.1, 0.2]))
print("all comparisons passed")

# %% [markdown]
# **Try it.** Change one expected value in the `assert_series_equal` line to `0.21` and run. Read pytest-style output
# from pandas: which position differs?

# %%
# your experiment here

# %% [markdown]
# ### Exercise 3 · test `order_values`
#
# Write `tests/test_order_values.py`. Build a tiny items table by hand: two orders, one with two lines, at least
# one line with a discount and one with quantity above 1. Work out each order's value on paper, then assert with
# `pytest.approx`. (`order_values` returns a Series indexed by `order_id`, so `result.loc[1]` is order 1's value.)

# %%
%%writefile {T}/tests/test_order_values.py
import pandas as pd
import pytest

from featurekit import order_values

### BEGIN SOLUTION

def test_two_orders_with_discount_and_quantity():
    items = pd.DataFrame({
        "order_id": [1, 1, 2],
        "quantity": [2, 1, 3],
        "unit_price": [10.0, 4.0, 1.5],
        "discount": [0.0, 0.25, 0.1],
    })
    result = order_values(items)
    assert result.loc[1] == pytest.approx(23.0)   # 2*10 + 1*4*0.75
    assert result.loc[2] == pytest.approx(4.05)   # 3*1.5*0.9
### STARTER

def test_order_values():
    # YOUR CODE HERE
    raise NotImplementedError()
### END SOLUTION

# %%
!cd "{T}" && python -m pytest tests/test_order_values.py -q

# %%
grade("w08.test_order_values", T / "tests" / "test_order_values.py")

# %% [markdown]
# ### Exercise 4 · test `safe_ratio`, including division by zero
#
# `safe_ratio(numerator, denominator)` divides element by element and must return `NaN` where the denominator is 0
# (a ratio feature such as "tickets per order" must not become infinite for a customer with no orders). Write
# `tests/test_safe_ratio.py` with one ordinary division and one zero denominator.

# %%
%%writefile {T}/tests/test_safe_ratio.py
import numpy as np
import pytest

from featurekit import safe_ratio

### BEGIN SOLUTION

def test_ordinary_division():
    assert safe_ratio([6.0, 1.0], [3.0, 4.0]) == pytest.approx([2.0, 0.25])


def test_zero_denominator_gives_nan():
    result = safe_ratio([1.0, 2.0], [0.0, 2.0])
    assert np.isnan(result[0])
    assert result[1] == pytest.approx(1.0)
### STARTER

def test_safe_ratio():
    # YOUR CODE HERE
    raise NotImplementedError()
### END SOLUTION

# %%
!cd "{T}" && python -m pytest tests/test_safe_ratio.py -q

# %%
grade("w08.test_safe_ratio", T / "tests" / "test_safe_ratio.py")

# %% [markdown]
# ## 4. Fixtures, parametrize and `tmp_path`
#
# **Why.** Real test files repeat themselves: the same small table built in ten tests, the same check on twenty
# inputs, files written somewhere and never cleaned up. pytest has three tools for exactly this.
#
# **Idea.**
#
# * **`@pytest.mark.parametrize("raw, expected", [(...), (...)])`** runs one test function once per case. Each case
#   is reported separately, so you see exactly which input failed.
# * A **fixture** is a function decorated with `@pytest.fixture` that builds something tests need. A test asks for it
#   by naming it as an argument: `def test_x(orders):` gets a *fresh* copy of what the fixture `orders()` returns.
#   Fresh means one test cannot spoil the data for the next.
# * **`tmp_path`** is a fixture built into pytest: a new, empty temporary folder (a `pathlib.Path`) for each test.
#   Tests that write files use it, so they never touch your real project and never collide.
#
# **See it.**

# %%
%%writefile {T}/tests/test_tools_demo.py
import pandas as pd
import pytest

from featurekit import clean_city, spend_in_window


@pytest.mark.parametrize("raw, expected", [
    ("almaty", "Almaty"),
    ("  shymkent", "Shymkent"),
])
def test_clean_city_cases(raw, expected):
    assert clean_city(raw) == expected


@pytest.fixture
def two_orders():
    return pd.DataFrame({
        "customer_id": [1, 2],
        "order_date": pd.to_datetime(["2025-06-10", "2025-06-20"]),
        "status": ["delivered", "delivered"],
        "value": [10.0, 20.0],
    })


def test_both_orders_in_a_30_day_window(two_orders):
    result = spend_in_window(two_orders, "2025-06-30", 30)
    assert result.sum() == pytest.approx(30.0)


def test_files_go_to_tmp_path(tmp_path):
    (tmp_path / "hello.txt").write_text("hi")
    assert (tmp_path / "hello.txt").read_text() == "hi"

# %%
!cd "{T}" && python -m pytest tests/test_tools_demo.py -v

# %% [markdown]
# With `-v`, the two parametrized cases appear as `test_clean_city_cases[almaty-Almaty]` and
# `test_clean_city_cases[  shymkent-Shymkent]`: four tests from three functions.
#
# **Try it.** Add a third case `("", None)` to the parametrize list and re-run.

# %%
# your experiment here (edit the cell above, then re-run the pytest cell)

# %% [markdown]
# ### Exercise 5 · a parametrized test for `clean_city`
#
# Write `tests/test_clean_city_param.py`: **one** test function with `@pytest.mark.parametrize` and at least five
# `(raw, expected)` cases that together cover everything `clean_city` promises in its docstring: Title Case, spaces
# around the name, repeated spaces inside it, blank text, and a missing value (`None`).

# %%
%%writefile {T}/tests/test_clean_city_param.py
import pytest

from featurekit import clean_city

### BEGIN SOLUTION

@pytest.mark.parametrize("raw, expected", [
    ("almaty", "Almaty"),
    ("  Astana ", "Astana"),
    ("new   york", "New York"),
    ("", None),
    ("   ", None),
    (None, None),
])
def test_clean_city(raw, expected):
    assert clean_city(raw) == expected
### STARTER

def test_clean_city():
    # YOUR CODE HERE
    raise NotImplementedError()
### END SOLUTION

# %%
!cd "{T}" && python -m pytest tests/test_clean_city_param.py -q

# %%
grade("w08.test_clean_city_param", T / "tests" / "test_clean_city_param.py")

# %% [markdown]
# ### Exercise 6 · a fixture for `spend_in_window`
#
# `spend_in_window(orders, cutoff, days)` adds up the `value` of non-cancelled orders with
# `cutoff - days < order_date <= cutoff`. Write `tests/test_spend_window.py` with a **fixture** that returns a small
# orders table designed to catch mistakes at every edge: an order **on** the cutoff (counts), an order exactly
# `days` before the cutoff (does not count: the window starts just after it), a cancelled order inside the window,
# and an order **after** the cutoff. Give the edge orders very different values (1, 100, 1000, ...) so a wrong total
# shows immediately which order was miscounted.

# %%
%%writefile {T}/tests/test_spend_window.py
import pandas as pd
import pytest

from featurekit import spend_in_window

### BEGIN SOLUTION

@pytest.fixture
def orders():
    return pd.DataFrame({
        "customer_id": [1, 1, 1, 1, 2],
        "order_date": pd.to_datetime(["2025-06-30", "2025-06-01", "2025-05-31", "2025-07-01", "2025-06-15"]),
        "status": ["delivered", "cancelled", "delivered", "delivered", "delivered"],
        "value": [10.0, 100.0, 1000.0, 10000.0, 5.0],
    })


def test_only_valid_orders_inside_the_window_count(orders):
    result = spend_in_window(orders, "2025-06-30", 30)
    assert result.loc[1] == pytest.approx(10.0)
    assert result.loc[2] == pytest.approx(5.0)
### STARTER

def test_spend_in_window():
    # YOUR CODE HERE
    raise NotImplementedError()
### END SOLUTION

# %%
!cd "{T}" && python -m pytest tests/test_spend_window.py -q

# %%
grade("w08.test_spend_window", T / "tests" / "test_spend_window.py")

# %% [markdown]
# ### Exercise 7 · a round trip through a file
#
# `save_table(df, path)` writes a CSV and `load_table(path, date_cols=...)` reads it back. The property that matters
# is the **round trip**: what you load equals what you saved. Write `tests/test_round_trip.py` using `tmp_path`: build
# a small DataFrame with a date column and a float column, save, load with `date_cols`, and compare with
# `pd.testing.assert_frame_equal`.

# %%
%%writefile {T}/tests/test_round_trip.py
import pandas as pd

from featurekit import load_table, save_table

### BEGIN SOLUTION

def test_save_then_load_gives_the_same_table(tmp_path):
    table = pd.DataFrame({
        "customer_id": [1, 2],
        "order_date": pd.to_datetime(["2025-01-01", "2025-02-03"]),
        "value": [1.5, 2.0],
    })
    path = tmp_path / "table.csv"
    save_table(table, path)
    loaded = load_table(path, date_cols=["order_date"])
    pd.testing.assert_frame_equal(loaded, table, check_dtype=True)
### STARTER

def test_round_trip(tmp_path):
    # YOUR CODE HERE
    raise NotImplementedError()
### END SOLUTION

# %%
!cd "{T}" && python -m pytest tests/test_round_trip.py -q

# %%
grade("w08.test_round_trip", T / "tests" / "test_round_trip.py")

# %% [markdown]
# ## 5. What to test in ML code
#
# **Why.** ML code fails differently from ordinary code: it rarely crashes. A leaky split or a wrong feature still
# produces a model and a number; the number is just wrong, often *too good*. Tests are your defence against silent
# errors.
#
# **Idea.** In *Learning from Data* terms, the test set gives an honest estimate of $E_{out}$ only if nothing about
# it leaked into training. Unit tests are how you make sure the code respects that. Test:
#
# * **data transforms and features**: known input, known output (as you did above), including edge cases: empty
#   tables, missing values, ties, boundaries (`<` vs `<=`);
# * **no peeking at the future or the test set**: split functions put each row on the right side of the cutoff;
#   anything *fitted* (means, scalers, encoders) learns from training rows only, so changing the test rows does not
#   change what was learned;
# * **shapes and contracts**: one row per customer, no duplicated ids, the input not modified;
# * **the model code runs**: a tiny **smoke test** that fits on 20 rows and checks the predictions' shape and range.
#
# Do **not** unit-test model accuracy (`assert accuracy > 0.8`). It depends on the data and on randomness, it is slow,
# and when it fails it does not tell you which line is wrong. Accuracy belongs in evaluation (Weeks 5-7) and
# monitoring (Week 11).
#
# How do you know your tests are good? Plant a bug and see whether they notice. That is **mutation testing**, and it
# is exactly how this notebook grades you:
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c30-02.svg" alt="The same test suite runs on the correct code, where it must pass, and on several copies with one planted bug each, where it must fail" style="max-width:100%">
#
# **See it.** A leakage check written as a property: if `standardize` only learns from train, then changing the
# *test* rows must not change the scaled *train* rows.

# %%
from featurekit import standardize

train = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
test_a = pd.DataFrame({"x": [10.0]})
test_b = pd.DataFrame({"x": [-500.0]})
tr_a, _ = standardize(train, test_a, ["x"])
tr_b, _ = standardize(train, test_b, ["x"])
print(tr_a["x"].tolist(), tr_b["x"].tolist(), "identical:", tr_a.equals(tr_b))

# %% [markdown]
# **Try it.** Replace `train[columns].mean()` by `pd.concat([train, test])[columns].mean()` in a copy of
# `standardize` (write it in the next cell as `leaky_standardize`) and repeat the check: are the two results still
# identical?

# %%
# your experiment here

# %% [markdown]
# ### Exercise 8 · tests that catch leakage in `standardize`
#
# Write `tests/test_standardize.py`. Between them, your tests should show that `standardize`
#
# - learns the mean and standard deviation from the **training** rows only (for example: the scaled training column
#   has mean 0, whatever the test rows are),
# - scales the **test** rows with the *training* statistics (work out one scaled test value by hand; the function
#   uses the standard deviation with `ddof=0`, i.e. `train["x"].std(ddof=0)`),
# - does not modify the DataFrames it is given.

# %%
%%writefile {T}/tests/test_standardize.py
import pandas as pd
import pytest

from featurekit import standardize

### BEGIN SOLUTION

def make_data():
    train = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [10.0, 10.0, 40.0]})
    test = pd.DataFrame({"x": [100.0, 200.0], "y": [0.0, 0.0]})
    return train, test


def test_train_columns_have_mean_zero():
    train, test = make_data()
    scaled_train, _ = standardize(train, test, ["x", "y"])
    assert scaled_train["x"].mean() == pytest.approx(0.0, abs=1e-12)
    assert scaled_train["y"].mean() == pytest.approx(0.0, abs=1e-12)


def test_test_rows_use_training_statistics():
    train, test = make_data()
    _, scaled_test = standardize(train, test, ["x"])
    expected = (100.0 - 2.0) / train["x"].std(ddof=0)
    assert scaled_test["x"].iloc[0] == pytest.approx(expected)


def test_inputs_are_not_modified():
    train, test = make_data()
    before_train, before_test = train.copy(), test.copy()
    standardize(train, test, ["x", "y"])
    pd.testing.assert_frame_equal(train, before_train)
    pd.testing.assert_frame_equal(test, before_test)
### STARTER

def test_standardize():
    # YOUR CODE HERE
    raise NotImplementedError()
### END SOLUTION

# %%
!cd "{T}" && python -m pytest tests/test_standardize.py -q

# %%
grade("w08.test_standardize", T / "tests" / "test_standardize.py")

# %% [markdown]
# ### Exercise 9 · test the time split
#
# `split_by_time(df, date_col, cutoff)` must put every row dated **on or before** the cutoff in train and every later
# row in test, whatever order the rows are in. Write `tests/test_split_by_time.py`. Think about which input would
# expose a lazy implementation: rows that are **not sorted** by date, and a row dated **exactly** on the cutoff.

# %%
%%writefile {T}/tests/test_split_by_time.py
import pandas as pd

from featurekit import split_by_time

### BEGIN SOLUTION

def test_rows_go_to_the_right_side_even_when_unsorted():
    df = pd.DataFrame({
        "day": pd.to_datetime(["2025-03-01", "2025-01-01", "2025-02-01", "2025-01-15"]),
        "row": [1, 2, 3, 4],
    })
    train, test = split_by_time(df, "day", "2025-02-01")
    assert sorted(train["row"]) == [2, 3, 4]     # row 3 is ON the cutoff: train
    assert list(test["row"]) == [1]
    assert train["day"].max() <= pd.Timestamp("2025-02-01") < test["day"].min()
### STARTER

def test_split_by_time():
    # YOUR CODE HERE
    raise NotImplementedError()
### END SOLUTION

# %%
!cd "{T}" && python -m pytest tests/test_split_by_time.py -q

# %%
grade("w08.test_split_by_time", T / "tests" / "test_split_by_time.py")

# %% [markdown]
# ### Exercise 10 · catch a colleague's bug
#
# A colleague sends a "faster" rewrite of `featurekit.py`; the next cell saves it in a folder `colleague/`. Everything
# looks the same, but the churn model trained with it is slightly better, which is suspicious. The difference is in
# `days_since_last_order`.
#
# Write `tests/test_recency.py`: tests for `days_since_last_order(orders, cutoff)` (whole days from each customer's
# last **non-cancelled** order **on or before** the cutoff) that **pass on the original and fail on the colleague's
# version**. The second command below runs your tests against the colleague's file (by running pytest from inside
# `colleague/`, so its `featurekit.py` is the one imported). The grader also plants two other recency bugs.

# %%
from mlcourse.graders.w08 import COLLEAGUE_FEATUREKIT

(T / "colleague").mkdir(exist_ok=True)
(T / "colleague" / "featurekit.py").write_text(COLLEAGUE_FEATUREKIT)

# %%
%%writefile {T}/tests/test_recency.py
import pandas as pd

from featurekit import days_since_last_order

### BEGIN SOLUTION

def make_orders():
    return pd.DataFrame({
        "customer_id": [1, 1, 2, 2],
        "order_date": pd.to_datetime(["2025-06-01", "2025-06-20", "2025-06-30", "2025-07-05"]),
        "status": ["delivered", "cancelled", "delivered", "delivered"],
    })


def test_cancelled_orders_are_ignored():
    result = days_since_last_order(make_orders(), "2025-06-30")
    assert result.loc[1] == 29


def test_order_on_the_cutoff_counts_and_future_is_ignored():
    result = days_since_last_order(make_orders(), "2025-06-30")
    assert result.loc[2] == 0
### STARTER

def test_days_since_last_order():
    # YOUR CODE HERE
    raise NotImplementedError()
### END SOLUTION

# %%
print("--- original featurekit (should pass):")
!cd "{T}" && python -m pytest tests/test_recency.py -q
print("--- colleague's featurekit (should fail):")
!cd "{T}/colleague" && python -m pytest ../tests/test_recency.py -q

# %%
grade("w08.test_colleague", T / "tests" / "test_recency.py")

# %% [markdown]
# Now run the whole suite at once. This is the command you will run before every commit from now on (and in Week 10,
# a CI server will run it for you on every push).

# %%
!cd "{T}" && python -m pytest -q

# %% [markdown]
# Every file except `test_discounts.py` should pass: that one still tests the buggy `apply_discount`. In a real
# project you would now fix `discounts.py` and watch the test turn green; that is the normal rhythm of
# **test-driven bug fixing**: first a test that fails because of the bug, then the fix.

# %% [markdown]
# ## Quiz
#
# **Q1.** Which of these will pytest collect and run as a test?
#
# - a) Only methods of a class that inherits from `unittest.TestCase`.
# - b) Every function in every `.py` file of the folder.
# - c) Functions named `test_...` in files named `test_*.py`, each using plain `assert`.
# - d) Only files in a folder named exactly `tests/`.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w08.30_q1", answer)

# %% [markdown]
# **Q2.** `assert compute_fee(0.1, 0.2) == 0.3` fails although the function is right; the report says
# `assert 0.30000000000000004 == 0.3`. What is the fix?
#
# - a) Report a bug in pandas.
# - b) Compare with a tolerance: `== pytest.approx(0.3)`.
# - c) Round both sides to one decimal.
# - d) Avoid floats in tests.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w08.30_q2", answer)

# %% [markdown]
# **Q3.** A teammate adds `assert model_accuracy() > 0.80` to the unit tests. What is the best response?
#
# - a) Good: accuracy is the most important number.
# - b) Model code cannot be tested at all, so remove it.
# - c) Raise the threshold to 0.85 to be safe.
# - d) Move accuracy to evaluation and monitoring; unit-test the code around the model instead (features, splits,
#   no leakage, prediction shapes), which is fast, deterministic and points at the broken line.

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w08.30_q3", answer)

# %% [markdown]
# **Q4.** What makes a test suite *good*?
#
# - a) It passes on correct code and fails on code with realistic bugs.
# - b) It has many tests, all of which pass.
# - c) Every line of the code runs at least once during the tests.
# - d) It never fails.

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w08.30_q4", answer)

# %% [markdown]
# **Q5.** Why should a test that writes a file use `tmp_path`?
#
# - a) It makes disk access faster.
# - b) The file is never written to disk.
# - c) Each test gets its own new, empty temporary folder, so tests never touch your real files or each other.
# - d) Only CSV files need it.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w08.30_q5", answer)

# %% [markdown]
# ## Recap
#
# - A test arranges a small input with a known answer, calls the code, and asserts; pytest finds `test_*` functions
#   in `test_*.py` files and runs them with `python -m pytest`.
# - Read failures bottom-up: the `FAILED` line names the test, the `E` lines show the actual values.
# - Compare floats with `pytest.approx`, arrays with `np.testing.assert_allclose`, tables with `pd.testing`, and
#   missing values with `np.isnan`.
# - `@pytest.mark.parametrize` runs one test on many cases; fixtures build fresh test data; `tmp_path` isolates files.
# - In ML code, test transforms, boundaries, the split, "fitted on train only", shapes and inputs left unchanged;
#   keep accuracy out of unit tests.
# - A good suite fails on realistic bugs. Edge cases (`<` vs `<=`, cancelled rows, unsorted input) are where bugs hide.
#
# ## On the job
#
# In most teams, a pull request without tests is sent back. When you fix a bug, you first write the test that would
# have caught it, so it can never come back unnoticed. Before merging, a CI server (Week 10) runs the full suite on
# every push. In ML teams the most valuable tests are the boring ones you wrote today: one row per customer, the
# cutoff respected, nothing fitted on test rows. They catch the bugs that otherwise produce a model that looks
# great offline and fails in production.
#
# ## Going further
#
# - Tool guide: [pytest](../docs/tools/pytest.md): markers, `conftest.py`, `pytest.raises`, coverage, and a cheat sheet.
# - The advanced track's [testing ML code](../advanced/notebooks/05_testing_ml_code.ipynb) applies the same mutation
#   idea to a larger sensor-data package.
# - Next: [31 · Configuration, logging and reproducibility](31_config_logging_reproducibility.ipynb).

# %% [markdown]
# ## Record your progress

# %%
from mlcourse.progress import mark

# mark("30", "reading")
# mark("30", "guided")
