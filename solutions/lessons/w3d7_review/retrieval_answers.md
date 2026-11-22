# w3d7 - retrieval answers

Open only after all twelve questions have a written attempt. Each answer states what a "solid"
answer must contain, then common wrong answers and why they fail.

**Alignment note.** These answers were written from the Week 3 lesson objectives, the project
specification and findings, and standard correct content, while the lessons themselves were still
being written. They will be re-aligned with the final lesson texts. Where a statement was confirmed
by running code, that is said explicitly; everything else is reasoning, not a measurement. Project
facts are from `project/README.md` (runs on the real SKAB files).

## 1. Five kinds of leakage

| Kind | What leaks | One-line example |
|---|---|---|
| **Target leakage** | A feature is a consequence or a restatement of the label | `days_since_last_login` measured after the customer cancelled; call `duration` for "will the client subscribe" |
| **Preprocessing leakage** | Statistics fitted on rows later used for evaluation | Scaler, imputer, PCA or feature selection fitted on all rows before the split |
| **Temporal leakage** | Information from after the prediction time | Centred rolling window; a feature table joined on the latest value rather than as of the prediction time; training on later periods than the test period |
| **Group leakage** | Dependent rows on both sides | Windows of the same experiment, patient or machine in train and test; duplicated rows across SKAB files |
| **Selection leakage** | The evaluation data chose something | Hyperparameters, threshold, features, early-stopping epoch or "best seed" chosen on the test set |

A grouped split prevents **group leakage only**. It leaves target leakage (the leaky column is in
every group), temporal leakage inside a group, preprocessing fitted before the split, and selection
on the test set all in place. It also does nothing about *shortcuts shared by every group*, such as
the fixed fault-onset time in SKAB, which is not leakage between train and test but has the same
effect on the usefulness of the number.

| Common wrong answer | Why it fails |
|---|---|
| "Leakage means the label is among the features" | That is one kind of five; the others involve no label column at all |
| "We split by patient/experiment, so there is no leakage" | Addresses one mechanism |
| "Leakage always inflates the metric" | Usually, not necessarily visibly: the scaler leak of `w1d3` changed no printed metric. The procedure is wrong regardless |

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

*Splits.* Files that share rows are not independent. If `other/12` is in training and `other/13` in
test, 349 test rows have been seen in training, with their labels. Experiments connected by shared
rows form **overlap groups** (`{anomaly-free, other/5}`, `{other/12, other/13}`,
`{other/2, other/3, other/4}`, `{other/10, other/11}`) and each group must stay on one side of every
split and inside one fold. The fault-free "reference" overlapping a labelled experiment also means
reference statistics are not independent of that experiment.

*Achievable performance.* For the 235 rows with contradictory labels, identical inputs carry both
labels: no function of the sensors can be right on both copies. Labels are noisy at the boundaries
of anomalous segments, so point-level metrics have a ceiling below 1 and small differences near
segment edges are not meaningful. It is also a warning about what the labels are: markings by the
experimenters, not ground truth.

*Why `v2`.* Results already computed refer to `v1`. Editing `v1` in place would make old and new
numbers silently incomparable while carrying the same name. A new version makes the change an
explicit, reviewable event, and `validate_splits` can then reject any manifest that separates a
group.

| Common wrong answer | Why it fails |
|---|---|
| "Drop the duplicated rows" | Removes the symptom in the table and leaves two recordings of the same physical period on both sides; also breaks the time series |
| "1,290 of 46,806 rows is under 3 %, ignore it" | The unit is the experiment, not the row: 8 of the 14 `other` experiments and the fault-free reference are involved |
| "Fix v1, the old numbers were wrong anyway" | Then nobody can tell which numbers used which split |

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

When train and test rows come from the **same continuous series**, a feature computed over a window
of `w` samples (or a label defined over a horizon `h`) makes rows near the boundary share raw data.
**Purging** removes from training the rows whose windows or label horizons overlap the test period.
An **embargo** additionally drops a stretch *after* the test period before training resumes, to
cover serial correlation that outlasts the window. The gap must be at least the longest feature
window plus the label horizon, in *time* (here seconds, because of the sampling gaps).

This project splits by whole experiment and computes features per experiment, so no window crosses
a split boundary and purging is not needed between experiments. It becomes necessary if (a) a single
experiment's timeline is split (for example, burn-in rows for fitting and later rows for scoring
with a rolling feature spanning the boundary), (b) features are computed across concatenated
experiments, or (c) the same physical period appears in two files, which is the overlap-group
problem under another name.

