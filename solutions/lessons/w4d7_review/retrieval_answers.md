# w4d7 - retrieval answers

Open only after all twelve questions have a written attempt. Each answer states what a "solid"
answer must contain, then common wrong answers and why they fail.

Aligned with the final Week 4 lessons on 2026-11-22. Every real-data number is copied from those
lessons' authoring runs on the frozen manifest v2 (7 test, 27 development experiments; test
prevalence 0.373). Numbers marked *(SYNTHETIC)* come from the lessons' synthetic illustrations.

## 1. Stationarity, departures, effective sample size

**Weakly stationary:** mean, variance and autocovariances do not depend on time. Forecasters and
control limits fitted on one stretch are valid on another only if that holds.

Departures and usual remedies (w4d1, 2.2), three of:

| Departure | Remedy |
|---|---|
| Trend (temperatures warming through a run) | difference, detrend, or a trend term |
| Level shift | often *is* the anomaly; otherwise re-baseline after a known change |
| Seasonality / machine cycle | seasonal differencing or seasonal terms |
| Variance change | model the scale (rolling sigma), transform |
| Regime / operating point | condition on the regime, or fit per regime |

The tension: the fault is a non-stationarity. A model that adapts quickly (naive forecast, short
rolling baseline) absorbs the fault into "normal" within a few samples; one that never adapts alarms
forever after a benign change. Adaptation speed is a design decision with a false-alarm cost on one
side and a missed-state cost on the other.

Effective sample size for the mean of AR(1): `n_eff = n(1 − φ)/(1 + φ)`; with `φ = 0.9`, 300 rows
are worth about **16** independent observations (w4d1, 2.1). Consequence: rows are not the unit, so
row bootstraps and shuffled folds are over-confident (w3d2, w3d5).

| Common wrong answer | Why it fails |
|---|---|
| "Stationary means constant" | A noisy, autocorrelated series can be stationary |
| "Standardise the whole recording and it becomes stationary" | Changes units, not the time-dependence; and uses the future |
| "300 rows, so the standard error is σ/√300" | Ignores autocorrelation; about four times too small here |

## 2. Naive versus AR residual; why the numbers

* **Naive** (`x̂_t = x_{t−1}`): the residual is the first difference. After a level shift `Δ` it is
  `Δ` at the step and back to noise one sample later. It detects *changes*, not *states*.
* **AR(p) with intercept**: the forecast pulls towards the fitted mean `μ = c/(1 − Σφ)`, so after the
  shift the residual keeps an offset of about `(1 − Σφ)Δ` for as long as the shift lasts. The more
  persistent the fitted process (`Σφ → 1`), the more it behaves like the naive forecaster.

On the 7 test experiments: the naive residual's PR-AUC **0.401** is at the no-skill floor **0.373**
(the test prevalence) and it detected 1 of 7 events: almost every row inside a fault looks normal to it,
because the fault is a sustained state. AR(2) scored **0.809** (6/7 events): it keeps part of the offset
for the whole fault. Forgetting the intercept is the classic error: the coefficients then absorb the
mean and drift towards a unit root, which turns AR back into a naive forecaster.

A lower forecast error can be a worse detector because one-step error is minimised by adapting fast,
and a forecaster that adapts fast forecasts the fault too. In figure 2 of w4d1 the AR model forecasts
the shifted series *worse* than naive, which is exactly why its residual detects the shift.
Forecasters here are judged by detection metrics on held-out experiments, never by RMSE.

| Common wrong answer | Why it fails |
|---|---|
| "Choose the forecaster with the lowest RMSE" | Optimises the wrong quantity |
| "The naive residual failed because of noise" | It failed by design: it cannot see a state |
| "AR(2) needs no intercept; I standardised first" | The fit data's mean is not the scored data's mean; the intercept carries the level |

## 3. CUSUM

```
S⁺_t = max(0, S⁺_{t−1} + z_t − k)      S⁻_t = max(0, S⁻_{t−1} − z_t − k)      alarm if max(S⁺, S⁻) > h
```

`z_t` are standardised residuals (divided by the one-step residual SD on the fit data, not the series
SD). `k` is the reference value (half the shift to detect fastest); `h` the decision interval. The floor
at zero forgets evidence *against* a shift. Delay after a shift of `δ` SDs ≈ `h / (δ − k)` samples,
good above `δ ≈ 1`; it breaks down at `δ = k` (simulated median 27 samples there) *(SYNTHETIC)*.

