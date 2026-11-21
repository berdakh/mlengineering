# Mutant: end_to_end_metric_only

**The mistake.** The whole suite is one end-to-end run with a metric threshold
(`auc > 0.95`). This treats a statistical performance check as if it were a unit
test. A separable problem stays separable when RMS lacks its square root, when the
band edges are wrong, or when a unit leaks across the split, so the metric does
not move and the defects survive.

**Why it is plausible.** In research code "the number looks right" is the usual
acceptance test, and an AUC threshold feels like the most relevant thing to assert.

**Expected outcome.** Passes on the correct package; most bugs survive
(only gross wiring errors such as the wrong probability column are caught).
