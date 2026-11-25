# Hint 1 — concepts (w4d3)

**Lab.** Every task is one rule about what the model may know:

* a window for row `t` may contain rows `<= t` only (task 1);
* the weights you return must be the ones the validation data preferred, not the last ones (task 2);
* the model may learn only from rows that are past the burn-in and labelled normal, and the
  normalisation statistics may come only from training rows (task 3);
* scoring changes nothing that `fit` learned, and an experiment's scores depend only on that
  experiment (task 4).

When a check fails, ask which of these four rules was broken.

**Challenge.** Two different uncertainties are in play. Seeds tell you how much retraining moves a
method on a *fixed* test set; a test-set interval tells you how much the number would move on *other*
experiments. A deterministic detector has no seed spread but is still evaluated on a sample. A verdict
has to clear both.
