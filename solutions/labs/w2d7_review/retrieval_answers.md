# w2d7 - retrieval answers

Open only after all twelve questions have a written attempt. Each answer states the mechanism a
"solid" answer must contain, then common wrong answers and why they fail.

These answers were re-aligned with the final Week 2 lessons on 2026-11-21. Project numbers are the
ones reported in those lessons from runs on the real SKAB files. Where a statement was confirmed by running
code, that is said explicitly; everything else is reasoning, not a measurement. The diagnostic
database is **synthetic**: numbers quoted from it illustrate mechanisms only.

## 1. Grain and fan-out

The **grain** is what one row represents: "one row per customer", "one row per charge attempt".
A query result has a grain too, and stating it before writing the query is the main defence against
wrong aggregates.

Joining `customers` to `invoices` (many per customer) and to `tickets` (many per customer) produces
one row per *(invoice, ticket) pair* for each customer: a customer with `m` invoices and `k` tickets
contributes `m × k` rows, so `SUM(invoices.amount)` is multiplied by `k`. Executed on the diagnostic
database: for customer `C00679`, one of two customers with the most tickets (6), the three-table join sums to 2758.62 where the
true invoice total is 459.77, exactly six times too large. Customers with no ticket vanish entirely
under an inner join, which is the opposite error in the same query.

Two structurally different fixes:
* **Aggregate each child table to the target grain first** (one CTE per child, each `GROUP BY
  customer_id`), then join the pre-aggregated results to `customers` with `LEFT JOIN` and `COALESCE`.
* **Correlated scalar subqueries** in the select list, one per measure.

(`SUM(DISTINCT amount)` is not a fix: two invoices with the same amount collapse into one.)

| Common wrong answer | Why it fails |
|---|---|
| "Add `DISTINCT`" | `DISTINCT` on rows does not undo multiplication inside `SUM`; `SUM(DISTINCT ...)` removes legitimately equal amounts |
| "Use `LEFT JOIN` instead of `JOIN`" | Fixes the vanishing customers, not the multiplication |
| "Group by more columns" | Changes the grain of the output without removing duplicated measures |
| "The data has duplicates" | The tables are fine; the join created the duplication |

## 2. `ON` versus `WHERE` in a left join

A condition on `B` in the **`ON`** clause decides *which rows of `B` may match*; rows of `A` without
a match are kept, with NULLs for `B`. The same condition in **`WHERE`** is evaluated *after* the join:
for unmatched rows the `B` column is NULL, the predicate is UNKNOWN, the row is discarded, and the
left join has silently become an inner join. Executed on the diagnostic database: `customers LEFT
JOIN tickets ON ... AND t.category = 'billing'` keeps all 900 customers; moving the category
condition to `WHERE` leaves 210.

Use `ON` for "which matches count", `WHERE` for "which left rows do I want". The anti-join idiom
(`WHERE b.key IS NULL`) is the deliberate use of the post-join filter.

| Common wrong answer | Why it fails |
|---|---|
| "They are equivalent; the optimiser treats them the same" | True for inner joins only |
| "`WHERE` is just slower" | It is a semantic difference, not a performance one |

## 3. Counting and averaging with NULLs

* `COUNT(*)`: number of rows.
* `COUNT(col)`: number of rows where `col` is not NULL.
* `COUNT(DISTINCT col)`: number of different non-NULL values.
* `AVG(col)`: sum of non-NULL values divided by the count of non-NULL values; NULLs are ignored, not
  treated as zero. (Confirmed in SQLite: for values NULL, 2, 4 the results are 3, 2, and 3.0.)

Business examples: "customers billed this month" as `COUNT(*)` over invoices counts charge attempts
(retries inflate it; in the diagnostic data January 2025 gives 670 rows for 651 distinct customers);
"average resolution time" as `AVG` over a column that is NULL for open tickets describes resolved
tickets only, which looks better exactly when the backlog is growing; `AVG(COALESCE(col, 0))` answers
a different question again.

| Common wrong answer | Why it fails |
|---|---|
| "`COUNT(col)` counts distinct values" | It counts non-NULL rows |
| "`AVG` treats NULL as 0" | It excludes them from numerator and denominator |
| "`COUNT(DISTINCT a, b)` works everywhere" | Not portable (SQLite rejects it); pre-aggregate instead |

