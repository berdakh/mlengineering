# Skew report: logistic candidate, serving path vs training path (reference solution)

Method: `test_parity.py` scores SYNTHETIC runs with both paths and compares them at 1e-12. Before the
fixes, every case failed. Each bug was then isolated by fixing the others first.

## 1. Burn-in length hard-coded in the serving script

* **Symptom.** The serving path returned 40 more scores per run than the training path, and every
  score differed: the calibration used 60 rows instead of the model's 100.
* **Cause.** `BURN_IN = 60` was a module constant, a "sensible default" from an older experiment; the
  model's `n_burn` was ignored.
* **Fix.** Read `n_burn` from the model file. A parameter that changes the arithmetic belongs to the
  model, never to the code that serves it.
* **Test.** `test_burn_in_length_comes_from_the_model` uses `n_burn=80`, so a constant of 100 also fails.

## 2. Clip missing

* **Symptom.** Identical scores on ordinary runs; large differences only when a sensor is far outside
  its start-up range, i.e. during exactly the faults that matter.
* **Cause.** The training path clips z to ±20 before the logistic model; the serving copy did not.
* **Fix.** Clip with `model["z_clip"]`.
* **Test.** `test_matches_when_values_hit_the_clip` plants a shift of 500 units.

## 3. Feature order swapped

* **Symptom.** Every score differed, including on runs with no fault.
* **Cause.** The serving path built `[|z|, z]`; the coefficients were learned for `[z, |z|]`. Nothing
  fails at runtime: the matrix has the right shape.
* **Fix.** Build features in the trained order. Better: store the feature names with the model
  (`model["features"]`) and assert them at load time.
* **Test.** Any ordinary-run parity case.

## What would have prevented all three

One feature function imported by both training and serving, and a parity test in CI on every change.
