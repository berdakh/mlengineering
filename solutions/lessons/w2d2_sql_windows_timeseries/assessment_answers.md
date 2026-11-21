# W2D2 assessment — model answers

Open after writing your own answers. Numbers quoted for the lab database were read from runs on
2026-11-21 (SQLite 3.53.1). The data is SYNTHETIC.

## Q1 — frames by hand

| id | (a) default frame | (b) explicit ROWS, total order | (c) empty OVER |
|---|---|---|---|
| 1 | 10 | 10 | 36 |
| 2 | 35 | 30 | 36 |
| 3 | 35 | 35 | 36 |
| 4 | 36 | 36 | 36 |

(Executed: these are the values SQLite returns.) With `ORDER BY` and no frame, the frame is
`RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`, and under RANGE the current row extends to its
last peer, so rows 2 and 3 (both `t = 2`) each include the other. (c) has no `ORDER BY`, so every
row is a peer of every other and the frame is the whole partition.

*Common incorrect answers*

- **(a) = 10, 30, 35, 36.** Assumes rows. This is the belief the lesson exists to remove.
- **(a) = 10, 30, 30, 36 or "undefined".** The result is fully defined; it is the *order of ties in
  (b) without `id`* that would be undefined.
- **"They differ because of ROWS vs RANGE" with no mention of peers.** True but not an explanation:
  with no ties the two frames give identical results, which is why the bug hides in testing.

## Q2 — evaluation order

`WHERE alert = 1` is applied before the window is computed, so the partition contains only alerting
readings and `LAG` returns the previous *alerting* reading. The query returns the time since the
previous alert, not since the previous reading. Fix: compute the gap over all readings in a CTE,
filter afterwards.

```sql
WITH gaps AS (
    SELECT reading_id, alert,
           ts_epoch - LAG(ts_epoch) OVER (PARTITION BY device_id ORDER BY ts_epoch) AS gap_s
    FROM readings_dedup
)
SELECT reading_id, gap_s FROM gaps WHERE alert = 1;
```

On the lab database both versions return 546 rows; the median is 322.5 s for the wrong version and
304 s for the right one. The medians are close because most alerting readings sit inside runs, where
the previous reading is also an alert. The difference is concentrated at the first reading of each
run, where the wrong version reports the time since the previous episode. A bug that is right
for most rows is the usual shape of window-function errors.

*Common incorrect answers*

- **"Add `PARTITION BY`"** — it is already there; the problem is the row set, not the partition.
- **"Use `HAVING`"** — `HAVING` also runs before windows.
- **"`LAG` skips NULLs"** — unrelated; `LAG` reads the physical previous row of the partition.

pandas has the same hazard: `df[df.alert == 1].groupby("device_id").ts_epoch.diff()`.

## Q3 — "latest row"

- (i) and (ii) return **every** row tied at the maximum timestamp: two rows for each device in the
  lab data (verified: all six devices have two). A join on `device_id` then duplicates every
  downstream row for those devices; counts and sums inflate.
- (iii) returns one row per device, but *which* of the tied rows is not determined by the query.
  It can change with the query plan, an index, or the engine. One row, unstable content.
- Accept none as written. Require `ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY ts_epoch DESC,
  event_id DESC)`: a total order, justified by a domain rule ("log order"). Also ask for a test that
  `COUNT(*) = COUNT(DISTINCT device_id)` in the result.

*Common incorrect answers*

- **"(iii) is fine, ROW_NUMBER guarantees one row."** It guarantees one row, not the right one.
- **"Use `SELECT DISTINCT` to remove the duplicates."** The tied rows differ in `status`, so they
  are not duplicates; `DISTINCT` keeps both.
- **"Use `MAX(status)`"** — picks alphabetically; `running` beats `fault`.

## Q4 — merging runs separated by one reading

The grouping stays; only the start condition changes. Number each device's readings 1, 2, 3, ...
in time order (`pos`). Among alerting rows, a row starts a new episode unless the previous
*alerting* row is at most two positions back:

```sql
WITH seq AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY ts_epoch) AS pos
    FROM readings_dedup
),
alerts AS (
    SELECT *,
           CASE WHEN pos - LAG(pos) OVER (PARTITION BY device_id ORDER BY pos) <= 2 THEN 0 ELSE 1 END AS starts
    FROM seq
    WHERE alert = 1          -- deliberate: here "previous alerting row" is exactly what LAG should see
),
numbered AS (
    SELECT *, SUM(starts) OVER (PARTITION BY device_id ORDER BY pos
                                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS episode_no
    FROM alerts
)
SELECT device_id, episode_no, MIN(ts) AS start_ts, MAX(ts) AS end_ts, COUNT(*) AS n_alert_samples
FROM numbered
GROUP BY device_id, episode_no;
```

Executed on the lab database: 110 episodes instead of 113, covering the same 546 alerting readings.
Note that this is the Q2 mechanism used on purpose: the `WHERE` restricts the window to alert rows.
The first alerting row of a device has `LAG(pos)` NULL, the comparison is NULL, and `CASE` falls to
`ELSE 1`, which is the intended start.

Relation to detection work: this is the merge-gap rule (join detections closer than a refractory
interval). Differences worth stating: the gap here is measured in **rows**, so a 2-hour outage
between two alerts counts as "adjacent"; a time-based rule (`ts_epoch - LAG(ts_epoch) <= 600`) is
usually what the requester means, and you should ask. A minimum-duration rule would be a `HAVING`
on the grouped result.

*Common incorrect answers*

- **Changing `GROUP BY`** or post-merging episodes with a self-join: works, but quadratic and much
  harder to get right than changing the start mark.
- **`LAG(alert, 2) = 1`** on all rows as the only condition: mishandles the pattern 1, 0, 0, 1 vs
  1, 0, 1 unless combined carefully, and breaks at partition starts.

## Q5 — is it point-in-time correct?

- **(a) leaks.** For a label on the 10th, the monthly mean includes the 11th to the 31st. Any
  aggregate over a period that contains the label time, and extends past it, reads the future.
- **(b) leaks,** more subtly: the normalising constants are computed from all rows, including
  those after `t` (and, in a train/test setting, from test rows). The effect is often small, as you
  saw with the scaler in W1D3; the fix is by construction, not because a metric moved.
- **(c) can leak.** `readings_dedup` keeps the transmission with the highest `reading_id`, the
  *corrected* value, which arrived after the measurement and possibly after `t`. At prediction
  time only the first transmission existed. The measurement timestamp is in the past; the
  information is not. Detecting this needs an ingestion timestamp per row (bitemporal data:
  event time and knowledge time), and the feature rule becomes "ingested_at <= t". The lab
  database lacks that column, so this cannot be fixed there, only named.

*Common incorrect answers*

- **"(a) is fine because it's the same device."** Entity match is necessary, not sufficient.
- **"(c) is fine, it passed the future-invariance check."** The check edits rows by *event* time. It
  cannot see late-arriving corrections. No test replaces knowing how the table is written.

## Q6 — design choice (model answer)

Design 2. Converting the 2,000 calibration rows to half-open intervals `[valid_from, valid_to)`
with `LEAD(valid_from) OVER (PARTITION BY device_id ORDER BY valid_from)` is cheap and makes the
rule explicit and unit-testable on the small table: intervals of one device must not overlap and
must tile the time axis from its first `valid_from`; the last interval has `valid_to` NULL, meaning
open. The fact-side join then matches **at most one** row per reading by construction, so there is
no fan-out followed by a 500-million-row `ROW_NUMBER` sort, which is what design 1 costs: every
reading first joins to *all* earlier calibrations of its device and the excess is discarded.
Boundaries are visible in the predicate: `valid_from <= ts AND (valid_to IS NULL OR ts < valid_to)`
makes `valid_from` inclusive, matching the specification. A `LEFT JOIN` keeps readings older than
the first calibration. Ties cannot occur if `(device_id, valid_from)` is unique, which should be
enforced as a constraint or a data-quality check rather than assumed. Design 3 moves 500 million
rows out of the warehouse to do what the warehouse can do in place, and creates a second
implementation for the serving path to diverge from; `merge_asof` is the right tool for testing the
SQL on a sample. Tests: row count equals the reading count; no reading matches two intervals; the
lab's comparison against an independent implementation on a sample; future-invariance (appending a
later calibration row changes no earlier reading). I would revisit the choice if the engine has a
native as-of join, which is usually both clearer and faster than either pattern.

(Executed: the interval form returns exactly the same table as the reference `q6` on the lab database.)

*Common weak answers*

