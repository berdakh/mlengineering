# H1.2 Units, labels, costs and constraints

**Status:** Reviewed (single authoring pass; sources and their verification state in H1.2.9)
**Used by:** [w2d4](../../lessons/w2d4_problem_framing_splits/README.md) · **Follows:** [H1.1](h1_1_stakeholder_need_to_prediction_target.md) ·
**Continues in:** H6.1 Leakage taxonomy (planned, w3d1), H6.3 Group and temporal validation (planned, w3d2)

## H1.2.1 Overview

Once the decision and the target are chosen (H1.1), four specifications make the problem concrete
enough to build and to evaluate: the **units** (what one prediction, one decision and one
independent observation are), the **label** (where it comes from and when), the **costs** of errors,
and the **constraints**. The evaluation split is not a fifth, separate topic: it follows from the
units. This section treats each and ends with the split manifest as the place where the
specifications are frozen.

## H1.2.2 Three units and a clock

**Unit of prediction.** What a single model output refers to: a timestamp, a window, a
customer-month, a transaction.

**Unit of decision.** What the user acts on: an alert, a work order, a call list. Usually coarser.
Scoring at a finer unit than the decision is fine; *evaluating* only at the finer unit hides what
matters (a detector can have excellent per-sample recall while missing whole short events).

**Unit of generalisation.** What is new when the system runs: a recording, a patient, a machine, a
future period. Define it by completing: "in production the model always meets a ___ it was not
trained on." It may be compound (a future month *and* sometimes a new customer).

**The clock.** Every row needs two timestamps, even if only implicitly:

* `t_pred`, the moment the prediction would be made. Features may use information with timestamp
  `<= t_pred` only, *as it was known then* (late-arriving corrections do not count).
* `t_label`, the moment the label became fully known.

A feature violating the first rule is temporal leakage. A training row with `t_label` after the
moment of training is a label from the future. Both are invisible in a table that has lost its
timestamps, which is why the data dictionary must record, for every column, *when its value becomes
available*.

For a target defined over a horizon `H` after `t_pred` (churn within three months), a model trained
at time `T` may use rows with

```
t_pred + H  <  T            (label window closed before training)
```

and can be evaluated on rows with

```
t_pred >= T    and    t_pred + H <= t_end     (label window closes inside the data)
```

The rows with `T - H <= t_pred < T` are usable for neither: a **purge gap** of one horizon. Forgetting
it is the most common error in temporal splits of horizon-labelled data.

## H1.2.3 Labels: origin, delay, noise, censoring

Ask of every label: *who or what produced it, when, and under what incentive?*

| Origin | Example | Characteristic problem |
|---|---|---|
| Experimental protocol | SKAB: operator closed a valve at a logged time | marks the cause, not the first visible effect |
| Expert annotation | seizure onset marked by a neurologist | inter-rater disagreement; boundary uncertainty |
| Operational record | maintenance ticket, fraud chargeback | delayed; exists only for cases somebody noticed (selective labels) |
| User behaviour | click, cancellation | proxy for the construct; influenced by what the system showed |
| Derived rule | "pressure below limit" | circular if the model sees the same variable |

**Delay.** If labels arrive `d` after the prediction, every evaluation of the live system is `d`
old, and the newest `d` of data cannot be used for supervised training. Budget for it.

**Selective labels.** When the label exists only for acted-on cases (loans granted, parts
inspected), the labelled set is a biased sample and the model learns the old policy's blind spots.
The remedy is in data collection (a small random sample that is always labelled), not in modelling.

**Noise and boundaries.** For events in time, labels are intervals with uncertain edges. A
point-level metric punishes the model for disagreeing with the annotator about the exact second;
this caps achievable point-level scores below 1 and is one reason detection is also scored per event
with a tolerance. If two annotators agree on only 85 % of samples, 85 % is a ceiling worth knowing
before interpreting a model at 83 %.

**Censoring.** For horizon labels, positives are known as soon as the event occurs and negatives
only when the horizon has elapsed. Among recent rows, "label is known" therefore selects positives.
Selecting evaluation rows with `label.notna()` inflates the base rate; in the lesson's synthetic
churn table it moves the test churn rate from 0.163 to 0.199. Decide eligibility by the calendar
inequalities of H1.2.2, never by missingness of the target.

