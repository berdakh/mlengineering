# W4D2 — Classical detectors: PCA (T² and Q), isolation forest, boosted trees

Unit id `w4d2_classical_detectors` · Week 4, day 2 · Handbook:
[H5.3](../../handbook/ch05_classical_ml_baselines/h5_3_trees_ensembles_iforest_pca.md),
[H7.5](../../handbook/ch07_timeseries_grouped_modeling/h7_5_multivariate_detectors.md)
· Content status: see [STATUS.md](../../STATUS.md)

## 1. Purpose

**Objective.** Implement three classical detectors behind one interface — a PCA model with Hotelling's
T² and the Q (SPE) statistic, an isolation forest, and supervised gradient-boosted trees — and compare
them on SKAB under one protocol and one compute budget, including a leave-family-out protocol that
asks whether the labels support a supervised framing at all.

**Why an applied ML engineer needs it.** "Which model?" is the question everyone asks first and the
one that matters least until the comparison is fair: same features, same data, same tuning budget,
same threshold rule, same evaluation unit. You will be expected to run such a comparison, to choose
between a semi-supervised and a supervised framing from the structure of the labels, and to explain in
an interview why a model that wins on the test set may still be the wrong one to ship.

**Deliverable.** A tested `flowguard.detectors` module and `lab/COMPARISON.md`: the protocol A and
protocol B tables from the real data, and a five-sentence recommendation of which framing the labels
support.

**Completion criteria.**

* `python wb.py check w4d2` passes (guided practice).
* `lab/COMPARISON.md` has both tables and the recommendation.
* Independent skill: `python wb.py check w4d2 --challenge` passes and `challenge/DECISION.md` is written
  without hints.

**Prerequisites.** [w4d1](../w4d1_timeseries_fundamentals/README.md) (burn-in reference, single-sensor
baselines), the frozen split from [w3d1](../w3d1_leakage/README.md), leave-family-out validation from
[w3d2](../w3d2_group_temporal_validation/README.md), selection discipline from
[w3d3](../w3d3_hyperparameter_selection/README.md), and the Week 3 evaluation tools (snapshots ship
with the lab). Assumed: PCA, decision trees and boosting as algorithms.

**Time budget (2 h essential).**

| Activity | Minutes |
|---|---|
| Read section 2, run the worked example | 35 |
| Guided lab: implement `flowguard.detectors` (Tasks 1-4) | 45 |
| Guided lab: run the comparison (about 2.5 min), write `COMPARISON.md` (Task 5) | 20 |
| Independent challenge: start | 10 |
| Assessment and reflection | 10 |
| *Optional extension: finish the challenge; per-family thresholds; permutation importance* | *up to 60* |

Data needed for the real-data steps: `python project/get_skab.py` (once). Checks need no download.

## 2. Conceptual explanation

### 2.1 Two framings, decided by the labels

A **semi-supervised** detector learns what normal looks like and scores departures from it. It needs
labels only to select normal training rows (and to evaluate). It can flag fault types it has never
seen, and it flags anything unusual, including benign novelty. A **supervised** detector learns to
separate the labelled classes. It uses the labels fully and is usually sharper on the fault types in
its training data; it has no reason to score an unseen mechanism highly.

Which framing the labels support depends on three questions:

1. *Coverage:* do the labelled faults cover the mechanisms you will meet in deployment?
2. *Quantity per mechanism:* enough independent units (experiments, machines, accounts) per mechanism?
3. *Label process:* are labels a random sample, or produced by a process (review queues, maintenance
   tickets) that selects which units get labelled?

SKAB answers (1) with "partly": three families, and the `other` family is itself a mixture of
mechanisms (leaks, rotor imbalance, cavitation, temperature). Protocol B in the lab measures what that
means in numbers.

