# Hint 2 (approach)

**Lab.**
* `validate_input`: compute `missing` and `unexpected` as lists first and report both; only if both are
  empty compare the order. Coerce sensors with `pd.to_numeric(errors="coerce")` and treat a value that
  became NaN but was not NaN (or empty) before as a schema error.
* `score_batch`: `validate_input`, `reset_index`, preallocate `score` (NaN), `alarm` (0) and `status`
  arrays of the full length, then loop over `groupby("run_id", sort=False)`. Sort each run by
  `datetime` with `kind="stable"`, write results back through the run's index. That keeps the input order.
* `predict_batch`: hash the raw bytes before parsing; refuse a mismatching existing manifest before
  writing anything; serialise CSV and JSON to bytes first, then `_atomic_write` each.

**Challenge.** Make one synthetic case per suspected bug: an ordinary run, a run with a huge step on
one sensor (to exceed the clip), and the same run scored with a model whose `n_burn` you change
(`dict(model, n_burn=80)`). Fix one bug at a time and watch which cases turn green.
