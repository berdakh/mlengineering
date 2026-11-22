# Model answers: w7d4 model updates and rollback

## 1. Triggers and when they mislead

* **Scheduled** (e.g. quarterly): fires when nothing changed; a retrain on fresh data may only add
  variance. Gate it like any other candidate.
* **Measured degradation** (labelled metric below baseline, w7d3): may be a pipeline bug or a label change,
  not a model that needs new data; retraining on corrupted inputs bakes the bug in.
* **Drift**: the w7d3 recalibrated sensor moved PSI 9-13x past its threshold while the detector caught the
  same faults; retraining would have fitted the model to a calibration offset for nothing.
* **New data or features available**: fires on opportunity, not need; the new feature may not be
  available at serving time (2.0.0's accelerometers).

## 2. A lower end of exactly zero

1.1.0 catches valve1/8 in addition to everything 1.0.0 catches and misses nothing that 1.0.0 catches.
Per experiment the difference is +1 on one experiment and 0 on six. A paired resample can omit valve1/8
(difference 0) but can never produce a negative difference, so the 2.5th percentile is 0.000.
Superiority needs $L > 0$: reject. Non-inferiority with margin 0.05 needs $L > -0.05$: promote.
The data cannot show a one-fault improvement on 7 experiments; the choice is a policy decision, and
non-inferiority is justified only because the stakeholder explicitly accepted the higher alert budget.

*Common wrong answer:* "the bootstrap is broken because 0 is suspicious". It is the correct consequence
of a one-sided pattern of differences.

## 3. 2.0.0 dev versus test

(a) **Overfitting the operating point**: the threshold and post-processing were chosen on 27 development
experiments, with `merge_gap = 0` selected; with three sensors the grid has more ways to fit noise.
(b) **Shift between development and test experiments**: the accelerometers behave differently in the
test recordings (sensor-specific variation across runs), so the max over sensors fires late or not at all.
Distinguish them with grouped cross-validation inside development data (w3d2): if 2.0.0 also collapses
on held-out development folds, it is (a); if it holds on development folds but not on test, look at the
accelerometer distributions of the test runs (b).

## 4. Shadow coverage

The shadow traffic was 20 valve recordings, and 16 of them are development data 1.1.0 was tuned on. All
5 of 1.1.0's development false alarms happened in the `other` family, which the shadow never saw. And the
shadow labels were added afterwards from the dataset; in production, shadow outputs have no labels for
weeks. Shadow shows that the candidate runs and where it disagrees; the budget is checked on the traffic
that contains the risky slices, with the canary's alert-rate bound.

## 5. Canary and rare events

About 0.2 faults per week reach the canary machines (10 % of 2): almost surely zero or one. The canary
says nothing about recall. Its stopping rule watches what happens often: serving errors, latency
percentiles, alert rate per machine-hour (against the budget, with exact Poisson bounds), input
validation failures. Recall was decided by the offline gate and will be confirmed later by delayed labels.

## 6. Order and atomicity

* **Audit after the move**: if the pointer move fails (disk full, permissions) and the audit was written
  first, the log claims a promotion that never happened; the next rollback then "restores" a version
  based on a false history.
* **Atomic move**: writing the pointer in place truncates it first; a crash between truncation and write
  leaves an empty or partial pointer, and the service cannot start or loads a nonexistent version.
  `os.replace` of a fully written temporary file means readers see either the old pointer or the new one.

## 7. Rollback as a stack (design choice)

Sequence: promote 1.0.0, promote 1.1.0, rollback, rollback. With "go to the `from` of the last entry",
the first rollback goes 1.1.0 → 1.0.0 (correct) and writes `from 1.1.0, to 1.0.0`; the second rollback
then reads `from 1.1.0` and **re-deploys 1.1.0**, the version that was just removed, perhaps at night by
an on-call engineer who expected to go further back. With the stack, the second rollback finds that the
only remaining promotion has `from None` and refuses, which is the honest answer: there is nothing older
to return to. The stack also makes the meaning of "rollback" independent of how many rollbacks happened.

## Interview rep: fraud model rollout (worked outline)

1. **Contract and artifact.** Bundle model + threshold + feature schema + preprocessing as one immutable
   version; check the serving contract (features available within 50 ms) before anything else.
2. **Offline gate.** Paired comparison on the same held-out, time-ordered transactions (later than
   training), predeclared policy; guardrails: false-positive rate at the operating point (customer
   friction), p99 latency measured on the serving path; slices: merchant category, card-not-present,
   new customers.
3. **Shadow** for one to two weeks on full traffic: disagreement analysis, latency and error budget of the
   candidate, feature-availability errors. Outputs unlabelled; chargebacks arrive in 30-90 days.
4. **Canary** at 1-5 % with automatic stop on latency, errors, alert/decline rate bounds, with the
   repeated-looks problem handled (alpha spending or a minimum exposure).
5. **Promote** by pointer move with audit; keep the previous version warm.
6. **Rollback**: one command or an automatic guardrail breach, audited, compatible with today's schema;
   practised before it is needed.
7. **After**: delayed-label evaluation of the new model against the old one's history; a review date.

Score with the rubric in `assessment.md`; a 3 mentions label delay, what the canary cannot measure, and
versioning the threshold and features with the model.
