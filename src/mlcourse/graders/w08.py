"""Week 8 graders: code you can trust (notebooks 29-32).

Most answers this week are FILES that students write with %%writefile into a working folder
(`work_dir()`): a package, a pyproject.toml, a test suite. The graders therefore

* import a student's package freshly from its folder every time (`load_module`), so an edited file is
  always re-read and a stale import never hides a change;
* run a student's TESTS in a separate pytest process against a correct reference implementation (the
  tests must pass) and against copies with one realistic bug planted each (the tests must fail). This is
  "mutation grading": it measures whether the tests would protect you, not how they are written.

Reference implementations here are written independently of the notebook solutions.
"""
from __future__ import annotations

import ast
import contextlib
import importlib
import io
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, fields, is_dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from mlcourse.grader import exercise, register_quiz

# ============================================================================================ helpers


def work_dir() -> Path:
    """The folder where this week's projects are written: /content/work in Colab, <course>/work locally."""
    if "google.colab" in sys.modules:
        path = Path("/content/work")
    else:
        from mlcourse.paths import repo_root
        path = repo_root(Path(__file__).resolve().parent) / "work"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_module(project, module: str):
    """Import `module` (e.g. "shopfeat.features") from `project`/src, always re-reading the files.

    Python caches imports: after you edit a file, a plain `import` keeps the old version. This helper forgets
    the cached package first, so you always get what is on disk now.
    """
    src = Path(project) / "src"
    top = module.split(".")[0]
    for name in list(sys.modules):
        if name == top or name.startswith(top + "."):
            del sys.modules[name]
    importlib.invalidate_caches()
    sys.path.insert(0, str(src))
    try:
        return importlib.import_module(module)
    finally:
        with contextlib.suppress(ValueError):
            sys.path.remove(str(src))


def show_tree(path, prefix: str = "") -> None:
    """Print a folder as a tree (skips caches and build folders)."""
    path = Path(path)
    if not prefix:
        print(path.name + "/")
    skip = {"__pycache__", ".pytest_cache", "build", "dist"}
    entries = sorted([p for p in path.iterdir() if p.name not in skip and not p.name.endswith(".egg-info")],
                     key=lambda p: (p.is_file(), p.name))
    for i, p in enumerate(entries):
        last = i == len(entries) - 1
        print(prefix + ("└── " if last else "├── ") + p.name + ("/" if p.is_dir() else ""))
        if p.is_dir():
            show_tree(p, prefix + ("    " if last else "│   "))


def _project(answer) -> Path:
    if not isinstance(answer, (str, Path)):
        raise AssertionError("pass the project FOLDER (a path), for example grade(..., PROJECT)")
    p = Path(answer)
    if not p.is_dir():
        raise AssertionError(f"the folder {p} does not exist yet: run the %%writefile cells above first")
    return p


def _need_file(path: Path, what: str) -> str:
    if not path.is_file():
        raise AssertionError(f"{what} not found at {path}: did the %%writefile cell run, with this exact path?")
    text = path.read_text()
    if "NotImplementedError" in text or "YOUR CODE HERE" in text:
        raise NotImplementedError
    return text


def _also_import(project: Path, module: str):
    """Import another module of a package that was just loaded with load_module, without forgetting it."""
    if module in sys.modules:
        return sys.modules[module]
    src = str(Path(project) / "src")
    sys.path.insert(0, src)
    try:
        return importlib.import_module(module)
    finally:
        with contextlib.suppress(ValueError):
            sys.path.remove(src)


def _quiet_import(project: Path, module: str):
    """Import freshly and return (module, what it printed)."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            mod = load_module(project, module)
    except NotImplementedError:
        raise
    except SyntaxError as err:
        raise AssertionError(f"{module} has a syntax error on line {err.lineno}: {err.msg}") from None
    except ImportError as err:
        raise AssertionError(f"importing {module} failed: {err}") from None
    return mod, buf.getvalue()


def _toml(path: Path) -> dict:
    try:
        import tomllib
    except ModuleNotFoundError:  # Python < 3.11
        import tomli as tomllib  # type: ignore
    text = _need_file(path, "pyproject.toml")
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as err:
        raise AssertionError(f"pyproject.toml is not valid TOML: {err}") from None


def _python_env() -> dict:
    env = {k: v for k, v in os.environ.items() if k not in {"PYTEST_ADDOPTS", "MLCOURSE_GRADE_LOG"}}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


# ------------------------------------------------------------------------------- mutation grading
@dataclass(frozen=True)
class Bug:
    name: str
    description: str          # shown when the tests MISS this bug: describes the defect, not the test
    edits: tuple              # ((file, old, new), ...)


def _apply(files: dict, bug: Bug | None) -> dict:
    out = dict(files)
    for rel, old, new in (bug.edits if bug else ()):
        if out[rel].count(old) != 1:
            raise RuntimeError(f"grader error: bug {bug.name} does not apply cleanly")
        out[rel] = out[rel].replace(old, new)
    return out


def _run_pytest(tests: dict, package: dict, timeout: int = 120) -> tuple[int, str]:
    """Run test files {name: text} against package files {relpath: text} in a fresh process."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for rel, text in package.items():
            (tmp / "pkg" / rel).parent.mkdir(parents=True, exist_ok=True)
            (tmp / "pkg" / rel).write_text(text)
        (tmp / "run" / "tests").mkdir(parents=True)
        for name, text in tests.items():
            (tmp / "run" / "tests" / name).write_text(text)
        env = _python_env()
        env["PYTHONPATH"] = str(tmp / "pkg")
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "tests", "-q", "-x", "-p", "no:cacheprovider",
                 "--rootdir", str(tmp / "run")],
                cwd=tmp / "run", env=env, capture_output=True, text=True, timeout=timeout)
            return proc.returncode, proc.stdout + proc.stderr
        except subprocess.TimeoutExpired:
            return 124, f"the tests did not finish within {timeout} s"


def _read_tests(path: Path) -> dict:
    if path.is_dir():
        files = {p.name: p.read_text() for p in sorted(path.glob("test_*.py"))}
        if not files:
            raise AssertionError(f"no test_*.py files in {path}: pytest only collects files named test_*.py")
    else:
        if not path.is_file():
            raise AssertionError(f"{path} does not exist: did the %%writefile cell run?")
        if not path.name.startswith("test_"):
            raise AssertionError(f"{path.name}: pytest only collects files whose name starts with test_")
        files = {path.name: path.read_text()}
    text = "\n".join(files.values())
    if "NotImplementedError" in text or "YOUR CODE HERE" in text:
        raise NotImplementedError
    for name, t in files.items():
        try:
            ast.parse(t)
        except SyntaxError as err:
            raise AssertionError(f"{name} has a syntax error on line {err.lineno}: {err.msg}") from None
    return files


def _last_lines(output: str, n: int = 12) -> str:
    lines = [ln for ln in output.strip().splitlines() if ln.strip()]
    return "\n".join(lines[-n:])


def mutation_grade(tests_path, package: dict, bugs: list[Bug]) -> None:
    tests = _read_tests(Path(tests_path))
    with ThreadPoolExecutor(max_workers=min(6, (os.cpu_count() or 2) + 1)) as pool:
        ref_future = pool.submit(_run_pytest, tests, package)
        bug_futures = [pool.submit(_run_pytest, tests, _apply(package, b)) for b in bugs]
        code, out = ref_future.result()
        results = [f.result() for f in bug_futures]
    if code == 5:
        raise AssertionError("pytest collected no tests: test functions must be named test_something")
    if code != 0:
        raise AssertionError("your tests FAIL on the correct code, so they would raise false alarms. "
                             "pytest said:\n" + _last_lines(out))
    missed = [b for b, (c, _) in zip(bugs, results) if c == 0]
    if missed:
        listing = "\n".join(f"  - {b.description}" for b in missed)
        raise AssertionError(f"your tests pass on the correct code (good) but did not catch {len(missed)} of "
                             f"{len(bugs)} planted bugs. They still pass on a version where:\n{listing}")


# ===================================================================================== shared data


def _items_small() -> pd.DataFrame:
    return pd.DataFrame({
        "order_id": [7, 7, 9, 12, 12, 12],
        "product_id": [1, 2, 1, 3, 4, 5],
        "quantity": [2, 1, 1, 3, 1, 2],
        "unit_price": [10.0, 5.0, 40.0, 2.5, 100.0, 1.0],
        "discount": [0.0, 0.2, 0.5, 0.0, 0.1, 0.0],
    })


_ITEMS_EXPECTED = {7: 24.0, 9: 20.0, 12: 99.5}


def _orders_small() -> pd.DataFrame:
    rows = [
        (1, 10, "2025-01-05", "delivered"), (2, 10, "2025-03-01", "delivered"), (3, 10, "2025-04-10", "delivered"),
        (4, 11, "2025-02-01", "cancelled"), (5, 11, "2025-04-02", "delivered"),
        (6, 12, "2025-03-31", "delivered"),
        (8, 13, "2025-01-20", "returned"), (9, 13, "2025-03-20", "cancelled"),
        (10, 14, "2025-02-14", "delivered"), (11, 14, "2025-03-30", "shipped"),
        (12, 15, "2025-04-01", "delivered"),
    ]
    df = pd.DataFrame(rows, columns=["order_id", "customer_id", "order_date", "status"])
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


_SMALL_CUTOFF = "2025-03-31"
_DAYS_EXPECTED = {10: 30, 12: 0, 13: 70, 14: 1}


def _as_series(result, what: str) -> pd.Series:
    if isinstance(result, pd.DataFrame) and result.shape[1] == 1:
        result = result.iloc[:, 0]
    if not isinstance(result, pd.Series):
        raise AssertionError(f"{what} should return a pandas Series, got {type(result).__name__}")
    return result


def _check_order_values(fn) -> None:
    items = _items_small()
    before = items.copy()
    out = _as_series(fn(items), "order_values")
    if not items.equals(before):
        raise AssertionError("order_values changed the DataFrame it was given: work on a copy or new columns only")
    got = {int(k): float(v) for k, v in out.items()}
    if sorted(got) != sorted(_ITEMS_EXPECTED):
        raise AssertionError(f"expected one value per order_id {sorted(_ITEMS_EXPECTED)}, got index {sorted(got)}")
    for k, v in _ITEMS_EXPECTED.items():
        if abs(got[k] - v) > 1e-6:
            raise AssertionError(f"order {k}: expected {v}, got {got[k]}. Value of a line is "
                                 "quantity × unit_price × (1 − discount), summed over the order's lines")
    one = fn(items[items["order_id"] == 9])
    if len(_as_series(one, "order_values")) != 1:
        raise AssertionError("with a single order, expected a single value")
    empty = _as_series(fn(items.iloc[0:0]), "order_values")
    if len(empty) != 0:
        raise AssertionError("with no items, expected an empty Series")


