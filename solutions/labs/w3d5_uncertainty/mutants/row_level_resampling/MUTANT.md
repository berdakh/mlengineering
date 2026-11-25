# Mutant: row-level resampling

When the per-cluster results are arrays of rows, all rows are pooled and resampled individually, as
`sklearn.utils.resample` or `scipy.stats.bootstrap` on a flat array would do. This is the single most
common mistake with grouped data: it treats 1,200 dependent rows as 1,200 independent observations.

Why it is tempting: the code is shorter, the interval is pleasingly narrow, and the point estimate is
unchanged, so nothing looks wrong.

Rejected by: `test_coverage_is_near_nominal_under_within_cluster_dependence` (coverage about 0.3
where 0.95 is claimed; median width about 0.16 against 0.70).
