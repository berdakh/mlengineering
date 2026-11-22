# Interview set 4 - rubrics (part A) and worked answers (part B)

**Order of use (Weeks 3-5 rule).** After the first timed, recorded attempt read **part A only** and
score what is on the recording. Second attempt for anything below "Demonstrated". Then part B.

Reference code: `solutions/interview/set4/c3.py`; wrong answers the tests reject:
`solutions/interview/set4_wrong/`.

Verified in the authoring session (Python 3.13.18, pytest 9.1.1):
`SET4_DIR=solutions/interview/set4 python -m pytest interview/set4_tests -q` gives 12 passed in
under 1 s; the shipped stub fails all 12; each wrong answer fails at least one test (table at the
end). Numbers marked *(simulated)* or *(computed)* were produced by running code in that session.

**Where the project facts come from.** Every dataset fact and reference number below is from
`project/README.md` and the Week 2 lessons, which report runs on the real SKAB files. At the time of
writing the reference results had **no confidence intervals** (they are the subject of `w3d5`) and
no event-level numbers (`w3d4`). A strong answer says what has not been measured. If your own
project has those numbers, use yours.

Evidence levels per prompt: **Demonstrated**, **Partial**, **Not yet**.

---

# Part A - rubrics

## E1 - the five-minute walkthrough (self-scoring sheet)

Tick only what is audible on the recording.

**Protocol: could a listener reconstruct it?**

- [ ] What is predicted, per what unit (an anomaly score per timestamp, from past data only)
- [ ] What the data is, in one sentence, with its size in *independent units* (34 labelled experiments, one event each), not only rows
- [ ] How it was split and why (whole experiments; a fixed test set; development folds; the manifest is versioned)
- [ ] Where thresholds and hyperparameters were chosen (development data only), and that the test set was used once
- [ ] Which metrics, and why more than one (point-level and event-level answer different questions)
- [ ] The baselines, including a trivial one, with at least one number

**Trust: did you volunteer the weak points before being asked?**

- [ ] Uncertainty: few events, so intervals are wide (or: "I have not computed intervals yet")
- [ ] At least one dataset problem found and what was done about it (duplicated rows across files with contradictory labels; elapsed time predicts the label; the fault-free recording is not a clean reference)
- [ ] What the numbers do *not* show (prevalence is 35 %, a laboratory testbed, one event per recording, no claim about a real plant)
- [ ] A clear statement of what you would do next with more time

**Delivery**

- [ ] Finished within five minutes without rushing the last minute
- [ ] Numbers given with their conditions ("on 9 held-out experiments"), never a bare "92 %"
- [ ] No more than one sentence about model architecture before the protocol was explained

Levels: **Demonstrated** = all six protocol ticks, at least three trust ticks, delivery acceptable.
**Partial** = protocol reconstructible but weak points only on prompting. **Not yet** = a listener
could not say how the test set was formed.

The commonest failure for people coming from research: four minutes on the model, one on the
evaluation, nothing on limitations.

## E2 - follow-ups: what a strong answer contains

1. **Why by experiment.** Samples within an experiment are autocorrelated and share its conditions;
   the experiment is the independent unit, as the patient is in clinical data. Gives the measured
   gap: row-level folds ROC AUC 0.986 versus 0.849 with experiments held out (`w2d4`, development
   experiments, random forest on raw sensors).
2. **0.02 with 34 events.** Not confident at all without a paired, experiment-level interval. Test
   sets hold about 9 experiments; one event is 0.11 of event recall. States the right tool (resample
   experiments, compare models on the same resamples) and declines to rank.
3. **35 % prevalence.** Concedes the point: at sample level this is closer to segmentation of a
   long anomalous period than to rare-event detection. Precision does not transfer; computes or
   describes the fall under lower prevalence; proposes event-level metrics and false alarms per hour
   of normal operation, which do not depend on how long the fault lasts.
