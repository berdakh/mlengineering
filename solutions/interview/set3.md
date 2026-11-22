# Interview set 3 - rubrics (part A) and worked answers (part B)

**Order of use (Weeks 3-5 rule).** After your first timed attempt, read **part A only** and score
yourself. Make a second attempt at every prompt scored below "Demonstrated". Only then read part B.

Reference code: `solutions/interview/set3/c9.py`. Deliberately wrong answers rejected by the tests:
`solutions/interview/set3_wrong/`.

Verified in the authoring session (Python 3.13.18, pytest 9.1.1, scikit-learn 1.9.1):
`SET3_DIR=solutions/interview/set3 python -m pytest interview/set3_tests -q` gives 20 passed; the
shipped stub fails all 20; each wrong answer fails at least one test (table at the end). Numbers in
the worked answers marked *(simulated)* or *(computed)* were produced by running code in that
session; everything else is reasoning.

Evidence levels per prompt, not points: **Demonstrated** (every "must", unaided, in time),
**Partial**, **Not yet**. Record the level and the error pattern in `progress/notes.md`.

---

# Part A - rubrics

For every scenario the four "musts" are the same: **flaw named precisely; mechanism and direction of
bias; corrected procedure; expected effect and how to confirm**. The entries below say what each
must contain for that scenario.

## S1 - churn

* **Must:** the features are measured *after* (or at) the outcome: "features as of today" for a
  customer who cancelled months ago describe a cancelled account. Names it as target/temporal
  leakage through the absence of a prediction time.
* **Must:** the fix is a point-in-time dataset: choose snapshot dates, compute features from data
  strictly before each snapshot, label from the window after it, and split by time (and by customer).