## 4. Default window frame, ties, and `WHERE`

With `ORDER BY` and no explicit frame, the frame is `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT
ROW`. `RANGE` works on *values of the sort key*, so "current row" includes all **peers** (rows with
the same `t`): every tied row gets the total including all of its peers. Confirmed in SQLite: for
`(k, v)` = (1,10), (1,20), (2,5) ordered by `k`, the default gives 30, 30, 35, while
`ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` gives 10, 30, 35.

To make a running total independent of ties: state `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`
**and** make the ordering total with a tie-breaker (`ORDER BY t, id`); `ROWS` alone gives a
well-defined frame but an arbitrary order among peers.

Window functions are evaluated after `FROM`, `WHERE`, `GROUP BY` and `HAVING`, on the rows that
survive them; `WHERE` therefore cannot refer to a value that does not exist yet. Compute the window
in a CTE or subquery and filter outside. Corollary: a `WHERE` in the same query changes what the
window *sees* (filter-before-window), which is the January-has-no-previous-month error.

| Common wrong answer | Why it fails |
|---|---|
| "The default frame is the whole partition" | That is the default *without* `ORDER BY` |
| "The default is `ROWS ... CURRENT ROW`" | It is `RANGE`; the difference appears only with ties, which is why it survives testing on clean data |
| "Use `HAVING` to filter on the window function" | `HAVING` is also evaluated before window functions |

## 5. Gaps-and-islands; as-of joins

**Technique A (row-number difference).** Within each experiment, among rows with the same `anomaly`
value, `t - ROW_NUMBER() OVER (PARTITION BY experiment_id, anomaly ORDER BY t)` is constant along a
contiguous run and changes when a run is interrupted. Group by `(experiment_id, that difference)`,
keep `anomaly = 1`, take `MIN(t)` and `MAX(t)`.

**Technique B (change flag + running sum).** Mark a row as a segment start when `anomaly = 1` and
`LAG(anomaly)` is 0 or absent; a running `SUM` of the start flags numbers the segments; group by it.

Both were executed on a small synthetic table and returned the same segments. Technique A requires
`t` to be a gap-free row index (true for the project's `t`, not for raw timestamps with sampling
gaps); technique B does not, and extends naturally to "treat a gap longer than N seconds as a break".

An **as-of join** attaches to each row of the left table the *most recent row of the right table at
or before the left row's time* (per key). Features need it because a feature for time `t` must use
the latest information that was actually available at `t`: an equality join finds nothing when
timestamps differ, and a join on "nearest" may pick a future row.

| Common wrong answer | Why it fails |
|---|---|
| "`GROUP BY experiment_id` and take min/max of `t` where anomaly = 1" | Merges separate segments into one; correct on SKAB only because each file has a single segment, a property you would be relying on silently |
| "Self-join each row to the next row" | Finds boundaries but does not number segments; quadratic if done without an index |
| "As-of means nearest in time" | Nearest can be in the future: look-ahead |

## 6. Data validation versus model evaluation; checks for SKAB

*Data validation* asks whether the **input is what the code assumes** (well-formed, plausible,
complete), before any model exists and again on every new batch and every request. *Model evaluation*
asks whether **predictions are good** on held-out data. A model can score well on corrupted data and
badly on valid data; neither substitutes for the other. Validation failures are data or pipeline
incidents; evaluation shortfalls are modelling results.

Three categories with examples (canonical names from `docs/maintainers/flowguard-spec.md`):
* **Schema / structure:** exactly the eight sensor columns plus `datetime`, `anomaly`, `changepoint`;
  numeric dtypes; `anomaly` in {0, 1}; no missing values; `experiment_id` and `family` well-formed.
* **Value plausibility:** physical ranges and units (voltage near mains level, non-negative
  vibration RMS and flow rate, temperatures in a plausible band); no constant or all-zero channel.
* **Temporal and structural integrity:** timestamps strictly increasing within an experiment, no
  duplicated timestamps, expected median sampling interval of 1 s, gaps reported; exactly one
  contiguous anomalous segment per labelled file; 34 labelled experiments plus the anomaly-free file.

