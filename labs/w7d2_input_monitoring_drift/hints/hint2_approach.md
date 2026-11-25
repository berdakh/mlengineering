# Hint 2: approach

**Statistics.** `grid = np.sort(np.concatenate([ref, cur]))`;
`F_ref = np.searchsorted(np.sort(ref), grid, side="right") / ref.size`, same for `cur`.
KS: `max(abs(F_ref - F_cur))`. W1: `sum(abs(F_ref - F_cur)[:-1] * diff(grid))` (the CDFs are constant
between consecutive grid points). PSI: edges from `bin_edges(ref, bins)`, bin indices with
`searchsorted(edges, x, side="right")`, shares with `bincount(..., minlength=len(edges) + 1)`.

**Window report.** Violations: a boolean Series OR-ed over sensors: `isinf | (notna & outside limits)`.
Missing share over the clean rows. Statistics on clean, finite values when there are at least 2.

**Calibration.** Collect the statistic per sensor over all stable windows, then
`np.quantile(values, 1 - target_far / m, method="higher")`.

**Challenge.** A scale-free daily statistic (W1 divided by the reference standard deviation, or KS).
Threshold: leave-one-day-out inside the reference (each reference day against the others), maximum
times a margin. Calendar: for a settling period after a planned day, label alerts on that feature
`expected`; then replace that feature's reference with the post-change days and recalibrate its threshold.