| Common wrong answer | Why it fails |
|---|---|
| "Purging is only for finance" | It is needed wherever windows overlap a boundary |
| "A gap of one sample is enough" | The gap must cover the longest window and horizon |
| "Shuffle after windowing to decorrelate" | Shuffling distributes the overlap to both sides; it is the cause |

## 6. Nested cross-validation

The **inner loop** runs the whole selection procedure (hyperparameter search, threshold choice,
feature selection) on an outer training set only. The **outer score** is computed on the outer test
fold, which took no part in selection, so the average outer score estimates the performance of *the
procedure* "search, then fit" on new data. Different outer folds may select different
configurations; that is information about the stability of the choice, not a bug.

You **ship** the result of running the same selection procedure once on all development data. No
single outer-fold model is special.

The best inner score is the maximum over candidates of noisy estimates, so it is biased upward as an
estimate of the selected candidate's performance (question 7).

| Common wrong answer | Why it fails |
|---|---|
| "Report the best cross-validated score from the grid search" | Selection optimism |
| "Ship the model from the best outer fold" | Chosen by its test score, and trained on less data |
| "Nested CV picks the best hyperparameters" | It estimates performance of the selection procedure; picking is a separate, final run |
| "Outer folds chose different settings, so the method is broken" | Often the candidates are indistinguishable; say so and prefer the simplest |

## 7. Thresholds are fitted; optimism grows with K

A threshold is a number chosen by looking at scores **and labels** to optimise a criterion, exactly
as a weight is. It therefore has to be chosen on training/validation data, frozen, and carried to
the test set unchanged; maximising F1 over thresholds on the test set reports the best of many
candidates.

For `K` candidates of equal true quality whose scores have noise standard deviation `s`, the
expected best score exceeds the truth by `s` times the expected maximum of `K` standard normals:
about 1.5 `s` for `K = 10`, 2.2 `s` for 40, 2.5 `s` for 100 (simulated in the authoring session);
the growth is logarithmic, roughly `s·sqrt(2 ln K)` as an upper bound. Correlated candidates (the
usual case) inflate less. With few independent test units `s` is large, so on 9 experiments even a
modest search can manufacture several points.

| Common wrong answer | Why it fails |
|---|---|
| "The threshold is not a parameter, it is a post-processing choice" | It is chosen using labels; that is fitting |
| "AP/ROC AUC are threshold-free, so no problem" | The deployed system uses one threshold; and model selection by AP on test data is still selection |
| "Optimism grows linearly with the number of trials" | Logarithmically; the first few trials cost most |

## 8. Point-level versus event-level

Using the project's convention (one event = one contiguous anomalous segment; a prediction is a
thresholded score):

* **Event recall:** fraction of true events for which at least one alert falls inside the matching
  window of the event.
* **Detection delay:** time from event onset to the first alert that matches it, in seconds;
  reported for detected events only, alongside the recall, since missed events have no delay.
* **False alarms per hour:** number of alert *episodes* that match no event, divided by the hours of
  normal operation scored. Episodes, not rows: a false alert lasting 30 s is one interruption.

*Good at point level, bad at event level:* a detector that flags the late, obvious part of every
long segment has high sample recall and precision but a long delay; or one that flags the three
longest events completely and misses six short ones. *Opposite:* a change detector that fires for
a few samples at each onset has event recall near 1 and short delay but point-level recall near
zero, since it is silent for the rest of each segment.

Delay in **seconds**: six SKAB files have gaps of up to 247 s, so a row count across a gap is not a
duration; and an operator's requirement is stated in time.

The exact matching rule (how early an alert may be, whether alerts just after the segment count, how
adjacent alerts merge) changes the numbers and must be stated next to them.

| Common wrong answer | Why it fails |
|---|---|
| "Event metrics are point metrics averaged per event" | They ask different questions and can rank models oppositely |
| "Report mean delay over all events, counting misses as zero" | Rewards missing events; report recall and delay together |
| "False alarm rate = FP rows / normal rows" | That is the point-level FPR; an operator counts interruptions per unit time |
| "Point-adjust: if any sample in a segment is hit, count the whole segment as detected" | Inflates point metrics so far that a random scorer looks good on long segments; if used it must be labelled as such |

## 9. Cluster bootstrap with nine experiments

Procedure: compute the per-experiment ingredients once (scores and labels, or per-experiment
counts). Repeat `B` times (say 2,000): draw 9 experiments **with replacement** from the 9 test
experiments; recompute the metric on the drawn set as a whole (pool the rows of the drawn
experiments, a repeated experiment counting twice); store it. Report the point estimate on the
original test set with a percentile interval of the bootstrap values, and state "resampling unit:
experiment, n = 9".

