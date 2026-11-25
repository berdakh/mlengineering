# Hint 1 — concept

**Lab.** Every function in `flowguard.uncertainty` answers the same question: *what would this number
have been with a different, equally plausible set of clusters?* Three consequences:

* The object you resample is the list of clusters. You never need to know what is inside a cluster's
  result; `metric_fn` does.
* For a comparison, a replicate is one alternative test set. Both models are evaluated on *that*
  test set. There is one random draw per replicate, not one per model.
* A proportion with a handful of trials is not approximately normal. The Wilson interval asks "which
  true rates `p` would not have been rejected by a score test given `k` of `n`", which is why it can
  never leave [0, 1].

**Challenge.** Power is a long-run frequency: the fraction of imagined future studies of size `n` in
which your test would say "different". You cannot compute it from the one study you have, but you can
simulate many studies if you are willing to assume a distribution for the per-experiment
differences. The honest input is the distribution of differences you observed; the honest caveat is
that it was estimated from 30 values.

Before writing code, decide by hand: if the true mean difference is 0.02 and the per-experiment
differences have a standard deviation of 0.18, how large is the standard error of the mean with 30
experiments? How many standard errors from zero is 0.02? That ratio tells you what answer to expect.