"Fail loudly": the command exits non-zero with a message naming the check, the file and the offending
values, and writes a machine-readable report (`quality_report.json`); it never drops or repairs rows
silently. Per the spec, the check functions themselves *report* (`CheckResult(name, passed, detail,
severity)`) and the command decides: **error**-severity failures stop ingestion, **warning**-severity
findings are recorded and ingestion continues. The reference ingest on the real 35 files reports
11 checks, 0 errors and 1 warning (the sampling gaps).

**The gaps.** Ingestion should *detect, measure and record* them (per experiment: count, positions,
durations) and carry enough information forward (the timestamps, or a gap flag) for later steps to
decide. It should **not** interpolate across them, silently re-index as if sampling were uniform, or
discard the affected experiments: each of those is a modelling decision with consequences for rolling
windows (a 60-row window spanning a 247 s gap is not 60 s of history) and belongs in the feature
step, visibly. A gap is a *warning-level* finding here, not an error: the data is valid as recorded,
merely irregular (nine gaps longer than 5 s, in six experiments; about 5 % of all steps are 2 s). A
warning is a debt assigned to a later step, not something to ignore: detection delay must be measured
in seconds, not rows.

| Common wrong answer | Why it fails |
|---|---|
| "Validation is checking the model on validation data" | Confuses the two meanings of "validation" |
| "Fix the gaps by forward-filling during ingestion" | Invents data in the layer that is supposed to preserve the source |
| "Wrap ingestion in try/except and skip bad files" | Silent partial data; downstream numbers change without anyone knowing why |
| "Range checks from this dataset's min/max" | Circular: derived from the data they are meant to check, they pass by construction and encode outliers |

## 7. Provenance of an ingestion step

Record: the **source** (URL and the pinned upstream commit), the **licence** and citation, a
**SHA-256 per raw file** (the manifest written by `project/get_skab.py`), the **code version** that
ran (git commit) and its parameters, **row and experiment counts** in and out, the **hash of the
output** (`skab.csv`), the quality report, and the time of the run. With that, a second person can
establish identity of inputs, code and outputs, and a difference can be attributed.

The raw data is downloaded rather than committed because (a) its licence is GPL-3.0 and
redistribution inside this repository is a decision the course avoids, (b) Git is poor at large
binary or bulk data and history is permanent, and (c) identity is given by hashes and a pinned
source, which is stronger than "the copy that happened to be committed".

| Common wrong answer | Why it fails |
|---|---|
| "The download date is enough" | Upstream can change; only a pinned revision and hashes identify content |
| "Commit the CSV so everyone has the same file" | See (a)-(c); also invites silent local edits |
| "Record the path on my machine" | A path identifies a location, not content |

## 8. Units, splits and the manifest

*Unit of prediction:* one **timestamp** (a per-sample anomaly score computed from data up to that
time), later turned into alerts/events. *Unit of independence:* the **experiment** (`experiment_id`):
samples within an experiment are strongly autocorrelated and share its conditions, as samples within
a patient do. Splitting by row would put near-duplicates of each test sample in the training set and
estimate interpolation within a recording, not generalisation to a new one. `w2d4` measured it on the
development experiments: a random forest on raw sensor values scores ROC AUC 0.986 with rows shuffled
into folds and 0.849 with whole experiments held out (PR AUC 0.980 versus 0.841).

The manifest (`splits/v1.json`) contains: `version`, `seed`, `unit` (`experiment_id`), the list of
**test** experiments, the **development folds** (lists of experiment ids), the `reference_normal`
recording (`anomaly-free/anomaly-free`), and `protocol_b` (hold out the whole `other` family to
measure generalisation to unseen fault mechanisms). `validate_splits` rejects overlap between test
and folds and unknown ids. The frozen reference `v1` has 9 test experiments (4 `valve1`, 1 `valve2`,
4 `other`) and 25 development experiments in four folds (7/6/6/6).

`v1` has a known defect found after it was frozen: five pairs of files share identical rows
(1,290 rows; 235 with contradictory labels), and `v1` does not keep those experiments on the same
side. The correct response is the one the versioning exists for: do not edit `v1`; issue `v2` with
overlap groups kept together (`w3d1`) and treat earlier numbers as not comparable.

It is a versioned file rather than a seed because the split is part of the **experimental protocol**:
it must be identical across models, machines, library versions and months; it must be reviewable
(you can read which experiments are in the test set); and a change must be an explicit event (`v2`)
that invalidates comparison with earlier results. A seed gives none of that: library updates can
change what a seed produces, and every script can use its own.

