---
title: "Python packaging and environments"
parent: Tool guides
nav_order: 9
---

# Python packaging and environments

This guide covers how Python finds code, how to turn your code into an installable **package**, and how to keep
each project's libraries separate in a **virtual environment**. It is the reference for Week 8 (notebook 29 and the
lab, notebook 32) and is used again whenever you install something, build a Docker image (Week 10) or set up CI.

## What it is, and why teams use it

Code in a notebook can only be used by that notebook. Code in a package can be installed and imported by any
notebook, script, test, web service or scheduled job, in exactly one version. Teams package their code because:

* **one definition**: a feature function fixed once is fixed everywhere, instead of in one of five copies;
* **testability**: pytest imports the package like any user would (notebook 30);
* **deployability**: `pip install .` inside a Docker image or on a server is all it takes to ship it;
* **commands**: a package can install terminal commands, so the same code runs from a scheduler or CI job.

Environments solve the other half of the problem: project A needs pandas 2.1, project B needs pandas 2.2. Each
project gets its own isolated set of libraries, and a file that records them, so a teammate (or a server) can
recreate it exactly.

## Opening it

**In Google Colab** everything is already there: `pip` and `setuptools` are installed and the notebook runs as an
administrator. Install with `%pip install ...` in a cell. There is no need for virtual environments in Colab: each
session is a fresh, throw-away machine.

**On your own computer** (Week 10 sets this up in VS Code):

```bash
python --version                  # 3.9 or newer; on some systems the command is python3
python -m venv .venv              # create a virtual environment in the folder .venv
source .venv/bin/activate         # activate it (macOS/Linux)
.venv\Scripts\activate            # activate it (Windows PowerShell)
python -m pip install --upgrade pip
python -m pip install -e .        # install the project in this folder, editable
```

Once activated, your terminal prompt shows `(.venv)`, and `python` and `pip` refer to the environment's copies.
`deactivate` leaves it. Add `.venv/` to `.gitignore`: environments are rebuilt, never committed.

## How Python finds code

When you write `import shopfeat`, Python looks through the folders listed in `sys.path`, in order, for a file
`shopfeat.py` or a folder `shopfeat/` containing `__init__.py`. `sys.path` contains:

1. the folder of the script you ran (or, for `python -m ...` and notebooks, the current folder);
2. folders in the `PYTHONPATH` environment variable, if set;
3. the environment's `site-packages` folder, where `pip` installs things (and where editable installs leave a link).

```python
import sys
print(sys.path)                     # where Python will look
import pandas
print(pandas.__file__)              # where a module was actually found
```

Two consequences to remember:

* **Importing runs the file**, once. Keep top-level code to definitions: functions, classes, constants. Put
  script-like code under `if __name__ == "__main__":`.
* **Modules are cached** in `sys.modules`. Importing again returns the cached version, even if the file changed. In a
  notebook: restart the kernel, use `importlib.reload(module)`, or start a fresh process (`!python ...`).

## Modules, packages and the src layout

```
shopfeat/                   <- project folder (a Git repository)
├── pyproject.toml          <- the package description
├── README.md
├── src/
│   └── shopfeat/           <- the package: what `import shopfeat` loads
│       ├── __init__.py     <- runs on `import shopfeat`
│       ├── features.py     <- shopfeat.features
│       ├── report.py
│       └── cli.py
└── tests/
    └── test_features.py
```

