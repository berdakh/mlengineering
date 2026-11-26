---
title: "pytest"
parent: Tool guides
nav_order: 10
---

# pytest

pytest is the standard tool for writing and running tests in Python. This guide covers what you need from Week 8
(notebooks 30 and 32) onwards: writing tests, running them, reading failures, fixtures, parametrize, temporary
files, testing numbers and tables, and what to test in ML code.

## What it is, and why teams use it

A **test** is a small function that runs your code on an input with a known answer and fails loudly if the result is
wrong. A **test suite** is all of them together; a **test runner** finds them, runs them and reports. pytest is the
runner almost every Python team uses, because tests are plain functions with plain `assert` statements, failure
reports show the actual values, and it has a large ecosystem of plugins.

Teams test because:

* changes are safe: a mistake shows up in seconds, on your machine, not weeks later in a dashboard;
* bugs stay fixed: every fixed bug gets a test that would have caught it;
* code review is faster: the tests show what the code is supposed to do;
* CI (Week 10) runs the suite on every push and blocks changes that break it.

## Opening it

**In Google Colab** pytest is installed. Write test files with `%%writefile`, then run them from a cell:

```python
!cd /content/work/testing && python -m pytest tests/test_features.py -q
```

**On your own computer**: `python -m pip install pytest` inside your project's environment (see the
[packaging guide](packaging.html)), then from the project folder:

```bash
python -m pytest            # run everything
```

Prefer `python -m pytest` over a bare `pytest`: it uses the pytest of the active Python and adds the current folder
to the import path.

## Writing tests

```python
# tests/test_features.py
from featurekit import clean_city


def test_lower_case_becomes_title_case():
    assert clean_city("almaty") == "Almaty"


def test_blank_becomes_none():
    assert clean_city("   ") is None
```

The rules pytest follows (its **discovery** rules):

* files named `test_*.py` (or `*_test.py`);
* in them, functions named `test_*` (and methods of classes named `Test*`, if you prefer grouping);
* a test **passes** if it returns without an exception and **fails** on `AssertionError` (or any other error).

A good test follows **Arrange, Act, Assert**: build a small input whose answer you worked out by hand, call the code
once, compare. Name tests after the behaviour (`test_cancelled_orders_are_ignored`): the failure report then reads
like a sentence. Keep tests small, fast, independent (no test relies on another running first) and deterministic.

### Checking that errors are raised

```python
import pytest

def test_unknown_config_key_is_rejected(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("seed: 1\nsede: 2\n")
    with pytest.raises(ValueError, match="sede"):     # match: a regular expression on the message
        load_config(path)
```

## Running tests

| command | what it does |
|---|---|
| `python -m pytest` | run every test found under the current folder (or under `testpaths`) |
| `python -m pytest tests/test_features.py` | one file |
| `python -m pytest tests/test_features.py::test_blank_becomes_none` | one test |
| `-q` / `-v` | quieter (one character per test) / one line per test |
| `-x` | stop at the first failure |
| `-k "city and not blank"` | only tests whose name matches the expression |
| `--lf` | re-run only the tests that failed last time |
| `-s` | show `print` output (pytest hides it for passing tests) |
| `--pdb` | open the debugger at the failure |

Exit code `0` means all passed, `1` some failed, `2` interrupted (often an import error), `5` no tests collected.
CI systems read this code.

### Where pytest starts: rootdir and configuration

pytest searches upwards from your test files for a configuration file: `pytest.ini`, or a `pyproject.toml` that
contains a `[tool.pytest.ini_options]` table. The folder holding it is the **rootdir**: the project root.

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]          # where `python -m pytest` looks by default
addopts = "-q"                 # options added to every run
```

If tests behave differently depending on where you run them, look at the `rootdir:` and `configfile:` lines at the
top of a `-v` run.

## Reading a failure

```
F.                                                                  [100%]
================================ FAILURES =================================
__________________________ test_ten_percent_off ___________________________

    def test_ten_percent_off():