| Common wrong answer | Why it fails |
|---|---|
| "The unit of prediction is the experiment" | The model scores timestamps; experiments are what must not be shared across splits |
| "Random row split with stratification handles it" | Stratification balances labels; it does nothing about dependence within an experiment |
| "`random_state=0` everywhere is a fixed split" | Until the data order, the library version or one script's seed differs; and nobody can inspect it |
| "Regenerate the split when results look odd" | That is selecting the test set on the outcome |

## 9. Point versus event labels; 35 % and 34

A **point-level** label says whether each *sample* lies inside an anomalous period (`anomaly`
column); metrics count samples. An **event-level** label treats each contiguous anomalous period as
*one* event; metrics ask whether and how quickly each event was detected, and how many false alerts
were raised per unit of normal operating time. A detector can be excellent on one and poor on the
other: long events dominate point metrics; one early hit per event satisfies event recall.

* **About 35 % anomalous samples:** the positive class is not rare at the sample level. "Always
  normal" has accuracy about 0.65 and "always anomalous" has precision about 0.35 with recall 1, so
  accuracy is uninformative and every point metric must be reported next to these trivial baselines
  (an uninformative scorer has average precision about 0.35 here). It also means sample-level
  prevalence is unlike most production monitoring, where anomalies are rare: results do not transfer
  to that regime without re-weighting or event-level reporting.
* **34 events:** event-level quantities are estimated from 34 units (fewer in any test split). The
  resolution of event recall on a test set of, say, 9 experiments is 1/9, and intervals are wide;
  differences between models of one or two events are not evidence. Results need intervals computed
  by resampling experiments (Week 3), and claims must be sized accordingly.

| Common wrong answer | Why it fails |
|---|---|
| "37,401 samples is plenty of data for tight intervals" | The independent units are 34 experiments, not 37,401 rows |
| "35 % positives means the problem is balanced, use accuracy" | Accuracy still hides the trade-off the stakeholder cares about and is dominated by segment length |
| "Point and event metrics are the same thing at different resolution" | They answer different questions and can rank models differently |

## 10. Causal features and look-ahead

A feature value for time `t` is **causal** if it is a function only of data with time `<= t` (or
strictly `< t`, if the current sample is not available when the prediction is made) within the same
experiment. That is the condition for the feature to be computable online, in the same way, at
serving time.

* Violates causality: `rolling(w, center=True)`, `shift(-k)`, `bfill()`, interpolation across a gap
  using the next value, a global or per-experiment z-score (`(x - x.mean()) / x.std()` over the whole
  recording), or a rolling window not grouped by experiment (history from the previous recording).
  Executed: with `center=True` and window 3, changing only later values changed the feature at
  position 5 from 5.0 to 36.3; with a trailing window it stayed 4.0.
* Leaks across the split without violating causality: fitting normalisation statistics
  (`ReferenceStats`), a scaler, PCA or feature selection on **all** experiments, including test ones.
  Each value still uses only its own past, but the transformation was estimated with test data. Fit on
  training experiments (or the anomaly-free reference) only.

**What mattered on SKAB (`w2d5`).** Centring the window raised pooled average precision by only
0.002-0.014; the choice of reference rows moved it from about 0.50 to about 0.73. Two lessons, and
they point in different directions. First, a small effect on one offline number does not make
look-ahead acceptable: the centred feature cannot be computed at serving time at all, so the reason
to forbid it is construction, not the size of the gain (the same argument as the scaler leak in
`w1d3`). Second, the largest lever was a quiet modelling decision (what "normal" is measured
against), which deserves the scrutiny usually spent on model choice.

**Implementation-independent test (prefix invariance):** compute features on a full series; then
alter or delete everything after time `t` (or truncate to the first `t+1` rows) and recompute; the
features for all times `<= t` must be **exactly equal**. Use several `t` and random data. Compare
exactly, not approximately: a tolerance could hide a small dependence on the future. Add the
companion test that altering experiment B leaves experiment A's features unchanged.

