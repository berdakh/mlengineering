# w8d4 — model answers and reference notes

## Assessment questions

**Q1.** O(n · m) where m is the number of kept events scanned; worst case O(n²) when most events are kept
and keys repeat rarely (e.g. many keys, large gaps, or a small window). The check `test_p3_is_linear` uses
200,000 events with a small window so nearly all are kept. *Common wrong answer:* "O(n) because we break
early" — the break happens only when the key is found; for keys not seen recently the scan runs the full
list.

**Q2.** `RANK()` gives equal values the same rank, so three drivers tied at the top all get rank 1 and the
city returns three rows; `ROW_NUMBER()` numbers rows uniquely and the `driver_id` tie-breaker makes the
choice deterministic. `DENSE_RANK()` is right when the question asks for "all drivers with the top two
*counts*" (ties included by design). *Wrong:* `ROW_NUMBER()` without a tie-breaker — correct row count,
non-deterministic answer.

**Q3.** Storing values: O(n) memory, two passes, exact enough with `pvariance` (it uses exact arithmetic on
the input floats). Welford: O(s) memory for s sensors, one pass, streaming-friendly, numerically stable.
Both are O(n) time. In an interview, Welford if the input could be a stream or huge; storing is acceptable
if you say the memory cost. The one to avoid is `E[x²] − E[x]²`, which fails for large offsets (the check
uses values near 1e8-1e10 with spreads below 1).

**Q4.** Feasibility must be **monotone**: if a maximum batch cost X is achievable, every X' > X is too.
Then the smallest feasible X is found by binary search between max(costs) (a batch must hold the largest
item) and sum(costs) (one batch). The greedy check is correct because packing each batch as full as
possible never increases the number of batches needed.

**Q5.** `march_completed`: one row per completed March trip; `paid`: one row per trip with a succeeded
payment; the join `cities ⟕ march_completed ⟕ paid` has one row per (city, trip) or one per city with no
trips. Invariants: `SUM(completed_trips)` equals `SELECT COUNT(*) FROM trips WHERE status='completed' AND
March`; revenue equals the sum of succeeded payments of those trips computed separately; the city count is 5.

**Q6.** CPython's default recursion limit is about 1,000 frames; a recursive DFS on a 30,000-step chain
raises `RecursionError` (raising the limit risks a crash of the interpreter). Kahn's algorithm only emits a
step when all its predecessors are done; steps on a cycle never reach in-degree 0, so if fewer than V steps
are emitted, a cycle exists among the remaining ones.

**Q7.** Say it: "I have an O(n²) solution; let me write it so we have something correct, then optimise."
Write the brute force quickly with a test, then name the bottleneck (the repeated scan, the repeated sort)
and the data structure that removes it. Interviewers score progress and reasoning, not only the final
complexity.

## Notes on the timed set (read after your attempt)

| # | Pattern | Key insight | Most common mistake (and the mutant that encodes it) |
|---|---|---|---|
| P1 | hash maps | nested dict: latest label per annotator | collecting all labels per sample (`p1_counts_changed_minds`) |
| P2 | two pointers | the alarm pointer only moves forward | not consuming the alarm (`p2_alarm_reused`); nested loops (`p2_nested_loops`) |
| P3 | sliding window + hash map | only the last *kept* time per key matters | updating on every event (`p3_window_from_last_seen`) |
| P4 | aggregation + top-k | Welford or two-pass; population variance; explicit tie rule | n − 1 (`p4_sample_variance`); `E[x²] − E[x]²` (`p4_naive_sum_of_squares`) |
| P5 | binary search on the answer | monotone feasibility check | walking up one unit at a time (`p5_greedy_average`) |
| P6 | graphs (topological sort) | Kahn's algorithm with a min-heap | recursive DFS (`p6_recursive_dfs`); no cycle check (`p6_no_cycle_check`) |
| Q1 | grain, joins, fan-out | pre-aggregate payments per trip; LEFT JOIN from cities | joining attempts (`q1_fanout_count`); inner join drops a city (`q1_inner_join_drops_city`) |
| Q2 | top-n per group | `ROW_NUMBER` with a tie-breaker | `RANK` (`q2_rank_keeps_ties`); counting cancelled trips (`q2_all_statuses`) |
| Q3 | gaps and islands | `day - row_number` on DISTINCT days | one row per trip (`q3_trips_not_days`); latest tie (`q3_latest_tie`) |
| C1 | sliding window, monotonic deques | max and min of a window in amortised O(1) | adjacent differences only (`c1_adjacent_differences`); O(n²) (`c1_quadratic`) |
| C2 | cohorts, relative windows | first completed trip + `DATETIME(first, '+30 days')` | calendar month (`c2_calendar_month`); first trip of any status (`c2_first_trip_any_status`); integer division (`c2_integer_division`) |

Reference solutions: `lab/python/*.py`, `lab/sql/*.sql`, `challenge/python/c1_longest_stable_run.py`,
`challenge/sql/c2_driver_cohorts.sql`. Each mutant's `MUTANT.md` names the checks that reject it.
