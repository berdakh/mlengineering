# f5_leakage - reviewer notes (parallel form of b2)

## Problems in `leaky_eval.py` and their measured effect (SYNTHETIC; executed 2026-11-22)

Same model (logistic regression, preprocessing in a pipeline) throughout; AP on the stated test rows.

| Problem | Mechanism | Measured |
|---|---|---|
| `winback_call_logged` as a feature | written by the CRM *after* an account lapses or announces it; the label leaks through the outcome's paperwork | honest temporal 0.225 -> 0.648 with this column added |
| `last_pickup_offset_days` as a feature | days from the snapshot to the account's **last ever** pickup: computed from future shipments; small values mean "stops shipping soon" | 0.225 -> 0.690 with this column added |
| Random row split | test months precede training months; the deployment question is "next month" | 0.231 random vs 0.225 temporal: **no measurable effect on this data** |
| Imputation/scaling fitted on all rows | test rows' statistics enter training | not measured separately; with ~4,000 rows and 8 numeric columns the effect is expected to be negligible here |

Leaky script: AP 0.918, ROC AUC 0.986. Honest temporal evaluation: AP 0.225, ROC AUC 0.654, test
prevalence 0.129. Almost the whole gap comes from the two columns. A strong FINDINGS.md says that the
split and preprocessing problems are wrong *in principle* and were measured (or not) to have no
visible effect here - it does not invent an effect.

## What the corrected number still does not establish

One temporal split (four test months, 137 positives): no interval; synthetic data; no check that
September's fee increase for starter accounts did not change the relationship; nothing about
whether calls actually prevent lapse (the label is observational).

## Common incorrect answers and why they fail

* Dropping only `winback_call_logged` (mutant `kept_subtle_leak`).
* Account-grouped split without time (mutant `group_split_only`): the right instinct from
  cross-subject work, the wrong deployment question.
* Moving preprocessing "before the split" and calling it fixed (mutant `preprocessing_outside_model`).
* Claiming the random split "inflates AUC by X" without measuring it.

## Rubric (assign per aspect)

| Aspect | Demonstrated independently | Partial | Not yet demonstrated |
|---|---|---|---|
| Target leakage | both columns found, each with its mechanism | the obvious one only | neither |
| Validation design | forward-in-time split, with the label-window argument | temporal split without the argument, or grouped only | random |
| Preprocessing leakage | inside the estimator, explained | moved but not explained | outside |
| Scientific honesty | measured vs expected kept apart; nil effects reported as nil | effects asserted without measurement | none |
