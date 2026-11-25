# Hint 2 - approach

**Lab**

* Write one private helper that validates lengths, builds a frame with `experiment_id, family, t,
  label, flag`, and drops rows with `t < burn_in`. All three public functions start from it.
* Write one helper that turns a boolean array into inclusive `(start, end)` runs. Pad with `False` on
  both sides and look at where consecutive values differ.
* `per_experiment_table`: inside each experiment sort by `t`, then count. Detection delay uses only
  flagged rows whose label is 1; a flag before onset is a false alarm, not an early detection.
* `slice_metrics`: for each level take the metric column, split it into defined and undefined, and
  report both counts. Bootstrap only if at least `MIN_EXPERIMENTS_FOR_INTERVAL` are defined:
  draw indices of experiments with replacement, `n_boot` times, and take the 2.5 % and 97.5 % quantiles
  of the resampled means. Levels passed in `levels` but absent from the data still get a row.
* `error_segments`: first find the events (runs of label 1). For each event, find the first flagged
  position. No flag: one `miss` segment spanning the event. Otherwise the missed runs inside the event
  are `late`/`boundary` (if the run starts at the event's first row) or `fragment` (if not). Then
  handle the false-alarm runs: does the run touch an event edge and is it short? Is it before the
  first event, after the last, or is there no event?
* Check yourself with the invariant: the segments' `n_rows` sum to the number of wrong rows.

**Challenge**

* Leak audit: sort the columns into "printed on the invoice", "customer attribute", "history as of the
  issue date", "computed later". Two columns come from a master table that is overwritten in place.
  A quick test for such a column: is it constant within a customer over two years?
* Split: test is everything issued from the cut-off. Train is not "everything before": compute the date
  on which each label is decided and compare it with the cut-off.
* Metric: add a week number to the test frame, sort by score, take the first `k` per week.
* Sanity bound: an AUC in the high 0.8s or above on this table means a leak. Find it before going on.
* Interval: decide what the independent unit is among the *called* invoices.
