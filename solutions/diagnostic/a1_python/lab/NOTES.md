# a1 notes (reference)

## Bugs found
1. `load_events(lines, seen=[])`: mutable default is created once, so duplicates were remembered
   across calls and a second call on the same lines returned nothing. Fixed with a local set.
2. `parse_line` used `int()` for minutes, so `42.5` was silently dropped by the bare `except`.
   Fixed with `float()`, an explicit `ValueError` handler, and rejection of negative/non-finite minutes
   and of lines without exactly three fields.
3. `sessionize` assumed chronological input. Fixed by sorting per customer.
4. `sessionize` used `timedelta.seconds`, which ignores whole days: a gap of 1 day + 5 min counted as
   5 min. Fixed with `total_seconds()`.
5. `rolling_mean` averaged the *previous* `window` values, excluded the current one, divided by
   `window` even for short prefixes, and the negative slice start wrapped around. Rewritten.
6. `top_customers` sorted ties by customer_id descending (`reverse=True` applies to the whole tuple).

## Refactoring
`build_report` had three copies of the same loop; replaced by comprehensions over the sessions dict.
Events are a NamedTuple so fields have names but still unpack as tuples. Type hints and docstrings
state the contracts the tests rely on. No behaviour was changed in the same edit as a structural change.
