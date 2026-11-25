# Hint 3 (partial implementation)

~~~python
def traced(token: str, percent: bool, leaves: list[float]) -> bool:
    value = float(token.replace(",", ""))
    decimals = len(token.split(".")[1]) if "." in token else 0
    return any(round((v * 100 if percent else v), decimals) == round(value, decimals) for v in leaves)


def check(report, results, min_limitations=5):
    lines = report.splitlines()
    found = []
    secs = sections(lines)
    for req in REQUIRED_SECTIONS:
        if not any(t.lower().startswith(req.lower()) for t in secs):
            found.append(finding("missing_section", 0, f"no '## {req}...' section"))
    leaves = numeric_leaves(results)
    in_code = False
    for i, raw in enumerate(lines, 1):
        if raw.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or raw.lstrip().startswith(("#", "![")):
            continue
        for m in NUMBER.finditer(strip_markup(raw)):
            ...  # untraced_number with line i
    for start, block in blocks(lines):
        ...  # interval_without_unit, significance_without_test
    ...      # limitations_incomplete
    return found
~~~