4. **Simplest competitive thing.** A burn-in z-score on one sensor (flow rate): test PR AUC 0.805
   against 0.827 for supervised logistic regression and 0.373 for a constant. The gap that any
   complex model must justify is therefore small, and it has to be weighed against uncertainty.
5. **Learning the schedule.** Takes it seriously, because it is true of this dataset: the anomaly
   starts at row 550-600 in 31 of 34 files and a score equal to elapsed time reaches test F1 0.835.
   Says which features are forbidden and that the clock scorer is kept as a leakage probe.
6. **Problems with the dataset.** The duplicated rows (1,290 rows in five file pairs, 235 with
   contradictory labels; the fault-free file overlaps `other/5`) and the consequence for splits
   (overlap groups kept together, manifest v2). Also sampling gaps up to 247 s in six files.
7. **Threshold.** Chosen on development experiments, frozen, applied once to test. At deployment the
   threshold should come from an alert budget (false alarms per day the operator will tolerate) and
   be re-examined when the input distribution moves; no labels are available at that moment.
8. **Would an operator be happy.** Point-level F1 rewards flagging most of a long segment; an
   operator wants each fault caught once, early, with few false alerts. Names event recall, detection
   delay in seconds and false alarms per hour.
9. **No future information.** By construction (trailing windows, per-experiment, statistics fitted
   on training or burn-in rows) and by test: perturb everything after time `t`, recompute, features
   up to `t` must be bit-identical (`w2d5`). Notes the limit of the claim: causality within a series
   says nothing about protocol shortcuts such as the clock.
10. **What will not hold.** At least three, with reasons: prevalence and therefore precision;
    onset timing; one clean fault per recording; a single testbed and sensor set (no unit-to-unit
    variation); labels placed by the experimenters rather than taken from maintenance records.

## T1 - effective sample size

* **Must:** `n_eff ≈ n(1 − ρ)/(1 + ρ)`, about 32 for `n = 600`, `ρ = 0.9`.
* **Must:** where it comes from: the variance of the mean includes the covariances; summing the
  autocorrelations `ρ^k` gives the factor `(1 + ρ)/(1 − ρ)`.
* **Must:** one training consequence and one evaluation consequence (see part B).
* **Should:** says the formula is for the *mean* and that other statistics have other factors.

## T2 - forecast-residual detector

* **Must:** step: one spike at the change, then silence; drift: a constant small residual equal to
  the slope, never flagged; stuck sensor: residual exactly zero, the *least* anomalous score.
* **Must:** a concrete fix (a forecaster or reference that does not adapt instantly: compare with a
  slower baseline level, or accumulate residuals as CUSUM does) and its cost (delay; drift in normal
  operation becomes a false alarm; state to maintain).
* **Should:** states the general principle: a forecaster that adapts quickly forecasts the anomaly
  too.

## C3 - time-window statistics

* **Must:** all tests pass.
* **Must:** names the cancellation problem of `E[x²] − E[x]²` and avoids it (running mean and sum
  of squared deviations updated on add *and* remove, or sums of offset-centred values).
* **Must:** correct half-open boundary and time-based expiry.
* **Should:** discusses the gap case: after a long gap the window holds one value, the standard
  deviation is undefined, and a z-score detector should report "warming up", not a number.

---

# Part B - worked answers

## E1 - an example answer (about 4.5 minutes spoken)

"The task is to raise an alert soon after a pump test rig starts behaving abnormally. The model
gives an anomaly score for every one-second sample, using only data up to that second.

The data is the SKAB benchmark: 34 recorded experiments from one laboratory rig, eight sensors,
about 37,000 rows. The number that matters is 34: each experiment contains exactly one fault, and
samples inside an experiment are strongly correlated, so I have 34 independent examples, not 37,000.

I split by whole experiment. A fixed test set of 9 experiments was written to a versioned file
before any modelling; the other 25 are development data, in four grouped folds. Thresholds and all
tuning use development experiments only, and the test set is scored once. Splitting by row instead
would have been badly optimistic: I measured ROC AUC 0.99 with shuffled rows against 0.85 with
experiments held out.