* A **module** is one `.py` file. A **package** is a folder of modules with an `__init__.py`.
* Inside the package, import siblings **relatively**: `from .features import order_values` (the dot means "this
  package"). Outside, use the full name: `from shopfeat.features import order_values`.
* `__init__.py` usually holds `__version__ = "0.1.0"` and re-exports the main functions, so users can write
  `shopfeat.order_values`. Keep it light: no data loading, no heavy work.
* The **`src/` layout** (package inside `src/`) means the package cannot be imported by accident from the project
  folder; it must be installed. Your tests then exercise what users actually get. It is the layout recommended by
  the Python Packaging Authority and used in this course.

## pyproject.toml

`pyproject.toml` is the standard file describing a Python project. It is written in **TOML**: `key = value` lines,
grouped under `[table]` headers; strings in double quotes, lists in square brackets.

```toml
[build-system]                          # how to build the package (copy as is)
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "shopfeat"                       # name for pip (pip install shopfeat, pip show shopfeat)
version = "0.1.0"                       # MAJOR.MINOR.PATCH
description = "Features and reports for the shop data"
readme = "README.md"                    # optional
requires-python = ">=3.9"
dependencies = [                        # installed automatically with the package
    "pandas>=2.0",
    "scikit-learn>=1.4",
]

[project.optional-dependencies]
dev = ["pytest>=8"]                     # pip install -e ".[dev]" also installs these

[project.scripts]
shopfeat-summary = "shopfeat.cli:main"  # a terminal command that calls shopfeat/cli.py: main()

[tool.pytest.ini_options]               # settings for other tools live under [tool.<name>]
testpaths = ["tests"]
```

Notes:

* setuptools finds packages under `src/` automatically. If it does not (an unusual layout), add
  `[tool.setuptools.packages.find]` with `where = ["src"]`.
* **Versions**: raise PATCH for a bug fix, MINOR for a new feature that does not break users, MAJOR for a change
  that does. Keep `__version__` in `__init__.py` equal to the `version` in `pyproject.toml` (or read it at runtime
  with `importlib.metadata.version("shopfeat")`).
* **Dependency ranges** in `pyproject.toml` say what the package *works with* (`pandas>=2.0`), not exact versions:
  a library pinned to one exact version cannot be installed next to anything else.

## Installing

| command | what it does |
|---|---|
| `pip install -e .` | **editable** install of the project in the current folder: links to your source, so edits are picked up without reinstalling |
| `pip install .` | normal install: copies a snapshot; edits need a reinstall. Used in Docker images and deployments |
| `pip install -e ".[dev]"` | editable, plus the `dev` optional dependencies |
| `pip install -r requirements.txt` | install every line of a requirements file |
| `pip show shopfeat` | version, location, and for editable installs the project folder |
| `pip list` | everything installed in this environment |
| `pip uninstall shopfeat` | remove it |

Re-install (even editable) after you change `pyproject.toml`: new dependencies and new commands are only set up at
install time.

**Always use the pip that belongs to your Python.** `python -m pip install ...` in a terminal, `%pip install ...` in
a notebook. A bare `pip` may belong to a different Python on your computer, which leads to "I installed it but
import fails".

## Commands (entry points)

A function becomes a terminal command in two steps:

```python
# src/shopfeat/cli.py
import argparse

def main(argv=None):                       # argv=None: read the real command line
    parser = argparse.ArgumentParser(description="Summarise active customers.")
    parser.add_argument("orders_csv")                          # positional, required
    parser.add_argument("--cutoff", required=True)             # option, required
    parser.add_argument("--top", type=int, default=5)          # option with type and default
    parser.add_argument("--set", action="append", default=[])  # repeatable: a list
    args = parser.parse_args(argv)
    ...
    return 0                               # 0 means success to the shell
```

```toml
[project.scripts]
shopfeat-summary = "shopfeat.cli:main"
```

After `pip install -e .`, `shopfeat-summary data/orders.csv --cutoff 2025-06-30` works in any terminal where the
environment is active, and `shopfeat-summary --help` prints a usage message generated by argparse. Because `main`
takes `argv`, tests can call `main(["data/orders.csv", "--cutoff", "2025-06-30"])` directly.

You can also run a module directly with `python -m shopfeat.cli ...` if it ends with
`if __name__ == "__main__": raise SystemExit(main())`.

## Recording environments: requirements files and lock files

`pyproject.toml` lists what your *package* needs. An *application* run (a training job, a service, a CI run) also
needs a record of the **exact** versions used, so it can be recreated:

```bash
python -m pip freeze > requirements-lock.txt     # every installed package with its exact version
python -m pip install -r requirements-lock.txt   # recreate the same set elsewhere
```

A common arrangement, used in this course's repository:

* `pyproject.toml` (or `requirements.txt`) with ranges: what the code needs;
* a lock or "tested versions" file with exact versions: what was actually run, for reproducibility;
* Docker images (Week 10) that freeze the whole operating system as well.

Tools such as `uv`, `pip-tools` and Poetry automate locking. They are worth learning on the job; the ideas are the
same.

## Common errors and how to read them

* **`ModuleNotFoundError: No module named 'shopfeat'`.** Python did not find it on `sys.path`. Is it installed
  *in this environment* (`python -m pip show shopfeat`)? Did you activate the right environment? In a notebook that
  was running before the install, restart the kernel. With the src layout, running from the project folder is not
  enough: install it.
* **`ImportError: attempted relative import with no known parent package`.** You ran a file inside a package
  directly (`python src/shopfeat/report.py`). Run it as part of the package (`python -m shopfeat.report`) or through
  its command.
* **The old code still runs after an edit.** Module caching: restart, reload, or use a fresh process. If you used
  `pip install .` (not `-e`), reinstall.
* **`error: Multiple top-level packages discovered in a flat-layout`.** setuptools found several folders next to
  `pyproject.toml` and does not know which is the package. Use the src layout.
* **`tomllib.TOMLDecodeError` / "Invalid TOML".** A syntax slip: a missing quote, a table declared twice (easy to
  do by appending `[project.scripts]` twice), or a list without brackets. The message gives the line and column.
* **The command is not found after install.** Re-install after adding `[project.scripts]`; check the environment is
  active; on Windows, reopen the terminal.
* **`Running pip as the 'root' user ...` warning in Colab.** Harmless there: Colab is a throw-away machine. On
  your own computer, use a virtual environment instead of installing as administrator.
* **Version conflicts (`... requires pandas<2, but you have pandas 2.2`).** Two packages want incompatible
  versions. Use a separate environment per project, and loosen over-strict pins in your own `pyproject.toml`.

## Cheat sheet

```bash
# environments
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
deactivate

# install
python -m pip install -e .                # editable, from the project folder
python -m pip install -e ".[dev]"         # plus optional dev dependencies
python -m pip install -r requirements.txt
python -m pip freeze > requirements-lock.txt

# inspect
python -m pip show shopfeat               # version and location
python -c "import shopfeat, sys; print(shopfeat.__file__); print(sys.path)"
```

```python
# in a notebook
%pip install -q -e /content/work/shopfeat
import importlib; importlib.reload(module)            # re-read an edited module
import importlib.metadata; importlib.metadata.version("shopfeat")

# inside a package
from .features import order_values        # relative import of a sibling module
if __name__ == "__main__":                # only when run as a script
    raise SystemExit(main())
```

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "mypkg"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = ["pandas>=2.0"]

[project.scripts]
mycommand = "mypkg.cli:main"
```

## Where to go next

* Python Packaging User Guide, "Packaging Python Projects": <https://packaging.python.org/en/latest/tutorials/packaging-projects/>
* `pyproject.toml` reference: <https://packaging.python.org/en/latest/guides/writing-pyproject-toml/>
* `venv` documentation: <https://docs.python.org/3/library/venv.html>
* `argparse` tutorial: <https://docs.python.org/3/howto/argparse.html>
* In this course: notebook 29 (from notebook to package), notebook 32 (the `churnkit` lab), the [pytest](pytest.html)
  guide, and Week 10 (VS Code, Docker and CI), which install the same package in new places.
