# Independent challenge: an alert budget, and a matching rule for another domain

Work without the hints first. About 60-75 minutes for both parts. Finish the lab before starting:
the challenge imports your `flowguard.evaluation` from `../lab/src` (or from `challenge/src` if you
copy the package there).

## Part A - choose an operating point under an alert budget (graded by checks + rubric)

**Scenario.** The reliability engineer will accept the detector only if it raises **at most one
false alarm per eight hours of normal operation**. Within that budget they want as many faults
found as possible, as early as possible.

1. In `operating_point.py` implement
   * `rate_upper_bound(n_false_alarms, hours, confidence=0.95)`: the exact one-sided upper
     confidence bound for a Poisson rate, in false alarms per hour;
   * `choose_operating_point(dev_tidy, dev_scores, budget_per_hour, thresholds, min_durations,
     merge_gaps, burn_in, early_tolerance)`: evaluate every grid setting on the development data it
     is given and return the choice described in the file's docstring. Selection rule: a setting is
     feasible if its dev false-alarm rate is within the budget; among feasible settings take the
     highest event recall, then the lowest median delay, then the lowest false-alarm rate. If nothing
     is feasible, return the setting with the lowest false-alarm rate (ties: highest recall) and say
     so with `feasible = False`.
2. Run the report on the real data (it calls your two functions; nothing else is needed):

   ```bash
   python lessons/w3d4_point_vs_event_evaluation/challenge/budget_report.py
   ```

3. Write `REPORT.md` (half a page): the chosen setting, dev and test results, and **the exact
   sentence you would send to the engineer about whether the budget is met**.

Acceptance criteria

* `python wb.py check w3d4 --challenge` passes.
* The function receives development data only. The test experiments are touched once, by the report.
* `REPORT.md` states counts and exposure (false alarms, hours) and an upper bound, not only a rate.
* The claim about the budget is one the data supports. (Decide what that is before you write it.)

## Part B - a matching rule for intermittent network outages (rubric only)

`outages.py` simulates 24 hours of a monitored link (SYNTHETIC): forty outages of 3-20 s, labels
taken from a ticket log that lags the real outage by 0-8 s, and two detectors with known behaviour.
Run it:

```bash
python lessons/w3d4_point_vs_event_evaluation/challenge/outages.py
```

Under the rule you built for SKAB the table is badly wrong about both detectors.

1. Explain in `OUTAGE_RULE.md` what in this domain breaks the SKAB rule. Be specific about label
   timing, event length and event rate.
2. Design a rule for this domain and implement it in `outage_rule.py::score_outages`, built from
   your `flowguard.evaluation` functions.
3. Defend each choice in `OUTAGE_RULE.md`, including what your rule can no longer measure and one
   way a detector could exploit it.

Acceptance criteria

* The script prints your rule's results for both detectors.
* Each parameter of the rule is justified from a property of the domain, not from the resulting score.
* You state the resolution limit of the delay you report.
* You name at least one way to game your rule and how you would notice.

Self-assess with the rubric in `solutions/lessons/w3d4_point_vs_event_evaluation/assessment_answers.md`
only after writing both documents.
