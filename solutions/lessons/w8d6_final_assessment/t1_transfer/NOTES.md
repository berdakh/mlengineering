# t1_transfer - reviewer notes

## What the checks establish, and what is left to the rubric

The 18 checks grade the evaluation mechanics: declared features exclude the three post-decision
columns; the split is by service date (not booking date); the metric ranks within each service day
and rounds up; scores do not change when post-decision columns are scrambled or test labels flipped;
the model does not beat the generator's own probabilities; the run reports sizes, a baseline, an
interval and slices that partition the called reservations; it works on a re-seeded table.

Measured on the shipped table (2026-11-22): rule 0.322, reference model 0.371 [0.313, 0.425], oracle
0.409, random 0.173. A model that reads `customer_no_show_rate` reaches about 0.60 - the checks reject
it because it beats the oracle and because scrambling changes its scores.

## Rubric for REPORT.md

| Aspect | Demonstrated independently | Partial | Not yet demonstrated |
|---|---|---|---|
| Framing | unit, decision time (evening before), label, action, decision metric | metric chosen without the daily budget | AUC as headline |
| Leak audit | every column classified with a reason; the three leaks named with their mechanism | leaks removed without reasons, or one missed in the text | a leak used |
| Split | by service date, and the booked-before-cutoff rows discussed | correct split, no reasoning | by booking date or random |
| Baseline and comparison | rule without a model, compared on the same metric; uncertainty of the difference addressed | rule present, difference over-claimed | no rule |
| Interval | resampling unit justified (days or restaurants), what it does not cover stated | interval without a unit | none |
| Slice | size and precision reported, next check proposed | slice without size | none |
| Limitations | synthetic data, interval scope, deployment feedback/shift | one of them | none |

Within 90 minutes and unassisted, all rows "Demonstrated" is strong evidence for the transfer of
Weeks 2-4 to a new tabular problem. Compare with the w3d6 sitting (same rubric shape).
