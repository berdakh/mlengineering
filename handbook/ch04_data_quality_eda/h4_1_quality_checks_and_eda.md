# H4.1 Quality checks as code; exploratory analysis that changes decisions

**Status:** Reviewed (numbers from executed runs; see H4.1.9) · **Used by:** [w2d3](../../lessons/w2d3_data_quality_ingestion/README.md) · **Related:** [H3.3](../ch03_sql_data_pipelines/h3_3_ingestion_schemas.md), [H9.1](../ch09_testing_ml_systems/h9_1_unit_testing_ml_code.md)

## H4.1.1 Overview

A data-quality check is an executable statement about data that can be false. A set of them, with
severities and a defined consequence for each, is a gate. Exploratory analysis is how you learn
which statements are worth making and what the thresholds should be. The two feed each other:
exploration discovers a failure mode; a check makes sure it is never rediscovered by accident.

This section is about what to check, how to grade a failure, how to write checks so that they stay
trusted, and how to explore data so that every finding ends in a decision.

## H4.1.2 A taxonomy of checks

| Kind | Asks | Examples | Typical tool |
|---|---|---|---|
| Structural | Does the table have the declared shape? | columns, dtypes, non-empty | assertion on columns/dtypes |
| Row-level | Is each row valid alone? | not null, in range, in allowed set, matches pattern | boolean mask per column |
| Cross-field | Are the columns of a row consistent with each other? | `refund <= amount`; `delivered_ts >= order_ts`; field present iff status | mask over several columns |
| Set-level (relational) | Are the rows consistent together? | key unique; time ordered; no gaps; referential integrity; one event per experiment | `groupby`, `duplicated`, `diff`, joins |
| Distributional | Does this batch look like what we expect? | row count, missing share, class balance, mean within band | statistics with tolerances |
| Freshness and completeness | Did everything arrive, on time? | every day present; latest timestamp recent; all units reported | calendar/roster comparison |

Schema libraries make the first two kinds effortless, which is why pipelines tend to have many of
them and few of the rest. For time-series and grouped data the damaging defects are set-level:
duplicates corrupt every window, a gap changes what "the last 60 samples" means, a frozen sensor
looks like a perfectly valid constant.

**Set-level checks respect the grouping.** "Previous row" is defined within a unit (experiment,
machine, customer). A `diff` across the whole table compares the first row of one unit with the
last of another. This is the same mistake as filtering or epoching across a subject boundary.

Useful definitions for sequences $y_0,\dots,y_{n-1}$ within one unit:

- gap at $i$: $\Delta_i = \tau_i - \tau_{i-1} > \Delta_{\max}$;
- longest constant run: $\max$ over maximal intervals $[a,b]$ with $x_a = \dots = x_b$ of $b-a+1$;
- number of positive segments: $S = \sum_{i} \mathbb{1}[y_i = 1 \wedge y_{i-1} = 0]$, $y_{-1}=0$.

## H4.1.3 Writing validity so that unparseable values fail

After `errors="coerce"`, a bad cell is NaN, and every comparison with NaN is False. Verified:
`pd.to_numeric(["40,00", "-1", ""], errors="coerce") <= 0` gives `[False, True, False]`.

So a rule written as *invalid if `amount <= 0`* passes the unparseable and the empty value. Write
the rule the other way round:

```python
valid = amount.notna() & (amount > 0)        # NaN -> not valid
offenders = df.loc[~valid, key]
```

For relational rules between two columns, decide which rule owns an unparseable operand, so one
bad cell is reported once and under the right name:

```python
valid = refunded.notna() & (refunded >= 0) & ~(refunded > amount)   # a bad `amount` belongs to its own rule
```

## H4.1.4 Severity and consequences

A check without a consequence is a comment. Two levels are enough for most pipelines:

- **Error** — a later step would compute something false without any symptom. Consequence: stop;
  non-zero exit; no output table; a report that says what and where.
- **Warning** — the data is valid as recorded, and a decision depends on the fact. Consequence:
  recorded in the report, surfaced to a human, carried forward as a known constraint.