```mermaid
flowchart TD
    Q1{"Do labelled faults cover the<br/>mechanisms seen in deployment?"} -->|no / unknown| S["semi-supervised<br/>(model of normal)"]
    Q1 -->|yes| Q2{"Enough independent units<br/>per mechanism?"}
    Q2 -->|no| S
    Q2 -->|yes| Q3{"Is the label process<br/>roughly random?"}
    Q3 -->|no| B["supervised, but validate on the<br/>label process you will deploy into"]
    Q3 -->|yes| SUP["supervised"]
    S --> H["often: both, with the semi-supervised<br/>score as a safety net for novel faults"]
    SUP --> H
```

### 2.2 PCA detector: T² and Q

Standardise the sensors with the mean and SD of normal training rows, compute the principal components,
and keep `k` of them (enough to explain a chosen share of the variance). With loadings `P` (`d × k`),
component variances `λ_1 … λ_k` and a standardised row `x`:

```
scores           t = x P
Hotelling T²     T² = Σ_j t_j² / λ_j                    distance inside the retained subspace
Q (SPE)          Q  = ‖x − x P Pᵀ‖² = ‖x‖² − ‖t‖²       squared distance from the subspace
```

They see different faults. **T²** is large when the row is extreme *along* directions normal data
varies in (high load, every sensor moving together as usual). **Q** is large when the row leaves the
subspace: the usual relationships between sensors are broken (one sensor drifts, a valve no longer
couples pressure to flow). T² is a Mahalanobis distance in `k` dimensions; Q is what the model cannot
explain.

![SYNTHETIC two-sensor example: a correlated normal cloud with its retained principal direction; point A lies far along that direction with T2 = 7.0 above its limit 6.7 and Q = 0.00; point B lies off the direction with T2 = 0.0 and Q = 2.07 far above its limit 0.22](figures/t2_q_geometry.svg)

*Figure 1 (SYNTHETIC).* A is unusual in size but has normal structure: only T² sees it. B is ordinary
in size but breaks the relationship between the sensors: only Q sees it. Limits are the 99th
percentiles of each statistic on the fit rows.

