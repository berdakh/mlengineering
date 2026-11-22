# w4d7 - retrieval answers

Open only after all twelve questions have a written attempt. Each answer states what a "solid"
answer must contain, then common wrong answers and why they fail.

**Alignment note.** These answers were written from the Week 4 lesson objectives, the project
specification and findings, and standard correct content, while the lessons themselves were still
being written. They will be re-aligned with the final lesson texts. Where a statement was confirmed
by running code, that is said explicitly; everything else is reasoning, not a measurement. Small
simulations use **synthetic** data and illustrate mechanisms only.

## 1. Stationarity and a fixed threshold

A series is **weakly stationary** if its mean and variance are constant over time and the
covariance between two samples depends only on the lag between them, not on when they occur. A
detector that compares "now" with fixed reference statistics assumes this of normal operation.

Two normal non-stationarities on a pump rig:

* **Slow drift in level** (motor and fluid temperature rise during a run; a sensor baseline creeps).
  A z-score against statistics from the start of the run grows steadily: either false alarms late in
  every run, or, if the threshold was widened to avoid them, insensitivity early. It also turns the
  score into a clock, which on SKAB correlates with the label for reasons unrelated to faults.
* **Regime changes** (a setpoint or valve position changes on purpose; start-up transients).
  Mean and variance jump to a new normal level: a fixed threshold alarms at every legitimate change,
  and reference statistics pooled over regimes are too wide to detect anything within one.

Remedies trade one problem for another: differencing or a slowly adapting baseline removes drift
but also adapts to slow faults; conditioning on the regime needs the regime to be known.

| Common wrong answer | Why it fails |
|---|---|
| "Stationary means constant" | A noisy, autocorrelated signal can be stationary |
| "Standardise the whole recording and it is stationary" | Changes units, not the time-dependence of the mean; and uses the future |
| "Non-stationarity is an anomaly" | Much of it is normal operation; that is the difficulty |

## 2. Baseline forecasters; forecasting as a means

* **Naive (last value):** hard to beat on random-walk-like series, which most slowly varying
  physical signals are at short horizons.
* **Seasonal naive (value one period ago):** hard to beat when a strong, stable cycle dominates
  (daily load, a machine cycle).
* **Mean / drift, or a low-order autoregression (AR(p)):** the mean for noise around a fixed level;
  AR for short-memory, mean-reverting dynamics.

In this project the labels are anomalous *segments*, not future values. A forecaster is used only
to define "expected", and the residual is the anomaly score. The detector is judged by the Week 3
protocol (event recall, delay, false alarms), never by forecast error.

A better forecaster can be a worse detector because one-step forecast error is minimised by
*adapting quickly*, and a forecaster that adapts quickly follows the fault: after a step change the
last-value forecast is wrong for exactly one sample and then predicts the faulty level perfectly;
on a slow drift its residual is the slope, which is tiny. A model flexible enough to forecast
everything, anomalies included, leaves no residual to detect.

| Common wrong answer | Why it fails |
|---|---|
| "Pick the forecaster with the lowest RMSE as the detector" | Optimises the wrong quantity; see above |
| "Naive forecasts are too simple to be baselines" | They are frequently the strongest one-step baseline, which is the point of including them |
| "Evaluate the forecaster on anomalous periods too" | The forecaster should be fitted and judged on normal data; its error on faults is the signal |

## 3. PCA monitoring: T² and Q

Fit PCA on standardised normal data, keep `k` components with variances `λ_1..λ_k`. For a new
sample `x` with scores `t = Pᵀx` and reconstruction `x̂ = P t`:

* **T² = Σ_{i≤k} t_i² / λ_i**: squared, variance-scaled distance from the centre *within* the
  retained subspace. It is large when the sample is extreme but still obeys the usual relationships
  between sensors: a normal pattern, abnormally large.
* **Q (SPE) = ‖x − x̂‖²**: squared distance *from* the subspace. It is large when the usual
  relationships are broken: sensors that normally move together disagree.

