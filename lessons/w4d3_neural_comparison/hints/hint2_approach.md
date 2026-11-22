# Hint 2 — approach (w4d3)

**Task 1.** Pad first, then index: `padded = concat([x[0] repeated window-1 times, x])`; the window of
row `i` is `padded[i : i + window]`. Build all start offsets at once with
`np.arange(n)[:, None] + np.arange(window)[None, :]` and index `padded` with that matrix.

**Task 2.** Keep three variables across epochs: `best_loss`, `best_state` (a deep copy), `since_best`.
After each epoch compute the validation loss; if it improved, store a copy and reset the counter;
otherwise increment and stop at `patience`. After the loop, `model.load_state_dict(best_state)`.

**Task 3.** `_usable_rows` is one boolean expression over the `t` and `anomaly` columns. In `fit`, compute
features for the training frame, fit the normaliser on `features[usable]`, then let `_training_windows`
build windows for both frames with that normaliser. Seed, then build the model, then train.

**Task 4.** Loop over `tidy.groupby("experiment_id", sort=False)`, sort each group by `t`, keep its
positional index (`group.index` after `reset_index(drop=True)`), and write the per-window errors back
into a preallocated array at those positions.

**Challenge.** `statistics.stdev` or `np.std(ddof=1)`; check `len(values) < 2` and `np.isfinite` before
computing. The verdict needs the larger of the two margins, not their sum and not just one.