**Control limits.** Under multivariate normality, `T²` of a new row follows a scaled F distribution
(`k(n²−1)/(n(n−k)) F(k, n−k)`), and Q is approximately a scaled χ² (Jackson–Mudholkar or
Box's approximation). On real sensor data these assumptions are weak; the lab uses **empirical 99th
percentiles on the fit rows**, which are honest about the data and say nothing about anything else.

**Choosing `k`.** Too few components push normal variation into Q (false alarms); too many absorb
faults into the subspace (Q goes blind). Choose `k` by the share of variance on normal data as a
starting point, then by detection metrics on development units — which is what the lab does.

### 2.3 Isolation forest

An isolation tree splits the data on a random feature at a random value between that feature's minimum
and maximum, recursively, until each point is alone. Points that are easy to separate from the rest
need few splits. Averaged over many trees grown on subsamples of `ψ` rows, the expected path length
`E[h(x)]` is short for anomalies. The score normalises by `c(ψ)`, the average path length of an
unsuccessful search in a binary search tree (`c(ψ) = 2H(ψ−1) − 2(ψ−1)/ψ`, with `H` the harmonic
number):

```
s(x) = 2^(−E[h(x)] / c(ψ))        s → 1: anomalous,  s ≈ 0.5: nothing stands out
```

scikit-learn's `score_samples` returns `−s(x)` (higher = more normal); the lab negates it so that
higher means more anomalous, as for every other detector.

**`contamination` is a threshold in disguise.** In scikit-learn it does not change the fitted trees or
the scores; it only sets the cut-off used by `predict` so that that share of the *training* rows is
flagged. Choosing it is choosing an alarm rate without looking at any outcome. The worked example
demonstrates this; the lab sets thresholds on development data instead.

Practical properties: no distance metric, so features on different scales are fine; axis-aligned
splits make it weaker on anomalies that are only visible as broken correlations (an oblique direction).

### 2.4 Gradient-boosted trees on window features

A supervised baseline that is hard to beat on tabular features: an additive model of shallow trees,
each fitted to the gradient of the loss of the current ensemble. `HistGradientBoostingClassifier` bins
each feature into at most 255 bins, which makes training fast. Three cautions specific to this setting:

* **Features must be available at prediction time and causal.** The lab uses the w2d5 recipe: burn-in
  z of each sensor and trailing rolling means and SDs. `t`, `datetime` and identifiers are refused by
  the detector itself: SKAB faults start at row 550-600 in 31 of 34 experiments, and a tree finds that
  in seconds (project/README findings).
* **Early stopping uses a random row split.** With rows of one experiment on both sides, the internal
  validation is leaky; the lab turns early stopping off and treats the number of iterations as a
  hyperparameter like any other.
* **Feature importance is not explanation.** Impurity-based importance is biased towards
  high-cardinality and correlated features; permutation importance measured on held-out *experiments*
  is the minimum, and with 40 correlated features it still spreads credit arbitrarily among them.

### 2.5 A fair comparison

| Held equal | In the lab |
|---|---|
| Features | the same 40 causal window features for every detector |
| Data | the same development rows; semi-supervised detectors see the normal ones, GBT all of them |
| Tuning budget | 3 configurations per detector, chosen by out-of-fold PR-AUC over the 4 development folds |
| Threshold rule | best F1 on out-of-fold development scores |
| Evaluation | the 7 frozen test experiments; point PR-AUC with a cluster-bootstrap interval, event metrics |
| Compute | reported (fit + score seconds on the test experiments) |

A comparison that tunes one model for a week and runs the other with defaults compares the effort, not
the models. So does one that gives a detector access to a feature the others lack.

### 2.6 Connection to your EEG work

PCA/ICA artefact removal is the same geometry: components that capture the usual co-variation of
channels, and a residual that carries what does not fit. Cross-subject decoding is protocol B: a
classifier trained on some subjects' patterns of a condition may not transfer to a new subject's, and
you would not report within-subject accuracy as the cross-subject result. What is new is treating the
*fault mechanism* as the unit of generalisation, alongside the experiment.

### 2.7 Industry example

Multivariate statistical process control in chemical and semiconductor plants is PCA with T² and Q
charts, often with "contribution plots" that show which variables drive a Q alarm — an explanation an
operator can act on. Payment fraud teams typically run a supervised model trained on confirmed fraud
next to unsupervised anomaly scores, because new fraud patterns appear before labels for them exist;
the supervised model is sharper, the unsupervised one is the early warning.

### 2.8 Misconceptions

* "The model with the best test score should ship." Not if a second protocol (an unseen family, a
  later period, a new site) reverses the ranking, and not if its false-alarm rate breaks the budget.
* "Isolation forest needs a contamination rate." Only `predict` does; the scores do not.
* "T² is enough." It is blind to broken correlations; Q is blind to extreme but consistent states.
* "More features is fairer to the flexible model." It is a different comparison; hold features equal
  and compare feature sets separately.
* "Unsupervised means no labels needed." You need labels to evaluate it, and usually to select normal
  training data.

## 3. Worked example

`example/detectors_tour.py` builds a SYNTHETIC six-sensor plant driven by two hidden factors and two
fault types: A, an extreme but consistent operating point; B, one sensor leaving its usual relationship
by a small amount. It uses the reference implementation (set `DETECTORS_SRC` to your `lab/src` later).

```bash
python lessons/w4d2_classical_detectors/example/detectors_tour.py
```

Output from the authoring run:

```
1. PCA on 6 sensors driven by 2 factors: k = 2 components keep >= 90% of the variance; 99% limits: T2 9.0, Q 0.40
   fault A (extreme but consistent)   rows above the T2 limit 53.0%   above the Q limit  5.0%
   fault B (broken relationship)      rows above the T2 limit  1.5%   above the Q limit 97.5%
   normal test rows above the limits: T2 0.6%, Q 1.1%

2. ROC AUC against the normal test rows, per fault type
   PCA T2            fault A 0.945   fault B 0.520
   PCA Q             fault A 0.671   fault B 0.999
   isolation forest  fault A 0.947   fault B 0.699

3. `contamination` only moves the threshold of predict(); the scores do not change
   contamination 0.01: share of probe rows flagged 9.1%; first three scores [-0.4579 -0.3974 -0.3994]
   contamination 0.05: share of probe rows flagged 15.4%; first three scores [-0.4579 -0.3974 -0.3994]
   contamination 0.2 : share of probe rows flagged 32.4%; first three scores [-0.4579 -0.3974 -0.3994]

4. A supervised model trained on fault A only, tested on fault B (a mechanism it never saw)
   GBT on fault A (seen in training)   ROC AUC 0.975
   GBT on fault B (unseen)             ROC AUC 0.638
```

![Grouped bars of ROC AUC per detector and fault type from the worked example: PCA T2 0.94 on fault A and 0.52 on fault B; PCA Q 0.67 and 1.00; isolation forest 0.95 and 0.70](figures/example_auc.svg)

*Figure 2 (SYNTHETIC, from the worked example).*

**Reading it.** Two factors explain the six sensors, and the variance rule finds `k = 2`. Fault A
lives inside the model's subspace: T² sees it, Q barely. Fault B is small (one sensor shifted by about
one SD) but leaves the subspace: Q catches 97.5% of its rows while T² is at chance. The isolation
forest sees both, B only partly, because a broken correlation is an oblique direction that axis-aligned
random splits isolate slowly. The scores are identical for every contamination value; only the share of
rows flagged moves. And the supervised model, excellent on the fault it was trained on, is close to
chance on the one it never saw — protocol B in miniature.