A per-sensor z-score misses the second kind when each sensor is individually in range.
*(Synthetic illustration, computed: three standardised sensors, the first two correlated at about
0.99, `k = 2`. Normal-data 99th percentiles: T² 8.85, Q 0.07. The sample `[1.5, −1.5, 0]` has
max |z| 1.5 and T² 0.0, but Q 4.47, about sixty times the limit. The sample `[4, 4, 0]` has T² 16.2
and Q 0.0.)* The two statistics are complementary and are monitored together.

Choices that matter: `k` (too large and faults are reconstructed, shrinking Q; too small and normal
variation lands in Q); the data used for fitting (must be normal and from the right regime); small
`λ_i` in T² amplify noise.

| Common wrong answer | Why it fails |
|---|---|
| "T² and Q are the same information" | They measure orthogonal parts of the deviation |
| "Use reconstruction error only" | Misses large in-pattern excursions, such as everything scaling up together |
| "Keep components explaining 99 % of variance" | With correlated sensors that can retain the directions in which faults appear; choose `k` by detection performance on development data |

## 4. Isolation forest

Build many trees, each on a small random subsample: at every node pick a random feature and a
random split value between that feature's minimum and maximum in the node, until points are alone.
A point that is unusual gets separated after few splits, a point inside a dense region needs many.
The score is the **average path length** over trees, normalised by the length expected for the
subsample size: shorter path, more anomalous.

`contamination` does **not** change the fitted trees or the ranking of points. It only sets the
threshold on the score so that the stated fraction of the *training* data is flagged
(`predict` returns −1 for those). Choosing it to match the test prevalence, or to maximise test F1,
is selecting a threshold with test labels. Treat the forest as a scorer (`score_samples`) and choose
the threshold on development experiments like any other.

Limits worth stating: splits are axis-parallel, so a point that only breaks a *correlation* is not
isolated quickly unless a feature exposes it (residuals, ratios); and scores depend on what the
training sample contained, so anomalies present in training look normal.

| Common wrong answer | Why it fails |
|---|---|
| "It measures distance to neighbours" | No distances are computed |
| "`contamination` is how sensitive the model is" | It moves a threshold on fixed scores |
| "It needs no feature engineering" | It sees only the axes you give it |

## 5. Semi-supervised versus supervised framing; protocol B

* **Semi-supervised (novelty detection):** fit on normal data only (burn-in rows, or normal parts of
  training experiments); score deviation from normal. Argument: faults are diverse and future ones
  need not resemble past ones; no fault labels are required to fit. Labels are still needed to
  choose a threshold and to evaluate.
* **Supervised:** fit a classifier on labelled normal and anomalous rows of training experiments.
  Argument: uses all the information, typically better on fault types it has seen. Risk: it learns
  the signatures of the particular faults, and on SKAB possibly the timing of the protocol.

The standard split has all three families on both sides, so it measures performance on **new
experiments with familiar fault mechanisms**. **Protocol B** trains on the valve families and tests
on the whole `other` family (leaks, rotor imbalance, cavitation, temperature): performance on
**fault mechanisms never seen in training**. A supervised model that falls sharply under protocol B
while a semi-supervised one holds up is the evidence for which framing the labels support. Note
that `other` contains every experiment involved in the row-overlap finding except the reference,
so results on it carry that caveat.

| Common wrong answer | Why it fails |
|---|---|
| "Semi-supervised means unlabelled" | It uses the label "normal" for training data, and labels for evaluation |
| "Supervised is better because its test score is higher" | On the standard split; the question is which claim you need |
| "Unsupervised detectors need no threshold tuning" | Every alerting system has a threshold someone chose |

## 6. A fair neural comparison; five seeds

Conditions for fairness (four of):

1. Same split manifest, same test experiments, same preprocessing and the same information
   available (no extra features or longer history for one side).
2. Comparable **tuning budget**, stated: number of configurations or compute spent per model family.
3. All selection (architecture, epochs, early stopping, threshold) on development data for both.
4. Stochastic models run with **several seeds**; the spread reported, not the best.
5. The same metrics, intervals and resampling unit; the classical model's variability (across
   bootstrap resamples) reported too.
