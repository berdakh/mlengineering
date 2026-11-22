# Hint 2 - approach (w3d3)

**`param_grid`** - `itertools.product` over the values, in key order; one dict per combination.
**`sample_params`** - one `np.random.default_rng(seed)`; for each candidate, for each key in a fixed
order, draw according to the spec. Log-uniform: `exp(uniform(log low, log high))`.

**`grouped_search`** - for candidate i and fold k: training groups = union of the *other folds*
(not "everything except fold k": the table also holds test rows); build masks with
`tidy[group_column].isin(...)`; fit a **fresh** estimator from the factory; score fold k with the metric.
Record `fold_scores`, their mean and SE = sd(ddof=1)/sqrt(n_folds).

**`select_best`** - "max": argmax of means, earliest on ties. "one_se": band = best mean minus the
best trial's SE; among trials in the band, minimise `complexity(params)`, then maximise the mean.

**`nested_estimate`** - for each outer fold k: `inner = [f for j, f in enumerate(folds) if j != k]`;
`trials = grouped_search(..., inner, ...)`; `chosen = select_best(trials, rule, complexity)`; refit
`chosen["params"]` on all rows of the inner folds; score fold k. Report the mean and SE of the outer
scores, and keep the chosen params and inner best score per fold (they are the interesting part).

**Thresholds** - candidate thresholds are the observed dev scores. For best F1, evaluate each (vectorise
by sorting); for the alert budget, compute the fraction of normal rows flagged at each candidate and
take the lowest that satisfies the budget.

**Challenge `choose`** - write a private `_pick(scores, n_params)` that applies your rule to a matrix of
fold scores. The estimate: for each fold k, `_pick` on the matrix without column k, read that trial's
score in column k; average.