def _check_days(fn) -> None:
    orders = _orders_small()
    before = orders.copy()
    out = _as_series(fn(orders, _SMALL_CUTOFF), "days_since_last_order")
    if not orders.equals(before):
        raise AssertionError("days_since_last_order changed the DataFrame it was given")
    got = {int(k): v for k, v in out.items()}
    if 11 in got:
        raise AssertionError("customer 11's only order on or before the cutoff was cancelled, so they should not appear")
    if 15 in got:
        raise AssertionError("customer 15's first order is after the cutoff: they should not appear")
    if sorted(got) != sorted(_DAYS_EXPECTED):
        raise AssertionError(f"expected customers {sorted(_DAYS_EXPECTED)}, got {sorted(got)}")
    for k, v in _DAYS_EXPECTED.items():
        if int(got[k]) != v:
            hint = " (an order ON the cutoff day counts: 0 days)" if k == 12 else ""
            hint = hint or (" (cancelled orders do not count)" if k == 13 else "")
            raise AssertionError(f"customer {k}: expected {v} days, got {got[k]}{hint}")
    if any(isinstance(v, pd.Timedelta) for v in got.values()):
        raise AssertionError("return whole days as numbers (use .dt.days), not Timedelta values")
    out2 = _as_series(fn(orders, pd.Timestamp("2025-04-10")), "days_since_last_order")
    if int(out2.loc[10]) != 0 or int(out2.loc[15]) != 9:
        raise AssertionError("with cutoff 2025-04-10 the numbers are wrong: does the function use the cutoff argument?")


# ================================================================================ notebook 29


@exercise("w08.order_values", hint="Multiply the three columns, then group the line values by order_id and sum.")
def _t_order_values(fn):
    _check_order_values(fn)


@exercise("w08.days_since_last_order",
          hint="Drop cancelled orders, keep order_date <= cutoff, take each customer's max date, subtract from the cutoff.")
def _t_days(fn):
    _check_days(fn)


@exercise("w08.features_module", hint="The file is src/shopfeat/features.py inside PROJECT, with both functions and "
                                       "their imports at the top, and nothing that prints or runs at import time.")
def _t_features_module(answer):
    project = _project(answer)
    _need_file(project / "src" / "shopfeat" / "features.py", "src/shopfeat/features.py")
    mod, printed = _quiet_import(project, "shopfeat.features")
    if printed.strip():
        raise AssertionError(f"importing shopfeat.features printed {printed.strip()[:80]!r}: a module should only "
                             "define things when imported, not run them")
    for name in ("order_values", "days_since_last_order"):
        if not callable(getattr(mod, name, None)):
            raise AssertionError(f"shopfeat.features has no function {name}")
    _check_order_values(mod.order_values)
    _check_days(mod.days_since_last_order)


@exercise("w08.main_guard", hint="Put the work in make_report(orders); put the demo under "
                                 "if __name__ == \"__main__\": at the bottom.")
def _t_main_guard(answer):
    if not isinstance(answer, (str, Path)):
        raise AssertionError("pass the path of the script file")
    path = Path(answer)
    _need_file(path, path.name)
    import importlib.util
    spec = importlib.util.spec_from_file_location("_w08_report_check", path)
    mod = importlib.util.module_from_spec(spec)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        spec.loader.exec_module(mod)
    if buf.getvalue().strip():
        raise AssertionError("importing the script still prints the report: move the demo under the __main__ guard")
    if not callable(getattr(mod, "make_report", None)):
        raise AssertionError("the script needs a function make_report(orders)")
    df = pd.DataFrame({"customer_id": [4, 5, 5, 6], "value": [1.25, 2.0, 3.0, 4.0]})
    got = mod.make_report(df)
    if not isinstance(got, str):
        raise AssertionError("make_report should RETURN the text (a str), not print it")
    if got.strip() != "Report: 4 orders, total 10.25":
        raise AssertionError(f"for 4 orders worth 10.25 in total, expected 'Report: 4 orders, total 10.25', got {got!r}")
    run = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, timeout=60, env=_python_env())
    if run.returncode != 0:
        raise AssertionError("running the script with python failed:\n" + _last_lines(run.stderr, 5))
    if "Report: 3 orders, total 22.50" not in run.stdout:
        raise AssertionError(f"running the script should print the demo report 'Report: 3 orders, total 22.50'; "
                             f"it printed {run.stdout.strip()!r}")


@exercise("w08.package_init", hint="In __init__.py: __version__ = \"0.1.0\" and "
                                   "from .features import order_values, days_since_last_order")
def _t_package_init(answer):
    project = _project(answer)
    _need_file(project / "src" / "shopfeat" / "__init__.py", "src/shopfeat/__init__.py")
    pkg, printed = _quiet_import(project, "shopfeat")
    if printed.strip():
        raise AssertionError("importing shopfeat printed something: __init__.py should only import and define")
    v = getattr(pkg, "__version__", None)
    if not isinstance(v, str) or not re.fullmatch(r"\d+\.\d+\.\d+", v):
        raise AssertionError(f"shopfeat.__version__ should be a version string like \"0.1.0\", got {v!r}")
    feats = sys.modules["shopfeat.features"] if "shopfeat.features" in sys.modules else None
    for name in ("order_values", "days_since_last_order"):
        obj = getattr(pkg, name, None)
        if obj is None:
            raise AssertionError(f"`import shopfeat; shopfeat.{name}` does not work: re-export it in __init__.py")
        if feats is None or obj is not getattr(feats, name, None):
            raise AssertionError(f"shopfeat.{name} should be the function from shopfeat/features.py (imported, "
                                 "not a second copy)")


def _summary_reference(orders, items, cutoff):
    cutoff = pd.Timestamp(cutoff)
    v = (items.quantity * items.unit_price * (1 - items.discount)).groupby(items.order_id).sum()
    o = orders[(orders.status != "cancelled") & (orders.order_date <= cutoff)].copy()
    o["v"] = o.order_id.map(v).fillna(0.0)
    g = o.groupby("customer_id")
    return pd.DataFrame({"n_orders": g.size(), "total_spent": g.v.sum(),
                         "days_since_last_order": (cutoff - g.order_date.max()).dt.days})


def _shop_orders_items():
    from mlcourse.sql import sql
    orders = sql("SELECT * FROM orders", "shop")
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    items = sql("SELECT * FROM order_items", "shop")
    return orders, items


@exercise("w08.report_module", hint="Start report.py with `from .features import order_values, "
                                    "days_since_last_order` and build the summary from them.")
def _t_report_module(answer):
    project = _project(answer)
    text = _need_file(project / "src" / "shopfeat" / "report.py", "src/shopfeat/report.py")
    tree = ast.parse(text)
    defined = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    if defined & {"order_values", "days_since_last_order"}:
        raise AssertionError("report.py defines its own copy of a feature function: import it from the features "
                             "module instead (one definition, used everywhere)")
    imports_features = any(isinstance(n, ast.ImportFrom) and (n.module or "").endswith("features")
                           for n in ast.walk(tree))
    if not imports_features:
        raise AssertionError("report.py should import what it needs from the features module "
                             "(from .features import ...)")
    mod, _ = _quiet_import(project, "shopfeat.report")
    fn = getattr(mod, "customer_summary", None)
    if not callable(fn):
        raise AssertionError("report.py needs a function customer_summary(orders, items, cutoff)")
    orders, items = _shop_orders_items()
    for cutoff in ("2025-06-30", "2025-09-30"):
        got = fn(orders.copy(), items.copy(), cutoff)
        if not isinstance(got, pd.DataFrame):
            raise AssertionError("customer_summary should return a DataFrame")
        exp = _summary_reference(orders, items, cutoff)
        missing = {"n_orders", "total_spent", "days_since_last_order"} - set(got.columns)
        if missing:
            raise AssertionError(f"missing columns: {sorted(missing)}")
        if "customer_id" in got.columns:
            got = got.set_index("customer_id")
        if len(got) != len(exp):
            raise AssertionError(f"cutoff {cutoff}: expected {len(exp)} active customers, got {len(got)} rows")
        got = got.reindex(exp.index)
        if got.isna().any().any():
            raise AssertionError("some active customers are missing: index the result by customer_id")
        for col in exp.columns:
            if not np.allclose(got[col].astype(float), exp[col].astype(float), atol=0.01):
                raise AssertionError(f"cutoff {cutoff}: column {col} has wrong values for some customers")


@exercise("w08.pyproject", hint="Three tables: [build-system] (requires, build-backend), [project] (name, version, "
                                "requires-python, dependencies).")
def _t_pyproject(answer):
    project = _project(answer)
    data = _toml(project / "pyproject.toml")
    bs = data.get("build-system")
    if not bs:
        raise AssertionError("no [build-system] table: pip needs it to know how to build the package")
    if not any(str(r).startswith("setuptools") for r in bs.get("requires", [])):
        raise AssertionError("[build-system] requires should list setuptools")
    if bs.get("build-backend") != "setuptools.build_meta":
        raise AssertionError("[build-system] build-backend should be \"setuptools.build_meta\"")
    proj = data.get("project")
    if not proj:
        raise AssertionError("no [project] table")
    if proj.get("name") != "shopfeat":
        raise AssertionError(f"[project] name should be \"shopfeat\", got {proj.get('name')!r}")
    if not isinstance(proj.get("version"), str):
        raise AssertionError("[project] needs a version string")
    if "requires-python" not in proj:
        raise AssertionError("[project] should say which Python versions it supports (requires-python)")
    deps = proj.get("dependencies", [])
    if not any(re.match(r"pandas\b", str(d)) for d in deps):
        raise AssertionError("shopfeat uses pandas, so dependencies should list it")
    init = project / "src" / "shopfeat" / "__init__.py"
    if init.is_file():
        m = re.search(r"__version__\s*=\s*[\"']([^\"']+)", init.read_text())
        if m and m.group(1) != proj["version"]:
            raise AssertionError(f"pyproject says version {proj['version']} but __init__.py says {m.group(1)}: "
                                 "keep them the same")


@exercise("w08.installed_version", hint="Run the pip install cell above first, then use "
                                        "importlib.metadata.version(\"shopfeat\").")
