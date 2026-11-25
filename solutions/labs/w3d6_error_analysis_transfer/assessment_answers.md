# w3d6 assessment - model answers

## Reasoning questions

**1.** Pooled recall weights each experiment by its number of anomalous rows; the experiment mean
weights them equally. They agree when experiments have similar numbers of positives (SKAB development: 265-586,
mostly about 400) and disagree when sizes differ and correlate with difficulty (planted data: one
600-row success, three 30-row failures). (a) The reliability engineer cares about faults, so the
per-experiment view, and really the distribution: "7 of 27 below 0.5". (b) Alert storage scales with
flagged rows, so the pooled, row-level figure.

*Common incorrect answers.* "The mean is more robust" (to what? it answers a different question).
"Pooled is the correct recall" (it is one of two estimands). Reporting either without sizes.

**2.** Frequency: fragments are 50 % of wrong rows, late 4 %. Cost per case: a late detection costs
the delay the stakeholder named, 32-80 s each on five events; fragments cost recall on paper
and, operationally, hundreds of separate notifications per fault (alert fatigue), which also erodes
trust in the alerts that matter. Fixability: fragments about 0.6 with hysteresis, a known and cheap
change; late detections about 0.3 with this sensor. Product puts fragments first. It reverses if the
operator already merges alerts within an event (then fragments cost little) or if a missed 60 s is
safety-relevant. Note the interaction: the fragment remedy adds delay, so the two cannot be ranked
and fixed independently.

*Common incorrect answers.* Ranking by row count alone. Ranking late first "because the stakeholder
said delay" without sizing it (5 events, all detected). Ignoring that the fixes trade off.

**3.** (i) It is defined from the labels (mean flow during the anomalous segment), so it is not
available at prediction time and cannot be a routing rule or feature. (ii) It is close to a
tautology: a detector built on flow deviation has low recall where flow deviates little; the slice
restates the metric. Also acceptable: (iii) it was the fifth slice examined, on 6 experiments, with
no correction. A legitimate version: a slice computable before or without the outcome (fault family
from the maintenance log, operating regime at burn-in), stated in advance, confirmed on held-out
experiments.

*Common incorrect answer.* "It's significant because the intervals barely overlap." Overlap is not
the issue; the definition is.