`ARL₀ ≈ 460` samples (simulated, `k = 0.5, h = 5`, independent standard-normal input; median 330)
means one false alarm every six to eight minutes at 1 Hz, and only if residuals are independent and
correctly standardised; autocorrelated residuals make it much worse. Chart parameters are meaningful
only next to an alarm budget.

On SKAB the detector (AR(2) residual) is unchanged; CUSUM changes the **operating point**: 3.3 false
alarms per hour instead of about 223, at the cost of 4/7 events instead of 6/7 and a median delay of
111 s instead of 2 s. Its point-level PR-AUC is lower (0.605), because point metrics reward flagging
early rows that the accumulation delays. Which is better is decided by the alert budget, not by PR-AUC.

| Common wrong answer | Why it fails |
|---|---|
| "CUSUM is a better detector than AR(2)" | Same residual; different trade-off between delay and false alarms |
| "ARL₀ 460 means it is safe" | At 1 Hz that is several false alarms per hour, and only under i.i.d. assumptions |
| "CUSUM detects any shift" | Shifts well below `k` accumulate very slowly |

## 4. PCA T² and Q

With standardised `x`, loadings `P` (`d × k`), component variances `λ_j`, scores `t = xP`:

* **T² = Σ_j t_j²/λ_j**: distance *inside* the retained subspace. Large when the row is extreme along
  directions normal data varies in (everything moving together, but too far).
* **Q = ‖x − xPPᵀ‖²**: squared distance *from* the subspace. Large when the usual relationships between
  sensors break. *(SYNTHETIC figure 1 of w4d2: point A has T² 7.0 above its limit 6.7 and Q 0.00; point
  B has T² 0.0 and Q 2.07 against a limit of 0.22.)*

Limits in the lab: **empirical 99th percentiles on the fit rows** (the F and χ² approximations assume
multivariate normality, which sensor data does not satisfy). `k`: start from the share of variance on
normal data, then choose by detection metrics on development folds (the lab chose variance share 0.8).
Too few components push normal variation into Q; too many absorb faults into the subspace.

On SKAB, **Q was the weakest detector on both protocols** (protocol A 0.626, protocol B 0.699). The
faults mostly move the operating point, inside the subspace where T² looks, rather than break sensor
relationships. That is a property of these faults, not of Q.

| Common wrong answer | Why it fails |
|---|---|
| "T² and Q carry the same information" | They measure orthogonal parts of the deviation |
| "Use reconstruction error only" | Misses large in-pattern excursions |
| "Keep 99 % of the variance" | Can retain the directions faults appear in; choose `k` by detection on development data |

## 5. Isolation forest

Random feature, random split between the node's min and max, recursively, on subsamples of `ψ` rows;
anomalies are isolated in few splits. Score `s(x) = 2^(−E[h(x)]/c(ψ))`; scikit-learn's `score_samples`
returns `−s`, so the lab negates it to make higher mean more anomalous.

`contamination` does **not** change the trees or the scores; it sets the cut-off used by `predict` so
that that share of the *training* rows is flagged. The worked example shows identical scores for
contamination 0.01, 0.05 and 0.2 while the share flagged moved from 9 % to 32 %. Setting it from the
test prevalence or the best test F1 is choosing a threshold with test labels; the lab uses the scores
and a threshold chosen on development data.

Weakness: axis-aligned splits isolate anomalies visible only as broken correlations (oblique
directions) slowly, unless a feature exposes them (residuals, ratios). Anomalies present in the
training sample look normal.

| Common wrong answer | Why it fails |
|---|---|
| "It measures distance to neighbours" | No distances are computed |
| "`contamination` sets sensitivity" | It moves a threshold on fixed scores |
| "It needs no labels" | It needs labels to evaluate and usually to choose normal training rows |

## 6. Protocol A versus protocol B; which framing

* **Protocol A** (frozen test set, all families on both sides): performance on *new experiments of
  fault mechanisms seen in training*.
* **Protocol B** (train on `valve1` + `valve2`, score the 12 `other` experiments, 8 independent
  clusters): performance on *a fault family never seen in training*.

Reading: GBT 0.920 → 0.636 and the flow-rate z-score 0.886 → 0.640 fall; isolation forest 0.831 →
0.783 and PCA T² 0.762 → 0.761 hold. The GBT learned what separates *valve* faults. On protocol A its
interval overlaps the flow-rate z and isolation forest, so even its win there is not established; on
B, eight clusters make the intervals wide, so the drop is a warning, not a measured size.

