# Hint 3: partial implementation

```python
def provenance(splits_path, tidy_path):
    versions = {}
    for pkg in ("numpy", "pandas", "scikit-learn", "scipy"):
        try:
            versions[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            versions[pkg] = "not installed"
    try:
        out = subprocess.run(["git", "describe", "--always", "--dirty", "--abbrev=12"],
                             capture_output=True, text=True, cwd=Path(__file__).parent, timeout=5)
        code = out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else "unknown"
    except (OSError, subprocess.SubprocessError):
        code = "unknown"
    return {"splits_file": Path(splits_path).name, "splits_sha256": sha256(splits_path),
            "tidy_sha256": sha256(tidy_path), "python": platform.python_version(),
            "packages": versions, "code_version": code}


def _n(x, d=3):
    if x is None:
        return "n/a"
    text = f"{x:.{d}f}"
    return text[1:] if text.startswith("-") and float(text) == 0 else text   # never "-0.000"


# one table row in render():
lines.append(f"| {r['name'].replace('|', chr(92) + '|')} | {_n(r['primary'])} "
             f"[{_n(r['primary_lo'])}, {_n(r['primary_hi'])}] | ... |")
```

For `evaluate`, `lessons/w4d5_model_choice/lab/decision_table.py` already contains steps 2-5 of
hint 2 almost line for line. What changes is that the numbers go into a dict instead of `print`.
