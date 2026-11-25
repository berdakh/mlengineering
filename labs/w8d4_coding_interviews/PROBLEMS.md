# w8d4 — the timed set: six Python problems and three SQL problems

**Conditions (Weeks 6-8 level).** Timer on for each problem; talk aloud and record (the talk-aloud protocol
is in section 2.3 of the lesson). No hints, no AI assistance, no web search; the Python standard library
documentation and the SQLite documentation are allowed, as in most interviews that let you run code. Write
your own small tests before running the checks. Run the checks only when you would hand the answer in:

```bash
python wb.py check w8d4                                                     # everything
python -m pytest labs/w8d4_coding_interviews/checks -q -k p3            # one problem
```

After each problem, log in `progress/notes.md`: time taken, passed or not, pattern, the mistake (if
any), and the pattern behind the mistake. Score the talk-aloud against the rubric in `assessment.md`.

| # | Level | Pattern family (revealed after you finish) | Time box | File |
|---|---|---|---|---|
| P1 | easy | (hidden) | 10 min | `lab/python/p1_label_disagreements.py` |
| P2 | easy | (hidden) | 12 min | `lab/python/p2_match_alarms.py` |
| P3 | medium | (hidden) | 15 min | `lab/python/p3_dedup_events.py` |
| P4 | medium | (hidden) | 20 min | `lab/python/p4_top_k_variance.py` |
| P5 | medium | (hidden) | 20 min | `lab/python/p5_min_batch_cost.py` |
| P6 | medium-hard | (hidden) | 25 min | `lab/python/p6_pipeline_order.py` |
| Q1 | SQL | (hidden) | 12 min | `lab/sql/q1_city_revenue.sql` |
| Q2 | SQL | (hidden) | 12 min | `lab/sql/q2_top_drivers.sql` |
| Q3 | SQL | (hidden) | 18 min | `lab/sql/q3_longest_streak.sql` |

The essential session does P1, P2, P3, Q1, Q2 (about 65 minutes of problem time); P4-P6 and Q3 are the
optional extension or the next review day. The large-input checks enforce the complexity stated in each
docstring with a time limit of 4 seconds; a correct but quadratic solution fails them.

---

## P1 — Annotators who disagree (easy)

Labelling records arrive as `(sample_id, annotator, label)`. An annotator may label the same sample again
(a correction); only their latest label counts. Return the sorted list of sample ids for which the
annotators' latest labels are not all the same. Required: O(n).

## P2 — Which faults did the alarms catch? (easy)

`alarms` and `faults` are sorted lists of times. A fault at `f` is detected by an alarm at `a` when
`f <= a <= f + tolerance`. Each alarm can detect at most one fault; process faults in time order and give
each the earliest unused alarm in its interval. Return the detection delays `a - f` of the detected
faults, in fault order. Required: O(len(alarms) + len(faults)).

## P3 — Alert deduplication (medium)

Events `(t, key)` arrive sorted by `t`. Keep an event unless an event with the same key was **kept** less
than `window` seconds earlier. Suppressed events do not restart the window. Return the kept events in
order. Required: O(n).

## P4 — The noisiest sensors (medium)

Readings `(sensor_id, value)` arrive in any order. Return the `k` sensors with the largest **population**
variance of their values, largest first; ignore sensors with fewer than two readings; variances equal to
12 significant digits are ties, broken by sensor id ascending. Values can be around 1e9 with a spread
below 1. Required: about O(n + s log s) for `s` sensors.

## P5 — Micro-batches with a bounded worst batch (medium)

Inference requests with positive integer costs arrive in a fixed order and must be grouped into at most
`max_batches` contiguous batches. Return the smallest possible cost of the most expensive batch.
`n` up to 100,000, costs up to 1,000,000. Required: about O(n log(sum of costs)).

## P6 — Pipeline run order (medium-hard)

Given step names and `(before, after)` dependencies, return an order of all steps that respects every
dependency; when several steps are ready, run the alphabetically smallest first (so the answer is unique).
Raise `ValueError` if a dependency names an unknown step, or if there is a cycle (name a step on it).
Must handle 30,000 steps, including one chain of 30,000.

---

The SQL problems use the SYNTHETIC ride-hailing database `data/rides.db` (schema in
[`data/README.md`](data/README.md)). Write one SQLite query per file. Start each file with a comment
stating the **grain** of your result. Run a query yourself with:

```bash
python -c "import sqlite3,sys; c=sqlite3.connect('labs/w8d4_coding_interviews/data/rides.db'); [print(r) for r in c.execute(open(sys.argv[1]).read())]" labs/w8d4_coding_interviews/lab/sql/q1_city_revenue.sql
```

## Q1 — City revenue for March 2026

For **every** city (including cities with no trips), for trips requested in March 2026 with status
`completed`: the number of completed trips, the number of those trips with at least one `succeeded`
payment, and the revenue in currency units (sum of succeeded payment `amount_cents` / 100, rounded to 2
decimals; 0 when none). Columns: `city, completed_trips, paid_trips, revenue`, ordered by city.
A trip can have several payment attempts.

## Q2 — Top two drivers per city, March 2026

For each city, the two drivers with the most completed trips requested in March 2026 (ties broken by the
smaller `driver_id`; a city with one active driver returns one row; cities without trips return nothing).
Columns: `city, driver_id, completed_trips, rank` (1 or 2), ordered by city then rank.

## Q3 — Each driver's longest streak

For each driver with at least one completed trip (any date), the longest run of consecutive calendar days
on which they completed at least one trip. Columns: `driver_id, streak_start` (`YYYY-MM-DD`),
`streak_length`; if two streaks are equally long, report the earlier one; ordered by `driver_id`.
