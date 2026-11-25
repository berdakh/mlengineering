# W5D1 independent challenge: find the skew

**Setting.** The team wants to run the *second* candidate from w4d5, the supervised logistic model,
as a shadow scorer next to the shipped detector. A colleague who could not import the training code
wrote the serving path from the notebook: [`serve_scores.py`](serve_scores.py). It runs, its scores
have a plausible size, and its alarms look reasonable on a dashboard. It contains **three**
training/serving-skew bugs.

**Given (do not edit):**

* [`train_features.py`](train_features.py): the training path, the exact arithmetic the model was
  evaluated with in w4d5;
* [`model/logistic.json`](model/logistic.json): the trained model as plain data (16 coefficients,
  intercept, burn-in length, clip, sensor and feature order), written by
  [`make_model.py`](make_model.py) from the REAL development experiments;
* [`skew_on_real_data.py`](skew_on_real_data.py): scores the 7 real test experiments with both paths
  and prints the event metrics of each (needs `python project/get_skab.py` once).

**Your task.**

1. Write `test_parity.py` next to `serve_scores.py`: pytest tests that compare `score_run` with
   `training_scores` on SYNTHETIC runs you construct, at a tolerance you can justify.
2. Run it against the original `serve_scores.py` and use its failures to locate the bugs.
3. Fix them in `serve_scores.py`. Do not import `train_features` from it: the point is a serving path
   that is correct on its own and a test that proves it.
4. Fill in [`SKEW_REPORT.md`](SKEW_REPORT.md): for each bug, the symptom, the cause, the fix and the
   test case that catches it. Then what would have prevented all three.
5. Run `skew_on_real_data.py` before and after, and add one sentence on what the bugs did to the real
   test metrics.

**Acceptance criteria** (`python wb.py check w5d1 --challenge`):

* `score_run` equals the training path within 1e-12 on ordinary runs, on runs far outside the
  start-up range, and for models with burn-in lengths other than 100;
* your `test_parity.py` passes on your fixed serving path, and **fails** on the original and on each
  of the three bugs reintroduced on its own, including a version that hard-codes the burn-in at the
  value today's model happens to use;
* `SKEW_REPORT.md` has a `##` section per bug, no `TODO`, at least 150 words.

**Time.** 45-60 minutes; start in the session, finish in the extension or on the review day.
No solution is provided until you have attempted it.
