# Hint 1 - concept (w3d3)

* Selection is fitting. Whatever data chose the hyperparameters, the threshold or the winning trial
  has been *used*, and the score on that data is biased upward for the thing chosen.
* The number to report is the performance of the **procedure** (search + select + refit), estimated on
  data the procedure never saw. Nested validation does exactly that: the outer loop wraps the whole
  procedure, the inner loop is the procedure.
* "Never saw" has two levels here: rows of the outer fold must not be fitted by any inner model, and
  they must not be *scored* by any inner model either (scoring is how they would vote for a candidate).
* Rows outside the folds (test experiments, the reference recording) are never touched by any of this.
* A threshold is a parameter with one dimension. Choose it on development scores that are themselves
  out-of-fold, freeze it, apply it once to test.
* Challenge: the chosen trial's dev mean is the maximum (or near-maximum) of 60 noisy numbers. Ask what
  you would get if you re-ran your *whole rule* without one fold and scored its choice on that fold.
