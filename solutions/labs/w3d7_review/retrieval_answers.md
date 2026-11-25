# w3d7 - retrieval answers

Open only after all twelve questions have a written attempt. Each answer states what a "solid"
answer must contain, then common wrong answers and why they fail.

**Alignment.** Checked against the final Week 3 lessons and handbook sections H6.1, H6.3-H6.7, H7.2
and H7.3 on 2026-11-22. Project numbers are quoted from those lessons' recorded runs on the real SKAB
files, all on the frozen split manifest `v2` (7 test, 27 development experiments). Where a statement
was confirmed by running code here, that is said explicitly; everything else is reasoning.

## 1. Kinds of leakage

The w3d1 taxonomy sorts leaks by *where* the unavailable information sits: in a feature, in which rows
are on which side, in a fitted step, or in a choice. Eight kinds:

| Kind | One-line example | Detection probe |
|---|---|---|
| **Target / proxy** | `reminders_sent` on an invoice, written after the payment was late | single-feature AP/AUC near 1; ask *when is this column written?* |
| **Temporal aggregate** | a customer's late-payment rate computed over the whole export, including later invoices | recompute point-in-time; old rows change when new data arrives |
| **Shortcut / protocol** | elapsed time in SKAB (onset near row 570); ledger-number range; EEG session or site | single-feature probe; **clock probe**; `time_monotone_columns` |
| **Group** | windows of one experiment, machine or patient on both sides | grouped versus random split gap |
| **Duplicate / near-duplicate** | the 1,290 SKAB rows that appear in two files | row hashing across sides; nearest-neighbour distance test-to-train |
| **Temporal** | training rows later than test rows; windows crossing the boundary | forward versus random split; purge test (w3d2) |
| **Preprocessing** | scaler, imputer, selector or PCA fitted on all rows | change evaluation rows and see whether anything else moves |
| **Selection** | threshold, hyperparameters or best seed chosen on test | count test looks; best-of-N against a fresh hold-out |

A grouped split prevents **group leakage only**, and duplicate leakage only if duplicated units are
grouped together (which is why v2 keeps overlap groups on one side). It leaves target, temporal
aggregate and shortcut features in every group, preprocessing fitted before the split, and selection
on the test set in place. The clock shortcut is the clearest SKAB case: it is shared by every
experiment, so no split removes it; it must be forbidden by name (`audit_features`) and checked for in
disguise.

| Common wrong answer | Why it fails |
|---|---|
| "Leakage means the label is among the features" | One kind of eight |
| "We split by patient/experiment, so there is no leakage" | Addresses one mechanism |
| "Leakage always inflates the metric visibly" | The w1d3 scaler leak changed no printed metric, and w3d1's v1/v2 comparison on the shared test experiments moved 0.899 to 0.900. The procedure is wrong regardless |
| "No probe fired, so there is no leak" | Probes find known kinds; the feature-availability audit is the real defence |

## 2. Prevention by construction

A `Pipeline` passed to `cross_val_score`/`GridSearchCV` is **refitted on each training fold**: every
step's `fit` sees training rows only, and the fitted transformation is then applied to the held-out
rows. Correctness no longer depends on anyone remembering the order of operations, and the same
object does preprocessing and prediction at serving time.

Inside it must go everything that **learns from data**: scaling, imputation statistics, encoders
(especially target encoding), feature selection, dimensionality reduction, resampling for class
balance (which must apply to training folds only), and any learned threshold if it is tuned in the
search. Stateless row-wise transforms (a log, a ratio of two columns) are safe outside.

What a pipeline cannot prevent: **target leakage** (a column that should not exist at prediction
time), **temporal leakage created upstream** when the feature table was built, a **wrong splitter**
(row-wise where groups are needed), and **selection on the test set** by the person running it.

| Common wrong answer | Why it fails |
|---|---|
| "Pipelines make leakage impossible" | They fix one mechanism |
| "Fit the scaler on train, transform test by hand; same thing" | Correct once; inside cross-validation and search it must happen per fold, which is what gets forgotten |
| "Oversample before splitting so both sets are balanced" | Copies or interpolations of test rows enter training |

## 3. Duplicated rows with contradictory labels

