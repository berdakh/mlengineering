# What we can and cannot claim - reference

## Numbers

From `python solutions/labs/w3d5_uncertainty/challenge/run_power.py` (2026-11-22; seed 0;
n_sim 2000 for power, 1000 per grid point; grid 10, 20, 30, 50, 100, 200, 400, 800, 1600).
Input: per-cluster point-level PR-AUC, 30 independent clusters, rows `t >= 100`; split = the frozen
v2 manifest from w3d1 (logistic-regression scores are out-of-fold on its 23 development clusters).

| Comparison | Mean per-cluster difference | SD of differences | Clusters available | Simulated power now (30) | Clusters needed for 80% power |
|---|---|---|---|---|---|
| logistic regression vs flow_rate z | +0.0326 | 0.1768 | 30 | 0.134 | 400 (first grid point that suffices; 200 does not) |
| Mahalanobis vs flow_rate z | -0.0838 | 0.2906 | 30 | 0.354 | 200 resampling the observed differences (100 does not); 100 with normal differences of the same mean and sd |

Power with the 7 test clusters alone: 0.079 and 0.082. Cross-check with the normal approximation
`n = (2.80 * sd / mean)^2`: 231 and 94, consistent with the grid (the next grid points are 400 and 100;
the heavy-tailed observed differences need more clusters than the normal approximation for Mahalanobis).
Smallest mean difference detectable with 80% power at the observed spread (sd 0.177): about 0.25
PR-AUC with 7 clusters, 0.20 with 9, 0.10 with 30, 0.09 with 34.

## Claims

On 30 independent SKAB clusters the supervised logistic regression and the flow-rate z-score differ
by +0.033 in mean per-cluster PR-AUC, with a standard error of 0.032. The data do not show a
difference and could only have shown one of about 0.10 or more; they are equally compatible with a
small advantage for either. Resolving a true difference of 0.033 would take several hundred
independent experiments, which is not a sensible use of a testbed. We therefore treat the two as
practically equivalent on point-level PR-AUC and choose between them on other grounds: the z-score
needs no fault labels, has one parameter and is easier to explain; the supervised model would have to
earn its place on event-level delay and false alarms (w3d4) or on unseen fault families (protocol B).
The Mahalanobis scorer is estimated to be 0.084 worse than the flow-rate z-score; with 30 clusters
that is suggestive (power 0.35) and not established.

## Assumptions behind the power figures

1. The true mean difference equals the observed one. Most fragile: the observed +0.033 is about one
   standard error from zero, so the true effect may be zero or negative, in which case no sample size
   yields a "win". The figure answers "if the effect is what we saw", nothing more.
2. Future experiments are drawn from the same distribution as these 30 (same testbed, fault mix and
   labelling), and differences are independent across clusters.
3. The spread of differences (0.177) is itself estimated from 30 values, two of which exceed 0.5
   in absolute value; the required number scales with its square.
4. The test is the two-sided sign-flip permutation test at 0.05 on the mean difference, with the
   analysis fixed in advance. A different metric (event recall, delay) has a different answer.