6. Baselines given the same care as the favoured model.

With seeds from 0.78 to 0.86 (if evenly spread: mean 0.82, standard deviation about 0.03, computed)
and the classical model at 0.83: the classical score lies inside the seed-to-seed range of the
neural model. You cannot conclude that either is better. Reporting 0.86 as "the neural result" is
selection on the test set. Report the mean and range (or all five values) for the neural model, the
classical value with its experiment-level interval, and the paired difference using the seed-averaged
neural score. Then note that seed variance is *additional* to the uncertainty from having few test
experiments, and that an unstable model has an operational cost of its own.

| Common wrong answer | Why it fails |
|---|---|
| "Best seed 0.86 > 0.83, the neural model wins" | Best-of-five chosen on test data |
| "Fix the seed so results are reproducible; one run is enough" | Reproducible is not the same as representative; a fixed seed hides the variance |
| "Mean 0.82 < 0.83, so the classical model wins" | A 0.01 difference against a seed s.d. of 0.03 and a 9-experiment test set is noise |
| "Neural models need more tuning, so give them more" | Then the comparison is between budgets; say so and report both budgets |

## 7. Why a reconstruction detector misses anomalies

* **It reconstructs anomalies too.** An autoencoder with enough capacity, or one whose anomalies
  lie in the span of normal patterns (a level shift, a smoother-than-usual signal), learns something
  close to the identity on local structure, and reconstruction error stays low. *Check:* inject
  synthetic anomalies of known size into held-out normal windows and plot error against magnitude;
  vary the bottleneck size. If error barely rises, capacity is too high or the anomaly type is
  invisible to this score.
* **The training data contained anomalies** (contamination, or the wrong notion of normal). The
  model learns to reconstruct them. *Check:* confirm from the manifest that training windows come
  only from normal segments; compare the error distribution on training-normal with held-out normal.
* Also valid: **normal data in a new regime** reconstructs badly (false alarms that hide true ones
  by forcing the threshold up; check by per-experiment error on normal rows); **window too long**
  dilutes a short event in the average error; **per-window normalisation** removes exactly the
  level change you wanted to see.

| Common wrong answer | Why it fails |
|---|---|
| "Lower reconstruction loss means a better detector" | The loss is on normal data; detection needs a *gap* between normal and anomalous error |
| "Train longer" | Usually makes the first failure worse |
| "Deep models learn what normal is automatically" | Only relative to the training data and the capacity you gave them |

## 8. Reproducing a row from its run id

A run record needs: the **resolved configuration** (after defaults and overrides), the **code
version** (git commit, and whether the working tree was dirty), the **data identity** (hash of the
input table, and the split manifest *version and hash*), the **environment** (Python and package
versions, hardware if relevant), all **seeds**, the **command** that was run, the **metrics** with
the data they were computed on, and where the **artifacts** are (model file with its hash). The
results table is then generated *from* run directories, never typed.

Usually forgotten: the dirty-tree flag (uncommitted changes make the commit hash a false
statement), the split manifest version, and the threshold together with the data it was chosen on.

"Reproduced" should be stated in advance: bit-identical for deterministic classical pipelines on the
same platform and library versions; equal within a stated tolerance otherwise (different BLAS,
threads, GPU nondeterminism), where the tolerance is small compared with seed variance. A number
that only its author can regenerate has not been reproduced.

| Common wrong answer | Why it fails |
|---|---|
| "The seed and the commit hash are enough" | Not without config, data identity and environment |
| "The notebook is saved" | Hidden state and execution order are not |
| "Results are in a spreadsheet" | Hand-copied numbers drift from the runs that produced them |

## 9. What a sweep may report

From the sweep, the report may contain: the **search space and budget** (60 configurations, how
chosen); the **development-data scores** of all configurations (grouped CV over development
experiments), ideally as a distribution, since "how sensitive is performance to this setting" is a
result; and the selected configuration with the rule that selected it.

