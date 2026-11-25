# f1_python - reviewer notes (parallel form of a1)

Same aspects as a1, so the two sittings can be compared row by row.

## Planted defects (8)

int weight; missing field/positivity validation; bare except; mutable default `seen`; in-place sort of
the caller's list; `.seconds` wrap-around after a day; trailing-average divisor; reversed tie order.
Checks cover all of them; the reference `lab/NOTES.md` lists them with causes.

## Common incorrect answers and why they fail

* **Fixing `.seconds` only in `group_legs`** but not in the hour calculation of `build_report`:
  `test_build_report_long_leg_hours` fails: a 30 h leg (scans every 10 h) reads as 6 h.
* **`seen=None` then `seen = seen or set()`** is fine; **making `seen` a module global** still leaks
  between calls (`test_load_has_no_memory_between_calls`).
* **`sorted(..., reverse=True)` with key `(count, depot)`** keeps the tie order reversed.
* **Copying the list with `list(scans)` but sorting the copy in place** is correct; sorting `scans`
  and restoring the order afterwards is fragile and usually wrong for equal timestamps.

## Rubric (assign per aspect)

| Aspect | Demonstrated independently | Partial | Not yet demonstrated |
|---|---|---|---|
| Debugging | >= 7 of 8 defects found, each with its cause in NOTES.md | 4-6 found, or found by check-driven trial without stated causes | < 4 |
| Python semantics | Explains mutable default, `.seconds` vs `total_seconds()`, in-place sort side effect | Fixes them without explaining | Not fixed |
| Error handling | Catches only the expected exceptions; validates explicitly | Narrows `except` but keeps silent failures elsewhere | Bare `except` kept |
| Refactoring | One computation per concept, helper for hours, no duplicated loops, readable names | Some duplication removed | Unchanged structure |
