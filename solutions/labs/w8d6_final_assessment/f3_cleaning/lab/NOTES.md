# f3 notes (reference; counts are raw rows of accounts_dirty.csv, measured)

| Defect | Rows affected | How found | Decision |
|---|---|---|---|
| Several rows per account (17 exact duplicates, the rest stale versions with another tier) | 762 rows, 700 accounts | `account_id.nunique()` vs `len`; `duplicated()` | keep the row with the latest `updated_at` |
| `signup_date` in three formats: ISO, `DD.MM.YYYY`, local timestamp with offset | 223 dotted, 96 timestamps | `str.contains` on `.` and `T`; values like `25.12.2024` rule out MM.DD | parse each format explicitly; timestamps converted to UTC, then the calendar date |
| `region` case/whitespace noise and missing codes (`""`, `n/a`, `?`) | 40 rows missing-coded | `value_counts()` | strip, upper-case; codes -> missing |
| `tier` case/whitespace noise; invalid `platinum` | 7 `platinum` | `value_counts()` after normalising | normalise; outside the vocabulary -> missing |
| `fee` with `USD ` prefix; annual amounts (`usd_year`) | 149 prefixed, 189 annual | `fee_unit.value_counts()`; annual values are 12x the tier fee | strip prefix; annual / 12 |
| `employees` sentinels `-1`, `99999`; impossible `0`, `-40`, `250000` | 53 sentinels, 34 impossible | `value_counts()` of the extremes | missing |