Resampling rows is wrong because rows within an experiment are strongly autocorrelated: a
row bootstrap treats about 10,000 rows as 10,000 independent observations and returns an interval
several times too narrow. The variation that matters is *which experiments you happened to get*.

What remains doubtful with 9 clusters: the bootstrap approximates the population by the sample, and
9 units describe it coarsely. Percentile intervals from so few clusters tend to be too narrow; any
one experiment is absent from about 35 % of resamples (`(8/9)^9 = 0.346`, computed), so a single
unusual experiment makes the distribution lumpy; metrics such as event recall take few distinct
values; some resamples of a family-stratified question contain no experiment of a family. The
interval is a lower bound on honest uncertainty, to be reported as such. Stratifying the resampling
by family keeps the family mix fixed, which answers a slightly different question; say which you did.

| Common wrong answer | Why it fails |
|---|---|
| "Bootstrap the 10,000 test rows" | Ignores dependence; interval far too narrow |
| "Average the per-experiment metric and use a t-interval over rows" | Unit confusion again |
| "With 2,000 resamples the interval is precise" | More resamples reduce Monte Carlo error, not the error from having 9 units |
| "Report mean ± std over folds" | Folds share training data; the spread is not a standard error and is not an interval for the test estimate |

## 10. Paired comparison

Both models are scored on the same experiments, and experiments differ in difficulty: an easy one is
easy for both. Their scores are therefore positively correlated, and the variance of the
*difference* is much smaller than the two separate intervals suggest. Overlapping individual
intervals do not imply "no difference", and non-overlap is far stricter than needed.

Report the interval for **Δ = metric(A) − metric(B)**: on each bootstrap resample of experiments,
compute both models' metric on the *same* resample and store the difference; take the percentile
interval of the differences (and, if you like, the fraction of resamples with Δ > 0).

If the interval contains zero: "A and B are not distinguishable on these n experiments (Δ = x,
95 % interval [l, u])", then decide on other grounds (simplicity, latency, cost) and say so. Do not
write "B is slightly better" or "no difference exists": the data are compatible with both signs.

| Common wrong answer | Why it fails |
|---|---|
| "The two intervals overlap, so there is no difference" | Ignores the pairing; too conservative |
| "A t-test on per-row errors" | Rows are not independent |
| "A won on 5 of 9 experiments, so A is better" | A sign count on 9 units has almost no power; report it only as description |
| "Not significant, therefore equal" | Absence of evidence with 9 units is weak evidence of equality |

## 11. From errors to an error analysis

A list of misclassified samples is raw material. Analysis needs:

1. **The right unit:** group errors into missed events, late detections and false-alarm episodes,
   not rows.
2. **Slices:** break the metric down by variables known before looking (fault family, experiment,
   position relative to onset, presence of sampling gaps, sensor regime) and look for slices that
   are much worse than the aggregate, with their sizes.
3. **Reading examples:** plot the worst cases per slice, raw signals and scores together, and write
   one line per case about the apparent cause.
4. **A taxonomy:** a small set of failure categories with definitions that a second person could
   apply (for example: slow-onset faults flagged late; normal transients after a gap flagged;
   label-boundary disagreements; unseen fault mechanism).
5. **Ranking by impact:** count and cost per category, so the list says what to fix first, and which
   categories are *label or data* problems that no model change will fix.
6. **A hypothesis and a check per top category**, to be tested on development data.

The leak: error analysis done on the **test set**, followed by changes motivated by what was seen,
turns the test set into training data by way of the analyst. Do the analysis on development
experiments (out-of-fold predictions); look at test errors once, at the end, to describe, not to
iterate.

| Common wrong answer | Why it fails |
|---|---|
| "Plot the confusion matrix" | One aggregate; no slices, no causes, no ranking |
| "Look at the 20 highest-loss samples" | Dominated by one or two experiments and by label noise; not representative |
| "We fixed every error we found on the test set" | The reported test number is now optimistic |
| "Feature importance explains the errors" | It describes the model, not where and why it fails |

## 12. `NOT IN` with a NULL (delayed question from w2d1)

`technicians.site_id` is NULL for external contractors. `x NOT IN (a, b, NULL)` means
`x <> a AND x <> b AND x <> NULL`. The last comparison is UNKNOWN, so the conjunction is never TRUE
(it is FALSE if `x` equals a listed value, UNKNOWN otherwise), and `WHERE` keeps only TRUE rows.
One NULL in the subquery empties the result. *(Confirmed in SQLite 3.53.1 on a three-row example:
`NOT IN` returned no rows; each rewrite below returned the two unmatched rows.)*

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