## 4. Guided lab

Work in `lab/src/flowguard/detectors.py`. `windowfeatures.py` (the 40 features) and the Week 3
modules are given. Checks: `python wb.py check w4d2`. The starter fails all of them.

```mermaid
flowchart LR
    R["tidy SKAB rows"] --> F["window_features<br/>40 causal features per row"]
    F --> D["development rows<br/>(27 experiments, 4 folds)"]
    F --> T["test rows<br/>(7 frozen experiments)"]
    D --> O["out-of-fold scores for<br/>3 configs per detector"]
    O --> C["choose config (OOF PR-AUC)<br/>and threshold (OOF best F1)"]
    C --> FIT["refit on all development rows"]
    FIT --> T
    T --> E["PR-AUC + cluster bootstrap,<br/>events, false alarms per hour"]
    D --> B["protocol B: train on valve1 + valve2,<br/>score the `other` family"]
```

**Task 1 — `check_columns` (5 min).** Return the column names; raise `ValueError` naming every
forbidden one (identifiers, labels, anything naming elapsed time). Every detector calls it in `fit`.

**Task 2 — `PCADetector.fit` and `_stats` (20 min).** Standardise with the fit rows' mean and SD (1.0
where the SD is zero), `np.linalg.svd` of the standardised matrix, component variances
`s²/(n−1)`, `k` from `n_components` or the smallest `k` reaching `variance`, then the 99th-percentile
limits. `_stats(xs)` returns `(T², Q)` for standardised rows.
*Checkpoint:* `test_q_catches_a_broken_correlation_that_t2_misses`.
*Debugging:* if Q is large for points on the normal axis, you subtracted the projection in the wrong
space (scores `t` vs reconstruction `t Pᵀ`); if `score` depends on the batch, you standardised with
the scored rows' statistics.

**Task 3 — `IForestDetector` (5 min).** Wrap `sklearn.ensemble.IsolationForest` with
`random_state=self.seed`; score = `−score_samples`.

**Task 4 — `GBTDetector` (10 min).** Refuse forbidden columns, require labels with both classes,
`HistGradientBoostingClassifier(early_stopping=False, random_state=seed, ...)`, score = `P(anomaly)`.