*Splits.* Files that share rows are not independent. Experiments connected by shared rows form
**overlap groups** (`{anomaly-free, other/5}`, `{other/12, other/13}`, `{other/2, other/3, other/4}`,
`{other/10, other/11}`), and each group must stay on one side of every split and inside one fold. The
v1 manifest of w2d4 broke this: 370 test rows were also in development, 178 of them with the opposite
label.

*Achievable performance.* Where identical inputs carry both labels, no function of the sensors is
right on both copies. Labels near segment boundaries are noisy, so point-level metrics have a ceiling
below 1 and small differences near segment edges are not meaningful. The labels are the experimenters'
markings, not ground truth (w3d6 reports such units separately).

*Why `v2`, and why move rather than redraw.* Results already computed refer to `v1`; editing it in place
would make old and new numbers silently incomparable under one name. The repair moved only what had to
move (`other/11` and `other/12` left the test set; `other/4` changed development fold) and kept every
other test experiment, so the test set was not re-chosen after results had been seen. Redrawing would
have been a fresh look at a new test set, chosen by someone who already knew how models behave: a form
of selection. `validate_splits` now rejects any manifest that separates a group.

What the comparison showed (w3d1): v2 test PR-AUC is higher than v1 (logistic regression 0.900 vs
0.827), but on the seven experiments that are in test under both manifests the difference is 0.899
vs 0.900. The headline change comes from the test set changing, not from removing the leak; v1 was
wrong by construction, and the size and sign of its error depend on the model.

| Common wrong answer | Why it fails |
|---|---|
| "Drop the duplicated rows" | Breaks the time series and leaves the same physical period on both sides |
| "1,290 of 46,806 rows is under 3 %, ignore it" | The unit is the experiment: 8 of the 14 `other` experiments and the fault-free reference are involved |
| "Fix v1, the old numbers were wrong anyway" | Then nobody can tell which numbers used which split |
| "Draw a fresh v2 with the overlap constraint" | Re-chooses the test set after results were seen |
| "The leak cost 0.07 PR-AUC" | Compares different test sets |

## 4. What each validation scheme asks

* **Grouped** (hold out whole experiments, machines, patients, customers): *how well does the
  procedure work on a new unit from the same population?* This is "a detector trained on past
  experiments is run on a new experiment".
* **Temporal / forward-chaining** (train on the past, test on the following period): *how well does
  a model trained now work later, on the same units, as conditions drift?* This is "the same machine
  next month".
* **Combined** (test units are new *and* later): *a new unit installed in the future.* The most
  demanding and the smallest in data; often what deployment really is.

Choosing a scheme is choosing which claim you make. Random K-fold answers "how well do I interpolate
among rows I have already seen the neighbours of", which is rarely a deployment question.

| Common wrong answer | Why it fails |
|---|---|
| "Temporal validation is stricter, so always use it" | It does not hold out units; on data with strong unit identity it can be more optimistic than a grouped split |
| "Grouped K-fold handles time automatically" | A fold can train on later experiments and test on earlier ones; fine if experiments are exchangeable, wrong if there is drift across them |

## 5. Purging and embargo

When train and validation rows come from the **same continuous series**, a feature over a window of
`w` rows and a label over a horizon of `h` rows make rows near the boundary share raw samples. For a
validation block `[a, b]` (w3d2, section 2.5):

* **purge** the training rows in `[a - (w-1+h), a-1]`: their features and labels reach into the block;
* **embargo** the training rows in `[b+1, b + (w-1+h)]`: their feature windows reach back into it.

So each side removes `w - 1 + h` rows (`required_purge(30) == 29`, `required_purge(40, 30) == 69`), in
rows of a regular series or the equivalent *time* where sampling has gaps. In forward chaining there is
nothing after the block to embargo, and the purge is the `gap` argument. In the w3d2 demonstration on
unpredictable labels, a one-sided buffer still left an AUC of 0.518; both sides at `w-1+h` gave about
0.50: the embargo is not optional in blocked K-fold.