def _t_installed(answer):
    if not isinstance(answer, str):
        raise AssertionError("installed_version should be a string such as \"0.1.0\"")
    project = work_dir() / "shopfeat"
    import importlib.metadata as md
    try:
        real = md.version("shopfeat")
    except md.PackageNotFoundError:
        raise AssertionError("shopfeat is not installed: run the `pip install -e` cell and read its output") from None
    if answer != real:
        raise AssertionError(f"installed_version is {answer!r} but pip has shopfeat {real} installed")
    with tempfile.TemporaryDirectory() as tmp:
        env = _python_env()
        run = subprocess.run([sys.executable, "-c", "import shopfeat; print(shopfeat.__file__)"],
                             cwd=tmp, capture_output=True, text=True, timeout=60, env=env)
    if run.returncode != 0:
        raise AssertionError("a fresh Python started in another folder cannot import shopfeat:\n"
                             + _last_lines(run.stderr, 4))
    where = Path(run.stdout.strip()).resolve()
    if (project / "src").resolve() not in where.parents:
        raise AssertionError(f"shopfeat is imported from {where}, not from your project: install it with "
                             "`pip install -e` (editable) from the project folder")


def _write_csvs(tmp: Path):
    orders, items = _shop_orders_items()
    orders.to_csv(tmp / "orders.csv", index=False)
    items.to_csv(tmp / "order_items.csv", index=False)
    return orders, items


@exercise("w08.cli_main", hint="argparse: two positional arguments, --cutoff with required=True; print(json.dumps(...)); "
                               "return 0.")