**4.** Cannot conclude: that the detector raises many false alarms on normal operation. The rows it
flags before the labelled onset of `other/13` include rows that `other/12` labels anomalous, so at
least part of the "pre-onset alarm" is the detector agreeing with the other file's label. Can
conclude: the label for this physical stretch of data is contested, and any per-experiment figure for
these two files has an irreducible component. Presentation: keep both in the table, flag them, and
give headline figures with and without the contradictory-label group. Do not delete them silently and
do not let them drive a family comparison (they produce most of `other`'s false-alarm excess).

*Common incorrect answers.* "Drop the bad experiments" (changes the benchmark invisibly). "The model
is bad on `other`" (two files).

**5.** `flow_rate` is quantised, so within an experiment the burn-in z-score takes few distinct
values. Moving the threshold by 0.0017 (from the tuned 2.4044 to the next distinct score value, 2.4061) crosses
one of those values and flips every row sitting on that level at once (here 28 anomalous rows of
`valve1/3`, recall 0.834 to 0.765). Survives: the ranking of failure kinds (fragment
about 50 % at both thresholds), zero missed events, the lack of a family effect. Does not survive:
any statement about an individual experiment's recall or delay to two decimals, and anything inferred
from "the best threshold". General lesson: a tuned threshold on a discrete score is a point on a
staircase; report sensitivity to it.

**6.** The ceiling for this quarter is 0.751 (ranking by the true probabilities); the rule is at
0.727 and the model's interval is 0.65-0.78. The most a perfect model could add is about 0.02, well
inside the interval, so no model can be shown "clearly ahead" with 209 calls; a boosting model that
appears to be is more likely to have found a leak or noise. Instead: ship the rule; spend effort on
(a) whether calls change payment (randomised hold-out), (b) the no-history customers the policy never
calls, (c) a second cut-off date to check stability. In a real project the ceiling is unknown; the
interval alone already says the comparison cannot be resolved.

*Common incorrect answers.* "Try more models and pick the best on test." "Collect more features"
without asking what decision changes.

**7.** Because on the training day those labels do not exist. An evaluation is a rehearsal of
deployment; if the rehearsal uses information the deployment lacks, its number is not an estimate of
anything, whether or not the number moves. They differ a lot when the excluded window is informative
about the test period: fast drift (the late rate was rising here, mildly), a regime change just
before the cut-off, or a small training set where the last three months are a large share. They also
differ when label delay depends on the outcome (lates are known *later* than on-times, so the freshest
"known" labels are biased towards on-time; restricting by a fixed decision date avoids that).

## Design-choice explanation - model answer

Choose `h` and the lower threshold by grouped cross-validation over the 27 development experiments
(overlap groups kept together), never on test. For each candidate compute, on held-out folds,
fragment rows, pre-onset short runs, and detection delay per experiment; pick the smallest `h` after
which fragment rows stop falling, not the F1 maximum, since F1 on this benchmark rewards anything
that fills the event. Fix the candidate grid in advance (say `h` in {5, 10, 20, 40}, lower threshold
in {1.5, 2.0}) so the search is eight configurations. Expected side effect: delay rises by up to `h`
rows and post-event alarms lengthen. Abandon if fragment rows fall by less than 20 % at `h = 20`, or
if median delay rises by more than the stakeholder's tolerance (to be asked; it is not in the brief).
Report per-experiment changes, not only means, and run the chosen setting once on test at the end.

*Common weak answers.* Tuning `h` to maximise dev F1 on all 27 experiments and reporting that F1.
Omitting the delay cost. Having no abandon criterion.

## Interview rep - rubric (read after your first attempt)

| Aspect | Weak | Adequate | Strong |
|---|---|---|---|
| Opening | proposes a fix (retrain, more data) | lists possible causes | asks first what differs between the two measurements: population, time, label definition, feature pipeline |
| Ordering | random order | cheap checks first | orders by prior probability x cost of checking, and says so |
| Coverage | one hypothesis | two or three of: leakage in validation, train/serve feature skew, label definition or delay differences, population shift, sample size of the production estimate | all five, plus "0.97 was never real" stated as the leading hypothesis |
| Concreteness | "look at the data" | names a comparison | names the query: e.g. per-feature distribution train vs serving logs; AUC of validation recomputed with a temporal split; AUC with each feature group removed |
| Uncertainty | treats 0.71 as exact | asks sample size | asks how the labelled production sample was selected (only reviewed transactions? only flagged ones?) and what interval 0.71 has |
| Communication | monologue | structured | interacts: asks the interviewer for facts, states what each answer would rule out |

## Interview rep - worked answer (open only after a second attempt)

Outline of a strong answer. "Two numbers disagree, so first I check they measure the same thing.
(1) How was the production sample chosen and how large is it? If labels exist only for transactions
that were investigated, the sample is selected by the model itself and AUC on it is biased downward;
with a few hundred positives the interval could be wide. (2) My leading hypothesis is that 0.97 was
inflated. For fraud, 0.97 is high. I would recompute validation with a split by time and by account,
since random splits put the same card or merchant on both sides, and look for features computed
after the fact: chargeback flags, account status snapshots, aggregates over a window that includes
the transaction. Check: drop feature groups one at a time; a single group carrying 0.2 of AUC is a
suspect. (3) Train/serve skew: compare each feature's distribution in training data against serving
logs for the same period; look for defaults, units, nulls encoded differently, a join that returns
stale values online. (4) Label definition: validation labels may be mature (90 days of chargebacks),
production labels two weeks old, so many frauds are still labelled clean. (5) Real shift: new fraud
pattern, new merchant category; check by slicing production AUC by segment and time. I would do (1)
and (4) today because they are questions, not analyses; (2) and (3) each need a day. What I would
not do is retrain before knowing which of these it is."
