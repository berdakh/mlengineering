# Hint 2 — suggested approach

## Lab

1. `wilson_interval`: compute `z` from `level`, then centre and half-width exactly as in section 2.4.
   Validate `0 <= k <= n` first, return `(0.0, 1.0)` for `n == 0`, and pin the bound to exactly 0 or
   1 when `k == 0` or `k == n` (floating point leaves a residue of 1e-17 otherwise).
2. `cluster_bootstrap`:
   * `results = list(per_experiment_results.values())`, `n = len(results)`.
   * One generator: `rng = np.random.default_rng(seed)`.
   * For each replicate: `draw = rng.integers(0, n, size=n)`; pass `[results[i] for i in draw]` to
     `metric_fn`; store the float.
   * Keep the finite replicates, count the others, take the two quantiles.
   * `estimate = metric_fn(results)`.
3. `paired_bootstrap_diff`: build two lists **in the same cluster-id order** (iterate over the ids of
   one mapping and index both). Then the loop is the same as above with
   `metric_fn(a_drawn) - metric_fn(b_drawn)` using the *same* `draw`.
4. `sign_test`: drop zeros, `k = min(#positive, #negative)`, p = `2 * P(X <= k)` for
   `X ~ Binomial(n, 1/2)`, capped at 1. `math.comb` is enough.
5. `paired_permutation_test`: statistic = `|mean(d)|`. For small `n`, the `2^n` sign patterns are
   `itertools.product((1, -1), repeat=n)`; the p-value is the fraction of patterns whose statistic
   is at least the observed one (the identity pattern guarantees it is never 0). For large `n`, draw
   `n_perm` random patterns and use `(1 + count) / (1 + n_perm)`. Compare with a tiny tolerance:
   `0.1 * 10 / 10` and `0.1` are not always bit-identical.

## Challenge

* `power`: a loop over `n_sim` simulated studies. In each: `d = draw(rng, n_experiments)`; run the
  sign-flip test with `n_perm` random patterns drawn from the same `rng`; count `p <= alpha`.
  Return the fraction. A `(n_perm, n)` sign matrix times `d` gives all permuted sums in one product.
* `required_experiments`: evaluate candidates in ascending order and return the first that reaches
  the target; `None` if the loop ends.
* For `CLAIMS.md`: compute `d = logreg - flow_z` from the CSV, report mean, sd and count, then call
  your functions with `empirical_draw(d)`. Check the simulated answer against
  `n ≈ (2.80 · sd / mean)²`.
* Sanity checks worth running yourself before the automated ones: power at zero difference should
  be about `alpha`; power should rise with `n`.