The criterion is silent downstream falsehood, not how alarming the data looks. Duplicate keys in
0.1 % of rows are an error because rolling features are then wrong everywhere near them. A 247 s
hole in a recording is a warning because no row is wrong; a naive windowing would be.

Calibrating the set:

- Every error must be mechanical and defensible. If people argue about it each time it fires, it
  is a warning.
- A check that fires routinely on healthy data will be ignored, then disabled. Derive thresholds
  from observed normal behaviour and leave margin. (SKAB: the flow sensor legitimately repeats a
  value for 43 samples; a "stuck after 10" rule fails all 35 files.)
- Review warnings. An unreviewed warning list is an error log nobody reads.

**What a good failure report contains:** rule name, severity, count, and the identity of the
offending units or rows — enough for the owner of the data to find them without rerunning your code.
Evaluate every rule on every run; a checker that stops at the first failure costs one round trip
per defect.

**Checks never repair and never raise.** The checker describes the data as it arrived and returns
results; the caller decides. A checker that sorts first cannot detect disorder. A checker that
raises on the first unparseable value reports one problem, as a traceback, and hides the rest.

## H4.1.5 Validation, testing, evaluation, monitoring

Four activities are regularly confused because all four "check things":

| Activity | Subject | Verdict | Runs |
|---|---|---|---|
| Unit testing ([H9.1](../ch09_testing_ml_systems/h9_1_unit_testing_ml_code.md)) | Code | deterministic pass/fail | on every change to the code |
| Data validation (this section) | A batch of data | deterministic pass/fail per rule | on every batch |
| Model evaluation (chapter 6) | A model on held-out data | an estimate with uncertainty | after training; on labelled backfill |
| Monitoring (chapter 15) | A running system over time | alerts on trends and thresholds | continuously |

Data validation needs neither labels nor a model, which is why it can run first and run always.
The checks themselves are code and need unit tests: feed them synthetic tables with one planted
defect each and assert that the right rule fails for the right unit, and that a clean table passes.
That is how the w2d3 lab is graded.

## H4.1.6 Exploratory analysis that changes a decision

Exploration at this stage has an acceptance test: each finding is written as *observation →
consequence → owner*. A plot that changes nothing is not part of the report.

A sequence that works for grouped time series, with what it found on the project data (all numbers
from the run recorded in w2d3):

| Question | Finding on SKAB | Decision |
|---|---|---|
| What is the unit, and how many are there? | 34 labelled experiments, one event each; 37,401 labelled rows | The sample size for any claim about detection is 34, not 37,401 |
| Is sampling uniform? | 94.5 % of steps are 1 s, 5.3 % are 2 s; 9 steps exceed 5 s in 6 experiments, largest 247 s; 7 of 9 lie inside the anomalous segment | Windows must not span gaps; delays are measured in seconds |
| What is the base rate? | 34.9 % of labelled samples are anomalous (0.25–0.49 per experiment) | Not a rare-event problem at point level; read precision against 0.35 |
| What is the sensor resolution? | Pressure: as few as 5 distinct values per experiment; flow rate repeats up to 43 samples | Stuck-sensor threshold well above quantisation runs |
| How large is between-unit variation? | SD of experiment means is 60–200 times the within-experiment SD for four sensors | Per-experiment causal normalisation; evaluate on unseen experiments |
| Is the effect the same across groups of units? | Valve families: flow rate falls about 4 SD in nearly every experiment. `other`: no sensor moves beyond 1 SD in more than 57 % of experiments | A second evaluation protocol holding out a family |

**Aggregate within the unit before comparing across units.** The first attempt at the last row
pooled rows by family and subtracted pooled means. It reported a 243-SD accelerometer shift for the
`other` family. Computed within each experiment and then summarised, the median shift is −0.20 SD.
The pooled number measured which experiments contributed anomalous rows, not what the fault does.
This is Simpson's paradox in its everyday form, and the defence is procedural: compute the contrast
inside the independent unit, then summarise across units.

