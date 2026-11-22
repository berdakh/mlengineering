# Error analysis: `flow_rate` burn-in z-score on SKAB development experiments - reference reading

Produced from `error_report.py`, run 2026-11-21 on SKAB v0.9 (commit `b2c0d46`). Your wording will
differ; the numbers should not, if you used the same manifest.

## Object

| | |
|---|---|
| Model | abs z of `flow_rate` against the experiment's own first 100 rows (the bar from w2d6) |
| Threshold and how it was chosen | 2.577, best F1 on the 25 development experiments (dev F1 0.686). Chosen on the analysed data: one parameter, mild optimism |
| Data | manifest v2 (`make_splits(seed=0, keep_together=overlap groups)`), 25 development experiments, rows `t >= 100`. The 9 test experiments were not scored |
| Date / commit | 2026-11-21 |

The v2 manifest has a different test set from w2d6's v1 table, so the development F1 here (0.686) is
not comparable with numbers in `BASELINES.md`.

## Headline

Recall per experiment: mean 0.663, range 0.007 to 0.993. Row-pooled recall 0.656. The spread, not the
mean, is the result: six experiments are below 0.5 and six are above 0.85.

At the event level nothing is missed: every one of the 25 anomalous segments has at least one flagged
row, and 19 are first flagged within 30 rows of onset.

## Failure modes, ranked

| Rank | Kind | Size (segments / rows / experiments) | Evidence | Suspected cause | Cost | Fixability |
|---|---|---|---|---|---|---|
| 1 | Fragment: alarm drops out after first detection | 695 / 2,861 / 24 | 50 % of all wrong rows. `other/5`: flagged 3 rows after onset, then silent for 375 rows (recall 0.007). `valve1/2`: 185-row dropout | A per-sample threshold on a noisy score; and in some experiments flow responds to the fault transiently, then settles at a level within 2.6 sd of burn-in | Point recall collapses; operationally, one fault produces many separate alerts | 0.6 for the threshold-noise part (hysteresis or hold time); low for the transient part (needs another sensor or a change statistic) |
| 2 | Pre-onset alarms | 648 / 1,346 / 23 | 24 % of wrong rows; mostly very short runs (median well under 5 rows), plus `other/13` with a 329-row run before its labelled onset | Mostly threshold noise (2.6 sd is exceeded by chance about 1 % of the time, and normal rows are autocorrelated); `other/13` is the experiment whose rows overlap `other/12` with contradictory labels | False alerts; trust | 0.7 for the short runs (minimum duration); `other/13` is a label issue, not fixable in the model |
| 3 | Post-event alarms | 407 / 1,081 / 21 | 19 % of wrong rows; `other/12` 171 rows, `other/13` 161 rows | Flow does not return to the burn-in level after the fault; reference is stale | False alerts after a real fault, probably cheap | 0.4 (re-baselining after an event) |
| 4 | Late detection (> 30 rows) | 6 / 273 / 6 | `other/7` 80 rows, `valve1/6` 46, `valve1/2` 41, `other/10` 38, `valve2/2` 37, `other/1` 31 | Slowly developing faults; flow moves gradually | Delay is the stakeholder's stated concern | 0.3 with this sensor alone |
| 5 | Boundary | 25 / 149 / 19 | Short runs at event edges | Label timing and response lag | None worth work | Handle by tolerance in evaluation (w3d4) |

Ranking by frequency x cost x fixability puts fragmentation first on all three. Late detection has
the highest cost per case and the smallest size.

## Slices checked and found unremarkable

| Slice | Values (mean recall, experiments) | Reading |
|---|---|---|
| family | valve1 0.681 (12), valve2 0.680 (3), other 0.635 (10); intervals for valve1 and other overlap almost entirely | no family effect on recall is supported |
| has a time gap > 5 s | gap 0.622 (5), none 0.673 (20) | nothing |
| shares rows with another file | shares 0.617 (5, range 0.007-0.987), unique 0.674 (20) | nothing on recall |
| burn-in flow level | low 0.695 (16), high 0.606 (9) | nothing |

One slice does differ: experiments whose mean flow moves less than one burn-in sd under the fault have
mean recall 0.445 (7 experiments, interval 0.21-0.70) against 0.747 (18, interval 0.64-0.83). That
slice is defined using the labels and is close to a restatement of "a flow detector fails when flow
does not move". It is an explanation of the misses, not a discovery, and not a usable feature.

False-alarm rate does differ by family: other 0.256 (10 experiments, interval 0.12-0.43) against
valve1 0.110 (12, interval 0.06-0.16). Two `other` experiments (`other/13` at 0.878, `other/12` at
0.618) carry much of that, and both are in the contradictory-label group.

Five slicing variables were examined for recall. No correction was applied; the one difference
reported is large relative to its interval, and it is tautological anyway.

## Label issues

235 distinct measurements occur in two files with opposite labels (`other/12`/`other/13`: 178;
`other/3`/`other/4`: 57). A detector that is a function of the sensors alone is wrong on one copy of
each. `other/12` and `other/13` are in development; `other/3` and `other/4` are in test. With burn-in
normalisation the two copies can receive different scores, so the count of baseline errors on
contradictory rows (24 across the four experiments, `label_conflicts_skab.py`) is not the irreducible
figure. The large pre-onset run in `other/13` coincides with rows labelled anomalous in `other/12`.

## Next experiments

1. **Hysteresis / hold time.** Raise the alarm at 2.6 sd, clear only below a lower level or after a
   minimum hold. Expect: fragment rows down by more than half, pre-onset short runs down with a
   minimum-duration rule, detection delay up by the minimum duration. Wrong if: fragment rows fall by
   under 20 %, which would mean the dropouts are sustained returns to baseline and not threshold noise.
2. **A second signal for transient responders** (`other/5`, `valve1/2`, `valve1/0`, `other/8`): add a
   multivariate burn-in score or a change statistic. Expect recall on those four up; false-alarm rate
   up. Wrong if recall on them stays under 0.3.
3. **Report with the contradictory-label experiments excluded and included,** so later comparisons are
   not driven by rows no model can get right.

## Limits

* One model, one threshold, tuned on the analysed data.
* `valve2` has three development experiments: its row in any table is three numbers.
* Segment counts depend on `late_after = 30` and on treating row index as time; six experiments have
  recording gaps longer than 5 s that the row index ignores.
* The "pre-onset" category may contain genuine precursors. Nothing here distinguishes them from noise.
* Whether hysteresis helps is a prediction until it is run on these same development experiments and
  then, once, on test.
