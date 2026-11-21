# W2D2 — SQL II: CTEs, window functions and time-series queries

**Unit id:** `w2d2` · **Week 2, day 2** · **Content status:** Execution verified (see [Verification record](#verification-record))
**Handbook:** [H3.2 Window functions and time-series SQL](../../handbook/ch03_sql_data_pipelines/h3_2_window_functions_timeseries_sql.md)
**Data:** [`data/coldchain.db`](data/README.md) — SYNTHETIC, built to contain specific traps. Results in this lesson show that queries are correct; they say nothing about real equipment.

---

## 1. Purpose

**Primary objective.** Write window-function queries that are correct on tied, duplicated and
irregularly sampled data — ranking, running statistics, run-length segmentation (gaps and islands)
and as-of joins — and reproduce each result in pandas.

**What you will learn**

- Where window functions sit in SQL's logical evaluation order, and why that forces CTEs.
- The three parts of a window (`PARTITION BY`, `ORDER BY`, frame) and the default-frame trap.
- Gaps and islands: turning a per-sample flag into events, inside the database.
- As-of joins and point-in-time correctness: the SQL form of "no future information".
- The pandas idiom for each pattern, and where the two disagree at boundaries.

**Why an applied ML engineer needs it.** Features and labels are usually born in SQL, before any
Python runs. The three failures this lesson targets all produce queries that execute, return the
right number of rows and are wrong: a "latest row" that is not unique, a rolling window that
silently counts rows instead of time, and a join that reads a value that did not exist yet at
prediction time. The last one is temporal leakage, and it is far easier to commit in a join than
in a training loop. Window functions are also the most common SQL interview topic above the
join-and-group level.

**Prerequisites.** [W2D1](../w2d1_sql_joins_grain/README.md): stating the grain of a result, join
fan-out, `NULL` semantics. Python >= 3.11 whose `sqlite3` module is linked against SQLite >= 3.28
(`python -c "import sqlite3; print(sqlite3.sqlite_version)"`; the checks tell you if it is too old).
No `sqlite3` command-line tool is needed.

**Time budget — essential path 2 h**

| Activity | Time |
|---|---|
| Read section 2 (2.2, 2.3 and 2.6 carefully; skim what you know) | 25 min |
| Worked example: run it, predict each table before reading it | 15 min |
| Guided lab: six queries (40 min), three pandas functions (15 min) | 55 min |
| Independent challenge: specification, first working version | 15 min |
| Assessment questions (written) | 10 min |

**Optional extension — up to 1 h:** finish the challenge until its checks pass (30 min), interview
rep (15 min), handbook H3.2.6 on engine differences (15 min).

---

## 2. Conceptual explanation

### 2.1 Intuition: a window function adds a column without collapsing rows

`GROUP BY` answers "one number per group" and destroys the rows. A window function answers "for
each row, a number computed from *related* rows" and keeps every row. You already do this
constantly: a z-score against a subject's own baseline, a moving RMS over the preceding second, the
sample index within a trial. In pandas these are `groupby(...).transform(...)`, `rolling(...)`,
`groupby(...).cumcount()`. SQL spells them all the same way:

```sql
function(args) OVER (PARTITION BY <who are my relatives> ORDER BY <in what sequence> <frame: which of them>)
```

| Part | Meaning | Signal-processing analogue |
|---|---|---|
| `PARTITION BY` | rows are only compared within the same partition | per subject / per channel / per trial |
| `ORDER BY` | the sequence inside a partition | the time axis |
| frame | which rows around the current one feed the function | the analysis window |

### 2.2 Logical evaluation order

A `SELECT` is evaluated, logically, in this order:

```
FROM / JOIN  ->  WHERE  ->  GROUP BY  ->  HAVING  ->  window functions  ->  SELECT list / DISTINCT  ->  ORDER BY  ->  LIMIT
```

Three consequences you will meet today:

1. **A window function cannot appear in `WHERE`, `GROUP BY` or `HAVING`**, because those run earlier.
   "Keep the row with `rn = 1`" therefore needs two levels: compute `rn` in a CTE or subquery,
   filter outside. SQLite's message when you forget is `misuse of aliased window function rn`.
2. **`WHERE` changes what a window sees.** A filter removes rows before the window is computed, so
   `LAG` returns the previous *surviving* row. Filtering to `alert = 1` and then asking for the
   previous reading gives the previous alerting reading, which is rarely what you meant.
3. **Windows run after aggregation**, so `RANK() OVER (ORDER BY SUM(x) DESC)` in a grouped query is
   legal and ranks the groups.

A **CTE** (`WITH name AS (...)`) is the tool for staging these levels. Treat each CTE as one step
with a stated grain, exactly as you would name intermediate DataFrames.

### 2.3 Frames, and the default that bites

The frame is the subset of the partition used for the current row. Two units matter here:

- `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW` counts **physical rows**.
- `RANGE BETWEEN 1800 PRECEDING AND CURRENT ROW` measures the **`ORDER BY` value**: all rows whose
  key lies in `[current − 1800, current]`. It needs exactly one ordering key, numeric to be meaningful
  (hence `ts_epoch`, not the text `ts`).

With irregular sampling these are different windows. "Seven rows" is thirty minutes only if no
sample was lost. On the lab data the two definitions give a different mean for 2,929 of 4,707 rows.

**Peers.** Rows with equal `ORDER BY` values are *peers*. Under `RANGE`, `CURRENT ROW` means "the
current row and all its peers". Under `ROWS` it means the physical row.

**The default frame.** If you write `ORDER BY` inside `OVER` and no frame, the frame is

```sql
RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
```

so a running total includes the current row's peers. Two rows that tie get the same total, each
containing the other. With no `ORDER BY` at all, the frame is the whole partition.

For a cumulative sum $S_i = \sum_{j \le i} x_j$ to be well defined, the index $i$ must be a
*total* order. So the rule is: **make the ordering total (add a tie-breaker such as an id) and
write the frame explicitly** when you mean rows.

The ranking functions express the three possible attitudes to ties:

| Function | Ties | Values for scores 70, 55, 55, 40 |
|---|---|---|
| `ROW_NUMBER()` | broken arbitrarily unless the ordering is total | 1, 2, 3, 4 |
| `RANK()` | share a rank, then skip | 1, 2, 2, 4 |
| `DENSE_RANK()` | share a rank, no skip | 1, 2, 2, 3 |

"Top 1 per group" with `RANK() = 1` (or `WHERE ts = (SELECT MAX(ts) ...)`) returns several rows
when the top is tied. If the result is then joined on the group key, every downstream row is
duplicated. Use `ROW_NUMBER()` with a deterministic tie-breaker when the contract is "exactly one".
`ROW_NUMBER()` with a non-total ordering is worse than `RANK()`: it returns one row, but which one
may change between runs or engines.

### 2.4 Offsets: `LAG`, `LEAD` and intervals from events

`LAG(x)` and `LEAD(x)` read the previous and next row of the partition; they ignore the frame.
Two standard uses:

- **Differences and gaps:** `ts_epoch - LAG(ts_epoch) OVER (PARTITION BY device_id ORDER BY ts_epoch)`.
- **Events to intervals:** a status log stores *changes*. The state that begins at one event ends at
  the next one, so `LEAD(ts_epoch)` gives the interval end. The last event has no successor; you
  must decide where it ends (a report horizon) and say so. Summing durations by state gives
  time-in-state. A cheap invariant: per device the durations must add up to the observed span.

### 2.5 Gaps and islands: from samples to events

You have written this many times in NumPy: `np.diff` on a thresholded detector output, pair up
rising and falling edges, get events with onset and offset. The SQL form has the same two steps.

1. **Mark starts.** A row starts an island if it is flagged and the previous row *of the same
   partition* is not: `alert = 1 AND COALESCE(LAG(alert) OVER (...), 0) = 0`.
2. **Number islands.** A running sum of the start marks is constant within an island and increases
   by one at each new start. Group by it.

```
alert        0 0 1 1 1 0 1 0 0 1 1
start        0 0 1 0 0 0 1 0 0 1 0
cumsum       0 0 1 1 1 1 2 2 2 3 3     <- on flagged rows this is the island number
```

An equivalent trick subtracts two row numbers (`ROW_NUMBER()` over all rows minus `ROW_NUMBER()`
over flagged rows is constant within a run). The start-mark version generalises better: change the
start condition to "gap since previous row > 30 minutes" and the same query **sessionises** by time
gap; change it to "status differs from previous" and it collapses repeated states.

Where the analogy with your detection work breaks: in iEEG you usually merge events closer than a
refractory gap and discard events shorter than a minimum duration, on a uniform sample grid. Here
"consecutive" means adjacent *rows*, and a lost sample between two flagged rows does not split the
run. Whether that is right is a definition you owe the reader; state it (the lab does).

The classic error is forgetting the partition in step 1. `LAG` then looks at the previous row of
another device, which is the same bug as running event extraction across concatenated channels.

### 2.6 As-of joins and point-in-time correctness

Some tables describe *what was true from when*: a calibration, a price list, a customer's plan, a
model version. For a fact at time $t$ you need the dimension row in force at $t$:

$$\text{match}(t) = \arg\max_{k} \{\, v_k : v_k \le t \,\}$$

where $v_k$ are the `valid_from` times of that entity's rows. This is an **as-of join**. Standard SQL
has no single keyword for it; the portable pattern is: join on the entity key **and**
`valid_from <= t`, then keep the latest match per fact row with `ROW_NUMBER()`. Use a `LEFT JOIN`
so that facts older than the first dimension row survive with `NULL`s rather than vanishing.

The same construction defines a **point-in-time-correct feature**. For a label observed at
prediction time $t_\ell$, a feature may be any function of rows with timestamp $\le t_\ell$ and of
nothing else:

$$f_\ell = g\big(\{\, r : \text{entity}(r) = \text{entity}(\ell),\ t_r \le t_\ell \,\}\big)$$

This gives a property you can test without knowing the right answer: **edit every row after
$t_\ell$ arbitrarily; $f_\ell$ must not change.** The challenge checks use exactly this.

Three ways a join reads the future, all common:

| Mistake | What it looks like |
|---|---|
| Join to the *current* dimension row | `JOIN calibration USING (device_id)` on a "latest" view |
| Symmetric window | `ABS(r.ts - l.label_ts) <= 3600`, a centred window carried over from offline analysis |
| Nearest instead of previous | `ORDER BY ABS(r.ts - l.label_ts)`, or `merge_asof(direction="nearest")` |

There is one more that no query can detect: a row whose *timestamp* is in the past but which was
*written* later (a backfilled or corrected value, such as the re-sent readings in today's data).
Point-in-time correctness is about when information became available, which needs an ingestion
time. Today's data has only `reading_id` as a proxy for arrival order; H3.2.5 discusses this.

### 2.7 The same operations in pandas

| SQL | pandas | Boundary to watch |
|---|---|---|
| `ROW_NUMBER() OVER (PARTITION BY g ORDER BY k)` | `df.sort_values(k).groupby(g).cumcount() + 1` | sort first; ties need a total order in both |
| `RANK()` / `DENSE_RANK()` | `groupby(g)[k].rank(method="min" / "dense")` | default `method="average"` matches neither |
| `LAG(x)` / `LEAD(x)` | `groupby(g)[x].shift(1)` / `shift(-1)` | a bare `df.x.shift()` crosses groups |
| running sum, `ROWS` frame | `groupby(g)[x].cumsum()` | row order is whatever the frame currently has |
| `RANGE BETWEEN 1800 PRECEDING AND CURRENT ROW` | `rolling("1800s", closed="both")` on a datetime index | pandas' default is `closed="right"`: `(t−30 min, t]` |
| aggregate `OVER (PARTITION BY g)` | `groupby(g)[x].transform("mean")` | — |
| as-of join | `pd.merge_asof(left, right, on=..., by=..., direction="backward")` | both frames sorted by the `on` key; `allow_exact_matches=True` means `<=` |
| top-1 per group | `sort_values(...).groupby(g).head(1)` or `drop_duplicates(g, keep="last")` | — |

Pushing work into SQL is not a matter of taste: the database filters and aggregates next to the
data, and the feature definition lives where the serving path can reuse it. Pandas is the better
place to prototype and to test. Doing both and asserting equality, as today, is a cheap way to
find the boundary cases neither version handles on its own.

### 2.8 Industry example

A logistics company bills cold-chain customers for temperature compliance. The compliance report
is three of today's queries: the current status of each unit (latest row per device), hours spent
in each state last month (events to intervals), and excursion episodes with duration and peak
(gaps and islands on calibrated readings joined as of each reading's time). A re-calibration in
the middle of the month must not rewrite last week's excursions; that is the as-of join. When the
same company later trains a failure-prediction model, the feature table is the challenge query,
and the first model review asks precisely whether any feature could see past the inspection time.

### 2.9 Limits and misconceptions

- *"The query ran and the row count is right, so it is right."* Every mutant kept for this lesson
  satisfies both. Check the grain, check ties, check a boundary case.
- *"`ROW_NUMBER` makes it deterministic."* Only if the ordering is total.
- *"`ORDER BY` in the window sorts the output."* It orders rows for the function only; the result
  order is undefined without a final `ORDER BY`.
- *"A window function is slow / always fast."* It needs a sort per distinct window; an index on
  `(partition key, order key)` can supply it. The range-join form of an as-of join is quadratic
  per entity in the worst case. Fine for today's data; see H3.2.6 for what engines offer.
- *"SQLite behaves like the warehouse."* The window semantics used today are standard. Time
  arithmetic, types and named as-of syntax differ by engine.

---

## 3. Worked example: scan events on two packaging lines

**File:** [`example/window_tour.py`](example/window_tour.py). Fourteen hand-typed scan events
(SYNTHETIC, small enough to follow by eye) in an in-memory SQLite table:

| Column | Type | Meaning |
|---|---|---|
| `event_id` | int | log order |
| `line` | text | packaging line, A or B |
| `ts` | text | scan time |
| `operator` | text | who scanned |
| `units` | int | units in the scanned batch |

Planted on purpose: events 2 and 3 share a timestamp and a unit count; event 9 is an exact re-send
of event 8; there are gaps of more than 30 minutes.

```bash
python lessons/w2d2_sql_windows_timeseries/example/window_tour.py
```

The script runs five patterns and asserts that each equals its pandas equivalent. Output of the
run on 2026-11-21 (SQLite 3.53.1, pandas 3.0.5), abridged to the three tables worth studying:

```
--- 1. ranking functions on line A, ORDER BY units DESC ---
 event_id line  units  row_number  rank  dense_rank
        5    A     70           1     1           1
        2    A     55           2     2           2
        3    A     55           3     2           2
        1    A     40           4     4           3
        4    A     30           5     5           4
        6    A     20           6     6           5

--- 3. running total on line A: default frame versus explicit ROWS ---
 event_id                  ts  units  default_frame  rows_frame
        1 2026-05-04 08:00:00     40             40          40
        2 2026-05-04 08:10:00     55            150          95
        3 2026-05-04 08:10:00     55            150         150
        4 2026-05-04 08:25:00     30            180         180
        5 2026-05-04 09:40:00     70            250         250
        6 2026-05-04 09:55:00     20            270         270

--- 4. de-duplicated, sessionised by a 30-minute gap ---
line  session_no            start_ts              end_ts  n_scans  units
   A           1 2026-05-04 08:00:00 2026-05-04 08:25:00        4    180
   A           2 2026-05-04 09:40:00 2026-05-04 09:55:00        2     90
   B           1 2026-05-04 08:05:00 2026-05-04 08:45:00        3    160
   B           2 2026-05-04 10:30:00 2026-05-04 10:40:00        2     50
   B           3 2026-05-04 11:30:00 2026-05-04 11:35:00        2    105
...
All five SQL results equal their pandas equivalents.
```

**Reading the output**

- *Table 1.* The three functions agree until the tie at 55 units. Which of events 2 and 3 gets
  `row_number` 2 is not determined by `ORDER BY units DESC`; it happened to be event 2.
- *Table 3.* Event 2's `default_frame` total is 150, not 95: it already contains event 3, its peer.
  Nothing fails, and the last row of the partition is correct in both columns, which is why this
  bug survives a glance at totals.
- *Table 4.* Line B, session 1 has three scans, not four, because the exact duplicate was removed
  first. De-duplicating *after* sessionising would have given 250 units instead of 160.

**Code decisions worth noticing**

- The top-1 query (pattern 2 in the script) is shown twice, with `RANK` and with `ROW_NUMBER` plus
  `event_id` as tie-breaker. Line B has two rows in the first version.
- Sessionisation is three CTEs — `dedup`, `gaps`, `numbered` — each with one job. The start
  condition is `gap_min IS NULL OR gap_min > 30`: the first row of a partition has no predecessor
  and must start a session explicitly, because `NULL > 30` is not true.
- The pandas version of the ranking uses `rank(method="min")` and `rank(method="dense")`. The
  default, `method="average"`, would give 2.5 for the tied rows and matches no SQL function.
- Every comparison sorts both results by a key first. SQL results have no inherent order.

**Reproduce:** the script has no inputs and no randomness; the output above should match exactly
apart from the version line.

---

## 4. Guided lab: six queries on cold-chain data

**You produce:** six SQL files in [`lab/queries/`](lab/queries/) and three functions in
[`lab/pandas_equiv.py`](lab/pandas_equiv.py). Each starter file contains the full specification
(source, grain, columns, rules) and a placeholder statement.

Read [`data/README.md`](data/README.md) first (3 minutes): it lists the tables and the properties
built into the data. Then explore:

```bash
python lessons/w2d2_sql_windows_timeseries/lab/run_query.py --sql "SELECT * FROM device_status_events LIMIT 8"
python lessons/w2d2_sql_windows_timeseries/lab/run_query.py q1            # runs lab/queries/q1*.sql
python lessons/w2d2_sql_windows_timeseries/lab/run_query.py q5 --where "device_id = 'D03'" --rows 30
python wb.py check w2d2                                                   # all lab checks
python -m pytest lessons/w2d2_sql_windows_timeseries/checks -q -k q1      # one query only
```

The checks run every query on the shipped database **and** on a second database generated from a
different seed, and compare with results computed independently in plain Python. Column names must
match the specification; column order and row order do not matter.

Before each query, write its grain in a comment at the top (you did this in W2D1). It is the
fastest way to notice a wrong result.

### Task 1 — `q1_latest_status.sql`: one row per device (5 min)

Latest status per device, with log order deciding between equal timestamps.

*Checkpoint:* exactly 6 rows. Then run this and explain the difference to yourself:

```bash
python lessons/w2d2_sql_windows_timeseries/lab/run_query.py --sql "SELECT device_id, COUNT(*) FROM device_status_events e WHERE ts_epoch = (SELECT MAX(ts_epoch) FROM device_status_events WHERE device_id = e.device_id) GROUP BY 1"
```

### Task 2 — `q2_time_in_state.sql`: events to intervals (8 min)

Seconds per device and status. `LEAD` has a three-argument form, `LEAD(expr, offset, default)`,
which is the neat way to close the last interval.

*Checkpoint:* 24 rows (6 devices × 4 statuses in the shipped data). For each device the seconds
must sum to the time from its first event to the report end; all six devices start at
2026-03-01 00:00:00, so each total is 259,200.

### Task 3 — `q3_running_alerts.sql`: a running count that survives ties (6 min)

This one runs on the **raw** table, where a measurement can appear twice with the same timestamp.

*Checkpoint:* 4,811 rows. Write the obvious version first
(`SUM(alert) OVER (PARTITION BY device_id ORDER BY ts_epoch)`), then find a row where it is wrong:

```bash
python lessons/w2d2_sql_windows_timeseries/lab/run_query.py q3 --where "reading_id IN (SELECT MIN(reading_id) FROM sensor_readings GROUP BY device_id, ts_epoch HAVING COUNT(*) > 1 AND MIN(alert) <> MAX(alert))" --rows 5
```

Compare the count on such a row with the count on the row just before it in `(ts_epoch, reading_id)` order.

### Task 4 — `q4_rolling_features.sql`: a time window on an irregular grid (8 min)

From here on use the view `readings_dedup`. Look at its definition first:

```bash
python lessons/w2d2_sql_windows_timeseries/lab/run_query.py --sql "SELECT sql FROM sqlite_master WHERE name = 'readings_dedup'"
```

Two windows are needed (one for the 30-minute frame, one for `LAG`). A `WINDOW` clause after
`FROM` lets you name them once: `WINDOW seq AS (...), w30 AS (...)`.

*Checkpoint:* 4,707 rows; `n_30m` ranges from 1 to 8; `gap_s` has median 302 and maximum 7,734; `delta_prev` and
`gap_s` are `NULL` on exactly 6 rows.

### Task 5 — `q5_alert_episodes.sql`: gaps and islands (8 min)

*Checkpoint:* 113 episodes in the shipped data, the longest 15 samples. Sanity check you can
compute yourself: the sum of `n_samples` equals `SELECT SUM(alert) FROM readings_dedup`.

### Task 6 — `q6_asof_calibration.sql`: as-of join (8 min)

*Checkpoint:* 4,707 rows — the same as `readings_dedup`; if you have fewer, a join dropped rows; if
more, you kept more than one calibration row per reading. 68 rows (all D06, before 06:00 on the
first day) have `NULL` in the three computed columns.

### Task 7 — `pandas_equiv.py`: three functions (15 min)

Implement `rolling_features`, `alert_episodes` and `asof_calibration`. The checks compare each
with the specification and with *your own* SQL result.

*Checkpoint:* `python wb.py check w2d2` passes all 26 checks, in about 2 seconds.

### Debugging guidance

| Symptom | Likely cause |
|---|---|
| `misuse of aliased window function rn` | You filtered on a window result in the same `SELECT`. Move the window into a CTE (section 2.2). |
| `more than one row per ['device_id']` | Ties: your ordering is not total, or you used `RANK`. |
| q2 totals do not sum to the span | The last interval is not closed, or `LEAD` is ordered by `ts_epoch` alone and a tied pair is taken in the wrong order. |
| q3 differs on "26 of 4811 rows" or similar small count | Default frame; peers are being added to each other. |
| q4 `temp_mean_30m` differs on thousands of rows | A `ROWS` frame where time was meant. |
| q4 differs on a handful of rows | Window boundary: is `t − 1800` itself included? |
| q5 has several times too many episodes | `LAG` without `PARTITION BY device_id`. |
| q6 has NULLs in different rows than expected | Inner join dropped the uncalibrated period, or a later calibration was applied to earlier readings. |
| pandas `ValueError: left keys must be sorted` | `merge_asof` needs both frames sorted by the `on` key (globally, not within `by`). |
| pandas rolling result is misaligned | After `groupby(...).rolling(...)` the result has a (group, time) index; align by position only if your frame is sorted the same way. |
| pandas `ValueError: index values must be monotonic` | Sort by time within each group before a time-based `rolling`. |

Do not print whole tables to find a wrong row. Filter the *result* with `--where`, or select the
rows around one timestamp for one device.

---

## 5. Independent challenge: a point-in-time-correct feature table

Specification and acceptance criteria: [`challenge/README.md`](challenge/README.md). You write one
query, [`challenge/features.sql`](challenge/features.sql), producing five features for each of the
38 rows of `maintenance_labels`, using only information available at the label time.

```bash
python wb.py check w2d2 --challenge
```

No solution is linked from here. The check that matters rewrites everything after each label's
timestamp and requires that label's features to stay exactly the same.

---

## 6. Progressive hints

Open them in order, and only after a real attempt. They apply to the challenge; the lab has its
own debugging table above.

1. [Hint 1 — concept](hints/hint1_concept.md)
2. [Hint 2 — approach](hints/hint2_approach.md)
3. [Hint 3 — partial implementation](hints/hint3_partial.md)

The full reference solution is in `solutions/lessons/w2d2_sql_windows_timeseries/`. Opening it
before your own version passes means the `independent` flag stays unset for this unit.

---

## 7. Assessment

[`assessment.md`](assessment.md): five short reasoning questions, one design-choice explanation,
the rubric, and a 10–15 minute SQL interview rep. Write your answers before opening
`solutions/lessons/w2d2_sql_windows_timeseries/assessment_answers.md`.

Automated checks: `python wb.py check w2d2` (lab, 26 checks) and
`python wb.py check w2d2 --challenge` (4 checks).

---

## 8. Reflection and review

**You should now be able to, without help**

- return exactly one "latest" row per entity on data with tied timestamps, and say why it is exactly one;
- write a running or moving statistic with an explicit frame and justify `ROWS` versus `RANGE`;
- convert a per-row flag into events (or sessions) with start, end and size, per entity;
- join a fact to the dimension row in force at the fact's time, keeping unmatched facts;
- state and test the invariant that makes a feature point-in-time correct;
- reproduce each of these in pandas and name the boundary case where a naive translation differs.

**Reflection prompt** (3 minutes, in `progress/notes.md` via `python wb.py note w2d2 "..."`):
In your own research pipelines, where was a "centred" or "nearest" operation applied to data that
would later be used to predict something? Would that operation have been available online?

**Retrieval question — answer from memory at the Week 2 review (w2d7) and again in Week 3:**
A colleague's feature query uses `AVG(x) OVER (PARTITION BY device_id ORDER BY ts)` and reports
"mean of the last readings". (a) Exactly which rows are averaged for a given row? (b) Name two data
conditions under which this differs from what they probably meant. (c) What test would you run to
show that no feature in their table reads the future?

**Next:** [W2D3 — pandas ingestion, schemas and data-quality checks](../w2d3_data_quality_ingestion/README.md)
(`w2d3_data_quality_ingestion`). Today's de-duplication view and tie rules are data-quality
decisions that were made *for* you; tomorrow you write such rules as code that fails loudly, on the
project dataset. The point-in-time idea returns in `w2d5` (causal rolling features) and `w3d1`
(leakage taxonomy).

---

## Verification record

Executed on 2026-11-21 with Python 3.13.18, SQLite 3.53.1, pandas 3.0.5, NumPy 2.5.3, pytest 9.1.1.

| What | Result |
|---|---|
| `python lessons/w2d2_sql_windows_timeseries/example/window_tour.py` | ran; output above copied from this run; all five SQL-versus-pandas assertions hold |
| `python lessons/w2d2_sql_windows_timeseries/data/make_db.py --check` | regenerated table contents identical to the committed database |
| Reference SQL and pandas versus the independent plain-Python oracle | equal on the shipped database and on a re-seeded one (seed 77) |
| `python tools/verify_checks.py lessons/w2d2_sql_windows_timeseries` | lab: solution passes, 7 mutants rejected; challenge: solution passes, 3 mutants rejected |
| Shipped starter | lab checks: 26 of 26 fail; challenge checks: 4 of 4 fail |
| Check runtime | lab about 2 s, challenge about 2 s |
| Interview-rep reference query | executed against a hand-checked table; expected rows returned |

Row counts and other numbers in sections 2–4 were read from these runs. Not verified: any SQLite
older than 3.53.1 (the 3.28 minimum is from memory of the SQLite release history; the
SQLite documentation site was unreachable from the authoring environment), Python 3.11 and 3.12,
and behaviour on other database engines.