**Task 5 — the comparison (20 min including writing).**

```bash
python lessons/w4d2_classical_detectors/lab/compare_detectors.py     # about 2.5 minutes on 4 CPU cores
```

Do not run two copies at once: scikit-learn's tree models use all cores through OpenMP, and two
processes competing for them ran about eight times slower in the authoring session.

Output from the authoring run (reference implementation; yours should match):

**A. Frozen split** (7 test experiments; config chosen by out-of-fold development PR-AUC):

| detector | chosen config (OOF dev PR-AUC) | test PR-AUC [95% CI] | events | false alarms / h | median delay (s) | fit+score s |
|---|---|---|---|---|---|---|
| flow_rate abs z (w2d6 baseline) | none (0.765) | 0.886 [0.811, 0.929] | 7/7 | 238.6 | 4 | 0.0 |
| PCA T² | variance 0.8 (0.747) | 0.762 [0.628, 0.868] | 7/7 | 204.8 | 12 | 0.1 |
| PCA Q (SPE) | variance 0.8 (0.663) | 0.626 [0.453, 0.783] | 7/7 | 369.4 | 1 | 0.1 |
| isolation forest | max_samples 1024 (0.721) | 0.831 [0.752, 0.901] | 7/7 | 195.0 | 4 | 0.5 |
| gradient-boosted trees | lr 0.1, 15 leaves, 200 iterations (0.836) | 0.920 [0.806, 0.980] | 7/7 | 62.5 | 8 | 0.6 |

**B. Leave-family-out** (development experiments only: train on 15 valve1/valve2 experiments,
evaluate on the 12 `other` experiments = 8 independent clusters; prevalence 0.393):

| detector | PR-AUC on unseen family [95% CI] | same detector, protocol A test |
|---|---|---|
| flow_rate abs z (w2d6 baseline) | 0.640 [0.527, 0.781] | 0.886 |
| PCA T² | 0.761 [0.663, 0.860] | 0.762 |
| PCA Q (SPE) | 0.699 [0.604, 0.801] | 0.626 |
| isolation forest | 0.783 [0.662, 0.906] | 0.831 |
| gradient-boosted trees | 0.636 [0.462, 0.836] | 0.920 |

![Dumbbell-style interval plot: for each detector, protocol A test PR-AUC and protocol B unseen-family PR-AUC with 95% intervals; gradient-boosted trees drop from 0.920 to 0.636, flow-rate z from 0.886 to 0.640, while isolation forest (0.831 to 0.783) and PCA T2 (0.762 to 0.761) hold](figures/protocols.svg)

*Figure 3 (REAL SKAB).* Protocol A asks "how well on new experiments of the families we trained on?";
protocol B "how well on a family we never trained on?". The rankings disagree.

**Interpretation (what the authoring run supports).**

* On protocol A the supervised GBT has the best point estimate (0.920) and by far the lowest
  false-alarm rate at its development threshold (62.5 per hour against roughly 200-370 for the others).
  Its interval overlaps the flow-rate z-score's and the isolation forest's; with 7 test experiments
  the ranking among the top three is not established.
* On protocol B, the GBT falls to 0.636 and the single flow-rate z-score to 0.640, while the isolation
  forest (0.783) and PCA T² (0.761) hold their level. For the z-score the reason is visible in the data:
  the median |z| of the flow rate is 5.22 in valve1 fault rows against 0.55 in valve1 normal rows, but
  3.58 against 1.25 in the `other` family (computed in the authoring session) — valve faults move the
  flow directly, other mechanisms less, and normal `other` rows are noisier. The GBT learned what
  separates *valve* faults.
  Eight clusters: the intervals are wide and overlap, so this is a warning, not a measurement of the
  size of the drop.
