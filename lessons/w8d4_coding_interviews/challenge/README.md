# w8d4 challenge — a 45-minute mock with two unseen problems

**Conditions.** One 45-minute timer for both problems, talking aloud and recording, exactly as in a
technical screen. Do not open `checks_challenge/` or `solutions/` first. Spend the first two minutes
reading both problems and deciding the order. Write your own tests; run the checks at the end only.

```bash
python wb.py check w8d4 --challenge
```

## C1 — The longest stable stretch (Python, `python/c1_longest_stable_run.py`)

A sensor produces `values`. Return `(start, length)` of the longest contiguous run whose maximum minus
minimum is at most `tolerance`; the earliest run wins ties; empty input gives `(0, 0)`; a negative
tolerance raises `ValueError`. Must handle 300,000 values within a few seconds (O(n) is expected).

## C2 — March driver cohort (SQL, `sql/c2_driver_cohorts.sql`)

On the rides database: a driver belongs to the **March 2026 cohort** if their first **completed** trip was
requested in March 2026. A cohort driver is **active** if they completed at least 25 trips in the 30 days
starting at the timestamp of that first completed trip (from the first trip's `requested_at`, inclusive, to
30 days later, exclusive). For each city with at least one cohort driver (city from `drivers.city_id`):
`city, cohort_size, active_drivers, active_share` (active / cohort, rounded to 3 decimals), ordered by city.

## Acceptance criteria

1. Both check suites pass, including the large-input time limit for C1.
2. Your recording shows: restating each problem with an example, a stated brute force and its complexity,
   the improvement, your own tests (including an edge case), and the final complexity.
3. Score yourself with the talk-aloud rubric in `../assessment.md` before reading the reference notes in
   `solutions/lessons/w8d4_coding_interviews/assessment_answers.md`.