Test-set numbers appear only for the configuration(s) **frozen before** the test set was scored:
normally one per model family, each evaluated once. Mechanically: the sweep command has no access
to the test experiments; a separate `evaluate` command takes a frozen run id; the number of test
evaluations is itself recorded. If you look at test results and then go back to sweep again, the
next test number is no longer clean, and the honest remedy is to say so or to obtain new test data.

| Common wrong answer | Why it fails |
|---|---|
| "Report the best of the 60 on the test set" | Maximum of 60 noisy estimates |
| "Report test scores for all 60 to be transparent" | Transparent, and it invites choosing by them; the test set is then spent |
| "Random search needs no validation set" | The search strategy does not change what is being selected on |

## 10. Δ = 0.02, interval [−0.03, 0.07]

The interval includes zero and is wider than the estimate: on this evidence the two are **not
distinguishable**. Considerations:

* **Evidence:** size of the effect relative to its uncertainty; whether it holds across families
  and under protocol B; seed variance of the complex model.
* **Cost of errors:** does 0.02 in this metric change an operational quantity (missed events, false
  alarms per day) that anyone would notice?
* **Serving cost:** latency, memory, dependencies (a PyTorch runtime in the image), cold start.
* **Maintenance:** retraining complexity, number of hyperparameters, how failures are diagnosed, how
  explainable an alert is to the operator.
* **Risk:** behaviour off-distribution; how the model fails (silently or visibly).
* **Reversibility:** how cheaply the decision can be revisited when more data arrives.

Defensible decision: **ship the simpler model**, record the complex one as a challenger with the
exact evidence that would change the decision (for example, an interval excluding zero on a larger
test set, or a clear advantage on unseen fault families). "The complex model is better but we chose
the simple one" overstates the evidence; "they are equivalent" overstates it the other way.

| Common wrong answer | Why it fails |
|---|---|
| "Higher point estimate, ship the complex model" | Ignores the interval and every cost |
| "Not significant, so the models are the same" | The interval allows +0.07 |
| "Collect more seeds until it is significant" | Seeds do not add test experiments; and optional stopping biases the result |

## 11. What a regenerated report guarantees

`make evaluate` guarantees that the tables and figures are **produced by code from recorded
inputs**: no hand-copied numbers, no stale figure, and a second person can regenerate them and get
the same thing. It makes errors findable and the report auditable.

It does not guarantee that the protocol is right: a leak, a wrong split or a mislabelled metric is
reproduced faithfully every time. Reproducible is not the same as correct.

Besides the comparison table, the report must contain (three of): the **protocol** (split version,
what was tuned where, the number of test evaluations); **uncertainty** with its resampling unit;
**baselines** including the trivial and the elapsed-time scorer; **error analysis** (failure
categories ranked by impact, per-family results); **limitations and threats to validity** (dataset
findings, prevalence, what was not measured); **provenance** (data hashes, commit, environment);
and the **decision** with the evidence that would reverse it.

| Common wrong answer | Why it fails |
|---|---|
| "It guarantees the results are correct" | It guarantees they are regenerable |
| "The table and the best model's plots" | No protocol, uncertainty or limitations: a reader cannot judge the numbers |
| "Limitations weaken the report" | They are what lets a reader trust the rest |

## 12. Bootstrap over rows (delayed question from w3d5)

See answer 9 of `solutions/lessons/w3d7_review/retrieval_answers.md`. In brief: rows within an
experiment are strongly autocorrelated (ten minutes at 1 Hz with lag-one correlation 0.9 is worth
about 32 independent samples for a mean: `n(1 − ρ)/(1 + ρ)`, confirmed by simulation), so a row
bootstrap gives an interval several times too narrow. Resample **experiments** with replacement and
recompute the metric on each resample. With about 9 test experiments the interval itself is rough:
few clusters make percentile intervals too narrow, single experiments dominate, and event-level
metrics take few distinct values. Report it with its unit and `n`, as a lower bound on uncertainty.
