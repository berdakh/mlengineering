# f5 - Leakage and validation (parallel form of b2)

**Time box: 35 minutes.** Sitting B, section 2 of 4. No hints.

## Situation

A colleague evaluated a lapse model on the full feature export
`labs/w8d6_final_assessment/data/lapse_export_full.csv` (**synthetic**; columns documented in
[`../data/README.md`](../data/README.md)) and is delighted:

```bash
python labs/w8d6_final_assessment/f5_leakage/lab/leaky_eval.py
```

The model is meant to be used like this: on the 1st of each coming month, score every active account
with what is known on that day, and hand the ranking to the account managers.

## Task

1. Read `lab/leaky_eval.py`. Find everything that makes its score untrustworthy *for that use*.
   There is more than one problem and they are of different kinds.
2. Write a corrected evaluation in `lab/fixed_eval.py`:
   * `FEATURES` - the export columns the model may use.
   * `make_split(df)` - positional `(train_idx, test_idx)`; train keeps at least half of the rows,
     test at least 10%.
   * `build_model()` - a fresh, unfitted scikit-learn estimator that can be fitted directly on the
     raw `df[FEATURES]` frame (missing values and text categories included).
   * `evaluate(df)` - returns `ap`, `roc_auc`, `n_train`, `n_test`, `test_prevalence`.
3. Fill in `lab/FINDINGS.md`: each problem, why it is leakage (which information crosses which
   boundary), its expected effect on the score, and how you confirmed it. Where you could not
   measure an effect, say so - do not assert one.

## Check your work

```bash
python labs/w8d6_final_assessment/f5_leakage/lab/fixed_eval.py
python wb.py check labs/w8d6_final_assessment/f5_leakage       # or:
python -m pytest labs/w8d6_final_assessment/f5_leakage/checks -q
```

The starter fails all checks. The checks re-run the evaluation from your `FEATURES`, `make_split`
and `build_model`; they accept any model family and any cut-off that satisfies the contract.

## Acceptance criteria

* All checks pass.
* `FINDINGS.md` identifies each problem with a mechanism, not just a label ("leakage"), and
  separates what you measured from what you expect.
* You state what the corrected number still does not establish.

## Submit

`lab/fixed_eval.py`, `lab/FINDINGS.md`, time used.