- **"Design 1 because it is the one from the lab."** No cost reasoning.
- **"Design 3 because pandas is easier to test."** Ignores data volume and the duplicated logic.
- **Design 2 with `BETWEEN valid_from AND valid_to`.** `BETWEEN` is closed on both sides, so a
  reading exactly at a change time matches two intervals.

## Interview rep — reference and rubric

Reference query: [`interview_rep/longest_streak.sql`](interview_rep/longest_streak.sql), verified by
`python solutions/lessons/w2d2_sql_windows_timeseries/interview_rep/check_longest_streak.py`.

The idea: after de-duplicating to one row per (user, day), consecutive days have consecutive
`ROW_NUMBER()` values, so `day_number − row_number` is constant within a streak. Group by it.

| Criterion | What a good answer shows |
|---|---|
| Grain first | de-duplicates to (user, day) before anything else and says why |
| Island key | date minus row number (or start-mark and running sum) with correct partitioning |
| Date arithmetic | converts dates to day numbers; does not subtract text; month and year ends work |
| Final selection | one row per user via `ROW_NUMBER` ordered by length descending then start; not `MAX` joined back (ties) |
| Verification | builds a tiny table including a duplicate day, a month boundary, a single-day user, a tied pair of streaks |
| Communication | states grain at each step; answers the follow-ups |

Follow-ups: grain after step one is (user, day). Month boundaries work because the day number is a
count of days, not a `YYYYMMDD` integer (a frequent bug: 20260131 + 1 is not 20260201). Allowing
one missed day means switching to the start-mark form: a new streak starts when
`day − LAG(day) > 2`.

*Common incorrect answers*

- **Skipping the de-duplication.** Two logins on one day get row numbers n and n+1 with the same
  date, which splits the streak.
- **`ROW_NUMBER` without `PARTITION BY user_id`.** Row numbers run across users.
- **Final step `WHERE streak_days = (SELECT MAX(...))`.** Returns two rows for a user with tied streaks.

## Challenge — what the feature table shows

Reference: [`challenge/features.sql`](challenge/features.sql). Point-in-time correctness rests on one
condition per source, each placed in a join's `ON` clause: `r.ts_epoch <= l.label_ts_epoch` (twice)
and `e.ts_epoch <= l.label_ts_epoch`.

ROC AUC of each raw feature against `failed` on the shipped database (38 labels, 15 failures;
missing values filled with the median; for `seconds_since_fault` the sign is flipped and missing
means "long ago"):

| Feature | Correct query | With the named leak |
|---|---|---|
| `last_temperature` | 0.484 | 0.670 (nearest reading instead of last prior) |
| `mean_temp_60m` | 0.441 | 0.971 (window of 60 minutes on both sides) |
| `n_alerts_24h` | 0.514 | — |
| `seconds_since_fault` | 0.458 | 1.000 (nearest fault at any time) |

How to read this honestly:

- With 15 positives and 23 negatives, the standard error of an AUC near 0.5 is roughly 0.10
  (Hanley–McNeil approximation), so the correct features are **indistinguishable from chance** on
  this data. The generator contains a weak precursor, but it does not show at this sample size.
  That is a legitimate result: "no usable signal in these features with 38 labels".
- Each leaky variant looks like a breakthrough. `seconds_since_fault` reaches 1.000 because the
  fault event *is* the failure, logged minutes later. An AUC that jumps from about 0.5 to about 1.0
  from one feature should trigger an audit of that feature before anything else.
- The tempting wrong conclusion is "the honest features are useless, so the centred window is
  better". The centred window is not a better feature; it is not available when the prediction is
  made.
- This is SYNTHETIC data built to show the mechanism. It says nothing about how predictable real
  refrigeration failures are.

*Common incorrect submissions* (kept as mutants; all rejected by the checks):

| Mutant | Mistake |
|---|---|
| `centered_window` | `ABS(r.ts_epoch - l.label_ts_epoch) <= 3600` for the hourly mean |
| `nearest_reading` | orders candidate readings by absolute time distance |
| `fault_any_time` | joins fault events without a time bound and takes the nearest |

Two further mistakes the specification check catches without reading the future: putting the time
bound in `WHERE` after a `LEFT JOIN` (labels without history disappear), and `>=`/`<` slips at the
interval ends (a reading exactly at the label time must be included).
