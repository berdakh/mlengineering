# a1_python - reviewer notes

Reference: `lab/usage_report.py`, `lab/NOTES.md`. Verified with `python tools/verify_checks.py diagnostic/a1_python`.

## The planted defects

| # | Defect | Concept probed |
|---|---|---|
| 1 | `load_events(lines, seen=[])` | default arguments are evaluated once; hidden state between calls |
| 2 | `int(parts[2])` inside a bare `except` | silent data loss; catching only expected exceptions |
| 3 | negative minutes / wrong field count accepted | validating at the boundary |
| 4 | `sessionize` assumes sorted input | undocumented preconditions |
| 5 | `timedelta.seconds` instead of `total_seconds()` | API semantics; bugs that only appear on rare inputs |
| 6 | `rolling_mean` slice `values[i-window:i]` and `/ window` | off-by-one, negative slice wrap-around, warm-up |
| 7 | `reverse=True` on a `(total, id)` key | sort keys with mixed directions |

## Common incorrect answers and why they fail

* **`seen=None` plus `seen = seen or []`** - fine. But **moving `seen` to module level** keeps the bug.
* **Catching `Exception` around the whole body of `parse_line`** - passes the checks, but hides
  programming errors exactly as the bare `except` did. Mark as Partial on error handling.
* **Sorting `events` in place inside `sessionize`** (`events.sort()`) - fixes ordering, mutates the
  caller's list; rejected by `test_sessionize_does_not_mutate_input`.
* **`(ts - last["end"]).seconds`** kept - passes same-day tests only (mutant `seconds_wraparound`).
* **Rolling mean divides by `window`** during warm-up (mutant `rolling_fixed_divisor`).
* **`sorted(..., reverse=True)`** kept, or two-pass sort in the wrong order (mutant `ties_reversed`).
* **"Refactor" that only renames variables** while the three duplicated loops in `build_report` remain.
* **Fixing bugs and restructuring in one undifferentiated edit** with no way to tell which change
  fixed what - a process weakness worth naming even when the result is correct.

## Rubric (evidence, not points)

| Aspect | Demonstrated independently | Partial | Not yet demonstrated |
|---|---|---|---|
| Debugging | All checks pass in time; NOTES names each defect's *cause* | Most checks pass; causes vague ("fixed rolling mean") or 1-2 defects left | Under half the failing checks fixed, or fixes by trial and error without explanation |
| Python semantics | Explains mutable default, `.seconds`, sort-key direction correctly | Fixed them but cannot say why the original failed | Did not locate them |
| Error handling | Narrow exception handling; invalid input rejected deliberately | Broad `except Exception`; validation incomplete | Bare `except` kept |
| Refactoring | Duplication removed, intent-revealing names, behaviour unchanged, no gratuitous rewrite | Some duplication removed; or over-engineered (classes/abstractions the task does not need) | Structure untouched |

A full rewrite that passes is acceptable, but note it: at work the usual constraint is a minimal,
reviewable diff.
