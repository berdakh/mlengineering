# Promotion detector — decision (w4d1 challenge) — REFERENCE

Numbers from the authoring run on the shipped `sales.csv` (SYNTHETIC) and on generator seeds 11-13.

## What I chose and why

Seasonal naive (same weekday last week) on log sales, scored by the **positive part** of the
standardised residual, with the threshold chosen on the second half of the development period.
Log sales make the weekly pattern and the uplift additive, so one residual scale fits every weekday.
The score is one-sided because a promotion only raises sales, and because the seasonal-naive forecast
for the week *after* a promotion is the promotion week itself: with absolute residuals every promotion
produces a second burst of large (negative) residuals seven days later, an "echo" false alarm. The AR(7)
alternative includes lag 1, so from the second promotion day onwards it forecasts the raised level and
the residual collapses — it detects promotion *starts*, not promotion *days*. AR is also anchored to the
fitted level, so the three stores with an unlabelled permanent level increase keep producing positive
residuals; seasonal naive absorbs such a change after one week.

## Development results (validation half, models fitted on the first half)

| method | score | dev F1 | test F1 (for reference only; not used to choose) |
|---|---|---|---|
| seasonal naive | positive part | 0.900 | 0.945 |
| seasonal naive | absolute | 0.611 | 0.641 |
| AR(7) | positive part | 0.667 | 0.637 |
| AR(7) | absolute | 0.547 | 0.530 |

Chosen: seasonal naive, one-sided, threshold 1.432 (residual standard deviations).

## Test result

Precision 0.941, recall 0.949, F1 0.945 over 1,830 store-days (117 promotion days) in the test half
year. On three fresh generator seeds the same procedure gave F1 0.881, 0.813 and 0.879.

What this establishes: on data from this generator, the procedure (not just this threshold) works and
the one-sided choice matters (absolute residuals: F1 0.53-0.64 on the same seeds). What it does not:
anything about real retail data. The unit of evaluation is the store-day, and days within a promotion
are not independent; with 10 stores and about 25 test promotions, an interval on F1 would be wide.
Test errors were spread over stores (at most 2 false positives in any store), but the AR alternative's
errors concentrated in the stores with a level change (11 and 5 false positives in S01 and S05).

## What would break this detector in a real retailer

* Holidays and events that move the weekly pattern (a public holiday on a Monday): the forecast from
  last week is wrong for a week, and so is the forecast the week after. A holiday calendar is needed.
* Stock-outs and closures: a zero-sales day becomes the reference for next week and creates an echo
  in the other direction; one-sidedness helps only partly.
* Promotions longer than a week, or weekly recurring promotions: the reference week is itself a
  promotion, and the residual vanishes. A longer reference (median of several past weeks) is the usual fix.
