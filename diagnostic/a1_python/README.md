# a1 - Python: debug and refactor

**Time box: 40 minutes.** Session A, section 1 of 3. No hints; standard-library docs are fine.

## Situation

You inherit `lab/usage_report.py`, a small module that turns raw viewing-event lines into a usage
report. It "works on the sample file". It also has several defects, and `build_report` is hard to change.

## Task

1. **Debug.** Make every function satisfy the specification below. Do not change function names or
   the meaning of their arguments (you may add type hints, helpers, classes).
2. **Refactor.** Leave the module in a state you would be content to have reviewed: no duplicated
   logic in `build_report`, clear names, errors handled deliberately rather than swallowed.
3. **Write down** what you found in `lab/NOTES.md` (one line per bug; 3-6 lines on the refactor).

## Specification

An event line is `customer_id,ISO-8601 timestamp,minutes`, e.g. `C00017,2025-03-02T21:15:00,42.5`.

* `parse_line(line)` returns `(customer_id, datetime, minutes)` (a tuple or anything that unpacks like
  one). `minutes` may be fractional. Returns `None` for malformed lines: wrong number of fields,
  unparseable timestamp or number, negative minutes.
* `load_events(lines)` parses an iterable of lines, skipping malformed lines and exact duplicate lines
  *within that call*. Two calls with the same lines return the same result.
* `sessionize(events, gap_minutes=30)` returns `{customer_id: [session, ...]}` with sessions in
  chronological order. A session is a dict with `start`, `end` (datetimes of first/last event),
  `minutes` (sum) and `n_events`. A new session starts when the gap since the customer's previous
  event is **strictly greater** than `gap_minutes`. Events may arrive in any order. The input is not modified.
* `rolling_mean(values, window)` returns a list as long as `values`; element *i* is the mean of the
  last `window` values up to **and including** *i* (fewer at the start, where fewer exist).
* `top_customers(totals, k=3)` returns up to `k` `(customer_id, total)` pairs, largest total first,
  ties broken by `customer_id` ascending.
* `build_report(lines, gap_minutes=30, k=3)` returns a dict with keys `n_events`, `n_customers`,
  `total_minutes`, `n_sessions`, `longest_session_minutes` (each a dict by customer) and `top_customers`.

## Check your work

```bash
python wb.py check diagnostic/a1_python          # or:
python -m pytest diagnostic/a1_python/checks -q
```

The shipped starter fails several checks; that is expected.

## Acceptance criteria

* All checks pass (behaviour).
* `NOTES.md` names each defect and its cause - not just "fixed test X".
* The refactor is judged by reading your code (see `SUBMISSION.md`); checks cannot grade it.

## Submit

`lab/usage_report.py`, `lab/NOTES.md`, and the time you actually used.
