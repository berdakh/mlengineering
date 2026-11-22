# Rubric: monitoring and label-backfill plan (w7d3 challenge)

Score each line 0 (absent or wrong), 1 (present but vague), 2 (specific and justified). The automated
checks only establish consistency; these lines judge quality.

| # | Criterion | 2 looks like |
|---|---|---|
| 1 | Three questions separated | validity, drift and performance each have their own signal, window, owner and action |
| 2 | Drift threshold | calibrated on stated reference data with a stated false-alarm rate; explains what a flag does and does not mean |
| 3 | Label sources | every source has a join key, delay range, coverage; says which metric each one can and cannot support |
| 4 | Windows and power | window length derived from the label rate and min_labels; says what difference the window can detect |
| 5 | Delay handling | metrics evaluated only after labels can have arrived; early estimates labelled as provisional and biased |
| 6 | Verification bias | names who decides what gets labelled and the direction of the resulting bias |
| 7 | Actions | drift alone never retrains; degradation escalates; insufficient data reported as unknown |
| 8 | Limits | states at least two things the plan cannot detect, quantitatively where possible |

12-16: a plan a reliability team could run. 8-11: workable with review. Below 8: rewrite.

## Common weak answers and why they fail

* **"Retrain when PSI > 0.2."** A fixed folklore threshold, and drift alone as a trigger. The replay's
  recalibrated sensor would have triggered a pointless retrain of a model whose scores had not changed.
* **"Monitor recall weekly."** Without a source of missed faults recall cannot be computed; with
  inspections arriving 14-60 days late a weekly recall is mostly empty or biased upward.
* **"Report 0 when there are no labels."** Reads as a collapse; the correct output is unknown with the
  count of pending labels.
* **"All alarms are labelled, so precision is unbiased."** True only if every alarm is investigated; if
  operators pick the worst-looking alarms, precision is biased upward.