I report two kinds of metric. Point-level precision-recall, because it is easy to compare. And
event-level: was each fault caught, how many seconds after onset, and how many false alerts per
hour of normal running, because that is what an operator experiences.

On baselines: a constant score gives PR AUC 0.37, which is just the prevalence. A z-score on a
single sensor, normalised on the first minutes of each run, gives 0.81. Supervised logistic
regression gives 0.83. So the simple baseline is already close, and I do not yet have intervals;
with 9 test experiments I expect them to be wide enough that I cannot rank those two.

Three things limit how far you should trust this. First, I found that some rows are duplicated
across files, a few with contradictory labels, so the first version of my split let related
experiments fall on both sides; I issued a second version that keeps them together. Second, the
faults are injected at almost the same time in every recording. A 'detector' that only reads the
clock gets F1 0.84. I banned time-like features and keep that clock baseline in every table as a
check. Third, 35 % of samples are anomalous, which is nothing like a real plant, so precision would
not carry over.

So my honest summary: the pipeline and protocol are sound and reproducible from a command; the
dataset supports conclusions about methods relative to each other on this rig, not about field
performance. Next I would add experiment-level bootstrap intervals and test on the held-out fault
family."

*Why this works:* protocol before model; the independent unit stated early; every number with its
condition; three limitations volunteered; an explicit boundary on the claim.

## E2

The rubric entries in part A are the answers in compressed form. Three deserve the full argument.

**Q2.** A difference of 0.02 in point-level PR AUC between two models evaluated on the same 9
experiments is not interpretable on its own. Rows are not independent, so a row-level standard
error would be far too small. The right computation resamples *experiments* with replacement,
recomputes both models' metric on each resample, and looks at the distribution of the *difference*
(paired, because both models see the same experiments and their errors are correlated). With 9
units the interval will be wide; if it contains zero, the statement is "indistinguishable on this
data" and the choice falls to cost and simplicity. I have not seen an interval for these two models,
and I would say that.

**Q3.** Precision at prevalence `π` is `π·TPR / (π·TPR + (1 − π)·FPR)`. A detector with TPR 0.80
and FPR 0.10 has precision 0.81 at 35 % and 0.075 at 1 % *(computed)*. Nothing about the model
changed. That is why I report TPR and FPR, false alarms per hour of normal operation, and
event-level recall, which survive a change in how much of the time the plant is faulty.

**Q5.** It is exactly what a model would do here if allowed. Onset is at row 550-600 in 31 of 34
files. Any feature that grows with elapsed time (a long rolling mean of a warming temperature, a
cumulative sum, the row index) lets the model learn "late in the recording means faulty". Correct
grouped splits do not prevent it, since the regularity is the same in train and test. My defences:
forbid such features; keep an elapsed-time scorer as a baseline that an honest model must clearly
beat; and check that scores stay flat on fault-free data as time passes.

## T1

For a stationary series with variance `σ²` and autocorrelation `ρ_k`,

`Var(mean) = (σ²/n) · [1 + 2 Σ_{k=1}^{n−1} (1 − k/n) ρ_k]`.

For AR(1), `ρ_k = ρ^k`, and for `n` large relative to the correlation time the bracket tends to
`1 + 2ρ/(1 − ρ) = (1 + ρ)/(1 − ρ)`. So `n_eff = n(1 − ρ)/(1 + ρ) = 600 × 0.1/1.9 ≈ 32`
*(simulated with 20,000 AR(1) series: 31.9)*. Ten minutes of 1 Hz data carries the information of
about thirty independent readings about the mean.

