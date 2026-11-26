---
title: "Python for engineers"
parent: Tool guides
nav_order: 2
---

# Python for engineers

You already know Python's basics: variables, `if`, `for`, lists, functions. This guide covers the habits and
standard-library tools that turn notebook code into code a team can rely on: functions with clear contracts,
exceptions, the core data structures used idiomatically, and files (text, JSON, CSV) with `pathlib`. Everything here
is in Python's standard library, so it works in Colab and on any computer with nothing to install.

## Why "engineering" Python is different

Code in a notebook usually runs once, on data you have looked at, and you are its only user. Production code runs
thousands of times, on data nobody has looked at, and is called by people who never read it. Three consequences:

1. **Contracts matter.** Each function states what it takes, what it returns, and what it refuses.
2. **Failures must be loud and early.** A clear error now beats a wrong number in a report next month.
3. **Code is read far more often than written.** Names, docstrings and small functions are for the reader.

## Getting set up

- **Colab:** nothing to do; Python 3 and the standard library are there. Run the notebook's setup cell.
- **Your computer:** install Python 3.10 or newer from [python.org](https://www.python.org/downloads/) (on Windows,
  tick *Add Python to PATH*). Check in a terminal with `python --version` (on macOS/Linux it may be `python3`).
  Week 8 covers virtual environments and packaging in depth.

Run a script from a terminal with `python script.py`; open an interactive prompt with `python` (leave it with
`exit()`).

## The 20% you will use 80% of the time

### Functions with a contract

```python
def bmi(weight_kg: float, height_m: float) -> float:
    """Body-mass index: weight divided by height squared.

    Args:
        weight_kg: body weight in kilograms.
        height_m: height in metres (not centimetres).
    Returns:
        The index as a float.
    Raises:
        ValueError: if height_m is not positive.
    """
    if height_m <= 0:
        raise ValueError(f"height must be positive, got {height_m}")
    return weight_kg / height_m ** 2
```

- **Type hints** (`weight_kg: float`, `-> float`) document intended types. Python does *not* check them at run time;
  editors and checkers such as `mypy` do. Useful forms: `list[str]`, `dict[str, int]`, `tuple[int, str]`,
  `float | None` (a float or `None`).
- The **docstring** (the string right after `def`) describes the contract; `help(bmi)` shows it.
- **Return, do not print.** A function that prints its result gives the caller `None`.
- **One job per function**, a name that says what it does (`parse_price`, not `process`), and few arguments.
- **Default arguments**: `def top_n(counts, n=5)`. Never use a mutable default such as `def f(items=[])`: the same
  list is shared between calls. Use `items=None` and create the list inside.

### Exceptions

An **exception** signals "I cannot do this". `raise` creates one; `try` / `except` handles one.

```python
def parse_price(text: str) -> float:
    cleaned = text.strip().replace("$", "").replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        raise ValueError(f"not a price: {text!r}") from None

try:
    price = parse_price(cell)
except ValueError as err:
    print("skipping row:", err)
```

| Exception | Raised when |
|---|---|
| `ValueError` | right type, unacceptable value (`int("abc")`, a negative age) |
| `TypeError` | wrong type (`"3" + 4`, `len(5)`) |
| `KeyError` | missing dictionary key (`d["nope"]`) |
| `IndexError` | list index out of range |
| `FileNotFoundError` | opening a file that does not exist |
| `ZeroDivisionError` | dividing by zero |
| `AttributeError` | calling a method that does not exist (`None.strip()`) |

Rules of thumb:

- Catch the **specific** exception you can handle, around the **smallest** piece of code. `except Exception: pass`
  hides real bugs.
- Validate inputs at the edges of your program (reading files, receiving requests) and raise with a message that
  shows the bad value (`{value!r}` shows quotes and spaces).
- `finally:` runs whether or not an error happened; `with` blocks (below) usually do this for you.

### Strings and f-strings

```python
name, score = "Aru", 0.91234
f"{name} scored {score:.2f}"     # 'Aru scored 0.91'
f"{1234567:,}"                   # '1,234,567'
f"{value!r}"                     # repr: shows quotes, e.g. "' 3 '"
"  a,b ,c ".strip().split(",")   # ['a', 'b ', 'c']
",".join(["a", "b"])             # 'a,b'
"Hello".lower(), "x".upper(), "abc".startswith("a"), "a-b".replace("-", "_")
```

### Lists, dictionaries, sets and tuples

```python
counts = {}
for word in words:
    counts[word] = counts.get(word, 0) + 1          # count

groups = {}
for name, team in pairs:
    groups.setdefault(team, []).append(name)        # group

seen = set()                                        # fast membership tests
if value in seen: ...
seen.add(value)

point = (3, 4)                                      # tuple: fixed, unchangeable
x, y = point                                        # unpacking
for i, item in enumerate(items, start=1): ...       # index and value
for a, b in zip(list_a, list_b): ...                # walk two lists together
```

`collections.Counter(words).most_common(3)` does counting and ranking in one line once you understand the loop.

### Comprehensions

```python
squares = [x * x for x in range(10)]
evens = [x for x in numbers if x % 2 == 0]
lengths = {w: len(w) for w in words}
unique = {w.lower() for w in words}
```

Use a comprehension when it fits on one readable line; otherwise write a loop.

### Sorting

```python
sorted(values)                                     # new sorted list
sorted(values, reverse=True)                       # largest first
sorted(counts.items(), key=lambda kv: kv[1])       # by count
sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))   # count desc, then name asc
```

`key=` takes a function that maps each item to what should be compared. `lambda kv: kv[1]` is a small unnamed
function. Returning a tuple sorts by the first element, then the second for ties.