>       assert apply_discount(100.0, 0.1) == 90.0
E       assert 110.0 == 90.0
E        +  where 110.0 = apply_discount(100.0, 0.1)

tests/test_discounts.py:9: AssertionError
========================= short test summary info =========================
FAILED tests/test_discounts.py::test_ten_percent_off - assert 110.0 == 90.0
1 failed, 1 passed in 0.04s
```

Read it bottom-up: the summary names the failed test; the `E` lines show the assertion with the **actual** values
(left: what the code returned, 110.0; right: what the test expected, 90.0) and where the left value came from; the
`>` marks the failing line, and `file:line` tells you where it is. For strings, lists and DataFrames, pytest and
pandas print a diff of what differs.

## Fixtures

A **fixture** builds something tests need. A test asks for it by naming it as an argument; pytest calls the fixture
and passes in the result, freshly for each test.

```python
import pandas as pd
import pytest


@pytest.fixture
def orders():
    return pd.DataFrame({
        "customer_id": [1, 1, 2],
        "order_date": pd.to_datetime(["2025-06-01", "2025-06-30", "2025-07-02"]),
        "status": ["delivered", "cancelled", "delivered"],
        "value": [10.0, 100.0, 1000.0],
    })


def test_cancelled_orders_are_ignored(orders):
    assert spend_in_window(orders, "2025-06-30", 30).loc[1] == pytest.approx(10.0)
```

Fixtures shared by several test files go in `tests/conftest.py`; pytest loads it automatically, no import needed.

### Built-in fixtures you will use

* **`tmp_path`**: a new, empty temporary folder (`pathlib.Path`) per test. Use it for every file a test writes.
* **`monkeypatch`**: temporarily replace an attribute, environment variable or dictionary entry for one test, e.g.
  `monkeypatch.setenv("MODEL_PATH", str(tmp_path / "model.pkl"))`. Undone automatically afterwards.
* **`capsys`**: capture what the code printed: `out = capsys.readouterr().out`.
* **`caplog`**: capture log records: `assert "missing" in caplog.text`.

## Parametrize: one test, many cases

```python
@pytest.mark.parametrize("raw, expected", [
    ("almaty", "Almaty"),
    ("  Astana ", "Astana"),
    ("new   york", "New York"),
    ("", None),
    (None, None),
])
def test_clean_city(raw, expected):
    assert clean_city(raw) == expected
```

Each case runs and is reported separately (`test_clean_city[almaty-Almaty]`), so one failing input does not hide the
others. Use it for edge-case tables: boundaries, empty values, odd formatting.

## Comparing numbers, arrays and tables

Floating-point arithmetic rounds (`0.1 + 0.2` is `0.30000000000000004`), so never compare computed floats with
plain `==`.

```python
import numpy as np
import pandas as pd
import pytest