* PCA Q is the weakest on both protocols here. On SKAB the faults mostly move the operating point
  (inside the subspace, T²'s territory) rather than break sensor relationships; that is a property of
  these faults, not of Q in general (figure 2 shows the opposite case).
* Compute is not a differentiator at this scale (all under a second to fit and score the test
  experiments); maintenance is: the GBT needs labelled faults of every kind to stay good, the
  semi-supervised detectors need a clean normal reference.
* Which framing the labels support: supervised for the valve families, which are labelled with many
  experiments each; not for fault mechanisms outside them. The defensible design is a supervised model
  plus a semi-supervised safety net, with protocol B reported next to protocol A.

![Real SKAB test experiment valve1/5: four detector scores as percentiles of their development scores, with each detector's threshold dashed and the labelled fault shaded; the flow-rate z-score and the boosted trees rise sharply in the fault, PCA T2 and the isolation forest rise more gradually and also exceed their thresholds outside the fault](figures/skab_scores.svg)

*Figure 4 (REAL SKAB, test experiment valve1/5).* Scores are shown as percentiles of each detector's
out-of-fold development scores, so they share an axis. The thresholds sit near the 50th-65th
percentile because best-F1 thresholds on data with about 40% anomalous rows flag a large share of rows;
that is why every detector's false-alarm rate is high (w3d4 chose operating points from a budget instead).

**If the lab runs long.** Write the recommendation on the review day; the tables are the essential part.

## 5. Independent challenge

[challenge/README.md](challenge/README.md): SYNTHETIC card transactions with account-level labels on
about 5% of the training customers. Compare an isolation forest with a supervised GBT, estimate each
honestly, choose, and report — graded on how close your estimate is to performance on new customers.
Transfer: a different domain, a different grouping unit (the customer), and labels produced by a
review process.

## 6. Progressive hints

[Hint 1: concept](hints/hint1_concept.md) · [Hint 2: approach](hints/hint2_approach.md) ·
[Hint 3: partial implementation](hints/hint3_partial.md)

## 7. Assessment

[assessment.md](assessment.md): reasoning questions, a design-choice explanation, a rubric and a
10-15 minute interview rep on trees and ensembles. Answers in
`solutions/lessons/w4d2_classical_detectors/assessment_answers.md`.

## 8. Reflection and review

**You should now be able to, without notes:**

* compute T² and Q from a PCA model and say which fault each one sees;
* explain isolation-forest scores and why `contamination` is a threshold;
* train a supervised tree model on causal features without leaking time or identity;
* design and run a comparison that holds features, budget, threshold rule and evaluation equal;
* argue from a second protocol whether labels support a supervised framing.

**Reflection prompt** (5 minutes, in `progress/notes.md`). Think of a cross-subject result in your
research. If you had reported only the within-subject number, which decision would have been wrong?
What is the "protocol B" of the system you most want to build next?

**Retrieval question for later** (review day): a PCA detector with `k` chosen to keep 99% of the
variance has stopped alarming on a known fault that a `k` for 80% caught. Explain in terms of T² and Q.

**Next.** w4d3: a neural comparison where it is justified — a small sequence model under the same
protocol, with seed variance reported (status in [roadmap/SCHEDULE.md](../../roadmap/SCHEDULE.md)).

---

### Verification record

Executed on 2026-11-22 with Python 3.13.18, NumPy 2.5.3, pandas 3.0.5, scikit-learn 1.9.1, matplotlib
3.11.2 on 4 CPU cores: the worked example; `lab/compare_detectors.py` with the reference implementation
on the real SKAB files (two runs, identical tables; 2 min 26 s when run alone); `figures/make_figures.py`
(four figures inspected as rendered images); the reference challenge on the shipped data and generator
seeds 101-104; `python tools/verify_checks.py lessons/w4d2_classical_detectors` (reference passes both
parts; 5 lab and 4 challenge mutants rejected); the shipped starters fail their checks. Not verified:
Python 3.11/3.12; time boxes; the F-distribution limit for T² and the Q approximations in section 2.2
are stated from memory and not used by any code.