Labels support a **supervised model for the valve families** (many labelled experiments each), not for
mechanisms outside them. Defensible design: a supervised model plus a semi-supervised safety net,
with protocol B reported next to protocol A. Maintenance differs too: the GBT needs labelled faults of
every kind to stay good; semi-supervised detectors need a clean normal reference.

| Common wrong answer | Why it fails |
|---|---|
| "Ship the GBT, it has the best test score" | Protocol B reverses the ranking for unseen faults; and the A ranking is not established |
| "Protocol B proves the GBT is bad" | Eight clusters; wide intervals; it shows a risk, not a size |
| "Semi-supervised detectors need no labels" | Evaluation and the selection of normal rows use labels |

## 7. A fair neural comparison

Held equal (w4d3, 2.4): same FIT/VAL/TEST experiments with TEST read once; rows `t ≥ 100` scored for
everyone; the same per-experiment burn-in calibration; four configurations per family chosen on VAL
PR-AUC; early stopping on VAL loss only; the same metric and cluster-bootstrap interval; five seeds for
the neural model. **Not** equal, and to be said: the training loop's own settings (learning rate, batch,
optimiser, hidden size) were fixed, not tuned; a reviewer could argue it deserved more budget. The answer
is to report the budget, not to tune until it wins.

Conclusion: the classical Mahalanobis score (0.768) lies inside the neural seed range (0.682-0.837), and
the paired difference for the median-by-VAL seed, −0.057 [−0.194, +0.104], contains zero: **no evidence
that either is better under this protocol**. The flow-rate z-score (0.884) is ahead of the median neural
seed by 0.173 [0.035, 0.327], with the multiple-comparisons caveat of w3d5. Report all five seeds (or mean,
sd, range), the test interval for one fitted model, and the cost (3,658 parameters, PyTorch dependency,
about 6.5 versus 1.7 ms per 1,000 rows on the authoring host). The claim is narrow: one architecture, one
budget, 21 training experiments.

Seed 3 had the lowest VAL reconstruction loss (0.550) and the lowest TEST PR-AUC (0.682): reconstruction
loss is a training signal, not the detection metric. Select on the detection metric on VAL.

| Common wrong answer | Why it fails |
|---|---|
| "Best seed 0.837 > 0.768: neural wins" | Best of five chosen on test |
| "Mean 0.754 < 0.768: classical wins" | A 0.014 gap against a seed sd of 0.068 and 7 test experiments |
| "Fix the seed and one run is enough" | Reproducible is not representative; on CPU even thread count changed the result |

## 8. What a run records; identity; status; reproduce

Record (w4d4, 2.1): resolved configuration including seed; code version (commit with `-dirty`);
data fingerprint (SHA-256); environment (Python, libraries, platform, threads/device for numerically
sensitive work); metrics; completion status; artifacts.

**Run id** = first 12 hex of SHA-256 of the **canonical** JSON of the config (sorted keys). Without
canonical serialisation the same config built in a different key order hashes differently (the worked
example shows two hashes for one config). The seed is part of the identity.

**`status.json` last, atomically** (temporary file, then `os.replace`): a reader never mistakes a
half-finished run for a finished one; "metrics.json exists" is not a completion signal. Partial and
failed runs are cleared and retried; complete ones are immutable and skipped.

**Index derived from directories:** it is a cache. Deleting a bad run, copying runs from another
machine, or repairing a partial one is reflected automatically; a hand-maintained index drifts.

**Reproduce** must re-run the stored config and compare every metric within a tolerance stated in
advance. Comparing stored metrics with themselves, or with a cached copy, proves nothing. The lab's
isolation-forest run `0668c9c60359` reproduced with `max_abs_diff` 0.0.

| Common wrong answer | Why it fails |
|---|---|
| "Seed and commit hash are enough" | Not without config, data identity and environment |
| "The index CSV is the registry" | It is a view; the directories are the record |
| "Name runs by timestamp" | Re-running a sweep cannot skip completed work, and duplicates are invisible |

## 9. What a sweep may report

May appear: the search space and budget; development scores of every configuration (the 12-row table,
with `n`, mean, sd over seeds and excluded runs counted); the selection rule; the selected configuration.
In the lesson: 200-row burn-in beats 100 rows by about 0.025 for every shrinkage, shrinkage moves the
result by at most 0.005, and the isolation forest is about 0.08 below Mahalanobis.

