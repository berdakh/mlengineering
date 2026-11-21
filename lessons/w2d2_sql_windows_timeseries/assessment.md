# W2D2 assessment

Write your answers (a few sentences each, plus SQL where asked) before opening
`solutions/lessons/w2d2_sql_windows_timeseries/assessment_answers.md`. Automated checks cover the
lab and the challenge; these questions cover the reasoning the checks cannot see.

## Reasoning questions

**Q1 — frames by hand.** A table has four rows `(id, t, x)`: `(1, 1, 10)`, `(2, 2, 20)`, `(3, 2, 5)`,
`(4, 3, 1)`. Without running anything, give the four values of each expression, listed by `id`:

- (a) `SUM(x) OVER (ORDER BY t)`
- (b) `SUM(x) OVER (ORDER BY t, id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)`
- (c) `SUM(x) OVER ()`

Then say in one sentence why (a) and (b) differ.

**Q2 — evaluation order.** This query is meant to return, for each alerting reading, the time
since the device's previous reading:

```sql
SELECT reading_id,
       ts_epoch - LAG(ts_epoch) OVER (PARTITION BY device_id ORDER BY ts_epoch) AS gap_s
FROM readings_dedup
WHERE alert = 1;
```

What does it actually return, why, and how do you fix it?

**Q3 — "latest row".** Three colleagues compute the latest status per device with
(i) `WHERE ts = (SELECT MAX(ts) ...)`, (ii) `RANK() ... = 1`, (iii) `ROW_NUMBER() OVER (PARTITION BY
device_id ORDER BY ts DESC) = 1`. For data with tied timestamps, describe the result of each and
the consequence for a downstream `JOIN ... USING (device_id)`. Which would you accept in review?

**Q4 — changing the definition of an event.** Operations asks that two alert runs separated by a
*single* non-alert reading be reported as one episode. Describe the change to the gaps-and-islands
query from the lab (the start condition is enough; SQL is welcome). How does this relate to event
merging rules you have used for detections in iEEG?

**Q5 — is it point-in-time correct?** For each feature attached to a label at time `t`, say whether it
can read the future and why:

- (a) the device's mean temperature over the calendar month containing `t`;
- (b) temperature z-scored with the mean and standard deviation of the whole `sensor_readings` table;
- (c) `last_temperature` as defined in the challenge, computed from `readings_dedup`.

## Design-choice explanation

**Q6.** The calibration as-of join must go to production on a warehouse table with about 500
million readings and 2,000 calibration rows. Three designs are proposed:

1. the lab's pattern: join on `valid_from <= ts`, then `ROW_NUMBER()` and keep 1;
2. first turn `calibration` into intervals `[valid_from, valid_to)` with `LEAD`, then join on
   `valid_from <= ts AND ts < valid_to`;
3. export both tables and use `pandas.merge_asof`.

Choose one and justify it in 6–10 sentences. Address correctness (ties, boundaries, readings before
the first calibration), cost, and how the result will be tested.

## Rubric

| Criterion | Not yet | Adequate | Strong |
|---|---|---|---|
| Frame semantics (Q1) | values guessed or (a) = (b) | all values right | explains peers and the default frame, and why the last row hides the error |
| Evaluation order (Q2) | "LAG is wrong" without mechanism | identifies that `WHERE` runs before the window; gives a two-level fix | also notes the same hazard for any filter (time range, device subset) and for pandas `df[mask].shift()` |
| Uniqueness contracts (Q3) | prefers (i) or (ii) | picks `ROW_NUMBER`, notes fan-out | demands a total order, states that (iii) as written is non-deterministic, proposes a uniqueness test |
| Transfer of islands (Q4) | restarts from scratch or changes the grouping | correct new start condition | relates it to merge-gap / minimum-duration rules and notes the definition is in rows, not seconds |
| Leakage reasoning (Q5) | judges by whether a timestamp is "used" | (a) and (b) leak, with reasons | also catches (c): values corrected after `t`; names the missing column |
| Design explanation (Q6) | chooses by familiarity | defensible choice with cost and correctness | states the invariants to test (row count, future-invariance, boundary inclusion) and what would change the decision |

## Interview rep — SQL (10–15 minutes, timed)

Conditions for Week 2: first attempt untimed is allowed, but time yourself. Write the query
before running anything; then build a six-row table and test it. Say the grain of every
intermediate result aloud.

> Table `logins(user_id TEXT, login_date TEXT)` holds one row per login, with dates as
> `YYYY-MM-DD`. A user may log in several times a day. For each user return the length in days of
> their longest streak of consecutive calendar days with at least one login, and the first day of
> that streak. If a user has two longest streaks of equal length, return the earlier one.
> One row per user.

Follow-up questions an interviewer would ask: What is the grain after your first step? What does
your query do at a month boundary? How would it change if "consecutive" allowed one missed day?

Log the rep in `progress/notes.md`: time taken, what went wrong, the pattern behind the error.
