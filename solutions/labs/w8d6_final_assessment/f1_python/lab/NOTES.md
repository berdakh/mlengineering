# f1 notes (reference)

## Defects found

1. `parse_scan` used `int()` for the weight: fractional weights such as `2.75` were rejected. -> `float()`.
2. `parse_scan` accepted zero/negative weights, empty ids/depots and extra fields (no field-count check). -> explicit validation.
3. Bare `except:` swallowed every error, including programming errors. -> catch `ValueError` only.
4. `load_scans(lines, seen=set())`: mutable default argument, so duplicates "remembered" from an earlier call were dropped in the next one. -> local `seen`.
5. `group_legs` called `scans.sort(...)`: mutated the caller's list, and sorted by time only (fine for grouping, but the side effect violates the contract). -> `sorted()` copy, keyed by (parcel, time).
6. `timedelta.seconds` ignores whole days: a 24 h 30 min gap read as 30 min, so legs were not split and leg hours were wrong. -> `total_seconds()`.
7. `trailing_average` divided by `window` even when fewer values existed (start of the list). -> divide by `len(chunk)`.
8. `busiest_depots` sorted `(count, depot)` descending, so ties came out in *descending* depot order. -> key `(-count, depot)`.

## Refactor

`build_report` computed leg hours twice with the same buggy expression and counted legs with a manual
loop; it is now one comprehension per output key over a shared `_hours` helper. A `Scan` named tuple
documents the record, still unpacks like a tuple. Every function states its contract in a docstring.
`trailing_average` rejects `window < 1` instead of silently returning nonsense.