* **Should:** notes the label is also wrong (cancelled "in the past year" is not "in the next 30
  days"); notes survivorship (only currently existing rows); suggests a check such as the
  feature's distribution by time-relative-to-cancellation.
* **Not enough:** "the random split is the problem" (it is *a* problem, not the one that produced 0.93).

## S2 - selection before CV

* **Must:** states that with random labels the procedure reports accuracy far above 50 %, and why:
  the selection step used the labels of the rows later used for testing.
* **Must:** selection goes *inside* each training fold (a pipeline), or the whole procedure is nested.
* **Should:** proposes the permutation demonstration (shuffle the labels, rerun both procedures);
  says the effect grows with features/samples ratio.
* **Not enough:** "use more folds" or "use a held-out test set chosen after selection".

## S3 - overlapping windows

* **Must:** two distinct problems: (a) overlapping windows put nearly identical samples on both
  sides; (b) even without overlap, windows from one machine share machine identity, so the split
  must be by machine.
* **Must:** design: machine-wise (grouped) splits; if a machine's timeline is split, a gap (purge)
  of at least the window length.
* **Should:** names what remains uncertain: only 40 machines (wide intervals), later machines may
  differ systematically (time/installation shift), label quality; hyperparameters and early stopping
  were tuned on a leaky validation set too.
* **Not enough:** "reduce the overlap".

## S4 - forty configurations

* **Must:** 0.91 is the *maximum* of 40 noisy estimates, not an unbiased estimate of that
  configuration's performance; the test set was used for selection.
* **Must:** selection on validation data (or inner CV); the test set is used once for the chosen
  configuration; with no data to spare, nested cross-validation over experiments.
* **Should:** quantifies: with 9 test experiments one event is 0.11 of recall; 0.91 versus 0.90 is
  far inside the noise; the top configurations are indistinguishable, so prefer the simplest.
* **Not enough:** "apply a multiple-comparison correction" with no change to the procedure.

## S5 - the clock

* **Must:** recognises that the features can encode *elapsed time in the recording*, and that fault
  onset time is nearly constant across recordings in this benchmark: a correct split does not
  protect against a shortcut shared by all experiments.
* **Must:** a concrete fast test: a baseline that scores by elapsed time alone; if it matches the
  model, the model has shown nothing.
* **Must:** remedy: forbid clock-like features, and evaluate so the shortcut cannot pay (for example
  compare against the clock baseline, or randomise/truncate recording starts).
* **Should:** generalises: shortcut learning from acquisition protocol (site, scanner, session
  order) is the same failure; grouped splitting addresses dependence, not shared artefacts.

## F6 - ridge and correlated features

* **Must:** OLS: the sum of the two coefficients is determined, the split between them is not
  (unstable, large opposite-signed values). Ridge: splits the weight evenly. Lasso: tends to keep
  one and zero the other, arbitrarily.
* **Must:** the ridge argument: for fixed `w1 + w2 = c` the fit is unchanged and the penalty
  `w1² + w2²` is minimised at `w1 = w2 = c/2`.
* **Should:** consequence: coefficient magnitude is not importance when features are correlated;
  mentions elastic net or grouping; notes scaling matters for the penalty.

## F7 - prevalence

* **Must:** ROC AUC, recall (TPR) and FPR are unchanged; precision changes.
* **Must:** precision from Bayes' rule, both values approximately right (about 0.81 and 0.075).
* **Should:** average precision depends on prevalence, so a benchmark AP does not transfer; report
  the operating point and the deployment prevalence, or alerts per unit time.

## F8 - bias of the maximum

* **Must:** the expected maximum of `K` equal-mean noisy scores exceeds the truth by an amount that
  grows with `K` roughly like `s·sqrt(2 ln K)` (an upper-bound flavour; smaller in practice); about
  1.5 `s` for 10, 2.5 `s` for 100.
* **Must:** three places and remedies, e.g. hyperparameter search (validation/nested CV), choosing
  the best epoch or checkpoint (separate validation), choosing among models/seeds for a paper
  (untouched test set), threshold selection, feature selection.
* **Should:** notes correlated candidates shrink the effect; the bias is in the *reported score*,
  the selected model may still be a fine choice.

## C9 - grouped K-fold

* **Must:** all tests pass; rows mapped to groups first, folds built from whole groups.
* **Must:** a stated balancing strategy (largest group first into the currently smallest fold) and
  an honest statement that it is a greedy heuristic for a partition problem, not optimal.
* **Must:** seed affects assignment without breaking determinism.
* **Should:** complexity `O(n + g log g + g·k)`; names `GroupKFold` (deterministic by default, balances fold
  sizes) and `StratifiedGroupKFold`;
  asks whether balance should be in rows or in positives.

---

# Part B - worked answers

## S1

The dataset has no **prediction time**. Features are read "as of today", labels come from the past
year, so for every cancelled customer the features were measured after the outcome: a cancelled
account has no recent logins and a burst of tickets around cancellation. The model learns to
recognise accounts that *have already* churned, which is easy (0.93) and useless. In production the
features are measured before the outcome, the shortcut is gone, and the honest signal gives 0.71.

Rebuild as a point-in-time table: pick snapshot dates (say the first of each month); for each
active customer at a snapshot compute features from events strictly before it (an as-of join, as in
`w2d2`); label = cancelled within the following 30 days; rows whose 30-day window has not closed are
excluded. Split by time, training on earlier snapshots and testing on later ones, keeping in mind
that the same customer appears at several snapshots. Expect the offline AUC to fall to about the
production figure; confirm the diagnosis by plotting `days_since_last_login` against days relative
to cancellation in the original table.

Also wrong, but secondary: the label definition differs from the stated task, and customers who left
and were purged are missing.

## S2

Expect very high accuracy on pure noise. *(Simulated: 120 samples, 20,000 standard-normal features,
random balanced labels, five repetitions: selecting 50 features on all rows then 5-fold CV gave
mean accuracy 0.96; with the selection inside each fold, 0.45.)* With 20,000 candidates, some
features correlate with any labelling of 120 rows by chance; choosing them with all labels means
the held-out fold's labels helped choose the features, and the classifier then "predicts" those
labels.

Fix: `make_pipeline(SelectKBest(k=50), LogisticRegression())` passed to `cross_val_score`, so
selection is refitted on each training fold. If `k` is tuned as well, nest the tuning. The
demonstration for a sceptic is the permutation test above: shuffle `y`, run both procedures; an
honest procedure returns about 50 %.

## S3

Three sources of optimism. (a) With 90 % overlap, consecutive windows share 9 s of signal; a random
split puts a test window between two training windows that contain most of it. (b) Without any
overlap, windows from the same machine share its resonances, mounting and sensor gain; the model
can identify the machine and recall its label. (c) Early stopping and hyperparameters were chosen on
a validation set with the same leaks, so model selection was optimistic too.

Design: split by machine (grouped K-fold over the 40 machines, or hold out whole machines), all
tuning inside the training machines. If healthy and faulty periods of the same machine must be
separated in time, leave a gap of at least one window length between train and test segments.
This estimates performance on a *new machine from the same population*. It does not cover machines
that differ systematically (a later installation batch, another site, another sensor model), and
with 40 machines, or fewer faulty ones, the interval on any metric is wide. The 81 % on three new
machines is itself three units of evidence.

## S4

0.91 estimates the expected value of *the best of 40 noisy measurements*, which is higher than the
true performance of the selected configuration. The test set has been used as a validation set and
there is no longer any unbiased estimate.

Size: with 9 test experiments, event recall moves in steps of 1/9 = 0.11; a standard error of
several points of F1 is plausible. The maximum of 40 equal candidates sits about 2.2 standard
errors above the mean *(simulated for independent candidates; correlated configurations reduce it)*,
so several points of the 0.91 can be selection alone, and 0.91 versus 0.90 carries no information
about which is better.

Procedure: choose among the 40 using development experiments only (grouped cross-validation),
freeze configuration and threshold, evaluate once on the test experiments, report with an interval
from resampling experiments. If no separate test set can be afforded: nested cross-validation, with
the search repeated inside each outer training set; the outer score estimates the *procedure*.
Among configurations that are indistinguishable, take the simplest or cheapest.

## S5

Experiment-wise splits protect against dependence between train and test rows. They do not protect
against a regularity **shared by every experiment**: here the fault is injected at nearly the same
elapsed time in each recording (rows 550-600 in 31 of 34 SKAB files). A 600-row rolling mean of a
slowly warming temperature, or cumulative energy, is a monotone function of elapsed time. The model
can score well by learning "it is late in the recording". On a real plant, faults do not arrive on
schedule and the model is worth nothing.

Test in under an hour: add a baseline whose score is the row index `t`. In the project it reaches
test F1 0.835, above every sensor baseline (`w2d6`). Then: remove clock-like features and refit;
plot the model's score against `t` on normal-only data, such as the fault-free recording, where an
honest detector should stay flat; evaluate on recordings truncated or shifted so that onset time
varies.

Changes: forbid `t`, timestamps and cumulative or very long-window features; keep the clock scorer
in every results table as a leakage probe; state in the report that the benchmark's protocol makes
this shortcut available. The general name is shortcut learning; scanner, site and session-order
artefacts in neuroimaging and EEG are the same thing.

## F6

Let the two columns be identical, `x1 = x2 = x`. The prediction depends only on `w1 + w2`. OLS
therefore has infinitely many solutions; with near-identical columns it has one, but it is
ill-conditioned: tiny noise decides the split and coefficients can be large with opposite signs
*(computed: true relation `y = 3x`, second column = `x` plus noise of 0.001: OLS gave 5.80 and
-2.80)*.

Ridge adds `λ(w1² + w2²)`. For any fixed sum `w1 + w2 = c` the fit term is constant, and by
convexity `w1² + w2²` is smallest at `w1 = w2 = c/2`: the weight is shared equally *(computed:
1.4999 and 1.4999; the pair behaves like one feature with half the penalty)*. More generally ridge
shrinks most along low-variance directions of the feature matrix, and the difference between two
correlated features is such a direction.

Lasso's penalty `|w1| + |w2|` is constant along `w1 + w2 = c` (same signs), so it has no preference
and optimisation picks a corner: one coefficient carries everything, the other is zero *(computed:
2.95 and 0)*; which one is arbitrary and can flip between resamples.

Implication: with correlated features, a coefficient is not that feature's importance. Ridge
dilutes a shared effect across the group, lasso assigns it to an arbitrary member. Reason about
groups of features, or use elastic net, and check stability across resamples.

## F7

TPR (recall) and FPR are properties of the score distribution *within* each class, so they do not
change; ROC AUC, built from them, does not change. Precision mixes the classes:

`precision = π·TPR / (π·TPR + (1 − π)·FPR)`

*(Computed)* at `π = 0.35`: `0.28 / (0.28 + 0.065) = 0.81`. At `π = 0.01`: `0.008 / (0.008 + 0.099) =
0.075`. Same detector, same threshold: thirteen alerts out of fourteen are now false.

Average precision is an average of precisions and inherits this dependence; its chance level is the
prevalence itself. A benchmark AP at 35 % positives says little about a 1 % deployment. Report the
operating point (TPR, FPR), the deployment prevalence or the false alerts per hour, and recompute
precision for the target prevalence. For SKAB this is not hypothetical: sample-level prevalence is
about 0.35, far from a real monitoring setting.

The assumption (class-conditional distributions unchanged) is itself often false after deployment;
then nothing is guaranteed and you need labelled data from the new setting.

## F8

For `K` independent estimates with common mean `μ` and standard deviation `s`, the expected maximum
is `μ + s·m_K`, where `m_K` is the expected maximum of `K` standard normals: *(simulated)* 1.54 for
`K = 10`, 2.16 for `K = 40`, 2.51 for `K = 100`. The familiar `sqrt(2 ln K)` (2.15, 2.72, 3.03) is
an upper bound that is approached slowly. So with `s` = 2 points of accuracy, the best of 100
equally good models looks 5 points better than it is.

Where it appears, with the structural remedy:

1. **Hyperparameter search** scored on the data used for the final report. Remedy: select on
   validation or inner CV, report on untouched test data (or nested CV).
2. **Best epoch / early stopping / best checkpoint** chosen on the test curve. Remedy: a validation
   set for stopping.
3. **Best seed or best of several model families** reported as "our method". Remedy: report the
   distribution over seeds; the comparison protocol fixed in advance.
4. **Threshold** chosen to maximise F1 on test data; **feature subset** chosen on all data.
   Remedy: both are fitted parameters and belong to training/validation.

Two qualifications. Candidates are usually correlated (same data, similar models), which reduces
the inflation below the independent-case figure. And the bias is in the reported number: the
selected model is still a reasonable choice, you just cannot use the selection score as its estimate.

## C9

See `solutions/interview/set3/c9.py`. Strategy: collect row indices per group; shuffle the group
ids with the seed; stable-sort by size descending (so the seed only decides order among groups of
equal size, and among the many small ones); assign each group to the fold that currently has the
fewest rows. This is the greedy "largest first" heuristic for multiway number partitioning, which
is NP-hard in general; greedy is close to even when there are many groups and no single group
dominates. It cannot do better than whole groups allow: one group with half the rows makes one fold
large whatever you do.

Complexity: `O(n)` to index rows, `O(g log g)` to sort groups, `O(g·k)` for assignment (or
`O(g log k)` with a heap), `O(n·k)` to emit index lists.

scikit-learn: `GroupKFold` with its default `shuffle=False` is deterministic and balances fold sizes
greedily in the same way; since version 1.6 it also accepts `shuffle=True` with a `random_state`
(installed docstring, scikit-learn 1.9.1, checked). `StratifiedGroupKFold` also balances class
proportions; `GroupShuffleSplit` draws random group subsets without guaranteeing that each row is
tested once. A question worth asking the interviewer: balanced in rows, in groups, or in positive
cases? For the project, folds balanced by *family* matter more than by row count.

| Wrong answer (`set3_wrong/`) | Tests it fails | Why it is plausible |
|---|---|---|
| `c9_row_level` | 16 of 20, including "a group is on both sides" | The ordinary K-fold written from habit; the function still returns well-formed folds |
| `c9_ignores_seed` | the seed test | Deterministic greedy is correct for one split; the bug appears only when repeated splits are needed |
| `c9_unbalanced_dropped` | row balance; missing `ValueError` | Round-robin over shuffled groups looks fair but ignores group size; with `k` larger than the number of groups it silently yields empty folds |