0.735 is the maximum of noisy development estimates, so it is optimistic for its configuration
(the optimism of the maximum, w3d3); the honest estimate of the *procedure* needs nested validation or
the one test look of the frozen choice. Mechanically, the sweep task evaluates on development rows only
(`dev_pooled_pr_auc`, the same 24,642 rows `t ≥ 200` for every configuration so a longer burn-in is not
also an easier evaluation set); test metrics do not belong in sweep runs; a separate command scores the
frozen choice once.

| Common wrong answer | Why it fails |
|---|---|
| "Report the best of the 12 on test" | Selection on test |
| "Report all 12 test scores for transparency" | Invites choosing by them; the test set is then spent |
| "One seed per configuration is enough for isolation forest" | Seed sd ≈ 0.009 is comparable to the differences being compared |

## 10. MPID, interval readings, the decision

**MPID** (minimum practically important difference): the smallest improvement that would change what
the business does, fixed **before** results. For flowguard, +0.05 PR-AUC.

Readings of an interval for (candidate − reference), higher better: **better** (wholly above +MPID);
**worse** (wholly below −MPID); **equivalent** (wholly inside the band); **inconclusive** (anything else).

Logistic +0.069 [+0.022, +0.128]: it excludes zero but reaches inside the band, so **inconclusive**: a
detectable difference not shown to matter. No candidate is "better", so the rule chooses the simplest
candidate not shown worse, per the complexity ranking fixed in advance: **flow-rate |z|** (one sensor,
no training). The supervised model ranks last on complexity because retraining needs new labelled
faults, the scarcest input in maintenance. The isolation forest was the only candidate shown to differ,
and it was worse (−0.203 [−0.299, −0.120]).

Do **not** switch after the test look: logistic 0.901 vs 0.884 is one look at 7 experiments; the choice
is made on development data and the test set confirms the chosen model once (choosing by test is
selection on test, w3d3). The difference is below the MPID; on test the paired interval for logistic minus
flow-rate was +0.016 [−0.003, +0.049] (w3d5). The chosen model caught 5/7 test events (Wilson 95 %
[0.36, 0.92]) with no false alarms at its frozen operating point. Record logistic as the challenger and
state what evidence would change the decision.

| Common wrong answer | Why it fails |
|---|---|
| "Interval excludes zero, so logistic is better" | Not shown to exceed the MPID |
| "Inconclusive means equivalent" | Equivalent needs the whole interval inside the band |
| "Test says logistic is higher, switch" | Selection on the test set; and smaller than the MPID |

## 11. What a regenerated report guarantees

Guarantees (w4d6, 2.1): one command rebuilds every number, table and figure from raw data and the frozen
manifest; nothing typed by hand (the render step formats, it does not compute; every number in the report
occurs in `results.json`); a rebuild from the same inputs gives the **same bytes**, checkable with
`sha256sum`; the report states its inputs (hashes, code version, library versions).

Does **not** guarantee correctness: a leak or a wrong split is reproduced faithfully every time.

No timestamp, because it makes every rebuild unique and byte identity uncheckable (when it ran belongs in
a log). No latency, because it depends on the host; it lives in the separately labelled w4d5 memo. `make`
tracks **timestamps, not contents or variable values**: changing `N_BOOT` on the command line does not
make results stale (the optional stamp file fixes that), and a checkout that touches a file without
changing it triggers a rebuild anyway.

Sections besides results (three of): problem, data, protocol (split version, resampling unit, MPID,
"development chooses, test confirms"), error analysis, decision, limitations, provenance.

| Common wrong answer | Why it fails |
|---|---|
| "Reproducible means correct" | It means regenerable |
| "Add a timestamp for provenance" | Destroys byte identity; record input hashes instead |
| "`make clean` should delete `data/`" | Raw data is an input, not a build output |

## 12. Bootstrap over rows (delayed question from w3d5)

Full key: answer 9 of `solutions/lessons/w3d7_review/retrieval_answers.md`. In brief: rows within an
experiment are strongly autocorrelated (answer 1: 300 rows at `φ = 0.9` are worth about 16), so a row
bootstrap is far too narrow (3-7 times on SKAB). Resample the **7 test experiments** with replacement and
recompute the metric each time; for comparisons, resample the same experiments for both models (paired).
Doubts: only 1,716 distinct resamples; each experiment missing from about 34 % of them; in w3d5's
simulation nominal 95 % percentile intervals covered about 87-88 % with 7-9 clusters. Report the unit and
`n` and treat the interval as a lower bound on the honest uncertainty.