## H1.2.4 Costs, thresholds and capacity

Let `s = P(y = 1 | x)` be calibrated, `c_FP` the cost of acting on a negative, `c_FN` the cost of
not acting on a positive (correct decisions costing zero for simplicity). Expected cost of acting is
`(1 - s) c_FP`; of not acting, `s c_FN`. Act when

```
s  >  t*  =  c_FP / (c_FP + c_FN)
```

| `c_FN : c_FP` | `t*` |
|---|---|
| 1 : 1 | 0.50 |
| 5 : 1 | 0.17 |
| 10 : 1 | 0.09 |
| 100 : 1 | 0.01 |

Consequences and caveats:

* The default 0.5 threshold assumes equal costs. So, implicitly, does accuracy.
* F1 embeds a particular trade-off that corresponds to no stated cost; use it for development if you
  like, never as the argument for a threshold.
* The formula needs **calibrated** scores. Many models rank well and are miscalibrated; then choose
  the threshold empirically on validation data to minimise estimated cost (and treat that choice as
  a fitted parameter: it must not see test data).
* **Capacity constraints** replace cost thresholds: with room for `k` actions, act on the top `k`
  and report precision and recall at `k`. This is often the more truthful description of an
  operations team.
* **Budgets on one error type**, "at most one false alert per hour", are constraints of the
  Neyman-Pearson kind: maximise detection subject to the bound. Report the operating point, not only
  the curve.
* Costs are rarely constant per instance (a large customer, a critical pump). Start with a single
  ratio; refine when the first version shows where it is wrong.
* In streams, decisions are not independent: repeated alerts on one episode are one decision. Count
  events (planned: H6.5).

## H1.2.5 From the unit of generalisation to the split

**Dependence within groups.** If a group contributes `m` observations with intraclass correlation
`ρ`, the variance of a mean over `n` observations is inflated by the design effect:

```
deff = 1 + (m - 1) ρ ,        n_eff = n / deff
```

For `m = 1,100` rows per recording and `ρ = 0.5`, `n_eff` per recording is about 2. Uncertainty must
be computed over groups, and splits must keep groups whole, whenever groups are the unit of generalisation.

**Deriving the split.**

| What is new in production | Split | Note |
|---|---|---|
| new groups (patients, recordings, sites) | whole groups held out | stratify groups by any higher-level attribute you will report on |
| future time, same entities | train on the past, test later; purge by the label horizon | grouping by entity is *not* required; a random group split answers a different question |
| both | temporal split, with a set of entities withheld from training | report "known" and "new" entities separately |
| nothing (a fixed, closed population scored once) | random split is defensible | rare outside competitions |

The reflex to hold out groups is right for cross-subject research and wrong for the second row. A
demand model for the same 200 shops must be tested on a later period, with all 200 shops in training.

**Small numbers.** A test set of `n` independent units gives a proportion (event recall, say) with
standard error `sqrt(p(1-p)/n)`: 0.13 for `p = 0.8`, `n = 9`. Know this before the experiment, not after.

**A second protocol for a second question.** One split answers one question. "How well on recordings
like those seen?" and "how well on fault mechanisms never seen?" need different partitions (in the
project: a stratified test set, and protocol B holding out one whole family). State which number
answers which question.

## H1.2.6 The split manifest

A split is a decision with consequences for every later number, so store it as data:

```json
{"version": "v1", "seed": 0, "unit": "experiment_id",
 "test": ["other/1", "..."], "dev_folds": [["..."], ["..."]],
 "reference_normal": ["anomaly-free/anomaly-free"],
 "protocol_b": {"holdout_family": "other"}}
```

Properties worth enforcing in code (`validate_splits` in the lab):

* entries are unit identifiers, not row indices;
* every eligible unit appears exactly once; no unit on two sides;
* no identifier unknown to the data, so a stale manifest fails loudly when data changes;
* units that must never be evaluated (fault-free reference) are listed separately.