Consequences. *Training:* reference statistics from a short burn-in are much noisier than the row
count suggests, and a covariance matrix of eight sensors estimated from 300 correlated rows is
estimated from perhaps tens of effective samples, which is why shrinkage matters for a Mahalanobis
detector. *Evaluation:* row-level standard errors and significance tests are invalid; neighbouring
rows are near-duplicates, so a random row split leaks; uncertainty must be computed over
experiments. The formula above is for the mean; variances and correlations have their own, usually
larger, effective sample sizes, so treat 32 as an order of magnitude.

## T2

`r_t = |x_t − x_{t−1}|` is the absolute first difference.

* **(a) Step of size Δ.** One large residual at the change, then the forecast has adopted the new
  level and residuals return to noise *(computed on a step of 50 noise standard deviations: exactly
  one residual above threshold)*. The fault persists; the alert lasts one sample. Point-level recall
  over the anomalous segment is near zero even though the event was "detected".
* **(b) Linear drift with slope `b` per sample.** Every residual equals `b` plus noise. If `b` is
  below the noise in differences it is never flagged, however far the level eventually moves.
* **(c) Stuck sensor.** Residual exactly zero: the most normal-looking score possible. A flat line
  needs its own check (variance over a window below a floor), which is a data-quality rule as much
  as a model.

It can never flag an anomaly defined by *level* rather than by *change*. The underlying principle:
a forecaster that adapts quickly forecasts the anomaly as well.

Fix: measure deviation from a reference that does not follow the signal immediately. Options: the
z-score against a burn-in or slowly updated baseline level; a slow EWMA as forecaster; or keep the
fast residual and accumulate it (CUSUM: `S_t = max(0, S_{t−1} + r_t − k)`), which integrates a small
persistent shift into a large statistic. Costs: detection delay grows with the smoothing; slow
legitimate changes of regime (a setpoint change, warming up) now accumulate into false alarms; the
detector has state that must be initialised and reset after gaps. This is the delay versus
false-alarm trade-off that window length controls in `w2d5`.

## C3

See `solutions/interview/set4/c3.py`. It keeps a deque of `(t, x)`, a running mean and a running sum
of squared deviations `M2`, updated with Welford's recurrences on insertion and their inverses on
removal:

```
add x     (n is the count after adding):    d = x − mean;  mean += d/n;  M2 += d·(x − mean)
remove x  (n is the count after removing):  d = x − mean;  mean −= d/n;  M2 −= d·(x − mean)
```

`std = sqrt(max(M2, 0)/(n − 1))`. Each value is appended once and popped once, so all operations are
O(1) amortised; memory is O(values in the window).

**Why not sums of `x` and `x²`.** `Σx² − (Σx)²/n` subtracts two numbers of size `n·x²` to obtain one
of size `n·var`. With `x ≈ 10⁶` and a variance near zero, the terms are about `10¹³·n` and agree to
all sixteen available digits, so the difference is rounding noise of either sign. *(Computed: for a
constant 1,000,000.1 and a 50-value window, the naive formula gave a negative variance at 476 of 499
steps, so `sqrt` raises or returns `nan`.)* If you must keep plain sums, subtract a fixed offset
(the first value) from every `x` first.

Removal recurrences also accumulate error, more slowly; a long-running service recomputes from the
deque occasionally. Clamping `M2` at zero guards the square root.

**After a gap.** A 250 s gap with a 60 s horizon leaves one value: mean equals that value, standard
deviation undefined. That is correct, and a detector built on it must treat `len < n_min` as "no
opinion", not as zero deviation or as an alarm. A row-count window would instead mix data from
before and after the gap, which is the bug this prompt is about.

| Wrong answer (`set4_wrong/`) | Tests it fails | Why it is plausible |
|---|---|---|
| `c3_row_count_window` | gap, boundary, brute-force comparison, timing (9 of 12) | `rolling(60)` habits: treats the horizon as a number of rows |
| `c3_population_std` | known-answer and brute-force comparison (8 of 12) | Divides by `n`; also returns 0.0 for a single value, which a z-score then divides by |
| `c3_rescan` | timing only | Correct values, recomputed over the window on every call; passes every small test |