### Paths with `pathlib`

```python
from pathlib import Path

data = Path("data") / "course" / "shop.db"   # "/" joins parts correctly on every OS
data.exists(), data.is_file(), data.name, data.suffix, data.parent
Path("out/reports").mkdir(parents=True, exist_ok=True)
for p in Path("data").glob("*.csv"): ...     # files in one folder
for p in Path("data").rglob("*.csv"): ...    # including subfolders
p.relative_to("data").as_posix()             # 'raw/x.csv', with / on every OS
```

Avoid building paths by string concatenation: Windows uses `\` and Linux and macOS use `/`.

### Files: text, JSON and CSV

```python
from pathlib import Path
import json, csv

Path("notes.txt").write_text("hello\n", encoding="utf-8")
text = Path("notes.txt").read_text(encoding="utf-8")

Path("config.json").write_text(json.dumps({"lr": 0.1, "features": ["age"]}, indent=2))
config = json.loads(Path("config.json").read_text())

with open("people.csv", newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))          # [{'name': 'Aru', 'age': '31'}, ...]  values are strings

with open("out.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["name", "age"])
    writer.writeheader()
    writer.writerows(rows)
```

- `with open(...) as f:` closes the file automatically, even after an error.
- Modes: `"r"` read (default), `"w"` write (replaces), `"a"` append.
- Always pass `encoding="utf-8"` for text you share: Windows otherwise uses a different default.
- `newline=""` is what the `csv` module expects; without it you can get blank lines on Windows.
- **JSON** keeps structure (numbers, strings, lists, nested dicts, `true`/`false`/`null`); use it for settings,
  reports and API messages. **CSV** is for flat tables; every value comes back as text.

### Dates

```python
from datetime import date, datetime, timedelta
date.fromisoformat("2024-03-01")             # raises ValueError for '2024-13-01'
date(2024, 3, 1) + timedelta(days=30)
datetime.now().isoformat(timespec="seconds")
```

### Scripts and modules

A `.py` file is a **module**; `import validator` runs it once and gives access to its functions. Code that should run
only when the file is executed directly goes under:

```python
if __name__ == "__main__":
    import sys
    main(sys.argv[1:])          # command-line arguments after the script name
    sys.exit(0)                 # exit code: 0 success, anything else failure
```

## Common errors and how to read them

Read a traceback from the **bottom**: the last line is the error type and message; the frame just above it that
points to your file is where to look.

```
Traceback (most recent call last):
  File "/content/x.py", line 7, in <module>
    total = add_tax(price)
  File "/content/x.py", line 3, in add_tax
    return price * 1.12
TypeError: can't multiply sequence by non-int of type 'float'
```

Here `price` is a string (a *sequence* of characters), probably read from a CSV and never converted with `float()`.

| Message | Typical cause |
|---|---|
| `TypeError: unsupported operand type(s) for +: 'int' and 'str'` | mixing numbers and text; convert first |
| `TypeError: 'NoneType' object is not subscriptable` | a function returned `None` (forgot `return`?) and you indexed it |
| `AttributeError: 'NoneType' object has no attribute 'strip'` | same: a value you expected is `None` |
| `KeyError: 'age'` | the dictionary or CSV row has no such key: check spelling and the header |
| `ValueError: invalid literal for int() with base 10: '4.5'` | the text is not a whole number |
| `IndentationError: unexpected indent` | inconsistent spaces; use 4 per level |
| `UnboundLocalError` | assigning to a variable inside a function that you also read from outside it |
| `ModuleNotFoundError: No module named 'x'` | package not installed (`pip install x`) or wrong folder |
| `FileNotFoundError: [Errno 2] No such file or directory: 'data.csv'` | path relative to a different working folder; print `Path.cwd()` |

## Cheat sheet

| Need | Python |
|---|---|
| Function with contract | `def f(x: int) -> str:` + docstring + `return` |
| Refuse bad input | `raise ValueError(f"bad value: {x!r}")` |
| Handle a failure | `try: ... except ValueError as err: ...` |
| Count | `d[k] = d.get(k, 0) + 1` or `Counter(items)` |
| Group | `d.setdefault(k, []).append(v)` |
| Filter / transform | `[f(x) for x in xs if cond(x)]` |
| Rank with ties | `sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))` |
| Path | `Path("a") / "b.csv"`, `.exists()`, `.mkdir(parents=True, exist_ok=True)` |
| Find files | `Path(folder).rglob("*.csv")` |
| Text file | `Path(p).read_text(encoding="utf-8")`, `.write_text(...)` |
| JSON | `json.dumps(obj, indent=2)`, `json.loads(text)` |
| CSV rows | `list(csv.DictReader(open(p, newline="")))` |
| Date | `date.fromisoformat("2024-03-01")` |
| Script entry | `if __name__ == "__main__":` |
| Exit code | `sys.exit(0)` ok, `sys.exit(1)` failure |

## Where next

- The official [Python tutorial](https://docs.python.org/3/tutorial/), especially chapters 4 (functions),
  5 (data structures), 7 (files) and 8 (errors).
- Standard library docs: [pathlib](https://docs.python.org/3/library/pathlib.html),
  [json](https://docs.python.org/3/library/json.html), [csv](https://docs.python.org/3/library/csv.html),
  [datetime](https://docs.python.org/3/library/datetime.html).
- [PEP 8](https://peps.python.org/pep-0008/), the community style guide, and
  [PEP 257](https://peps.python.org/pep-0257/) on docstrings.
- In this course: week 8 (*Code you can trust*) adds packaging, logging and pytest.