This project splits by whole experiment and computes features per experiment, so no window crosses a
split boundary and no purge is needed between experiments. It becomes necessary when one experiment's
timeline is split (blocked folds within an experiment, as in w3d2's within-experiment scheme with purge
= embargo = 29), when features are computed across concatenated experiments, or when the same physical
period appears in two files (the overlap groups again).

| Common wrong answer | Why it fails |
|---|---|
| "Purging is only for finance" | Needed wherever windows or labels cross a boundary |
| "A gap of one sample is enough" | The gap must cover `w - 1 + h` |
| "Purging removes temporal leakage" | It removes shared raw samples; slow drift and protocol shortcuts remain |
| "Shuffle after windowing to decorrelate" | Shuffling spreads the overlap to both sides; it is the cause |

## 6. Nested cross-validation

The **inner loop** runs the whole selection procedure (search, one-SE choice, refit, threshold) on the
outer training folds only. The **outer score** is computed on the outer fold, which never fitted a
model, scored a candidate or moved a threshold, so the mean outer score estimates the performance of
*the procedure*. Different outer folds may select different configurations (on SKAB: boosting in
three folds, logistic regression in one); that is information about stability, not a bug.

You **ship** the result of running the same procedure once on all development data, then look at the
test set once with its threshold frozen. No outer-fold model is special.

The best inner score is a maximum over noisy estimates, so it is biased upward (question 7).

| Common wrong answer | Why it fails |
|---|---|
| "Report the best cross-validated score from the grid search" | Selection optimism |
| "Ship the model from the best outer fold" | Chosen by its own test score, trained on less data |
| "Nested CV gives the performance of the final model" | It estimates the procedure; the final model is one draw from it |
| "Outer folds chose different settings, so the method is broken" | Often the candidates are indistinguishable; say so and prefer the simplest |

## 7. Thresholds are fitted; optimism grows with K

A threshold is chosen by looking at scores **and labels** to optimise a criterion; it is a
one-parameter model. It is chosen on development (out-of-fold) scores, frozen, and the test result is
reported at that frozen threshold, never at the test-optimal one.

For `K` equally good candidates with independent errors `N(0, σ²)`, the optimism of the best is `σ`
times the expected maximum of `K` standard normals: 0.56σ for K = 2, 1.54σ for K = 10, 2.25σ for
K = 50, growing like `σ√(2 ln K)` (w3d3, section 2.2). With correlation `ρ` between candidates the
shared part does not change the winner, and the optimism shrinks by about `√(1−ρ)`. With few test
units `σ` is large, so even a modest search manufactures several points.

On SKAB (w3d3): best development CV PR-AUC 0.891, one-SE choice 0.878, **nested estimate 0.850 ±
0.032**. The nested estimate is the number for the procedure; the 0.891 is the best of 24 noisy
estimates. The single test look gave 0.922, above the nested estimate: with 7 test experiments that is
within noise, and it does not mean the nested estimate was pessimistic.

| Common wrong answer | Why it fails |
|---|---|
| "The threshold is post-processing, not a parameter" | It is chosen using labels; that is fitting |
| "AP/ROC AUC are threshold-free, so no problem" | The deployed system uses one threshold, and choosing a model by AP on test is still selection |
| "Optimism grows linearly with the number of trials" | Slowly, like `√ln K`; the first trials cost most |
| "The one-SE rule removes the optimism" | It changes the choice, not the bias of the number attached to it |
| "Test came out higher, so report test" | One look at 7 experiments; report it as the test result next to the nested estimate |

## 8. Matching, event metrics, and why point metrics mislead

*The course's default matching rule (w3d4, section 2.4).* An alarm is judged by its **start**. It
detects an event if it starts inside the event (or at most `early_tolerance` rows before it; default
0). The earliest such alarm is the **hit**; later alarms in the same event are **redundant** (neither
true nor false). An alarm that starts during normal operation is a **false alarm**, even if it runs on
into the event: it carried no news when the fault began. An alarm starting before the labelled onset is
therefore a false alarm unless a stated tolerance covers it.

* **Event recall** = detected events / true events.
* **Event precision** = hits / (hits + false alarms); redundant alarms excluded.
* **Detection delay** per event: from the true onset to the moment the hit is raised (including the
  confirmation time of a minimum-duration rule), and **infinite for a missed event**. Report the
  median and a high percentile over *all* events, misses included; averaging over detected events
  only rewards missing hard cases.