**Other habits worth keeping.**

- Look at raw rows and raw traces before any summary; summaries hide duplicated and frozen stretches.
- Ask of every missing value *why* it is missing before deciding what to do. Missing completely at
  random, missing depending on something observed, and missing depending on the unobserved value
  itself call for different treatments, and the third can carry signal — or leak the label.
- Ask of every regularity whether it is physics or procedure. In SKAB the gaps cluster inside
  anomalous segments. If the logger drops samples when the rig is disturbed, "there was a gap" is a
  property of the recording procedure; a feature built on it would not exist in deployment.
- Explore on training data only once splits exist (w2d4). Until then, restrict yourself to
  structure and quality; decisions that tune a model on what the test set looks like are leakage.

## H4.1.7 Practical decisions and tradeoffs

| Decision | Tradeoff |
|---|---|
| Hand-written checks or a library | Hand-written: full control, clear semantics, more code. pandera-style schemas: concise for structural and row-level rules; relational rules still need custom functions. Expectation suites with stored results: valuable with many datasets and stakeholders, heavy for one table. Learn the concepts by hand; adopt a tool when the boilerplate, not the thinking, is the cost. |
| Where checks run | At ingestion (gate), before training (assert assumptions), at inference (per-request validation, Week 5), in monitoring (trends, Week 7). The same rule often appears in several places with different consequences. |
| Fixed thresholds or learned ones | Fixed: explainable, need maintenance. Learned from history: adapt, but can learn a degraded state as normal. Start fixed, record the statistics, revisit. |
| Reject the batch or quarantine rows | Rejecting keeps semantics simple and is right when rows interact (time series). Quarantining bad rows suits independent records (orders) but must report how many were set aside, and the remainder must still be a valid sample. |

## H4.1.8 Common failure modes and quick reference

- Column-wise validation only; relational and cross-field defects pass.
- Set-level statistics computed across unit boundaries; clean units blamed.
- Rules written as "invalid if ..." that NaN slips through.
- Thresholds from intuition; the check cries wolf and is disabled.
- A report without identifiers ("14 rows failed") that nobody can act on.
- Checks that mutate or sort their input.
- A gate with no consequence: exit code 0 whatever happens.
- Exploration on pooled rows that confounds unit with effect.
- A passing report read as "the data is correct" rather than "no known failure mode occurred".

```python
# per-unit set-level checks
g["datetime"].duplicated(keep=False)                       # duplicate keys
(g["datetime"].diff().dt.total_seconds() < 0).any()        # out of order
g["datetime"].diff().dt.total_seconds().gt(max_gap)        # gaps
starts = np.flatnonzero(np.r_[True, x[1:] != x[:-1]])      # run starts
np.diff(np.r_[starts, len(x)]).max()                       # longest constant run
int((np.diff(np.r_[0, y]) == 1).sum())                     # number of positive segments

# validity masks: parsed AND condition
valid = v.notna() & (v > 0)
has_ts == (status == "delivered")                          # "if and only if"
```

## H4.1.9 Sources and verification status

Executed in this session: every number in H4.1.6 (from `lessons/w2d3_data_quality_ingestion/example/explore_skab.py`
on SKAB at the commit pinned in `project/get_skab.py`); the NaN-comparison example in H4.1.3; the
reference checkers for the lab and the challenge, verified against four wrong submissions each.

From general knowledge, not re-verified against documentation in this session: the descriptions of
pandera and expectation-suite tools in H4.1.7; the missingness terminology (MCAR/MAR/MNAR) follows
Rubin, "Inference and missing data", Biometrika 63(3), 1976, and Little & Rubin, *Statistical
Analysis with Missing Data* (cited from memory; not opened). "Simpson's paradox" is used in its
standard sense. Dataset: Katser & Kozitsin, *Skoltech Anomaly Benchmark (SKAB)*, Kaggle, 2020,
DOI 10.34740/KAGGLE/DSV/1693952 (upstream README and LICENSE opened; see `project/README.md`).
