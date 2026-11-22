# Model answers: w7d3 drift versus degradation

## 1. Shift types

* **Covariate shift**: $P(x)$ changes, $P(y \mid x)$ fixed. SKAB: the flow sensor is recalibrated, or the
  pump runs at a different set point.
* **Prior shift**: $P(y)$ changes, $P(x \mid y)$ fixed. SKAB: valves start failing more often (older
  parts), each failure looking as before.
* **Concept shift**: $P(y \mid x)$ changes. SKAB: a new fault mechanism (e.g. rotor imbalance) that leaves
  the flow rate untouched, or the plant redefines a fault to include short transients.

*Common wrong answer:* "concept drift = the data looks different". That is covariate shift; concept
shift can leave every input statistic unchanged.

## 2. Period B

The score is $\max_j |x_j - \mu_j| / \sigma_j$ with $\mu, \sigma$ estimated on each run's own burn-in.
Under $x' = a x + b$ with $a > 0$, $\mu' = a\mu + b$ and $\sigma' = a\sigma$, so every score is unchanged
(up to $10^{-14}$ rounding, which flipped 198 samples that sat exactly on the threshold but not which
faults were caught). A detector with *fixed* reference statistics (e.g. the w2d6 z-score against
development data, or a gradient-boosted model on raw levels) would see every sample shifted by
$(0.08\bar x + 2.5)/\sigma \approx (0.08 \cdot 32 + 2.5)/0.45 \approx 11$ standard deviations and alarm continuously: precision collapses.

*Common wrong answer:* "PSI was high so the model degraded but we got lucky." There was nothing lucky:
invariance to affine changes is a design property of per-run normalisation.

## 3. Period C's three numbers

* **Day 65, unknown.** Four alarms confirmed (four caught faults) and no missed-fault report had arrived
  yet (reports take 14-60 days). Four events is below `min_events = 5`.
* **Day 90, 0.67 [0.30, 0.90].** Two reports had arrived: 4 / (4 + 2).
* **Day 150, 0.36 [0.15, 0.65].** All 7 reports that will ever arrive: 4 / 11. The truth is 4 / 20; the
  9 missed faults that inspections never found are invisible. The estimate is an upper bound.

*Common wrong answer:* "the estimate converged, so it equals recall." It converged to $C / (C + \rho M)$
with $\rho \approx 0.6$, not to $C / (C + M)$.

## 4. Verification bias

Upward: the investigated alarms are those most likely to be true. Unbiased options: investigate a
**random** sample of the uninvestigated alarms as well (even 10 %), then weight each labelled alarm by
the inverse of its investigation probability (Horvitz-Thompson). Or investigate a random fraction of
all alarms instead of the top fraction. Report both the weighted estimate and the counts.

## 5. Window sizing

±0.10 needs about 90 faults of known outcome near recall 0.6 (Wilson). At 2 faults a week that is
about 45 weeks per window, and each answer is available 60 days after the window closes. Conclusion:
recall cannot be monitored on a useful cadence; use a fast proxy (alert rate, precision under a fixed
alert budget, operator feedback) for detection and recall for quarterly confirmation, and say so.

*Common wrong answer:* "a weekly window". It holds two faults.

## 6. Event time versus label time

* Window by event time, existence by label time (correct): each period is judged on its own events,
  with only the evidence available on that day.
* Window by **label** time: a fault from January confirmed in March counts in March. Degradation appears
  in the wrong period and is smeared over the delay distribution.
* Existence ignored (all labels used): a back-test sees labels that had not arrived; the monitor looks
  faster and more certain than it can be in production (the `ignores_as_of` mutant).

## 7. Inconclusive instead of a point comparison (design choice)

A point comparison turns noise into decisions: with 20 faults per period, the same model's recall
estimate moves by ±0.2 between periods. Comparing it with `baseline - 0.1` would raise false
"degraded" alarms and miss real drops at random. "Inconclusive" says what the evidence supports. To the
manager: green means the evidence shows the model is not worse by more than the margin; red means it
shows it is; amber means not enough evidence yet, with the date by which there will be. The cost: slower
and rarer red lights, and more ambers when events are rare; the remedy is longer windows or a faster
proxy, not a looser rule.

## Interview rep: churn dashboard (rubric and worked answer)

**Worked answer (outline).** The label (cancelled within 90 days) arrives 90 days after each
prediction, so "is the model still accurate this week" is not answerable this week. Show four panels.
(1) **Input validity**: share of requests rejected or imputed. (2) **Input and score drift**: calibrated
PSI on the top features and on the score distribution, plus the share of customers above the action
threshold, labelled as "inputs changed", not "model broken". (3) **Delayed performance**: AUC, precision
at the retention team's capacity, and calibration for the cohort predicted 90-120 days ago, with
intervals and the cohort size; earlier cohorts shown as "pending". (4) **Selection effects**: customers
who received a retention offer were treated, so their outcomes are not the model's untreated outcomes;
keep a random holdout without offers to measure the model honestly. Actions: drift → investigate;
measured drop → escalate; pending → wait. Mention seasonality (prior shift in churn) and that precision
moves with prevalence.

**Scoring.** 0-3 with the rubric in `assessment.md`. A 3 must mention the 90-day delay and pending
cohorts, intervals with counts, the treatment/holdout problem and one fast proxy with its failure mode.
