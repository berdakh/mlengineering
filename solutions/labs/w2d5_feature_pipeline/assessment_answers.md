# W2D5 — assessment answers

Open after writing your own answers. Numbers in Q1 were computed, not estimated.

## Q1

(a) `delay ≈ w·θ/Δ = 40 × 0.6 / 1.2 = 20` samples.
(b) `σ/√w = 0.8/√40 = 0.126`. The threshold 0.6 is 4.74 of these: a one-sided Gaussian tail of
about 1 in a million per sample.
(c) Positive autocorrelation inflates the variance of the mean by about `(1+φ)/(1−φ) = 9`, so the
standard deviation rises by about 3 (exact value for *w* = 40: 2.83, giving 0.358). The same
threshold is now only 1.68 standard deviations away; the per-sample exceedance probability goes
from about 1e-6 to about 0.047. The delay in (a) is unchanged. A threshold set from the
white-noise formula would alert constantly.

*Common incorrect answers.*
- "Delay is w/2 = 20 because the window is half full." Right number, wrong reason: it is 20
  because θ/Δ happens to be 1/2. With θ = 0.3 the delay is 10.
- "Autocorrelation reduces noise in the mean because neighbouring samples agree." It is the
  reverse: agreeing neighbours carry less independent information, so averaging removes less.
- Answering (c) by re-deriving σ/√w with a smaller σ. The marginal σ is unchanged; the
  *effective sample size* is what shrinks (40 × 0.2/1.8 ≈ 4.4).

## Q2

The perturbation test covers one function. Future information can still enter through:

1. **Statistics fitted on future or held-out rows**: reference means, a scaler, a PCA basis or
   a threshold estimated on the whole table, including validation/test experiments or the
   later part of the same recording.
2. **Selection**: windows, feature subsets or thresholds chosen by looking at test-period
   performance.
3. **Labels and preprocessing upstream**: a tidy table whose values were interpolated across
   gaps, de-trended over the whole recording, or filtered zero-phase before the feature step.
4. **The split itself**: random row splits with overlapping windows put near-duplicates of test
   rows in training.

Any two, with the mechanism, is a solid answer. *Common incorrect answer:* "the model could
still overfit" — true and unrelated to temporal leakage.

## Q3

Two faults. (1) `s.mean()` and `s.std()` are computed over the *whole* experiment, so the
z-score at time *t* depends on everything after *t*, including the anomalous segment itself;
it cannot be computed while the experiment is running. (2) Because the anomalous segment is
about a third of each recording, it shifts the mean and inflates the standard deviation that
normalise it: the feature partly removes the very effect to be detected, and the amount removed
depends on the label. It also makes every experiment's z-scores average exactly zero, erasing
information about experiments that are abnormal throughout.

Causal alternatives: calibrate on the first *k* seconds of each experiment and hold those
statistics fixed (assumes the start is normal and representative; costs *k* seconds without
scores), or an expanding/long-EWMA baseline (assumes slow drift is not the fault; a slowly
developing fault is absorbed into the baseline). Naming the assumption is required for "Solid".

*Common incorrect answer:* "it's fine because the groupby prevents leakage between experiments".
The groupby fixes cross-group contamination only; the leak is along time, inside the group.

## Q4 (design choice)

(i) Offline training table: NaN is defensible. Partial windows have a different variance from
full ones, so early rows would be systematically noisier examples of "normal" and a model or
threshold would learn the row index. Dropping 5 % of rows is cheap; `rows_since_reset` makes
the drop explicit and lets you report how much was dropped. The cost is that the model is never
evaluated on start-up behaviour, so nothing can be claimed about it.

(ii) Online service that must answer from the first reading: NaN cannot be the final answer.
Acceptable designs: return an explicit "warming up" status instead of a score for the first
*w* seconds (honest, but the service is blind after every restart and after every gap);
or score with the shortest full window available, with thresholds scaled for that window
(always answers, more code and more thresholds to validate); or partial windows with a variance
correction `×√(n/w)`. Whatever is chosen must be what the training table did, otherwise
training and serving differ. A strong answer notes that restarts and gaps make warm-up a
recurring state, not a one-off, and that it should be monitored.

*Common incorrect answers:* "fill with 0" (after standardisation 0 means perfectly normal);
"forward/backward fill" (backward fill is look-ahead).

## Q5

Stale: someone changes `std` from ddof=1 to ddof=0, or fixes a bug in the slope, and forgets to
bump `FEATURE_VERSION`. Keys are unchanged, the old table is served, and a model is trained on
features the current code would not produce. Nothing fails.

Commit hash worse: a README edit or a change to the API module produces a new commit; every
feature table is recomputed (minutes here, hours at scale) and, more seriously, two runs that
*should* be comparable now carry different feature keys, so "same features?" can no longer be
answered by comparing keys. Uncommitted changes are also invisible to a commit hash.

For this project either can be defended. A reasonable choice: explicit version in the key,
*plus* the commit hash recorded in `meta.json` for audit, *plus* a test that pins a small
golden feature table so that a semantic change without a version bump fails CI. Hashing the
source of `features.py` is a middle path (changes on any edit to that file, including comments).

## Q6

The proposal confuses "does not move this metric" with "is computable". Pooled sample-level
average precision is dominated by the hundreds of samples deep inside each anomalous segment,
whose ranking a half-window shift does not change; only samples near the edges move. The
quantity centring corrupts is *when* the score rises relative to onset, which that table does
not measure (the synthetic example shows the shift is −w/2 samples). So the table cannot show
that causality "does not matter"; it shows the metric is insensitive to it. Independently of
any metric, a centred feature cannot be produced by the service, so a model trained on it has
no deployable counterpart. The comparison with the reference-row effect is still worth keeping:
it tells you where the larger modelling risk on this dataset is.

*Common incorrect answer:* "0.014 is within noise, so both are equivalent." No interval was
computed, and equivalence of an offline metric is not the criterion.

## Interview rep — rubric

| Aspect | Solid answer |
|---|---|
| `sliding_max` | Monotonic deque of indices; each index pushed and popped at most once, hence O(n) time, O(w) space. Heap-based O(n log n) with lazy deletion earns partial credit if the complexity is stated correctly. Recomputing `max` per window is O(n·w) and does not meet the task. |
| `StreamingStats` | Ring buffer or deque plus running sum and sum of squares; subtract the value leaving the window. O(1) per update. |
| Numerical risk | Catastrophic cancellation in `E[x²] − mean²` when the mean is large relative to the spread; drift from repeated add/subtract over long streams. Mitigations: subtract a reference offset, Welford-style windowed update, periodic recomputation from the buffer, clamp at zero. |
| Tests | Brute-force comparison on random input; decreasing input (deque stays full); ties; `w = 1`; `w > len`. For the stats: comparison with recomputation; a large-offset input. |
| Communication | States the invariant ("values at the deque's indices are decreasing") before coding. |

Reference implementation and tests: `interview_rep/sliding.py`, `interview_rep/test_sliding.py`
(7 tests pass). Connection to the unit: `StreamingStats` is the online form of the rolling mean
and standard deviation, and its state is exactly what a `StreamScorer` must hold in Week 5.
