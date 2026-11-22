# W2D5 — Reproducible feature generation without look-ahead

**Unit id:** `w2d5` · **Week 2, day 5** · **Content status:** Execution verified (see [Verification record](#verification-record))
**Handbook:** [H7.1 Windowing and causality](../../handbook/ch07_timeseries_grouped_modeling/h7_1_windowing_and_causality.md) · [H3.4 Deterministic feature pipelines](../../handbook/ch03_sql_data_pipelines/h3_4_deterministic_feature_pipelines.md)
**Data:** real SKAB recordings for the lab run and one worked example (`python project/get_skab.py`); SYNTHETIC series for the other worked example and for every automated check.

---

## 1. Purpose

**Primary objective.** Build the project's feature step so that it is *causal* (a feature at time
*t* uses nothing after *t* and nothing from another experiment), *train-only* in its statistics,
*deterministic*, and *cached by content*, with tests that would catch each of those properties
being broken.

**What you will learn**

- Why a centred or zero-phase window is look-ahead leakage in a deployed detector, and how to test for it.
- The quantitative tradeoff between window length, noise suppression and detection delay.
- Handling warm-up rows, time gaps and experiment boundaries deliberately.
- Separating `fit` from `transform` for feature statistics, and why *which rows you fit on* is a modelling decision.
- Making a pipeline step a pure function of (data, code version, parameters) and addressing its output by a hash of those.

**Why an applied ML engineer needs it.** Features are where most time-series leakage lives, and
where training and serving most often diverge: the offline table was built with a convenient
whole-series operation, the online service can only see the past. A model evaluated on features
the service cannot compute has no valid evaluation. Feature code is also the part of an ML
system that is re-run most often, so "did this table come from the current code and
parameters?" has to be answerable without re-reading the code.

**Prerequisites.** [w2d4](../w2d4_problem_framing_splits/README.md) split manifest (a snapshot of
`flowguard.splits` is in the lab starter); [w1d5](../w1d5_testing_ml_code/README.md) for the
metamorphic-test idea used throughout; [w1d4](../w1d4_config_logging/README.md) for provenance.
You have computed sliding-window features on EEG for years; that is assumed, not taught.

**Time budget — essential path 2 h**

| Activity | Time |
|---|---|
| Read section 2 (do not skip 2.2, 2.4, 2.5) | 25 min |
| Worked examples: run both, read the output against the text | 20 min |
| Guided lab, tasks 1–5 | 60 min |
| Assessment questions (written answers) | 15 min |

**Optional extension — up to 1 h:** independent challenge (40 min), interview rep (15 min).

**Deliverable.** `flowguard.features` and the `flowguard features` command in your project,
passing this unit's checks, plus a five-line note in your project README stating: the windows
chosen, the warm-up and gap policy, and which rows the reference statistics are fitted on and why.

**Completion criteria.** `python wb.py check w2d5` passes; you ran the command on the real data
twice and saw a cache hit; your note exists. The independent flag requires the challenge without hints.

---

## 2. Conceptual explanation

### 2.1 Intuition: a feature is a promise about what was knowable

Write a feature as a function of the series and a time index, `f(x, t)`. In a deployed detector
the value used at time *t* can depend only on `x[..t]`. A feature that satisfies this is
**causal**. Everything convenient in offline analysis tends to violate it: centred moving
averages, zero-phase filtering, whole-recording z-scoring, interpolation across a gap,
`df[col].rolling(w)` on a table holding several recordings.

You already hold the two halves of this idea. Offline EEG analysis uses `filtfilt`
(zero-phase, non-causal: each output sample depends on the whole recording), while a real-time
BCI loop must use a causal filter and accept its group delay. An offline pipeline evaluated
with `filtfilt` features overstates what the online decoder will do. Rolling features on
sensor data are the same problem with a different name, and in industry the "online loop" is
the normal case rather than the special one.

### 2.2 Precise terms

- **Trailing (causal) window** of length *w* at row *i*: rows `i-w+1 … i`.
  **Centred window:** rows `i-⌊w/2⌋ … i+⌊w/2⌋`. A centred window is a trailing window shifted
  into the future by about `w/2` samples; that shift is the leak.
- **Warm-up:** the first `w-1` rows of a segment, where a full trailing window does not exist.
- **Segment:** a maximal run of rows of one experiment with no time gap longer than `max_gap_s`.
- **Reference statistics:** means and standard deviations (or any fitted quantity: PCA basis,
  regression coefficients of one sensor on another) estimated on a fixed set of rows and then
  *applied* to all rows. Estimating is `fit`; applying is `transform`.
- **Point-in-time correctness:** the feature table row for time *t* equals what a service that
  had only received data up to *t* would have computed. This is the property the perturbation
  test in the lab verifies.

```text
 time →            t-5  t-4  t-3  t-2  t-1   t   t+1  t+2  t+3
 causal, w = 5           [ ■    ■    ■    ■    ■ ]                      uses rows ≤ t: buildable online
 centred, w = 5                    [ ■    ■    ■    ■    ■ ]            uses t+1, t+2: exists only offline
 warm-up (first rows)    fewer than w rows exist → NaN (min_periods = w), never a silently shorter window
 gap or new experiment   ··· ■ ■ ║ ■ ■ ···    the window must not reach across ║ (reset, or define it in seconds)
```


### 2.3 The window-length tradeoff, with numbers

Take noise with standard deviation σ and a step fault of height Δ at time *t₀*. A trailing mean
of length *w* is, after onset, a mixture: `k` post-fault samples and `w-k` pre-fault samples, so
its expected value is `Δ·k/w`. With an alert threshold θ on the mean, the expected crossing is at

```
delay ≈ w · θ / Δ        samples                                  (1)
```

For independent noise the trailing mean has standard deviation

```
sd(mean_w) = σ / √w                                                (2)
```

so the false-alert rate at threshold θ falls quickly with *w*. Longer windows buy silence with
latency. Two corrections matter in practice:

1. **Autocorrelation.** Sensor noise is rarely white. For AR(1) noise with coefficient φ the
   variance of the mean of *w* samples is approximately `σ²/w · (1+φ)/(1-φ)` for large *w*: the
   window holds roughly `w(1-φ)/(1+φ)` *effective* samples. With φ = 0.9 a 60-sample window is
   worth about three independent samples (measured in the worked example: 3.7). Equation (2)
   then overstates the noise suppression badly. This is the same effective-sample-size
   reasoning you apply when overlapping EEG epochs are not independent trials.
2. **Centred windows.** Shifting the window `w/2` into the future changes (1) to
   `w·θ/Δ − w/2`. For θ < Δ/2 that is *negative*: the alert precedes the fault. Offline this
   reads as an excellent detector. It is a detector that cannot be built.

Other features follow the same logic with different constants. A rolling standard deviation
responds to a variance change after a comparable fraction of *w*. A rolling slope detects
drifts and has higher variance than the mean, of order `12σ²/w³` for white noise, so it needs longer
windows. An EWMA with span *s* (`α = 2/(s+1)`) weights the past geometrically, has no hard
warm-up edge and can be updated in O(1) state per sensor, which is why it is common in services;
its step response reaches fraction `1-(1-α)^k` of Δ after *k* samples.

![Line chart: the median detection delay of a causal rolling mean grows from 2 to 14 samples as the window grows from 10 to 60, tracking w times theta over delta; the centred window shows minus 2 to minus 15](figures/delay_vs_window.svg)

*SYNTHETIC data (the simulation of the first worked example, 400 series per window length). The blue
line is equation (1); the orange line is the same quantity minus w/2. Regenerate with
`python lessons/w2d5_feature_pipeline/figures/make_figures.py`.*


### 2.4 Boundaries: warm-up, gaps and experiments

Three places where a window can reach data it should not.

**Warm-up.** Options: return NaN until the window is full, or use a partial window
(`min_periods=1`). Partial windows give noisier early values whose variance differs from the
rest (equation 2 with a smaller *w*), which a threshold tuned on full windows will misread.
This unit uses NaN and exposes `rows_since_reset`, so the decision about early rows is made
explicitly by the consumer (drop, or score with a separate rule). The price is real: on the
project data 2,488 of 46,806 rows (5.3 %) have at least one NaN feature with windows up to 60.

**Time gaps.** A window of 30 *rows* is a window of 30 seconds only if sampling is regular.
Seven SKAB files contain a gap longer than 5 s, the largest 247 s. A row-count window that
bridges a four-minute hole computes a "30-second slope" across unrelated regimes. Policy in
this unit: a gap longer than `max_gap_s` starts a new segment and windows restart (with 5 s:
9 resets inside experiments, 44 segments in total). The alternative, time-based windows, is the
subject of the challenge.

**Experiment boundaries.** The tidy table stacks 35 recordings. `tidy[col].rolling(w)` without
a `groupby` fills the first `w-1` rows of each experiment from the end of the previous one.
With a split by experiment that is cross-group contamination, possibly across the train/test
boundary. It is the exact analogue of an epoching routine that lets a window span two
subjects' recordings after concatenation.

### 2.5 Train-only statistics, and the decision hidden inside them

Standardising a feature needs a mean and a standard deviation. Computing them on the whole
table uses test rows; computing them on the frame being transformed makes every frame look
normal on average and makes single-row scoring impossible. The rule is the one you apply to
scalers inside cross-validation folds: **fit on designated rows, store the result, apply
everywhere.** `ReferenceStats` in the lab is that rule made into an object that can be saved
with a model.

The rule does not tell you *which* rows. The second worked example shows that this choice
matters more on this dataset than causality does. The separate fault-free recording looks like
the obvious reference, yet the normal part of most labelled experiments lies tens of
reference standard deviations away from it in several sensors (median −57 for both the second
accelerometer and flow rate). The reference recording was taken at a different operating
point. A z-score against it mostly measures "which recording is this". Fitting on the normal rows of
*training experiments* is the defensible default for a split by experiment; per-recording
calibration on an initial normal period is another option with its own assumptions (it is what
a BCI session calibration does). Choosing among them is evaluation work for
[w2d6](../w2d6_baselines_metrics/README.md) and Week 3. What this unit fixes is the mechanism, so the
choice is one argument to `fit` and not a property scattered through the code.

```mermaid
flowchart LR
    subgraph FIT["fit: once, on designated rows only"]
        TR["reference rows<br/>(training experiments, normal operation)"] --> ST["ReferenceStats<br/>mean, sd per feature"]
    end
    ST --> SAVE[("saved with the model")]
    subgraph APPLY["transform: everywhere, with the stored state"]
        A1["training rows"] --> Z["z = (x - mean) / sd"]
        A2["validation / test rows"] --> Z
        A3["one live row in the service"] --> Z
    end
    SAVE --> Z
    TE["test rows"] -. "never reach fit" .-x ST
```


### 2.6 Determinism and content-addressed caching

Make the feature step a pure function:

```
features = F(data, parameters, code)
```

and name its output by a hash of the three arguments. Then "is this table current?" becomes a
key comparison, re-running with unchanged inputs is a no-op, and a model's provenance can
record one key instead of a description. The pieces:

- **Data identity:** SHA-256 of the input file bytes (cheap here; for large data, hash a manifest of part hashes).
- **Parameters:** serialised canonically (`json.dumps(..., sort_keys=True)`, lists normalised so
  that `--windows 30 10` and `--windows 10 30` are the same request).
- **Code identity:** an explicit `FEATURE_VERSION` you bump when the *meaning* of a feature
  changes. A git commit hash is the alternative; it invalidates the cache on every unrelated
  commit, which is safe and wasteful. An explicit version is efficient and relies on discipline. State
  which one you use.
- **Atomicity:** write the metadata file last and treat its presence as "entry complete", so a
  crash mid-write is not mistaken for a hit.

Determinism has to be checked, not assumed: the lab verifies byte-identical output from two
computations. Sources of nondeterminism in feature code are usually unordered iteration
(`set`, `groupby` on unsorted keys with `sort=False` and changing input order), parallel
reductions, and float formatting differences between library versions.

```mermaid
flowchart LR
    D["input data<br/>sha256 of file bytes"] --> K
    P["parameters<br/>canonical JSON, sorted"] --> K
    C["code identity<br/>FEATURE_VERSION"] --> K
    K["cache key = hash(data, parameters, code)"] --> Q{"entry with this key<br/>and its metadata file exists?"}
    Q -->|"yes"| HIT["reuse: no computation"]
    Q -->|"no"| RUN["compute features"] --> W["write table, then metadata LAST<br/>(metadata present = entry complete)"]
```


### 2.7 Industry example

A payments team builds "transactions by this card in the last hour" for fraud scoring. Offline,
an analyst computes it with a self-join on a daily table and a `BETWEEN` on the timestamp that
includes the current transaction's own later-arriving chargeback flag; a second analyst uses a
centred smoothing step from a dashboard query. The offline AUC is excellent, the online model
is far worse, and the gap is found only after launch because nobody could say which code and
parameters produced the training table. The fixes are the three ideas of this unit:
point-in-time correct windows, a perturbation or truncation test that proves it, and a
content-addressed feature table tied to code version and parameters.

### 2.8 Limits and common misconceptions

- *"Leakage always inflates the metric noticeably."* In the second worked example the centred
  window raises pooled average precision by at most 0.014. A small effect in one offline number
  does not make the feature computable online. Causality is fixed by construction and
  protected by a test, as with the scaler in w1d3.
- *"A causal filter is free."* It costs delay (equation 1). The honest comparison between two
  detectors includes their delays; that is formalised in w3d4.
- *"More windows, more features, better model."* Rolling features of one sensor at several
  lengths are strongly collinear, and 152 features on 34 experiments invite overfitting to
  recordings. Feature count is a hyperparameter to be justified in Week 4.
- *"Caching is an optimisation."* Here it is an identity scheme. The speed-up is incidental.
- *"NaN warm-up rows can be filled with zeros."* After standardisation zero means "exactly
  normal", which silently labels the least-informed rows as the most normal.

---

## 3. Worked examples

### 3.1 Synthetic: the centred window detects the fault before it happens

`example/lookahead_demo.py` simulates noise (σ = 0.5) with a step of Δ = 2 at a known onset and
measures the delay of a rolling-mean alert at θ = Δ/4. **SYNTHETIC data:** it demonstrates
equations (1) and (2); it shows nothing about real equipment.

```bash
python lessons/w2d5_feature_pipeline/example/lookahead_demo.py
```

Output of the authoring run (seeded; yours should match to the printed precision on NumPy 2.x):

```
1) Detection delay of a rolling mean, threshold = DELTA/4, white noise, median over 400 simulated series
   w  predicted w*theta/DELTA   causal  centred
  10                      2.5      2.0     -2.0
  30                      7.5      7.0     -7.0
  60                     15.0     14.0    -15.0
   A negative delay means the alert fires BEFORE the fault begins: the feature has read the future.

2) Standard deviation of the rolling mean on fault-free noise (unit-variance input)
   w  1/sqrt(w)    white  AR(1) phi=0.9  effective n (AR)
  10      0.316    0.315          0.853               1.4
  30      0.183    0.185          0.667               2.2
  60      0.129    0.127          0.517               3.7
   Under positive autocorrelation a window of w samples carries far fewer than w independent ones.

3) False alerts per 1000 fault-free samples at threshold DELTA/4 (white noise)
   w= 10:    0.80
   w= 30:    0.00
   w= 60:    0.00
```

Reading it:

- Causal delays sit just under `w·θ/Δ`, as predicted (noise makes the crossing slightly early).
  Centred delays are those values minus `w/2`: −2, −7, −15 samples.
- Part 2 confirms `σ/√w` for white noise and shows how little averaging buys under strong
  autocorrelation. The "effective n" column is `1/sd²`.
- Part 3 is the other side of the tradeoff: the short window alerts on noise 0.8 times per
  thousand samples at this threshold, the longer ones essentially never, at 3–7 times the delay.

Code decisions worth noticing: `min_periods=w` everywhere so partial windows cannot blur the
comparison; the crossing search starts 60 samples before onset so early (leaky) alerts are
visible instead of being clipped to zero; seeds are fixed per part.

One of the simulated series, with both rolling means and the alert threshold:

![Line chart of a noisy step signal with a causal and a centred 30-sample rolling mean; the centred mean crosses the alert threshold 7 samples before the fault onset, the causal one 7 samples after](figures/step_response.svg)

*SYNTHETIC data, one series, w = 30. The centred curve is the causal curve shifted 15 samples to the
left, which is all "centring" is. Offline, that shift reads as a better detector.*


### 3.2 Real data: reference rows matter more than centring here

`example/centred_vs_causal_skab.py` scores every labelled SKAB experiment with the largest
absolute z-score of a rolling mean across the eight sensors, for causal and centred windows and
for two choices of reference rows. It is plain pandas so it runs before the lab.

```bash
python project/get_skab.py     # once
python lessons/w2d5_feature_pipeline/example/centred_vs_causal_skab.py
```

Output of the authoring run (about 4.5 s):

```
34 labelled experiments; fault-free reference rows: 9405

1) How far is the NORMAL part of each labelled experiment from the fault-free recording?
   (mean of the experiment's normal rows, in reference standard deviations; median over experiments)
   Accelerometer1RMS      median   -39.0   range   -39.3 ..    7.7
   Accelerometer2RMS      median   -57.0   range   -57.5 ..    5.7
   Current                median    -2.9   range    -3.0 ..    0.1
   Pressure               median    -0.2   range    -0.4 ..    0.1
   Temperature            median   -27.1   range   -33.3 ..    6.1
   Thermocouple           median    -4.8   range    -8.7 ..    3.1
   Voltage                median     0.2   range    -0.1 ..    0.3
   Volume Flow RateRMS    median   -57.9   range   -58.1 ..    1.5

2) Pooled point-level average precision of the max-|z| score (prevalence 0.349)
   w   window  A anomaly-free  B other experiments
  10   causal           0.733                0.493
  10  centred           0.735                0.494
  30   causal           0.724                0.495
  30  centred           0.730                0.500
  60   causal           0.727                0.504
  60  centred           0.741                0.511
```

Interpretation, kept to what the run supports:

- **The fault-free recording is not at the operating point of most labelled experiments.** Flow
  rate and both accelerometers sit about 40–58 reference standard deviations away during
  *normal* operation, and the ranges show that a few experiments do match the reference. The
  dataset has at least two regimes. Any detector "fitted on normal data" from that file alone is
  mostly detecting the regime.
- **Centring helps the offline number only slightly** (0.002 to 0.014 in average precision).
  The effect of look-ahead on a sample-level ranking metric is small when anomalous segments are
  hundreds of samples long, because only the samples near the edges change. It would show up in
  detection delay, which this script deliberately does not report.
- **The reference choice changes the number far more** (about 0.73 versus 0.50), and not in the
  direction a tidy story would predict: the leave-one-experiment-out reference is *worse*. A plausible
  reason is that pooling normal rows from both regimes inflates the standard deviations so that
  real deviations become small z-scores; the script does not test that explanation. Neither
  column is a model evaluation: nothing was tuned, no threshold was chosen, all 34 experiments
  were scored, and a max-|z| of rolling means is a crude score.

What cannot be concluded: which reference is right for the project, or that either score is a
usable baseline. Those are w2d6 and Week 3 questions, to be answered inside the split protocol.
The conclusion that does follow is narrower and more useful today: *the rows passed to `fit` are a
first-order modelling decision, so the code must make them an explicit, recorded argument.*

---

## 4. Guided lab

Work in `lessons/w2d5_feature_pipeline/lab/` (or in your project, if it follows
[docs/FLOWGUARD_SPEC.md](../../docs/FLOWGUARD_SPEC.md)). The starter contains working snapshots
of `flowguard.data` and `flowguard.splits`, and stubs in `flowguard/features.py` and
`flowguard/cli.py`. The contract you implement is the docstring at the top of `features.py`.

Run the checks whenever you like; they use small synthetic frames and take a few seconds:

```bash
python wb.py check w2d5
```

**Task 1 — one experiment, one segment (15 min).** Write a helper that takes the sensor columns
of a single continuous segment and returns `mean`, `std`, `min`, `max` for each window with
`min_periods=w`, plus `diff1`. Use pandas rolling on the whole sensor frame at once.

*Checkpoint:* on a ramp `x = 2t`, `mean_w` at row *i* is `2i − (w−1)` and `diff1` is 2.

**Task 2 — slope and EWMA (10 min).** Add the least-squares slope against `k = 0..w−1` and
`ewm(span=w, adjust=False)`. For the slope avoid `rolling.apply` with `np.polyfit`: derive it
from rolling sums. With `S = Σ x` and `K = Σ k·x` over the window,
`slope = (K − (w−1)/2 · S) / (w(w²−1)/12)`.

*Checkpoint:* slope of the ramp is exactly 2; `test_matches_slow_reference` passes for one experiment.
*Debugging:* if the slope is right early in a segment and drifts later, you used the global row
position for `k` without subtracting the window start.

**Task 3 — experiments and gaps (15 min).** Wrap the helper: group by `experiment_id`, sort by
`datetime`, split into segments where `datetime.diff() > max_gap_s`, compute per segment,
reassemble in the *input's row order*, add `segment` and `rows_since_reset`.

*Checkpoints:* `test_causality.py` passes entirely. Then deliberately break it: add
`center=True`, run the checks, read the failure message, revert. Do the same by removing the
`groupby`. Knowing what each failure looks like is part of the deliverable.
*Debugging:* a failure only in `test_experiment_order_does_not_matter` means your output order
follows the groupby order instead of the input index.

**Task 4 — `ReferenceStats` (10 min).** Implement `fit` and `transform`. Then, in a scratch
script or REPL, use the split manifest: fit on the normal rows of the training experiments of
fold 0 and transform the validation fold.

```python
from flowguard.data import read_tidy
from flowguard.features import causal_rolling_features, ReferenceStats
from flowguard.splits import make_splits, training_experiments

tidy = read_tidy("data/interim/skab.csv")          # python lessons/w2d5_feature_pipeline/lab/make_tidy.py
feats = causal_rolling_features(tidy)
manifest = make_splits(tidy)
train = training_experiments(manifest, fold=0)
rows = feats["experiment_id"].isin(train) & (tidy["anomaly"].to_numpy() == 0)
stats = ReferenceStats.fit(feats[rows])
```

*Checkpoint (authoring run, default seed):* 19 training experiments, 13,420 training-normal rows,
152 fitted features, no zero standard deviations. Using labels to select normal *training* rows
is legitimate; using them for validation or test rows would not be.

**Task 5 — the cached command (10 min).** Implement `cache_key` and `run_features` to the
contract in the starter docstring, then run on the real table twice:

```bash
cd lessons/w2d5_feature_pipeline/lab && python -m pip install -e . && cd -
flowguard features --data data/interim/skab.csv --out-dir data/features
flowguard features --data data/interim/skab.csv --out-dir data/features
```

*Checkpoint (authoring run):* first call about 9 s and `"cache_hit": false`; second about 0.5 s
and `"cache_hit": true`; table of 46,806 rows × 156 columns. Note the size: 111 MB as CSV at
full float precision. That is a real cost of the "no parquet dependency" decision in the spec;
write one sentence in your project notes on what you would do about it (rounding changes the
content hash and the values; a columnar format adds a dependency).

**Result to produce.** Passing checks, the cached table, and the five-line policy note described in section 1.

---

## 5. Independent challenge

[challenge/README.md](challenge/README.md): causal features for an **irregularly sampled**
series using time-based windows, with outage handling. Graded by
`python wb.py check w2d5 --challenge`, which applies the same perturbation idea plus a
truncation test. No solution is given in the instructions.

## 6. Progressive hints

Open in order, and only when stuck for more than ten minutes:
[hint 1 — concept](hints/hint1_concept.md) · [hint 2 — approach](hints/hint2_approach.md) ·
[hint 3 — partial implementation](hints/hint3_partial.md). The full reference is in
`solutions/lessons/w2d5_feature_pipeline/`. Using hint 3 or the solution means the
independent flag stays unset.

## 7. Assessment

[assessment.md](assessment.md): six reasoning questions (one asks you to defend a design
choice), the rubric, and a 15-minute Python interview rep. Model answers and common incorrect
answers are in `solutions/lessons/w2d5_feature_pipeline/assessment_answers.md`.

## 8. Reflection and review

**You should now be able to, without help:** write a rolling-feature function that is causal
across experiments and gaps; prove it with a perturbation test; explain the delay/noise
tradeoff with equations (1) and (2) and say when (2) is wrong; separate fitting from applying
feature statistics; give a feature table an identity.

**Reflection prompt (5 min, write it in `python wb.py note w2d5 "..."`).** Think of one feature
pipeline from your own EEG work. Which step was non-causal? Did the evaluation that used it
correspond to something that could run online, and did the paper say so?

**Retrieval question for the review day (answer from memory):** A colleague's rolling z-score
"improves a lot" when computed with `df.groupby("unit").transform(lambda s: (s - s.mean()) / s.std())`.
Name the two distinct leaks and a test that would expose each.

**Next:** [w2d6 — strong simple baselines and metrics that match the decision](../w2d6_baselines_metrics/README.md).
The feature table and `ReferenceStats` from today are the inputs to the first baselines, and the
reference-row question raised in 3.2 is settled there with the split protocol.

---

## Verification record

Executed on 2026-11-21, Python 3.13.18, NumPy 2.5.3, pandas 3.0.5, scikit-learn 1.9.1.

- Both worked examples were run; the outputs above are copied from those runs.
- Reference package run on the real data: tidy table 46,806 × 14; features 46,806 × 156
  (152 features) in 0.7 s in memory; 44 segments; CLI 9.1 s cold, 0.46 s on a cache hit.
- Vectorised versus row-by-row reference on `valve1/2` (1,075 rows, two sensors): 0.017 s versus
  0.70 s, largest absolute difference 1.9e-14.
- `python tools/verify_checks.py lessons/w2d5_feature_pipeline`: reference passes both parts;
  5 lab mutants and 4 challenge mutants rejected, each on its intended checks.
- Shipped starters fail their checks (lab and challenge).
- `pip install -e` of the reference lab package into a fresh virtual environment, then
  `flowguard features` and `flowguard --version` (0.3.0): worked. Check suites take about 4 s
  (lab) and under 1 s (challenge); the full verification with mutants 46 s.
- Not verified: other Python or pandas versions; the explanation offered for column B in 3.2.