**Why not "just fix the seed".** A seeded splitter is a function of the seed, the list of groups,
their order, and the library's algorithm. Add a recording and membership changes silently: in the
lesson's demonstration, adding one machine to a list of 24 moved four of the six test machines into
training under the same `random_state`. The manifest keeps the seed as provenance only.

**Frozen after first results:** test membership; label and event definitions; metric definitions;
exclusion rules. A change is a new version; old numbers keep their version label and are not compared
across versions without recomputation.

## H1.2.7 Constraints

Collect them before modelling; each can invalidate an otherwise good model.

| Constraint | Question | Effect on design |
|---|---|---|
| Latency | how long between input and usable output? | model size, feature windows, batch versus online |
| Cold start | what does a new entity or a restarted stream have? | warm-up rules; fallbacks; features that need no history |
| Data at prediction time | which columns truly exist then, with what delay? | feature list; the single most common source of leakage |
| Interpretability | must a human justify the action? | per-alert attribution; simpler model class |
| Compute and cost | where does it run, at what price? | CPU-only, memory ceiling |
| Regulation and rights | may this data be used for this purpose? | exclusions; documentation |
| Change | how often does the process itself change? | retraining cadence; monitoring |

## H1.2.8 Common failure modes

| Failure | Mechanism | Guard |
|---|---|---|
| Row-level split of grouped data | near-duplicates across the boundary | manifest keyed by group; validator |
| Group split where time is the novelty | tests a question nobody asked; hides drift | derive the unit from deployment |
| No purge gap with horizon labels | training labels describe the test period | the inequalities in H1.2.2 |
| `dropna()` on the target | selects early-known positives | eligibility by calendar |
| Tiny family absent from test | unstratified draw of groups | stratify groups; report per family |
| Re-drawing the split after results | test set becomes a tuning parameter | freeze; version; refuse overwrite |
| Threshold 0.5 by default | assumes equal costs | cost ratio or capacity, stated |
| Evaluating only at the prediction unit | per-sample scores hide missed events | also score at the decision unit |
| Reporting sample counts as n | ignores design effect | count groups and events |

## Quick reference

* Units: prediction / decision / generalisation. The last one sets the split.
* Clock: features `<= t_pred`; train rows need `t_pred + H < T`; test rows need
  `t_pred >= T` and `t_pred + H <= t_end`.
* Label: origin, delay, selection, boundary noise, censoring.
* Threshold: `t* = c_FP / (c_FP + c_FN)` for calibrated scores; top-k under capacity; operating point
  under a false-alert budget.
* `n_eff = n / (1 + (m - 1)ρ)`; proportion SE `sqrt(p(1-p)/n)` over independent units.
* Manifest: unit ids, exactly-once, validated, versioned, never overwritten.

## H1.2.9 Sources and verification status

| Claim or content | Source | Status |
|---|---|---|
| Grouped data break the i.i.d. assumption; group-wise iterators keep a group out of both sides; time-ordered data need forward-chaining splits | scikit-learn user guide "Cross-validation" (`doc/modules/cross_validation.rst`, sections on i.i.d. data, grouped data, time series; read from the GitHub source) | opened this session |
| Behaviour of a seeded group splitter when the group list changes | `example/split_unit_demo.py` in lesson w2d4, executed with scikit-learn 1.9.1 | executed this session |
| Row-level versus experiment-level validation on SKAB (0.986 versus 0.849 ROC-AUC) | `example/skab_row_vs_experiment.py` in lesson w2d4 | executed this session |
| Censoring example (0.163 versus 0.199) | synthetic churn table of the w2d4 challenge | executed this session; SYNTHETIC |
| Cost-optimal threshold `c_FP / (c_FP + c_FN)` | standard Bayes decision theory; derivation given in the text. Commonly cited: Elkan (2001), "The Foundations of Cost-Sensitive Learning", IJCAI | derivation checked here; citation from memory, not re-opened |
| Design effect `1 + (m - 1)ρ` | survey-sampling literature (Kish, *Survey Sampling*, 1965) | formula from memory, not re-verified against the source |
| Neyman-Pearson framing of error budgets; "selective labels" terminology | general statistics / ML literature | from memory, not re-verified |