* **False alarms per hour of normal operation** = false alarms / hours outside true events, with the
  count and hours reported, and an upper bound: zero false alarms in the 1.22 test hours is still
  compatible with 2.46 per hour.

*Point and event disagree.* In w3d4's synthetic example, "long event only" has the best point F1
(0.899) and finds 1 of 10 events; "onset only" has point F1 0.066 and finds 10 of 10 at zero delay. On
SKAB the flow-rate z-score finds all 7 test events but as 469 separate alarms, 290 of them false. With
a minimum duration and gap merging it drops to 17 alarms and finds only 3 of 7, because at its low
threshold the merged alarm often starts before the onset and becomes a false alarm; Mahalanobis, worst
on point F1, is the best post-processed detector (5 of 7 events). Post-processing and threshold must be
chosen together.

*Timestamps.* Six SKAB files have gaps up to 247 s, so row counts are not durations: hours from rows
come out too small by about a factor 1.1 on SKAB, and an operator's requirement is stated in time.

| Common wrong answer | Why it fails |
|---|---|
| "Any overlap counts as detection" | Credits an alarm that started before the fault with a zero-delay detection |
| "Report mean delay over detected events" | Censoring error: missing hard events lowers the delay |
| "False alarm rate = FP rows / normal rows" | Point-level FPR; an operator counts interruptions per hour |
| "Point-adjust is the standard protocol" | It credits a whole segment for one hit; a random scorer looks strong on long segments (w3d4, 3.2) |
| "Event metrics fix leakage" | The elapsed-time clock finds 3 of 7 test events (7 of 7 under any-overlap) |

## 9. Cluster bootstrap with seven experiments

Procedure (w3d5): keep per-experiment scores and labels. Repeat `B` times (say 2,000): draw 7
experiment ids **with replacement** from the 7 test experiments; build the pseudo-test set from all
rows of the drawn experiments (an experiment drawn twice appears twice); recompute the metric on it;
store it. Report the estimate on the real test set with the percentile interval, and state "unit of
resampling: experiment, 7 clusters". If an overlap group were in the test set, the group would be the
cluster; the frozen v2 test set has none, so 7 experiments are 7 clusters.

Resampling rows is wrong because rows within an experiment are strongly correlated: the effective
sample size is close to the number of clusters, not the number of rows. On SKAB the row bootstrap gave
intervals about 3-7 times too narrow.

What remains doubtful: with `G = 7` there are only `C(13, 7) = 1,716` distinct resamples, any one
experiment is missing from about 34 % of them (`(6/7)^7 = 0.340`), and in w3d5's simulation a nominal
95 % percentile interval covered the truth only about 87-88 % of the time with 7 or 9 clusters. BCa
helps a little (it moved the lower limit by about 0.025 for the flow-rate baseline) and cannot rescue 7
clusters. The interval is a lower bound on the honest uncertainty, and the report says so.

| Common wrong answer | Why it fails |
|---|---|
| "Bootstrap the test rows" | Ignores dependence; far too narrow |
| "With 2,000 resamples the interval is precise" | More resamples reduce Monte Carlo error, not the error from having 7 units |
| "Report mean ± std over CV folds" | Folds share training data; not an interval for the test estimate |
| "A resample with no positives is an error; drop it" | It is a property of having few clusters; handle and document it (w3d5 lab) |

## 10. Paired comparison

Both models are scored on the same experiments, and experiments differ in difficulty: an easy one is
easy for both. The scores are correlated, so the variance of the *difference* is much smaller than the
two separate intervals suggest (w3d5's synthetic example: unpaired interval for the difference
[−0.063, +0.090], paired [+0.0155, +0.0191]).

Report the interval for **Δ = metric(A) − metric(B)**: in each bootstrap replicate draw one set of
cluster ids and apply it to both models; store the difference; take the percentile interval. A
sign-flip permutation test on per-cluster differences is an exact alternative for small `G` (with 7
clusters its smallest possible p-value is 2/128 = 0.016).

