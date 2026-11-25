# Hint 3 (partial implementation)

```python
def classify_failure(output: str) -> dict:
    mod = re.search(r"ModuleNotFoundError: No module named '([^']+)'", output)
    if mod:
        return finding("missing_dependency",
                       f"module {mod.group(1)!r} is imported but not installed by the declared requirements")
    missing = re.search(r"(FileNotFoundError|No such file or directory)[^\n]*", output)
    if missing:
        return finding("missing_file", f"a file the pipeline needs is not in the repository: {missing.group(0)[:300]}")
    return finding("step_failed", output.strip()[-500:])


def compare_headline(produced, expected, values):
    rows, problems = [], []
    for spec in values:
        key, tol = spec["key"], float(spec.get("abs_tol", 0.0))
        exp, got = get_path(expected, key), get_path(produced, key)   # TODO: handle KeyError -> headline_missing
        if isinstance(exp, (int, float)) and isinstance(got, (int, float)):
            diff = abs(float(got) - float(exp))
            ok = diff <= tol
        else:
            diff, ok = None, got == exp
        rows.append({"key": key, "expected": exp, "produced": got, "abs_diff": diff, "abs_tol": tol, "ok": ok})
        if not ok:
            problems.append(finding("headline_mismatch", f"{key}: committed {exp!r}, reproduced {got!r}"))
    return rows, problems
```

`make_venv` and `run_steps` are left to you; remember that the steps run in the clone and that the venv's
`bin` directory goes first on `PATH`, so `python` and `make` inside the steps use it.