def _t_cli(answer):
    project = _project(answer)
    _need_file(project / "src" / "shopfeat" / "cli.py", "src/shopfeat/cli.py")
    mod, _ = _quiet_import(project, "shopfeat.cli")
    main = getattr(mod, "main", None)
    if not callable(main):
        raise AssertionError("cli.py needs a function main(argv=None)")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        orders, items = _write_csvs(tmp)
        for cutoff in ("2025-06-30", "2025-03-31"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = main([str(tmp / "orders.csv"), str(tmp / "order_items.csv"), "--cutoff", cutoff])
            if code not in (0, None):
                raise AssertionError(f"main should return 0 on success, returned {code!r}")
            try:
                out = json.loads(buf.getvalue())
            except json.JSONDecodeError:
                raise AssertionError("main should print exactly one JSON object (use json.dumps); it printed "
                                     f"{buf.getvalue()[:120]!r}") from None
            exp = _summary_reference(orders, items, cutoff)
            for key in ("cutoff", "active_customers", "total_spent"):
                if key not in out:
                    raise AssertionError(f"the JSON should have a key {key!r}")
            if out["cutoff"] != cutoff:
                raise AssertionError("the JSON's cutoff should repeat the --cutoff value as given")
            if int(out["active_customers"]) != len(exp):
                raise AssertionError(f"cutoff {cutoff}: expected {len(exp)} active customers, got {out['active_customers']}")
            if abs(float(out["total_spent"]) - round(exp.total_spent.sum(), 2)) > 0.011:
                raise AssertionError(f"cutoff {cutoff}: total_spent should be {round(exp.total_spent.sum(), 2)}, "
                                     f"got {out['total_spent']}")
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            try:
                main([str(tmp / "orders.csv"), str(tmp / "order_items.csv")])
            except SystemExit as exc:
                if exc.code == 0:
                    raise AssertionError("without --cutoff the command should fail, not succeed") from None
            else:
                raise AssertionError("without --cutoff the command should stop with a usage error "
                                     "(make --cutoff required)")


@exercise("w08.entry_point", hint="[project.scripts] then shopfeat-summary = \"package.module:function\"")
def _t_entry(answer):
    project = _project(answer)
    data = _toml(project / "pyproject.toml")
    scripts = data.get("project", {}).get("scripts")
    if not scripts:
        raise AssertionError("no [project.scripts] table in pyproject.toml")
    if "shopfeat-summary" not in scripts:
        raise AssertionError(f"the command should be called shopfeat-summary; found {sorted(scripts)}")
    target = str(scripts["shopfeat-summary"]).replace(" ", "")
    if target != "shopfeat.cli:main":
        raise AssertionError(f"shopfeat-summary points to {target!r}: it should name the module and the function "
                             "that runs the command")


register_quiz("w08.29_q1", "c",
              "One definition in a package, imported everywhere: a fix in one place reaches every notebook and script.",
              {"a": "Packages do not make code faster.",
               "b": "Notebooks can be versioned too; the problem is copies of the same code drifting apart.",
               "d": "Packaging does not test anything by itself; it makes code importable and testable."})
register_quiz("w08.29_q2", "b",
              "Python caches modules in sys.modules: a second `import` returns the cached module. Restart, reload, or "
              "use a helper that forgets the cache.",
              {"a": "The file was saved; Python just did not read it again.",
               "c": "Notebook cells do not compile modules; the import system caches them.",
               "d": "There is no automatic reload on save in plain Python."})
register_quiz("w08.29_q3", "a",
              "With the code under src/, it is only importable after installing, so you test what users get, not a "
              "file that happens to be in the current folder.",
              {"b": "src layout does not change speed.",
               "c": "pip works with both layouts; src layout just prevents accidental imports from the working folder.",
               "d": "tests can live in tests/ with either layout."})
register_quiz("w08.29_q4", "d",
              "-e (editable) installs a link to your folder: edits are picked up by new Python processes without "
              "reinstalling. Changing pyproject.toml (dependencies, scripts) needs a re-install.",
              {"a": "A normal install copies the files; editable does not.",
               "b": "Editable installs work for any package with a pyproject.toml.",
               "c": "It still installs dependencies listed in pyproject.toml."})
register_quiz("w08.29_q5", "b",
              "Code under `if __name__ == \"__main__\":` runs only when the file is executed as a script, never when "
              "it is imported.",
              {"a": "It runs on `python file.py` too; that is its purpose.",
               "c": "It has nothing to do with speed or compiling.",
               "d": "Imports at the top still run; only the guarded block is skipped on import."})

# ================================================================================ notebook 30

FEATUREKIT = '''"""featurekit: small feature functions for the shop data (the code under test in notebook 30)."""
import numpy as np
import pandas as pd


def clean_city(name):
    """Tidy a city name: strip and collapse spaces, Title Case. Empty or missing -> None."""
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return None
    name = " ".join(str(name).split())
    if name == "":
        return None
    return name.title()


def order_values(items):
    """Value of each order: sum of quantity * unit_price * (1 - discount), indexed by order_id."""
    line = items["quantity"] * items["unit_price"] * (1 - items["discount"])
    return line.groupby(items["order_id"]).sum().rename("order_value")


def safe_ratio(numerator, denominator):
    """Element-wise numerator / denominator as a float array, with NaN where the denominator is 0."""
    num = np.asarray(numerator, dtype=float)
    den = np.asarray(denominator, dtype=float)
    out = np.full(num.shape, np.nan)
    np.divide(num, den, out=out, where=den != 0)
    return out


def spend_in_window(orders, cutoff, days):
    """Total `value` of non-cancelled orders per customer with cutoff - days < order_date <= cutoff."""
    cutoff = pd.Timestamp(cutoff)
    start = cutoff - pd.Timedelta(days=days)
    keep = (orders["status"] != "cancelled") & (orders["order_date"] > start) & (orders["order_date"] <= cutoff)
    return orders[keep].groupby("customer_id")["value"].sum().rename(f"spend_{days}d")


def days_since_last_order(orders, cutoff):
    """Whole days from each customer's last non-cancelled order on or before cutoff, to the cutoff."""
    cutoff = pd.Timestamp(cutoff)
    past = orders[(orders["status"] != "cancelled") & (orders["order_date"] <= cutoff)]
    return (cutoff - past.groupby("customer_id")["order_date"].max()).dt.days


def split_by_time(df, date_col, cutoff):
    """Rows dated on or before cutoff -> train, rows after it -> test (original row order kept)."""
    cutoff = pd.Timestamp(cutoff)
    return df[df[date_col] <= cutoff], df[df[date_col] > cutoff]


def standardize(train, test, columns):
    """Scale `columns` with the mean and std learned from TRAIN only. Returns new (train, test) frames."""
    mean = train[columns].mean()
    std = train[columns].std(ddof=0).replace(0, 1.0)
    train_out, test_out = train.copy(), test.copy()
    train_out[columns] = (train[columns] - mean) / std
    test_out[columns] = (test[columns] - mean) / std
    return train_out, test_out


def save_table(df, path):
    """Write a table to CSV (without the pandas index)."""
    df.to_csv(path, index=False)


def load_table(path, date_cols=()):
    """Read a table written by save_table, turning `date_cols` back into datetimes."""
    return pd.read_csv(path, parse_dates=list(date_cols))
'''

_FK = "featurekit.py"


def _fk_bug(name, description, old, new):
    return Bug(name, description, ((_FK, old, new),))


_B = {
    "city_no_title": _fk_bug("city_no_title", "clean_city does not change the capitalisation (\"almaty\" stays lower case)",
                             "    return name.title()", "    return name"),
    "city_empty": _fk_bug("city_empty", "clean_city returns \"\" instead of None for an empty or blank name",
                          '    if name == "":\n        return None\n', ""),
    "city_no_strip": _fk_bug("city_no_strip", "clean_city keeps the spaces around a name (\"  Almaty \")",
                             '    name = " ".join(str(name).split())', "    name = str(name)\n    if not name.strip():\n        name = \"\""),
    "city_inner": _fk_bug("city_inner", "clean_city strips the ends but keeps repeated spaces inside (\"New   York\")",
                          '    name = " ".join(str(name).split())', "    name = str(name).strip()"),
    "city_none": _fk_bug("city_none", "clean_city turns a missing value (None) into the text \"None\"",
                         "    if name is None or (isinstance(name, float) and np.isnan(name)):\n        return None\n", ""),
    "ov_plus": _fk_bug("ov_plus", "order_values ADDS the discount instead of subtracting it",
                       '(1 - items["discount"])', '(1 + items["discount"])'),
    "ov_no_qty": _fk_bug("ov_no_qty", "order_values ignores the quantity",
                         'line = items["quantity"] * items["unit_price"]', 'line = items["unit_price"]'),
    "ov_mean": _fk_bug("ov_mean", "order_values averages the lines of an order instead of adding them",
                       'line.groupby(items["order_id"]).sum()', 'line.groupby(items["order_id"]).mean()'),
    "ratio_inf": _fk_bug("ratio_inf", "safe_ratio returns inf (not NaN) when the denominator is 0",
                         "    np.divide(num, den, out=out, where=den != 0)\n",
                         "    with np.errstate(divide=\"ignore\", invalid=\"ignore\"):\n        out = num / den\n"),
    "ratio_zero": _fk_bug("ratio_zero", "safe_ratio returns 0 (not NaN) when the denominator is 0",
                          "    out = np.full(num.shape, np.nan)", "    out = np.zeros(num.shape)"),
    "ratio_flip": _fk_bug("ratio_flip", "safe_ratio divides the other way round (denominator / numerator)",
                          "    np.divide(num, den, out=out, where=den != 0)",
                          "    np.divide(den, num, out=out, where=(den != 0) & (num != 0))"),
    "win_cancelled": _fk_bug("win_cancelled", "spend_in_window counts cancelled orders",
                             'keep = (orders["status"] != "cancelled") & (orders["order_date"] > start)',
                             'keep = (orders["order_date"] > start)'),
    "win_start": _fk_bug("win_start", "spend_in_window includes an order exactly `days` days before the cutoff "
                                      "(the window should start just after that day)",
                         '(orders["order_date"] > start)', '(orders["order_date"] >= start)'),
    "win_future": _fk_bug("win_future", "spend_in_window also counts orders AFTER the cutoff (the future leaks in)",
                          ' & (orders["order_date"] <= cutoff)\n    return orders[keep]', '\n    return orders[keep]'),
    "split_boundary": _fk_bug("split_boundary", "split_by_time puts rows dated exactly on the cutoff into the test set",
                              "    return df[df[date_col] <= cutoff], df[df[date_col] > cutoff]",
                              "    return df[df[date_col] < cutoff], df[df[date_col] >= cutoff]"),
    "split_position": _fk_bug("split_position", "split_by_time counts the rows before the cutoff and then splits by "
                                                "POSITION, which is only right if the rows are sorted by date",
                              "    return df[df[date_col] <= cutoff], df[df[date_col] > cutoff]",
                              "    n = int((df[date_col] <= cutoff).sum())\n    return df.iloc[:n], df.iloc[n:]"),
    "std_all": _fk_bug("std_all", "standardize learns the mean from train AND test together (test rows leak into "
                                  "the scaling of the training data)",
                       "    mean = train[columns].mean()", "    mean = pd.concat([train, test])[columns].mean()"),
    "std_test_own": _fk_bug("std_test_own", "standardize scales the test rows with the TEST rows' own mean",
                            "    test_out[columns] = (test[columns] - mean) / std",
                            "    test_out[columns] = (test[columns] - test[columns].mean()) / std"),
    "std_inplace": _fk_bug("std_inplace", "standardize modifies the DataFrames it was given",
                           "    train_out, test_out = train.copy(), test.copy()", "    train_out, test_out = train, test"),
    "save_index": _fk_bug("save_index", "save_table also writes the pandas index, so loading adds an extra column",
                          "    df.to_csv(path, index=False)", "    df.to_csv(path)"),
    "load_dates": _fk_bug("load_dates", "load_table ignores date_cols, so dates come back as plain text",
                          "    return pd.read_csv(path, parse_dates=list(date_cols))", "    return pd.read_csv(path)"),
    "days_cancelled": _fk_bug("days_cancelled", "days_since_last_order counts cancelled orders",
                              'past = orders[(orders["status"] != "cancelled") & (orders["order_date"] <= cutoff)]',
                              'past = orders[orders["order_date"] <= cutoff]'),
    "days_future": _fk_bug("days_future", "days_since_last_order also looks at orders after the cutoff",
                           'past = orders[(orders["status"] != "cancelled") & (orders["order_date"] <= cutoff)]',
                           'past = orders[orders["status"] != "cancelled"]'),
    "days_strict": _fk_bug("days_strict", "days_since_last_order ignores an order placed ON the cutoff day",
                           '(orders["order_date"] <= cutoff)]\n    return (cutoff',
                           '(orders["order_date"] < cutoff)]\n    return (cutoff'),
}

COLLEAGUE_FEATUREKIT = _apply({_FK: FEATUREKIT}, _B["days_cancelled"])[_FK]


def _fk_grade(path, *bug_names):
    mutation_grade(path, {_FK: FEATUREKIT}, [_B[n] for n in bug_names])


@exercise("w08.test_clean_city", hint="Each test calls clean_city on one input and asserts the exact result: "
                                      "lower-case input, blank input.")
def _t_test_clean_city(path):
    _fk_grade(path, "city_no_title", "city_empty")


@exercise("w08.read_failure", hint="Look for the line starting with FAILED, and the `assert ... == ...` line "
                                   "with `where` underneath: it shows what the function returned.")
def _t_read_failure(answer):
    if not isinstance(answer, dict):
        raise AssertionError("failure should be a dict with keys 'test', 'expected', 'got'")
    missing = {"test", "expected", "got"} - set(answer)
    if missing:
        raise AssertionError(f"missing keys: {sorted(missing)}")
    if any(v is None for v in answer.values()):
        raise NotImplementedError
    name = str(answer["test"]).split("::")[-1].strip()
    if name != "test_ten_percent_off":
        raise AssertionError(f"{name!r} is not the test that failed: find the line that starts with FAILED")
    try:
        exp, got = float(answer["expected"]), float(answer["got"])
    except (TypeError, ValueError):
        raise AssertionError("expected and got should be numbers") from None
    if exp == 110.0 and got == 90.0:
        raise AssertionError("you swapped them: `expected` is what the test asserts, `got` is what the function returned")
    if exp != 90.0:
        raise AssertionError("`expected` is the value written in the test's assert")
    if got != 110.0:
        raise AssertionError("`got` is what apply_discount actually returned: pytest shows it in the assertion line")


@exercise("w08.test_order_values", hint="Build a tiny items table by hand (two orders, a discount), compute the "
                                        "expected values on paper, compare with pytest.approx.")
def _t_test_ov(path):
    _fk_grade(path, "ov_plus", "ov_no_qty", "ov_mean")


@exercise("w08.test_safe_ratio", hint="Include a zero denominator and check the result with np.isnan; also check "
                                      "one ordinary division.")
def _t_test_ratio(path):
    _fk_grade(path, "ratio_inf", "ratio_zero", "ratio_flip")


@exercise("w08.test_clean_city_param", hint="@pytest.mark.parametrize(\"raw, expected\", [...]) with at least four "
                                            "cases, including None and inner spaces.")
def _t_param(path):
    path = Path(path)
    if path.is_file() and "parametrize" not in path.read_text() and "YOUR CODE HERE" not in path.read_text():
        raise AssertionError("use @pytest.mark.parametrize for this one: one test function, many cases")
    if path.is_file() and "YOUR CODE HERE" not in path.read_text():
        cases = re.findall(r"\(\s*(?:None|['\"])", path.read_text())
        if len(cases) < 5:
            raise AssertionError("give at least four (input, expected) cases")
    _fk_grade(path, "city_no_title", "city_empty", "city_no_strip", "city_inner", "city_none")


@exercise("w08.test_spend_window", hint="A fixture returning a small orders table with: a cancelled order, an order "
                                        "exactly `days` before the cutoff, and an order after the cutoff.")
def _t_window(path):
    path = Path(path)
    if path.is_file() and "fixture" not in path.read_text() and "YOUR CODE HERE" not in path.read_text():
        raise AssertionError("build the orders table in a @pytest.fixture and use it in your tests")
    _fk_grade(path, "win_cancelled", "win_start", "win_future")


@exercise("w08.test_round_trip", hint="def test_...(tmp_path): save to tmp_path / \"t.csv\", load it back with "
                                      "date_cols, and compare with pd.testing.assert_frame_equal.")
def _t_round_trip(path):
    path = Path(path)
    if path.is_file() and "tmp_path" not in path.read_text() and "YOUR CODE HERE" not in path.read_text():
        raise AssertionError("use pytest's tmp_path fixture for the file, so the test never writes into your project")
    _fk_grade(path, "save_index", "load_dates")


@exercise("w08.test_standardize", hint="Test what must hold if only train was used: train columns have mean 0; "
                                       "changing the test rows does not change the scaled train rows; inputs unchanged.")
def _t_std(path):
    _fk_grade(path, "std_all", "std_test_own", "std_inplace")


@exercise("w08.test_split_by_time", hint="Use rows that are NOT sorted by date, and one row dated exactly on the cutoff.")
def _t_split(path):
    _fk_grade(path, "split_boundary", "split_position")


@exercise("w08.test_colleague", hint="Run your test against the colleague's version until it fails there and passes "
                                     "on the original. What does the colleague's version do with cancelled orders?")
def _t_colleague(path):
    _fk_grade(path, "days_cancelled", "days_future", "days_strict")


register_quiz("w08.30_q1", "c",
              "pytest collects files named test_*.py and, inside them, functions named test_*; a bare `assert` is "
              "all a test needs.",
              {"a": "No base class is needed (that is the older unittest style).",
               "b": "pytest does not run every function; only names starting with test_.",
               "d": "Tests can live anywhere pytest is pointed at; the names matter, not a special folder."})
register_quiz("w08.30_q2", "b",
              "Floating-point arithmetic rounds: 0.1 + 0.2 is 0.30000000000000004. Compare floats with a tolerance "
              "(pytest.approx, np.allclose, pd.testing with rtol).",
              {"a": "The values are equal to ~16 digits but not exactly; == is the wrong tool, not a pandas bug.",
               "c": "Rounding both sides hides real errors of the size you round away.",
               "d": "Floats are fine in tests; just compare them with a tolerance."})
register_quiz("w08.30_q3", "d",
              "A unit test must be fast and deterministic and point at one cause. Accuracy depends on data and "
              "randomness; track it in evaluation, and unit-test the code around the model (features, splits, shapes).",
              {"a": "Accuracy is important; it just belongs in evaluation and monitoring, not in a unit test.",
               "b": "You can test model code: shapes, determinism with a seed, no leakage.",
               "c": "A threshold on accuracy in a unit test is flaky and fails for reasons unrelated to a code change."})
register_quiz("w08.30_q4", "a",
              "A test that passes on correct code and fails on code with a realistic bug is doing its job. That is "
              "exactly what the graders measure this week.",
              {"b": "Many tests that all pass on buggy code protect nothing.",
               "c": "Coverage says which lines ran, not whether wrong results would be noticed.",
               "d": "A test that never fails gives no information."})
register_quiz("w08.30_q5", "c",
              "tmp_path gives each test its own empty temporary folder, so tests never touch your real files and "
              "never depend on each other.",
              {"a": "It does not speed up disk access.",
               "b": "It is deleted automatically later; you do not need to clean up.",
               "d": "Any test that writes files should use it, not only CSV ones."})

# ================================================================================ notebook 31


@dataclass
class _RunConfig:
    data_path: str
    cutoff: str
    horizon_days: int = 90
    test_size: float = 0.25
    seed: int = 0
    model: str = "logreg"


_CFG_FIELDS = [("data_path", str, None), ("cutoff", str, None), ("horizon_days", int, 90),
               ("test_size", float, 0.25), ("seed", int, 0), ("model", str, "logreg")]


@exercise("w08.run_config", hint="@dataclass, then one line per field: name: type = default. Fields without a "
                                 "default come first.")
def _t_run_config(cls):
    if not (isinstance(cls, type) and is_dataclass(cls)):
        raise AssertionError("RunConfig should be a class decorated with @dataclass")
    names = [f.name for f in fields(cls)]
    if names != [n for n, _, _ in _CFG_FIELDS]:
        raise AssertionError(f"expected fields {[n for n, _, _ in _CFG_FIELDS]} in that order, got {names}")
    cfg = cls(data_path="data.csv", cutoff="2025-06-30")
    for n, _, default in _CFG_FIELDS[2:]:
        if getattr(cfg, n) != default:
            raise AssertionError(f"the default for {n} should be {default!r}, got {getattr(cfg, n)!r}")
    try:
        cls(data_path="x.csv")
    except TypeError:
        pass
    else:
        raise AssertionError("cutoff should be required (no default)")
    for f, (n, typ, _) in zip(fields(cls), _CFG_FIELDS):
        ann = f.type if isinstance(f.type, str) else getattr(f.type, "__name__", str(f.type))
        if ann != typ.__name__:
            raise AssertionError(f"field {n} should be annotated as {typ.__name__}, got {ann}")


def _yaml_file(tmp: Path, text: str) -> Path:
    p = tmp / "config.yaml"
    p.write_text(text)
    return p


@exercise("w08.load_config", hint="yaml.safe_load the file into a dict; compare its keys with the dataclass fields; "
                                  "str() the cutoff; then RunConfig(**data).")
def _t_load_config(fn):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        cfg = fn(_yaml_file(tmp, "data_path: data/churn.csv\ncutoff: 2025-06-30\nseed: 7\n"))
        if not is_dataclass(cfg):
            raise AssertionError("load_config should return a RunConfig instance")
        if cfg.data_path != "data/churn.csv" or cfg.seed != 7:
            raise AssertionError("values from the file were not used")
        if cfg.cutoff != "2025-06-30" or not isinstance(cfg.cutoff, str):
            raise AssertionError(f"an unquoted date in YAML is read as a date object; cutoff should end up as the "
                                 f"string '2025-06-30', got {cfg.cutoff!r}")
        if cfg.horizon_days != 90 or cfg.model != "logreg":
            raise AssertionError("keys missing from the file should keep their defaults")
        cfg = fn(_yaml_file(tmp, "data_path: a.csv\ncutoff: '2024-12-31'\ntest_size: 0.4\nmodel: forest\n"))
        if (cfg.cutoff, cfg.test_size, cfg.model) != ("2024-12-31", 0.4, "forest"):
            raise AssertionError("the second config file was not read correctly")
        for text, word in [("data_path: a.csv\ncutoff: 2025-01-01\nsede: 3\n", "sede"),
                           ("data_path: a.csv\n", "cutoff")]:
            try:
                fn(_yaml_file(tmp, text))
            except ValueError as err:
                if word not in str(err):
                    raise AssertionError(f"the ValueError should name the problem key {word!r}; message was: {err}") from None
            except TypeError:
                raise AssertionError(f"a config with a missing or unknown key ({word!r}) should raise ValueError "
                                     "naming the key, not a TypeError from the dataclass") from None
            else:
                raise AssertionError(f"a config with a missing or misspelt key ({word!r}) was accepted silently: "
                                     "raise ValueError")


@exercise("w08.apply_overrides", hint="Split each item on the first '=', check the key is a field, convert the text "
                                      "with type(getattr(cfg, key)), then dataclasses.replace.")
def _t_overrides(fn):
    base = _RunConfig("d.csv", "2025-06-30")
    new = fn(base, ["seed=3", "test_size=0.3", "model=forest"])
    if base.seed != 0:
        raise AssertionError("apply_overrides changed the original config: return a new one (dataclasses.replace)")
    if (new.seed, new.test_size, new.model) != (3, 0.3, "forest"):
        raise AssertionError(f"expected seed=3, test_size=0.3, model='forest', got {new.seed!r}, {new.test_size!r}, "
                             f"{new.model!r}")
    if not isinstance(new.seed, int) or not isinstance(new.test_size, float):
        raise AssertionError("overrides arrive as text: convert '3' to the int 3 and '0.3' to the float 0.3")
    if fn(base, []) != base:
        raise AssertionError("with no overrides the config should be unchanged")
    if fn(base, ["cutoff=2024-01-31=x"]).cutoff != "2024-01-31=x":
        raise AssertionError("split on the FIRST '=' only: values may contain '='")
    for bad in (["sede=3"], ["seed"]):
        try:
            fn(base, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{bad} should raise ValueError (unknown key or missing '=')")


@exercise("w08.validate_config", hint="Start with problems = []; add one message per broken rule, each message "
                                      "naming the field; return the list.")
def _t_validate(fn):
    ok = _RunConfig("d.csv", "2025-06-30")
    if fn(ok) != []:
        raise AssertionError(f"a valid config should give an empty list, got {fn(ok)!r}")
    cases = [(_RunConfig("d.csv", "2025-06-30", test_size=1.2), "test_size"),
             (_RunConfig("d.csv", "2025-06-30", test_size=0.0), "test_size"),
             (_RunConfig("d.csv", "2025-06-30", horizon_days=0), "horizon_days"),
             (_RunConfig("d.csv", "2025-06-30", model="xgb"), "model"),
             (_RunConfig("d.csv", "2025-13-45"), "cutoff"),
             (_RunConfig("d.csv", "tomorrow"), "cutoff")]
    for cfg, field in cases:
        probs = fn(cfg)
        if not isinstance(probs, list):
            raise AssertionError("validate_config should return a list of messages")
        if len(probs) != 1 or field not in probs[0]:
            raise AssertionError(f"a config with a bad {field} should give exactly one message that names "
                                 f"{field!r}; got {probs!r}")
    probs = fn(_RunConfig("d.csv", "nope", horizon_days=-1, test_size=2, model="x"))
    if len(probs) != 4:
        raise AssertionError(f"with four broken rules, expected four messages, got {len(probs)}")


def _cleanup_logger(name: str) -> None:
    lg = logging.getLogger(name)
    for h in list(lg.handlers):
        lg.removeHandler(h)
        h.close()


@exercise("w08.setup_logging", hint="Get logging.getLogger(\"churn\"), remove old handlers, add a FileHandler with a "
                                    "Formatter, set the level from the argument.")
def _t_setup_logging(fn):
    with tempfile.TemporaryDirectory() as tmp:
        log_file = Path(tmp) / "run.log"
        try:
            lg = fn(log_file)
            lg = fn(log_file)  # twice: must not duplicate handlers
            if not isinstance(lg, logging.Logger) or lg.name != "churn":
                raise AssertionError("setup_logging should return the logger named \"churn\"")
            with contextlib.redirect_stderr(io.StringIO()):
                lg.info("hello info")
                lg.debug("hello debug")
                lg.warning("hello warning")
            for h in lg.handlers:
                h.flush()
            if not log_file.is_file():
                raise AssertionError("no log file was written: add a logging.FileHandler(log_file)")
            lines = [ln for ln in log_file.read_text().splitlines() if ln.strip()]
            info = [ln for ln in lines if "hello info" in ln]
            if len(info) == 2:
                raise AssertionError("each message appears twice: calling setup_logging again added a second handler. "
                                     "Remove existing handlers first")
            if len(info) != 1:
                raise AssertionError("the INFO message is not in the log file exactly once")
            if any("hello debug" in ln for ln in lines):
                raise AssertionError("at level INFO, DEBUG messages should be filtered out")
            line = info[0]
            if not re.match(r"\d{4}-\d\d-\d\d", line):
                raise AssertionError(f"each line should start with the date and time (%(asctime)s); got {line!r}")
            if "INFO" not in line or "churn" not in line:
                raise AssertionError(f"each line should show the level and the logger name; got {line!r}")
            if not any("WARNING" in ln and "hello warning" in ln for ln in lines):
                raise AssertionError("the WARNING message is missing")
            _cleanup_logger("churn")
            lg = fn(Path(tmp) / "debug.log", level="DEBUG")
            with contextlib.redirect_stderr(io.StringIO()):
                lg.debug("now visible")
            for h in lg.handlers:
                h.flush()
            if "now visible" not in (Path(tmp) / "debug.log").read_text():
                raise AssertionError("with level=\"DEBUG\" the DEBUG message should be written")
        finally:
            _cleanup_logger("churn")


class _Capture(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record):
        self.records.append(record)


@exercise("w08.describe_table", hint="logger.info(...) once with the row count; then, for each column whose "
                                     "isna().sum() is above 0, logger.warning(...) naming it.")
def _t_describe(fn):
    lg = logging.getLogger("w08.grader.describe")
    lg.handlers.clear()
    cap = _Capture()
    lg.addHandler(cap)
    lg.setLevel(logging.DEBUG)
    lg.propagate = False
    clean = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        fn(clean, lg)
    if out.getvalue().strip():
        raise AssertionError("describe_table printed to the screen: send everything through the logger instead")
    infos = [r for r in cap.records if r.levelno == logging.INFO]
    if not any("3" in r.getMessage() for r in infos):
        raise AssertionError("expected an INFO message with the number of rows (3)")
    if any(r.levelno >= logging.WARNING for r in cap.records):
        raise AssertionError("a table with no missing values should produce no warnings")
    cap.records.clear()
    messy = pd.DataFrame({"city": ["A", None, None, "B"], "spend": [1.0, np.nan, 2.0, 3.0], "id": [1, 2, 3, 4]})
    with contextlib.redirect_stdout(io.StringIO()):
        fn(messy, lg)
    warns = [r.getMessage() for r in cap.records if r.levelno == logging.WARNING]
    if len(warns) != 2:
        raise AssertionError(f"two columns have missing values, so expected 2 warnings, got {len(warns)}")
    if not any("city" in w and "2" in w for w in warns) or not any("spend" in w and "1" in w for w in warns):
        raise AssertionError("each warning should name the column and how many values are missing")
    if not any("4" in r.getMessage() for r in cap.records if r.levelno == logging.INFO):
        raise AssertionError("expected an INFO message with the number of rows (4)")


def _w31_table():
    from mlcourse.churn import build_churn_table
    if "t31" not in _CACHE:
        _CACHE["t31"] = build_churn_table()
    return _CACHE["t31"].copy()


_CACHE: dict = {}


@exercise("w08.train_and_evaluate", hint="train_test_split(..., test_size=cfg.test_size, random_state=cfg.seed, "
                                         "stratify=y); pass random_state=cfg.seed to the forest too.")
def _t_train(fn):
    table = _w31_table()
    cfg = _RunConfig("unused.csv", "2025-06-30")
    m1 = fn(cfg, table)
    if not isinstance(m1, dict):
        raise AssertionError("train_and_evaluate should return a dict of metrics")
    for k in ("accuracy", "roc_auc", "n_train", "n_test"):
        if k not in m1:
            raise AssertionError(f"the metrics dict needs a key {k!r}")
    if m1["n_train"] + m1["n_test"] != len(table):
        raise AssertionError("n_train + n_test should equal the number of rows in the table")
    exp_test = int(np.ceil(0.25 * len(table)))
    if m1["n_test"] != exp_test:
        raise AssertionError(f"with test_size 0.25 expected {exp_test} test rows, got {m1['n_test']}")
    if not (0.55 < m1["roc_auc"] <= 1.0) or not (0.0 <= m1["accuracy"] <= 1.0):
        raise AssertionError(f"metrics look wrong: accuracy {m1['accuracy']}, roc_auc {m1['roc_auc']} "
                             "(roc_auc needs predict_proba(...)[:, 1])")
    if fn(cfg, table) != m1:
        raise AssertionError("two runs with the same config gave different metrics: pass cfg.seed as random_state")
    other = fn(_RunConfig("unused.csv", "2025-06-30", seed=1), table)
    if other == m1:
        raise AssertionError("seed 0 and seed 1 gave identical metrics: is cfg.seed used for the split?")
    big = fn(_RunConfig("unused.csv", "2025-06-30", test_size=0.4), table)
    if big["n_test"] != int(np.ceil(0.4 * len(table))):
        raise AssertionError("cfg.test_size is not used")
    f1 = fn(_RunConfig("unused.csv", "2025-06-30", model="forest", seed=2), table)
    if f1 == fn(_RunConfig("unused.csv", "2025-06-30", seed=2), table):
        raise AssertionError("model='forest' gives the same result as 'logreg': is cfg.model used?")
    if fn(_RunConfig("unused.csv", "2025-06-30", model="forest", seed=2), table) != f1:
        raise AssertionError("the random forest is not reproducible: give it random_state=cfg.seed")


@exercise("w08.save_run", hint="run_dir = runs_dir / a unique name; mkdir(parents=True); write three json files.")
def _t_save_run(fn):
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _RunConfig("d.csv", "2025-06-30", seed=4)
        metrics = {"accuracy": 0.71, "roc_auc": 0.77, "n_train": 10, "n_test": 4}
        d1 = fn(cfg, metrics, Path(tmp) / "runs")
        d2 = fn(cfg, metrics, Path(tmp) / "runs")
        d1, d2 = Path(d1), Path(d2)
        if not d1.is_dir():
            raise AssertionError("save_run should create a folder and return its path")
        if d1 == d2:
            raise AssertionError("two runs were saved to the same folder: make each run's name unique")
        if d1.parent != Path(tmp) / "runs":
            raise AssertionError("each run folder should be directly inside runs_dir")
        for name in ("config.json", "metrics.json", "versions.json"):
            if not (d1 / name).is_file():
                raise AssertionError(f"{name} is missing from the run folder")
        if json.loads((d1 / "config.json").read_text()) != asdict(cfg):
            raise AssertionError("config.json should hold every field of the config (dataclasses.asdict)")
        if json.loads((d1 / "metrics.json").read_text()) != metrics:
            raise AssertionError("metrics.json should hold the metrics dict unchanged")
        vers = json.loads((d1 / "versions.json").read_text())
        need = {"python", "numpy", "pandas", "sklearn"}
        if not need <= set(vers):
            raise AssertionError(f"versions.json should have keys {sorted(need)}, got {sorted(vers)}")
        import sklearn
        if vers["sklearn"] != sklearn.__version__ or vers["pandas"] != pd.__version__:
            raise AssertionError("versions.json should record the versions actually in use (module.__version__)")


@exercise("w08.config_hash", hint="json.dumps(asdict(cfg), sort_keys=True), encode, hashlib.sha256, hexdigest()[:12].")
def _t_hash(fn):
    a = fn(_RunConfig("d.csv", "2025-06-30"))
    if not isinstance(a, str) or not re.fullmatch(r"[0-9a-f]{8,64}", a):
        raise AssertionError(f"the hash should be a short hexadecimal string, got {a!r}")
    if fn(_RunConfig(cutoff="2025-06-30", data_path="d.csv")) != a:
        raise AssertionError("the same config should always give the same hash")
    if fn(_RunConfig("d.csv", "2025-06-30", seed=1)) == a:
        raise AssertionError("changing the seed should change the hash")
    if fn(_RunConfig("e.csv", "2025-06-30")) == a:
        raise AssertionError("changing data_path should change the hash")
    import inspect
    try:
        src = inspect.getsource(fn)
    except (OSError, TypeError):
        src = ""
    if re.search(r"(?<![\w.])hash\(", src):
        raise AssertionError("Python's built-in hash() of a string changes every time Python starts: use hashlib")


@exercise("w08.reproduce_run", hint="Read config.json into RunConfig(**data), call train_and_evaluate again, compare "
                                    "with the saved metrics.json.")
def _t_reproduce(fn):
    table = _w31_table()
    cfg = _RunConfig("unused.csv", "2025-06-30", seed=5)
    with tempfile.TemporaryDirectory() as tmp:
        run = Path(tmp) / "run1"
        run.mkdir()
        (run / "config.json").write_text(json.dumps(asdict(cfg)))
        (run / "metrics.json").write_text(json.dumps({"accuracy": -1.0}))
        res = fn(run, table)
        if not (isinstance(res, tuple) and len(res) == 2):
            raise AssertionError("reproduce_run should return a tuple (new_metrics, matches)")
        new, _ = res
        (run / "metrics.json").write_text(json.dumps(new))
        new2, matches = fn(run, table)
        if matches is not True:
            raise AssertionError("re-running a saved run with the same config should reproduce its metrics "
                                 "(matches should be True)")
        tampered = dict(new2)
        tampered["accuracy"] = round(1.0 - float(tampered["accuracy"]), 6)
        (run / "metrics.json").write_text(json.dumps(tampered))
        _, matches = fn(run, table)
        if matches is not False:
            raise AssertionError("when the saved metrics differ from the re-run, matches should be False")
        cfg2 = dict(asdict(cfg), seed=6)
        (run / "config.json").write_text(json.dumps(cfg2))
        new3, _ = fn(run, table)
        if new3 == new2:
            raise AssertionError("the config file's seed was not used: build the config from config.json")


register_quiz("w08.31_q1", "b",
              "Settings that change between runs (dates, paths, seeds, model choice) belong in a config file that is "
              "saved with each run; code should not need editing to run an experiment.",
              {"a": "Constants that never change (like pi) can stay in code.",
               "c": "Config files hold settings, not secrets; secrets go in environment variables or a secret store.",
               "d": "A config file does not make code faster."})
register_quiz("w08.31_q2", "d",
              "YAML reads an unquoted 2025-06-30 as a date and `no` as False (in YAML 1.1). Quote values that must stay "
              "text, and convert and validate types when loading.",
              {"a": "YAML happily parses it; the surprise is the type it chooses.",
               "b": "It is not an error; it silently becomes a datetime.date.",
               "c": "JSON has no date type; YAML does, which is why the type changes."})
register_quiz("w08.31_q3", "a",
              "Logging gives levels you can filter, timestamps and a source on every line, and output to files that "
              "outlive the notebook or job.",
              {"b": "print is not slower in a way that matters; the problem is no levels, no timestamps, no file.",
               "c": "Both can print to the screen; logging can also go to files and be filtered.",
               "d": "Logs are often kept longer than any notebook output."})
register_quiz("w08.31_q4", "c",
              "A seed fixes the random numbers, not the data, the library versions or the hardware. Save the config, "
              "a data fingerprint and the versions with every run.",
              {"a": "A seed does not freeze the data the code reads.",
               "b": "Different library versions can change results even with the same seed.",
               "d": "Seeds are still essential; they are just not sufficient."})
register_quiz("w08.31_q5", "b",
              "WARNING is for something unexpected that the program can continue past; ERROR is for a failure of the "
              "current operation.",
              {"a": "DEBUG is detail for developers, normally switched off.",
               "c": "ERROR means the operation failed; here the run can continue.",
               "d": "CRITICAL is for the whole program being unable to continue."})

# ================================================================================ lab 32

CHURNKIT_CONFIG = '''"""Configuration for churnkit: a dataclass and a loader with key checks and command-line overrides."""
from dataclasses import MISSING, dataclass, fields

import yaml


@dataclass
class Config:
    data_dir: str
    cutoff: str
    horizon_days: int = 90
    test_size: float = 0.25
    seed: int = 0
    runs_dir: str = "runs"
    log_file: str = "churnkit.log"


def load_config(path, overrides=()):
    with open(path) as fh:
        raw = yaml.safe_load(fh) or {}
    known = {f.name: f for f in fields(Config)}
    unknown = sorted(set(raw) - set(known))
    if unknown:
        raise ValueError(f"unknown config keys: {unknown}")
    raw = {k: str(v) if k == "cutoff" else v for k, v in raw.items()}
    for item in overrides:
        key, sep, value = item.partition("=")
        if not sep or key not in known:
            raise ValueError(f"bad override {item!r}")
        raw[key] = known[key].type(value)
    missing = [n for n, f in known.items() if n not in raw and f.default is MISSING]
    if missing:
        raise ValueError(f"missing config keys: {missing}")
    return Config(**raw)
'''

CHURNKIT_FEATURES = '''"""Load the shop CSVs and build the churn table: features from on/before the cutoff, label after it."""
from pathlib import Path

import pandas as pd

FEATURES = ["n_orders", "total_spent", "days_since_last_order", "tenure_days", "segment"]


def load_data(data_dir):
    d = Path(data_dir)
    orders = pd.read_csv(d / "orders.csv", parse_dates=["order_date"])
    items = pd.read_csv(d / "order_items.csv")
    customers = pd.read_csv(d / "customers.csv", parse_dates=["signup_date"])
    return orders, items, customers


def order_values(items):
    line = items["quantity"] * items["unit_price"] * (1 - items["discount"])
    return line.groupby(items["order_id"]).sum()


def build_table(orders, items, customers, cutoff, horizon_days=90):
    cutoff = pd.Timestamp(cutoff)
    valid = orders[orders["status"] != "cancelled"].copy()
    valid["value"] = valid["order_id"].map(order_values(items)).fillna(0.0)
    past = valid[valid["order_date"] <= cutoff]
    end = cutoff + pd.Timedelta(days=horizon_days)
    future = valid[(valid["order_date"] > cutoff) & (valid["order_date"] <= end)]
    g = past.groupby("customer_id")
    table = pd.DataFrame({
        "n_orders": g.size(),
        "total_spent": g["value"].sum(),
        "days_since_last_order": (cutoff - g["order_date"].max()).dt.days,
    })
    info = customers.set_index("customer_id")
    table["tenure_days"] = (cutoff - info["signup_date"]).dt.days
    table["segment"] = info["segment"]
    table["churned"] = (~table.index.isin(future["customer_id"])).astype(int)
    table.index.name = "customer_id"
    return table.sort_index()
'''

_CK_FILES = {"churnkit/__init__.py": "", "churnkit/config.py": CHURNKIT_CONFIG,
             "churnkit/features.py": CHURNKIT_FEATURES}
_CF, _CC = "churnkit/features.py", "churnkit/config.py"
_LAB_BUGS = [
    Bug("label_window", "the churn label ignores an order placed exactly `horizon_days` days after the cutoff "
                        "(the window should include its last day)",
        ((_CF, '(valid["order_date"] <= end)', '(valid["order_date"] < end)'),)),
    Bug("counts_cancelled", "cancelled orders are counted in n_orders and total_spent",
        ((_CF, 'valid = orders[orders["status"] != "cancelled"].copy()', 'valid = orders.copy()'),)),
    Bug("future_features", "the features also use orders AFTER the cutoff (leakage)",
        ((_CF, 'past = valid[valid["order_date"] <= cutoff]', 'past = valid'),)),
    Bug("no_discount", "total_spent ignores discounts",
        ((_CF, 'line = items["quantity"] * items["unit_price"] * (1 - items["discount"])',
          'line = items["quantity"] * items["unit_price"]'),)),
    Bug("unknown_key_ok", "load_config silently accepts a misspelt key (it is ignored)",
        ((_CC, "    if unknown:\n        raise ValueError(f\"unknown config keys: {unknown}\")\n",
          "    raw = {k: v for k, v in raw.items() if k not in unknown}\n"),)),
    Bug("override_text", "an override such as seed=3 is stored as the text '3', not the number 3",
        ((_CC, "        raw[key] = known[key].type(value)", "        raw[key] = value"),)),
]


def _ref_mod(name: str, src: str):
    if name not in _CACHE:
        import types
        mod = types.ModuleType(name)
        exec(compile(src, name, "exec"), mod.__dict__)
        _CACHE[name] = mod
    return _CACHE[name]


def _lab_csvs(dest: Path) -> None:
    from mlcourse.sql import sql
    dest.mkdir(parents=True, exist_ok=True)
    sql("SELECT * FROM orders", "shop").to_csv(dest / "orders.csv", index=False)
    sql("SELECT * FROM order_items", "shop").to_csv(dest / "order_items.csv", index=False)
    sql("SELECT * FROM customers", "shop").to_csv(dest / "customers.csv", index=False)


def export_lab_data(dest) -> None:
    """Write orders.csv, order_items.csv and customers.csv from the shop database into `dest`."""
    _lab_csvs(Path(dest))


@exercise("w08.lab_project", hint="Copy the shape of shopfeat's pyproject.toml from notebook 29, with churnkit's "
                                  "name, three dependencies and the churnkit command.")
def _t_lab_project(answer):
    project = _project(answer)
    data = _toml(project / "pyproject.toml")
    if data.get("build-system", {}).get("build-backend") != "setuptools.build_meta":
        raise AssertionError("[build-system] should use setuptools (requires and build-backend)")
    proj = data.get("project", {})
    if proj.get("name") != "churnkit":
        raise AssertionError("[project] name should be \"churnkit\"")
    deps = " ".join(proj.get("dependencies", [])).lower()
    for d in ("pandas", "scikit-learn", "pyyaml"):
        if d not in deps:
            raise AssertionError(f"churnkit uses {d}, so dependencies should list it")
    if str(proj.get("scripts", {}).get("churnkit", "")).replace(" ", "") != "churnkit.cli:main":
        raise AssertionError("[project.scripts] should define the command churnkit = \"churnkit.cli:main\"")
    _need_file(project / "src" / "churnkit" / "__init__.py", "src/churnkit/__init__.py")
    pkg, _ = _quiet_import(project, "churnkit")
    if getattr(pkg, "__version__", None) != proj.get("version"):
        raise AssertionError("churnkit.__version__ should equal the version in pyproject.toml")


def _conf_obj_check(cfg, **expected):
    for k, v in expected.items():
        got = getattr(cfg, k, "<missing>")
        if got != v or type(got) is not type(v):
            raise AssertionError(f"{k} should be {v!r} ({type(v).__name__}), got {got!r}")


@exercise("w08.lab_config", hint="Reuse notebook 31: a dataclass with the seven fields, then load_config(path, "
                                 "overrides=()) with the unknown-key check and type conversion.")
def _t_lab_config(answer):
    project = _project(answer)
    _need_file(project / "src" / "churnkit" / "config.py", "src/churnkit/config.py")
    mod, _ = _quiet_import(project, "churnkit.config")
    load = getattr(mod, "load_config", None)
    if not callable(load) or not is_dataclass(getattr(mod, "Config", None)):
        raise AssertionError("config.py needs a dataclass Config and a function load_config(path, overrides=())")
    with tempfile.TemporaryDirectory() as tmp:
        p = _yaml_file(Path(tmp), "data_dir: data\ncutoff: 2025-06-30\nseed: 1\n")
        cfg = load(p)
        _conf_obj_check(cfg, data_dir="data", cutoff="2025-06-30", seed=1, horizon_days=90, test_size=0.25,
                        runs_dir="runs", log_file="churnkit.log")
        cfg = load(p, ["seed=3", "test_size=0.4", "runs_dir=out"])
        _conf_obj_check(cfg, seed=3, test_size=0.4, runs_dir="out")
        cfg = load(p, overrides=["horizon_days=60"])
        _conf_obj_check(cfg, horizon_days=60)
        for text, ov in [("data_dir: d\ncutoff: 2025-01-01\nhorizon: 30\n", []), ("data_dir: d\n", []),
                         ("data_dir: d\ncutoff: 2025-01-01\n", ["sed=3"]), ("data_dir: d\ncutoff: 2025-01-01\n", ["seed"])]:
            try:
                load(_yaml_file(Path(tmp), text), ov)
            except ValueError:
                pass
            except TypeError:
                raise AssertionError("a missing or unknown key should raise ValueError, not TypeError") from None
            else:
                raise AssertionError(f"this config was accepted but should raise ValueError: {text.strip()!r} "
                                     f"with overrides {ov}")


def _lab_small():
    orders = pd.DataFrame({
        "order_id": [1, 2, 3, 4, 5, 6, 7, 8],
        "customer_id": [1, 1, 2, 2, 3, 3, 4, 1],
        "order_date": pd.to_datetime(["2025-01-10", "2025-03-01", "2025-02-01", "2025-05-30", "2025-03-31",
                                      "2025-02-01", "2025-03-15", "2025-06-29"]),
        "status": ["delivered", "delivered", "delivered", "delivered", "delivered", "cancelled", "cancelled",
                   "delivered"],
        "channel": "web"})
    items = pd.DataFrame({"order_id": [1, 2, 2, 3, 4, 5, 6, 7, 8], "product_id": 1,
                          "quantity": [1, 2, 1, 1, 1, 3, 5, 1, 1],
                          "unit_price": [10.0, 5.0, 20.0, 8.0, 9.0, 4.0, 100.0, 50.0, 1.0],
                          "discount": [0.0, 0.5, 0.0, 0.25, 0.0, 0.0, 0.0, 0.0, 0.0]})
    customers = pd.DataFrame({"customer_id": [1, 2, 3, 4, 5], "name": "x", "city": "A",
                              "signup_date": pd.to_datetime(["2024-12-01", "2025-01-15", "2025-03-01", "2025-01-01",
                                                             "2025-02-02"]),
                              "segment": ["consumer", "business", "consumer", "consumer", "business"],
                              "email": "x"})
    return orders, items, customers


@exercise("w08.lab_features", hint="It is notebook 29's customer_summary plus tenure, segment and the label from "
                                   "Week 4: active on/before the cutoff, churned if no order in (cutoff, cutoff+horizon].")
def _t_lab_features(answer):
    project = _project(answer)
    _need_file(project / "src" / "churnkit" / "features.py", "src/churnkit/features.py")
    mod, _ = _quiet_import(project, "churnkit.features")
    for name in ("load_data", "build_table"):
        if not callable(getattr(mod, name, None)):
            raise AssertionError(f"features.py needs a function {name}")
    ref = _ref_mod("_w08_ref_features", CHURNKIT_FEATURES)
    o, i, c = _lab_small()
    got = mod.build_table(o.copy(), i.copy(), c.copy(), "2025-03-31", 90)
    exp = ref.build_table(o, i, c, "2025-03-31", 90)
    _compare_tables(got, exp, "the small hand-made data (cutoff 2025-03-31)")
    with tempfile.TemporaryDirectory() as tmp:
        _lab_csvs(Path(tmp))
        data = mod.load_data(tmp)
        if not (isinstance(data, tuple) and len(data) == 3):
            raise AssertionError("load_data should return (orders, items, customers)")
        orders, items, customers = data
        if not pd.api.types.is_datetime64_any_dtype(orders["order_date"]):
            raise AssertionError("load_data should parse order_date as dates (parse_dates=...)")
        if not pd.api.types.is_datetime64_any_dtype(customers["signup_date"]):
            raise AssertionError("load_data should parse signup_date as dates")
    for cutoff, h in (("2025-06-30", 90), ("2025-09-30", 60)):
        got = mod.build_table(orders.copy(), items.copy(), customers.copy(), cutoff, h)
        exp = ref.build_table(orders, items, customers, cutoff, h)
        _compare_tables(got, exp, f"the shop data (cutoff {cutoff}, horizon {h})")
    late = orders.copy()
    late.loc[late.order_date > pd.Timestamp("2025-06-30") + pd.Timedelta(days=90), "status"] = "cancelled"
    a = mod.build_table(late, items.copy(), customers.copy(), "2025-06-30", 90)
    _compare_tables(a, ref.build_table(orders, items, customers, "2025-06-30", 90), "orders far in the future changed")


def _compare_tables(got, exp, where):
    if not isinstance(got, pd.DataFrame):
        raise AssertionError("build_table should return a DataFrame")
    if "customer_id" in got.columns:
        got = got.set_index("customer_id")
    cols = ["n_orders", "total_spent", "days_since_last_order", "tenure_days", "segment", "churned"]
    missing = [c for c in cols if c not in got.columns]
    if missing:
        raise AssertionError(f"build_table is missing columns {missing}")
    if len(got) != len(exp):
        raise AssertionError(f"{where}: expected {len(exp)} active customers, got {len(got)} rows "
                             "(active = a non-cancelled order on or before the cutoff)")
    got = got.reindex(exp.index)
    if got[cols[:4]].isna().any().any():
        raise AssertionError(f"{where}: the rows are not the active customers, indexed by customer_id")
    for col in cols:
        if col == "segment":
            ok = (got[col].astype(str) == exp[col].astype(str)).all()
        else:
            ok = np.allclose(got[col].astype(float), exp[col].astype(float), atol=0.01)
        if not ok:
            raise AssertionError(f"{where}: column {col} is wrong for some customers")


def _lab_config_file(tmp: Path, data_dir: Path, seed: int = 0) -> Path:
    p = tmp / "config.yaml"
    p.write_text(f"data_dir: {data_dir}\ncutoff: 2025-06-30\nseed: {seed}\nruns_dir: {tmp / 'runs'}\n"
                 f"log_file: {tmp / 'churnkit.log'}\n")
    return p


@exercise("w08.lab_train", hint="train(cfg): set up logging, load_data, build_table, split with cfg.seed, fit the "
                                "pipeline, compute the metrics, save config.json and metrics.json, return the metrics.")
def _t_lab_train(answer):
    project = _project(answer)
    _need_file(project / "src" / "churnkit" / "train.py", "src/churnkit/train.py")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        _lab_csvs(tmp / "data")
        train_mod, _ = _quiet_import(project, "churnkit.train")
        cfg_mod = _also_import(project, "churnkit.config")
        cfg = cfg_mod.load_config(_lab_config_file(tmp, tmp / "data"))
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                m1 = train_mod.train(cfg)
                m2 = train_mod.train(cfg)
        finally:
            _cleanup_logger("churnkit")
        if not isinstance(m1, dict):
            raise AssertionError("train should return the metrics dict")
        need = {"accuracy", "roc_auc", "baseline_accuracy", "n_train", "n_test", "run_dir"}
        if not need <= set(m1):
            raise AssertionError(f"the metrics need keys {sorted(need)}; missing {sorted(need - set(m1))}")
        strip = lambda m: {k: v for k, v in m.items() if k != "run_dir"}  # noqa: E731
        if strip(m1) != strip(m2):
            raise AssertionError("two runs with the same config gave different metrics: use cfg.seed everywhere")
        ref = _ref_mod("_w08_ref_features", CHURNKIT_FEATURES)
        n = len(ref.build_table(*ref.load_data(tmp / "data"), "2025-06-30", 90))
        if m1["n_train"] + m1["n_test"] != n or m1["n_test"] != int(np.ceil(0.25 * n)):
            raise AssertionError(f"expected {n} customers split 75/25, got n_train={m1['n_train']}, n_test={m1['n_test']}")
        if not 0.6 < m1["roc_auc"] <= 1:
            raise AssertionError(f"roc_auc {m1['roc_auc']} is too low: use predict_proba(X_test)[:, 1] as the score")
        if not 0.45 <= m1["baseline_accuracy"] <= 0.6:
            raise AssertionError("baseline_accuracy should be the accuracy of always predicting the most common class "
                                 "in the TRAINING labels, measured on the test set")
        d1, d2 = Path(m1["run_dir"]), Path(m2["run_dir"])
        if d1 == d2 or d1.parent != tmp / "runs":
            raise AssertionError("each run should get its own new folder inside cfg.runs_dir")
        for name in ("config.json", "metrics.json"):
            if not (d1 / name).is_file():
                raise AssertionError(f"the run folder has no {name}")
        if json.loads((d1 / "config.json").read_text()).get("seed") != 0:
            raise AssertionError("config.json should hold the config fields (dataclasses.asdict)")
        saved = json.loads((d1 / "metrics.json").read_text())
        if abs(saved.get("roc_auc", -1) - m1["roc_auc"]) > 1e-12:
            raise AssertionError("metrics.json should hold the same metrics that train returns")
        log = (tmp / "churnkit.log")
        if not log.is_file() or "INFO" not in log.read_text():
            raise AssertionError("train should log INFO messages to cfg.log_file")
        text = log.read_text()
        if str(n) not in text:
            raise AssertionError(f"the log should mention how many customers the table has ({n})")


@exercise("w08.lab_cli", hint="argparse with --config (required) and --set (action=\"append\", default=[]); "
                              "load_config(args.config, args.set); train; print json.dumps(metrics); return 0.")
def _t_lab_cli(answer):
    project = _project(answer)
    _need_file(project / "src" / "churnkit" / "cli.py", "src/churnkit/cli.py")
    mod, _ = _quiet_import(project, "churnkit.cli")
    main = getattr(mod, "main", None)
    if not callable(main):
        raise AssertionError("cli.py needs main(argv=None)")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        _lab_csvs(tmp / "data")
        p = _lab_config_file(tmp, tmp / "data")
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                code = main(["--config", str(p), "--set", "seed=3", "--set", "test_size=0.3"])
        finally:
            _cleanup_logger("churnkit")
        if code not in (0, None):
            raise AssertionError(f"main should return 0, returned {code!r}")
        try:
            metrics = json.loads(out.getvalue())
        except json.JSONDecodeError:
            raise AssertionError("main should print the metrics as one JSON object (json.dumps)") from None
        run_dir = Path(metrics.get("run_dir", ""))
        if not (run_dir / "config.json").is_file():
            raise AssertionError("the printed metrics should include run_dir, the folder of this run")
        saved = json.loads((run_dir / "config.json").read_text())
        if saved.get("seed") != 3 or saved.get("test_size") != 0.3:
            raise AssertionError("--set seed=3 --set test_size=0.3 should end up in the run's config")
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            try:
                main([])
            except SystemExit as exc:
                if exc.code == 0:
                    raise AssertionError("without --config the command should fail") from None
            else:
                raise AssertionError("without --config the command should stop with a usage error")


@exercise("w08.lab_tests", hint="Small hand-made tables in a fixture; one test per rule: cancelled orders, the label "
                                "window's last day, orders after the cutoff, discounts; plus config tests.")
def _t_lab_tests(answer):
    project = _project(answer)
    tests = project / "tests"
    if not tests.is_dir():
        raise AssertionError(f"no tests/ folder in {project}")
    files = _read_tests(tests)
    text = "\n".join(files.values())
    if re.search(r"(load_data|read_csv)\(", text) and "tmp_path" not in text:
        raise AssertionError("unit tests should build their own small data (or write it to tmp_path), not read "
                             "the project's data/ folder")
    mutation_grade(tests, _CK_FILES, _LAB_BUGS)


@exercise("w08.lab_run", hint="After `churnkit --config config.yaml` ran, set lab_run_dir to the newest folder in "
                              "runs/ (the cell above shows how).")
def _t_lab_run(answer):
    if not isinstance(answer, (str, Path)):
        raise AssertionError("lab_run_dir should be the path of a run folder")
    run = Path(answer)
    if not run.is_dir():
        raise AssertionError(f"{run} is not a folder")
    for name in ("config.json", "metrics.json"):
        if not (run / name).is_file():
            raise AssertionError(f"{name} is missing in {run}")
    cfg = json.loads((run / "config.json").read_text())
    m = json.loads((run / "metrics.json").read_text())
    if cfg.get("cutoff") != "2025-06-30":
        raise AssertionError("this run should use the lab's config (cutoff 2025-06-30)")
    if not (0.6 < m.get("roc_auc", 0) <= 1 and m.get("accuracy", 0) > m.get("baseline_accuracy", 1)):
        raise AssertionError("the saved metrics do not look like a working model that beats the baseline")
    project = run.parent.parent
    if (project / "tests").is_dir() and (project / "src" / "churnkit").is_dir():
        env = _python_env()
        env["PYTHONPATH"] = str(project / "src")
        proc = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"],
                              cwd=project, env=env, capture_output=True, text=True, timeout=180)
        if proc.returncode != 0:
            raise AssertionError("your own test suite does not pass on your package:\n" + _last_lines(proc.stdout, 6))


register_quiz("w08.32_q1", "c",
              "The package holds the logic once; the config holds what changes; the CLI connects them; tests protect "
              "the logic; each run folder records exactly what happened.",
              {"a": "Notebooks are still great for exploration; the package is what you run and ship.",
               "b": "The config should not contain logic, only settings.",
               "d": "Tests do not replace evaluation; they check the code is correct."})
register_quiz("w08.32_q2", "a",
              "Mutation testing plants realistic bugs and checks that the suite notices. A suite that passes on "
              "buggy code gives false confidence.",
              {"b": "It measures the tests, not the model.",
               "c": "Line coverage can be 100% while no assert checks the right thing.",
               "d": "It does not make tests faster."})
register_quiz("w08.32_q3", "d",
              "With config.json, versions and the code version (a Git commit), anyone can re-run the experiment and "
              "should get the same numbers; that is the point of a run folder.",
              {"a": "Saving runs is cheap; the point is reproducibility, not storage.",
               "b": "Metrics alone do not tell you how they were produced.",
               "c": "Logs help, but they are not a substitute for the exact config."})
register_quiz("w08.32_q4", "b",
              "The label window is (cutoff, cutoff + horizon]: an off-by-one on its last day silently changes labels "
              "for a few customers. Only a test with an order on exactly that day catches it.",
              {"a": "Accuracy barely moves for a few labels; nobody would notice from metrics.",
               "c": "Type checks do not see a wrong comparison operator.",
               "d": "Logging shows what happened, not whether it was right."})