| Common wrong answer | Why it fails |
|---|---|
| "Read the code and check there is no `shift(-1)`" | Does not scale and misses indirect look-ahead (centred windows, global normalisation, interpolation) |
| "Check the output shape and for NaNs" | Unrelated to causality |
| "Causal features cannot leak" | Causality is within a series; train/test leakage is across series. They are separate conditions |
| "Compare to a slow reference implementation" | Useful differential test, but a reference with the same look-ahead passes |

## 11. Baselines, chance levels, thresholds

A trivial baseline (constant prediction, prior-only, a one-line rule such as a z-score threshold on
one sensor) answers "what does *no modelling* achieve under exactly this protocol?" It calibrates
the metric (what is a bad number here?), catches pipeline bugs (a model below the trivial baseline
signals an error; a trivial baseline scoring very high signals leakage or a degenerate metric), and
gives the denominator for any claim of improvement. Without it a number such as 0.72 has no meaning.

For an uninformative (random) scorer at prevalence `p`: expected **ROC AUC = 0.5**, independent of
`p`; expected **average precision ≈ p**, since precision is about `p` at every recall. (Simulated
with 200,000 samples at `p = 0.35`: AP 0.348, ROC AUC 0.498.) Consequences: an AP of 0.40 is barely
above chance at `p = 0.35` and enormous at `p = 0.01`; AP values are not comparable across
prevalences; ROC AUC can look comfortable under heavy imbalance while precision at any usable recall
is poor, because the false-positive *rate* divides by the very large number of negatives.

A **threshold** is a fitted parameter. It is chosen on training or validation data (within the
development folds), frozen, and then applied once to the test set. Choosing it on the test set
selects the best of many candidates using test labels, so the reported operating point is optimistic
and unavailable in deployment, where test labels do not exist. Threshold-free metrics (AP, ROC AUC)
do not excuse this: the shipped system makes decisions at one threshold.

**The clock baseline (`w2d6`).** On the 9 test experiments: constant score PR AUC 0.373 (the test
prevalence), burn-in z-score on flow rate 0.805, supervised logistic regression 0.827; and a scorer
that uses only elapsed time `t` reaches test F1 0.835, above every sensor baseline. The reason is the
experimental protocol: in 31 of 34 files the anomaly starts at row 550-600. So (a) the dataset lets a
model score well by learning *when in the recording it is*, which is worthless on a real plant;
(b) `t`, `datetime` and anything monotone in them are forbidden as features, and features that
accumulate over the recording (cumulative sums, expanding statistics, slow drifts) must be suspected
of encoding the clock; (c) the clock scorer stays in every results table as a *leakage probe*: a
model that does not clearly beat it has not shown that it detects faults.

| Common wrong answer | Why it fails |
|---|---|
| "PR AUC of a random model is 0.5" | That is ROC AUC; for PR it is the prevalence |
| "Baseline = logistic regression" | Useful as a *simple model* baseline, but the trivial baseline comes first and is what calibrates the metric |
| "Report best-F1 on the test set" | The maximisation over thresholds used test labels |
| "A high ROC AUC means the alerts will be precise" | Not under imbalance; look at precision at the recall you need |

## 12. The `band_power` test (delayed question from w1d5)

The two independent problems: (1) the **oracle is the code's own earlier output**, so the test can
only detect *change*, not error: if the notebook run had the factor-of-two bug, the test enforces
it; (2) **`rel=0.2` is not derived from anything**: it is far above numerical noise and has no
stated relation to the defects of interest (a factor of two happens to exceed it; a 15 %
normalisation error does not).

Redesign: input is a **pure tone at a bin frequency inside 8-12 Hz** with amplitude `A` (choose `fs`
and `N` so that, for example, 10 Hz is exactly a bin); the expected power is **`A²/2` from theory**;
tolerance about `rel=1e-9`; add **Parseval** on noise (total band power over `[0, fs/2]` equals the
variance) to pin the normalisation, and a tone at exactly 12 Hz to pin the half-open upper edge.

(This key is the one at the end of `solutions/labs/w1d5_testing_ml_code/assessment_answers.md`.)

| Common wrong answer | Why it fails |
|---|---|
| "Tighten the tolerance to 1e-6" and keep the copied value | Fixes problem 2, not problem 1: still a change detector |
| "Compare with `scipy.signal.welch`" | A different estimator with different scaling conventions; agreement needs its own derivation, and disagreement does not say who is wrong |
| "Use random noise and check the result is positive" | Detects almost nothing |