If the interval contains zero: "A and B are not distinguishable on these 7 experiments (Δ = x, 95 %
interval [l, u])", then decide on other grounds and say so. If methods disagree, report both. On SKAB
the Mahalanobis versus flow-rate comparison had a bootstrap interval excluding zero (−0.125
[−0.278, −0.013]) while the sign test (p = 0.45) and permutation test did not reject; w3d5 reports it as **not established**. The minimum detectable
difference with 7 clusters is about 0.25 PR-AUC; with 30 about 0.10.

| Common wrong answer | Why it fails |
|---|---|
| "The two intervals overlap, so there is no difference" | Ignores the pairing |
| "A t-test on per-row errors" | Rows are not independent |
| "A won on 5 of 7 experiments, so A is better" | A sign count on 7 units has almost no power |
| "Not significant, therefore equal" | With 7 clusters almost nothing is significant; absence of evidence is weak evidence |

## 11. From errors to an error analysis

An error analysis produces a short **ranked list of failure modes**, each with a size, a cost and a
hypothesis about its cause (w3d6). Steps:

1. **Work on development data** (out-of-fold predictions). Reading test errors and then changing the
   model turns the test set into a second development set.
2. **A unit table:** one row per experiment with its metrics; every later step is a group-by on it,
   and an undefined metric is missing, not zero.
3. **Slices written before looking** (family, regime, time since start, gaps, label conflicts),
   with sizes and cluster-aware intervals or counts.
4. **Error kinds** from runs of wrong rows: miss, late, boundary, fragment (alarm dropped out),
   pre-onset, post-event, false alarm. Each points to a different fix.
5. **Separate label noise from model error:** report units with contradictory labels separately.
6. **Rank by frequency × cost × fixability**, stating the assumptions; frequency caps the gain.
7. **A hypothesis and a test per top mode**, on other development units.

Two ways it misleads. *Slice hunting is multiple testing:* in w3d6's simulation, 24 machines with
identical recall 0.80 and 80 slices produced a "worst slice" averaging 0.729, and 45 % of searches found
one at least that bad. *Simpson's paradox:* a detector can be better in every regime and worse pooled.
(And the leak: error analysis on the test set.)

| Common wrong answer | Why it fails |
|---|---|
| "Plot the confusion matrix" | One aggregate; no slices, causes or ranking |
| "Look at the 20 highest-loss samples" | Dominated by one or two experiments and by label noise |
| "We found a slice at 0.73, fix it" | Expected by chance after 80 slices; test it on other units first |
| "We fixed every error we found on the test set" | The reported test number is now optimistic |

## 12. `NOT IN` with a NULL (delayed question from w2d1)

`technicians.site_id` is NULL for external contractors. `x NOT IN (a, b, NULL)` means
`x <> a AND x <> b AND x <> NULL`. The last comparison is UNKNOWN, so the conjunction is never TRUE
(it is FALSE if `x` equals a listed value, UNKNOWN otherwise), and `WHERE` keeps only TRUE rows.
One NULL in the subquery empties the result. *(Confirmed on the `w2d1` database `maintenance.db`, SQLite 3.53.1: 2 of 12
technicians have a NULL `site_id`; `NOT IN` returns 0 rows, `NOT EXISTS` returns 2.)*

Rewrites:

```sql
-- anti-join with NOT EXISTS: NULLs in the subquery simply never match
SELECT s.* FROM sites s
WHERE NOT EXISTS (SELECT 1 FROM technicians t WHERE t.site_id = s.site_id);

-- left join and keep the unmatched rows
SELECT s.* FROM sites s
LEFT JOIN technicians t ON t.site_id = s.site_id
WHERE t.tech_id IS NULL;
```

(`NOT IN (SELECT site_id FROM technicians WHERE site_id IS NOT NULL)` also works, but depends on
everyone remembering the filter.) In the left-join form, test a column that cannot be NULL in a
matched row, such as the primary key.

| Common wrong answer | Why it fails |
|---|---|
| "The data must have no such sites" | The query, not the data |
| "`NULL <> x` is true" | It is UNKNOWN; three-valued logic |
| "Use `IN` and negate the result set with `EXCEPT`" | Workable, but misses the mechanism, and `EXCEPT` also de-duplicates |