assert 0.1 + 0.2 == pytest.approx(0.3)                         # relative tolerance 1e-6
assert x == pytest.approx(0.0, abs=1e-12)                       # near zero: absolute tolerance
assert [0.1 + 0.2, 1.0] == pytest.approx([0.3, 1.0])           # lists and arrays too
np.testing.assert_allclose(actual_array, expected_array, rtol=1e-6)
assert np.isnan(value)                                          # never value == np.nan
pd.testing.assert_frame_equal(actual_df, expected_df)           # values, columns, index, dtypes
pd.testing.assert_series_equal(actual, expected, check_names=False)
```

`assert_frame_equal` is strict about dtypes and index: that strictness catches real bugs (dates read back as text,
an extra index column). Relax only what you mean to, with options such as `check_dtype=False` or
`check_like=True` (ignore column order).

## What to test in ML code

ML code rarely crashes when it is wrong; it produces a model and a number, and the number is wrong. Unit tests are
your protection against these silent errors.

**Test:**

* **transforms and features** on tiny hand-made tables, including edge cases: empty input, missing values, ties,
  and boundaries (`<` versus `<=`, the first and last day of a window);
* **time and leakage rules**: features only use rows on or before the cutoff; changing rows after the cutoff does
  not change the features; a split puts each row on the correct side; anything fitted (scalers, encoders, imputers)
  learns from training rows only, so changing the test rows does not change what was learned;
* **contracts**: one row per entity, no duplicated keys, expected columns and dtypes, inputs not modified;
* **configuration**: unknown keys rejected, overrides converted to the right types, invalid values refused;
* **a smoke test of training**: fit on 20 rows, check predictions have the right shape and lie in [0, 1].

**Do not unit-test model quality** (`assert accuracy > 0.8`): it is slow, depends on data and randomness, and a
failure does not point to a line of code. Quality belongs in evaluation and monitoring.

**Are your tests good enough?** Plant a realistic bug (flip `<=` to `<`, drop a filter, use the wrong column) and
check that at least one test fails. This is **mutation testing**; the Week 8 graders do exactly this, and tools such
as `mutmut` automate it. **Coverage** (`pip install pytest-cov`, then `python -m pytest --cov=shopfeat`) tells you
which lines ran during the tests; it is useful for finding untested code, but 100% coverage does not mean the
asserts check the right things.

## Common errors and how to read them

* **`collected 0 items` / exit code 5.** File or function names do not start with `test_`, or you ran pytest in the
  wrong folder.
* **`ModuleNotFoundError` during collection** (`ERROR collecting tests/test_x.py`). The code under test is not
  importable: install the package (`pip install -e .`), run from the project folder with `python -m pytest`, or (for
  a quick run) set `PYTHONPATH=src`.
* **`fixture 'orders' not found`.** The fixture is defined in another file; move it to `tests/conftest.py`.
* **A test passes alone but fails in the full suite** (or the other way round). Tests share state: a module-level
  DataFrame modified by one test, a file in a fixed location, a global setting. Build fresh data in fixtures and use
  `tmp_path`.
* **`assert 0.30000000000000004 == 0.3`.** Use `pytest.approx`.
* **`DataFrame.iloc[:, 0] (column name="x") are different` with `dtype` in the message.** `assert_frame_equal`
  found matching values with different types (`int64` vs `float64`, `datetime64` vs `object`). Decide whether the
  type difference is a bug (often it is).
* **Flaky tests** (sometimes pass, sometimes fail). Usually randomness without a seed, the current date
  (`pd.Timestamp.now()`), or dictionary/set order. Pass fixed seeds and dates in.

## Cheat sheet

```bash
python -m pytest                      # all tests
python -m pytest tests/test_x.py -q   # one file, quiet
python -m pytest -x --lf              # stop at first failure; only last failures
python -m pytest -k "window" -v       # tests matching "window", verbose
python -m pytest -s                   # show print output
```

```python
import numpy as np
import pandas as pd
import pytest

def test_something():                                   # discovered: test_*.py / test_*
    assert f(2) == 4

def test_error():
    with pytest.raises(ValueError, match="unknown"):
        f(-1)

@pytest.fixture
def table():                                            # fresh per test; share via tests/conftest.py
    return pd.DataFrame({"x": [1.0, 2.0]})

def test_uses_fixture(table, tmp_path):                 # tmp_path: empty temporary folder
    table.to_csv(tmp_path / "t.csv", index=False)

@pytest.mark.parametrize("raw, expected", [(" a", "A"), ("", None)])
def test_cases(raw, expected):
    assert clean(raw) == expected

# comparisons
x == pytest.approx(0.3); np.isnan(v)
np.testing.assert_allclose(a, b)
pd.testing.assert_frame_equal(df1, df2)
```

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

## Where to go next

* pytest documentation, "Get started" and "How-to guides": <https://docs.pytest.org/en/stable/>
* Fixtures reference: <https://docs.pytest.org/en/stable/how-to/fixtures.html>
* Parametrizing tests: <https://docs.pytest.org/en/stable/how-to/parametrize.html>
* In this course: notebook 30 (testing with pytest), the lab in notebook 32, notebook 35 (testing APIs) and Week 10
  (running the suite in CI on every push). The advanced track's testing notebook applies mutation testing to a
  larger package.
