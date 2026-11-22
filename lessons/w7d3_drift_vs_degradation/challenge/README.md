# Independent challenge: a monitoring and label-backfill plan for `flowguard`

**Time:** 30-40 minutes of the essential path; finish in the optional extension if needed.
**Assistance:** none beyond this lesson, the handbook (H15.4) and your own lab results. The hints in
`../hints/` are for the guided lab; this challenge has none on purpose.

## Task

Write the plan the reliability team would actually run for the shipped detector. Two files:

1. `monitoring_plan.toml`: the machine-readable plan. A starter with every required key is provided;
   replace each `TODO` and every placeholder number with a value you can defend.
2. `MONITORING_PLAN.md`: one page of prose that justifies the numbers. Keep the three headings in the
   template.

The plan must separate three questions and give each its own signal, window and action:
*is the input valid?* (contract checks at the boundary), *has the input changed?* (drift), and
*is the model still good?* (delayed labels).

## Acceptance criteria (checked by `python wb.py check w7d3 --challenge`)

* The TOML parses and has the tables `context`, `input_drift`, `actions` and at least one entry in each
  of the arrays `input_validity`, `performance` and `label_sources`.
* Drift thresholds are calibrated on reference data (`threshold_method = "calibrated"`, with a
  `calibration_quantile` between 0.9 and 1, exclusive), never a fixed folklore number.
* Every performance metric names a label source that exists, has `min_labels >= 1`, reports
  `when_insufficient = "report_unknown"`, and has a window long enough to collect `min_labels` labels at
  the rate stated in `[context]`.
* Every performance metric is evaluated only after its labels can have arrived:
  `evaluate_after_days` is at least the upper end of its source's `expected_delay_days`.
* If `event_recall` is monitored, some label source covers missed faults (`covers = "missed_faults"`);
  otherwise recall is not measurable and must not be in the plan.
* Every label source has a `join_key` that exists in the prediction logs (`alarm_id`, `fault_id` or
  `prediction_id`) and a delay range with `0 <= low <= high`.
* Actions: drift alone never triggers retraining or rollback, and measured degradation never maps to
  `no_action`.
* `MONITORING_PLAN.md` keeps the headings "Three questions", "Label backfill" and "What this plan cannot
  detect", each followed by real text.

Passing the checks shows the plan is internally consistent. Whether the numbers are good is judged
with the rubric in `solutions/lessons/w7d3_drift_vs_degradation/challenge/RUBRIC.md` (open it after
you have written your plan).
