# f1 - Python: debug and refactor (parallel form of a1)

**Time box: 40 minutes.** Sitting A, section 1 of 3. No hints; standard-library docs are fine.

## Situation

Parcelo (a **synthetic** parcel-shipping platform) hands you `lab/route_report.py`, which turns raw
depot scan lines into a routing report. It "works on yesterday's file". It also has several defects,
and `build_report` is hard to change.

## Task

1. **Debug.** Make every function satisfy the specification below. Do not change function names or
   the meaning of their arguments (you may add type hints, helpers, classes).
2. **Refactor.** Leave the module in a state you would be content to have reviewed: no duplicated
   logic in `build_report`, clear names, errors handled deliberately rather than swallowed.
3. **Write down** what you found in `lab/NOTES.md` (one line per defect; 3-6 lines on the refactor).

## Specification

A scan line is `parcel_id,ISO-8601 timestamp,depot_code,weight_kg`, e.g. `P004512,2025-06-02T08:15:00,ALA,2.75`.

* `parse_scan(line)` returns `(parcel_id, datetime, depot, weight_kg)` (a tuple or anything that
  unpacks like one). `weight_kg` may be fractional. Returns `None` for malformed lines: wrong number of
  fields, empty parcel id or depot, unparseable timestamp or number, weight that is not strictly positive.
* `load_scans(lines)` parses an iterable of lines, skipping malformed lines and exact duplicate lines
  *within that call*. Two calls with the same lines return the same result.
* `group_legs(scans, max_idle_hours=12)` returns `{parcel_id: [leg, ...]}` with legs in chronological
  order. A leg is a dict with `start`, `end` (datetimes of first/last scan), `n_scans` and `depots`
  (depot codes in scan order). A new leg starts when the time since the parcel's previous scan is
  **strictly greater** than `max_idle_hours`. Scans may arrive in any order. The input is not modified.
* `trailing_average(values, window)` returns a list as long as `values`; element *i* is the mean of the
  last `window` values up to **and including** *i* (fewer at the start, where fewer exist).
* `busiest_depots(counts, k=3)` returns up to `k` `(depot, count)` pairs, largest count first, ties
  broken by depot code ascending.
* `build_report(lines, max_idle_hours=12, k=3)` returns a dict with keys `n_scans`, `n_parcels`,
  `n_legs`, `transit_hours`, `longest_leg_hours` (each of these three a dict by parcel; a leg's hours
  are `end - start`), and `busiest_depots` (scan counts per depot over all valid scans).

## Check your work

```bash
python wb.py check labs/w8d6_final_assessment/f1_python      # or:
python -m pytest labs/w8d6_final_assessment/f1_python/checks -q
```

The shipped starter fails several checks; that is expected.

## Acceptance criteria

* All checks pass (behaviour).
* `NOTES.md` names each defect and its cause - not just "fixed test X".
* The refactor is judged by reading your code (see `../SUBMISSION.md`); checks cannot grade it.

## Submit

`lab/route_report.py`, `lab/NOTES.md`, and the time you actually used.
