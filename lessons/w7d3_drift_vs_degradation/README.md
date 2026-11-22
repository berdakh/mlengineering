# w7d3 — Drift is not degradation: delayed labels and measured performance

**Status:** Execution verified (see the verification record at the end).
**Handbook:** [H15.4 Drift versus degradation, delayed labels](../../handbook/ch15_logging_monitoring_updates/h15_4_drift_vs_degradation_delayed_labels.md)
**Prerequisites:** [w7d2](../w7d2_input_monitoring_drift/README.md) (input monitoring and drift statistics; this lab ships its
own `flowguard.drift`), [w3d4](../w3d4_point_vs_event_evaluation/README.md) (event metrics),
[w3d5](../w3d5_uncertainty/README.md) (intervals), [w5d2](../w5d2_artifacts_versioning/README.md) (the shipped model).

---

## 1. Purpose

**What you will learn.** To answer two different monitoring questions with two different kinds of
evidence: *has the input changed?* (drift statistics, available immediately) and *is the model still
good?* (labels, which arrive late, partially and selectively). You will join late labels to logged
predictions, compute precision and recall only from what is known at a given date, attach intervals,
and refuse to report a number when there is not enough evidence for one.

**Why an applied ML engineer needs it.** Most production models are judged by labels that arrive
days to months after the prediction: maintenance confirms a fault, a customer churns, a chargeback
lands. A team that treats a drift alarm as "the model is broken", or a quiet dashboard as "the model
is fine", will retrain models that were working and keep models that were not. Interviewers probe
this directly: *"Your drift monitor fires. What do you do?"*

**Primary objective.** Implement `flowguard.delayed_eval` and use it with a drift monitor to show, on a
replay of real SKAB recordings, one case of drift without degradation and one of degradation without
drift.

**Deliverable.** A working `delayed_eval.py` that passes the checks, the replay report on real data,
and a monitoring and label-backfill plan (the challenge).

**Completion criteria.**
- `python wb.py check w7d3` passes (guided practice).
- You can state, for each replay period, what the drift monitor said, what the labels said on day 65
  and on day 150, and why those differ.
- `python wb.py check w7d3 --challenge` passes and your plan scores at least 12/16 on the rubric
  (independent skill).

| Activity | Essential (2 h) | Optional (≤ 1 h) |
|---|---|---|
| Read sections 2-3 and run the worked example | 30 min | |
| Guided lab, tasks 1-5 | 55 min | |
| Real-data replay and interpretation (task 6) | 15 min | change the label policy and re-run |
| Independent challenge (start) | 15 min | finish it |
| Assessment and reflection | 5 min | interview rep (15 min) |

---

## 2. Conceptual explanation

### 2.1 Intuition

A drift monitor compares *inputs* today with inputs from a reference period. It is fast, needs no
labels, and answers exactly one question: are the numbers arriving different from before? It cannot
say whether the model's decisions got worse. A model may be built to be indifferent to the change
(this project's detector normalises every run by its own burn-in), or the change may be in a direction
the model never uses. Conversely, a model can get worse while every input statistic stays put, because
what changed is the relationship between inputs and outcomes, or the pipeline around the model.

Performance needs labels. Labels in production arrive **late** (a fault is confirmed days after the
alarm), **partially** (missed faults are found only if someone inspects), and **selectively** (people
investigate the alarms that look worst). Each of these bends the numbers you can compute, always in a
known direction once you write down how labels are produced.

```mermaid
sequenceDiagram
    participant S as Service (t = 0)
    participant L as Prediction log
    participant M as Maintenance
    participant I as Inspection
    participant E as Delayed evaluation
    S->>L: score and alarm with alarm_id and model_version
    Note over S,L: drift monitor reads the inputs now
    M-->>L: verdict for alarm_id, 2-10 days later, may be corrected
    I-->>L: missed fault report with fault_id, 14-60 days later, only some faults
    E->>L: join by id, keep labels known by as_of
    E->>E: precision and recall with intervals, or insufficient data
```

### 2.2 Precise terms

Write $x$ for the inputs, $y$ for the outcome (fault or not) and $f$ for the deployed model.

* **Covariate shift**: $P(x)$ changes, $P(y \mid x)$ does not. A recalibrated sensor, a new operating
  regime. The *right* model is unchanged; whether *your* model still performs depends on whether it
  extrapolates correctly into the new region of $x$.
* **Prior (label) shift**: $P(y)$ changes, $P(x \mid y)$ does not. More faults this season. Precision at
  a fixed threshold moves even though the model did not change: precision depends on prevalence (w2d6).
* **Concept shift**: $P(y \mid x)$ changes. A new fault mechanism that leaves the monitored sensor
  untouched, a new fraud pattern, or a change in what the plant *calls* a fault. Input statistics may
  not move at all.
* **Data drift** in monitoring tools usually means "some statistic of $x$ moved". It is a *symptom*.
  **Performance degradation** means a labelled metric of $f$ got worse. It is the *outcome* you care
  about. Neither implies the other.
* **Label delay**: time from prediction to the label's arrival. **Label coverage**: the fraction of
  predictions that will ever get a label. **Verification bias**: the labelled subset is chosen by a
  process correlated with the outcome (here, by peak score), so metrics on it are biased.
* **As-of evaluation**: a metric computed "as of day $d$" uses only labels with $\text{label\_time} \le d$.
  Back-testing a monitor without this rule lets it see the future.

### 2.3 The mathematics you need

**Precision from investigated alarms.** If only alarms in a set $\mathcal{I}$ are investigated, the
estimate $\hat p = \frac{1}{|\mathcal I|}\sum_{a \in \mathcal I} y_a$ estimates $P(y = 1 \mid a \in \mathcal I)$,
not $P(y = 1 \mid \text{alarm})$. When investigation is chosen by score and $P(y=1 \mid \text{score})$
increases with score, $\hat p$ is biased upward. With a known, random investigation rate the bias
vanishes; with a known score-dependent rate, inverse-probability weighting corrects it.

**Recall from inspections.** Let $C$ be faults confirmed by alarms, $M$ faults missed, and $\rho$ the
probability that a missed fault is ever reported. What you can compute is
$\hat r = \frac{C}{C + M_{\text{reported}}}$ with $E[M_{\text{reported}}] = \rho M$, so for $\rho < 1$,
$\hat r$ is biased *upward*; it is an upper bound on recall. Early in the label delay,
$M_{\text{reported}}$ is smaller still, so early estimates are even more optimistic.

**Power.** With $n$ faults of known outcome and recall near $r$, a 95 % Wilson interval has half-width
roughly $1.96\sqrt{r(1-r)/n}$. At $r = 0.6$ that is about ±0.20 at $n = 20$ and ±0.10 only at
$n \approx 89$. A window must contain enough *labelled events*, not enough samples.

![Half-width of a 95 % Wilson interval for recall 0.6 against the number of faults: about 0.20 at 20 faults, 0.10 at 89](figures/power_wilson.svg)

*Figure 1 (arithmetic).* One replay period of this lab has 20 faults; pinning recall to ±0.10 takes about 89.

![SYNTHETIC: precision measured on the top-scoring investigated alarms falls from 1.0 towards the true 0.68 only as the investigated fraction approaches 100 %](figures/verification_bias.svg)

*Figure 2 (SYNTHETIC: 400 alarms, P(true) logistic in peak score).* Investigating the worst-looking half
of the alarms reports precision near 1.0 against a true 0.68.

### 2.4 Connection to what you already know

In BCI work you track decoder accuracy across sessions only on calibration blocks where the intended
class is known; free-use periods have no labels, and EEG amplitude changes between sessions (electrode
impedance, gel drying) are covariate shift that a per-session normalisation can absorb. That is this
project's burn-in normalisation. You also know verification bias from clinical evaluation: if only
patients with positive screening get the reference test, sensitivity is overestimated. Maintenance
investigating only alarmed segments is the same design.

### 2.5 An industry example

A card issuer's fraud model raises alerts that analysts review within a day; missed fraud surfaces
as chargebacks one to three months later. The worked example below simulates exactly this. When a
new fraud pattern appears that the model scores like normal traffic, the score distribution does not
move (PSI 0.001), recall halves, and the recall estimate computed a week after each week still reads
1.00 because no chargeback has arrived. The only fast signal is that, with a fixed number of alerts per
day, precision of the reviewed alerts falls (0.29 to 0.13): the alert budget is now filled by
legitimate transactions.

### 2.6 Limitations and common misconceptions

* *"PSI > 0.2 means retrain."* A folklore threshold, and drift is not degradation. Calibrate the
  threshold on stable reference windows (w7d2) and treat a flag as a reason to investigate the input.
* *"No labels yet, so precision is 0 (or 100 %)."* It is unknown. Report the count of pending labels.
* *"Recall from the labels we have is unbiased."* Missed events are found only by a separate process;
  recall from it is an upper bound, and early in the delay a very loose one.
* *"Monitor the model weekly."* Weekly windows may contain three labelled events. Derive the window from
  the label rate and the difference you need to detect.
* *"Drift detectors can replace labels."* Unsupervised performance estimation (e.g. confidence-based
  estimates of accuracy) assumes the model stays calibrated under the shift; under concept shift that
  assumption is exactly what fails.

---

## 3. Worked example: fraud alerts with late chargebacks (SYNTHETIC)

`example/fraud_label_delay.py` is self-contained (numpy and pandas only). It simulates 12 weeks of
4,000 transactions a day, 0.5 % fraud, the top 40 scores alerted and reviewed 1-3 days later, and
missed fraud charged back 30-90 days later for 90 % of cases. From week 7, half of the fraud scores like
legitimate traffic. The rules are stated in the file's docstring; nothing about real fraud follows.

```bash
python lessons/w7d3_drift_vs_degradation/example/fraud_label_delay.py
```

Output (verbatim from the authoring run):

```
 week  psi_scores  true_recall  recall_est_+7d  precision_+7d  recall_est_+30d  recall_est_+120d
    1        0.00         0.51            1.00           0.27             0.97              0.52
    2        0.00         0.57            1.00           0.29             0.96              0.60
    ...
    6        0.00         0.59            1.00           0.28             0.94              0.63
    7        0.00         0.28            1.00           0.15             0.81              0.29
    ...
   12        0.00         0.21            1.00           0.10             0.82              0.23

mean true recall: weeks 1-6 0.55, weeks 7-12 0.27
max PSI of the score distribution, weeks 5-12: 0.001
mean precision of reviewed alerts (+7 d): weeks 1-6 0.29, weeks 7-12 0.13
```

**Important code decisions.** `known_metrics` filters by `verdict_day <= as_of` and
`chargeback_day <= as_of` before computing anything; drop that filter and every column becomes the
`+120d` column. PSI is computed on the *score* distribution, the best case for a drift monitor: it is
the quantity closest to the decision, and it still does not move because fraud is 0.5 % of traffic.

**Interpretation.** Recall halved in week 7. Drift said nothing. Recall estimated a week later said
1.00 in every week; a month later it was still 0.81-0.94; only at 120 days did it approach the truth.
The fast signal was precision under a fixed alert budget, a proxy that works here because the number of
alerts is fixed by design. With a fixed *threshold* instead, the same concept shift would show as fewer
alerts, not lower precision. Know which design you are monitoring.

**Reproduce.** Seeded (`default_rng(42)`); the numbers above are exact on NumPy 2.5.3 / pandas 3.0.5.

---

## 4. Guided lab

Work in `lab/`. The `flowguard` snapshot there is complete except `src/flowguard/delayed_eval.py`.
Given modules you will use: `replay` (builds a timeline, logs predictions and alarms, simulates label
arrival), `drift` (calibrated PSI/KS/Wasserstein monitor), `uncertainty.wilson_interval`, `models`
(the shipped detector).

Data the functions receive (all `pandas.DataFrame`):

| Table | Columns | Produced by |
|---|---|---|
| `alarms` | `alarm_id, run_id, experiment_id, start_time, end_time, peak_score, model_version` | the service at prediction time |
| `verdicts` | `alarm_id, verdict (bool), fault_id (or None), label_time, source` | maintenance, later; may repeat an alarm |
| `fault_reports` | `fault_id, run_id, experiment_id, start_time, end_time, label_time, source` | inspections, much later; missed faults only |

Run the checks after each task: `python wb.py check w7d3` (all fail at the start; that is expected).

**Task 1: `join_verdicts(alarms, verdicts, as_of=None)`.** Keep only verdicts with
`label_time <= as_of` (all of them if `as_of` is None). For each alarm keep the verdict with the
*latest* `label_time` (corrections supersede). Left-join onto the alarms, preserving their order; a
missing verdict is `<NA>` (use pandas' nullable `boolean` dtype). Return `(joined, report)` with
`n_alarms`, `n_labelled`, `n_pending`, `orphan_verdicts` (verdicts whose alarm id is unknown) and
`superseded` (known verdicts that lost to a later one).
*Checkpoint:* `test_latest_label_time_wins_even_when_rows_arrive_out_of_order` and
`test_labels_after_as_of_do_not_exist_yet` pass.
*Debugging:* a `TypeError` from `Series.map` on an empty frame is a pandas edge case; a left `merge`
avoids it.

**Task 2: `alarm_precision(joined, min_labelled=5, level=0.95)`.** Precision among labelled alarms
only. Return `status` (`"ok"` or `"insufficient_data"`), `estimate`, `low`, `high` (Wilson), `k`, `n`,
`n_pending`. Below `min_labelled`, estimate and interval are NaN.
*Checkpoint:* `test_verification_bias_known_answer` passes. Read it: your function reports 1.0 on 10
labelled alarms while the truth is 0.5. That is correct behaviour; the bias is in the labelling process,
and the report (`n_pending = 10`) is what lets a reader see it.

**Task 3: `recall_estimate(joined, fault_reports, as_of=None, min_events=5, level=0.95)`.** Caught =
distinct `fault_id` among alarms confirmed True. Missed = distinct `fault_id` in reports known at
`as_of`, minus the caught ones. Estimate `caught / (caught + missed)` with a Wilson interval and the
same insufficiency rule; also return `n_caught` and `n_missed_reported`.
*Checkpoint:* `test_recall_counts_distinct_faults_and_only_known_reports`.

**Task 4: `window_metrics(...)`.** Windows `[start + k*freq, start + (k+1)*freq)` up to `end`. An
alarm belongs to the window of its `start_time`, a reported fault to the window of its `start_time`:
**event time decides where a label counts; label time decides whether it is known yet.** One row per
window with the columns used in the checks (`n_alarms`, `n_labelled`, `n_pending`, `precision`,
`precision_low/high/status`, `n_caught`, `n_missed_reported`, `recall`, `recall_low/high/status`).
*Checkpoint:* `test_windows_use_event_time_and_as_of`.

**Task 5: `monitor_report(drift_result, window, baseline, margin=0.1)`.** Judge each metric that has a
baseline (None = not monitored):

* `"unknown"` if its status is insufficient;
* `"no"` if the estimate is more than `margin` below baseline *and* the interval's upper end is below
  the baseline;
* `"yes"` if the interval's lower end is within `margin` of the baseline;
* otherwise `"inconclusive"`.

Combine: any "no" → "no", else any "inconclusive" → "inconclusive", else any "yes" → "yes", else
"unknown". `input_changed` is `drift_result["drift"]` and nothing else. Map the pair to an action: drift
without measured degradation investigates the input; degradation without drift escalates; never
infer one answer from the other.
*Checkpoint:* all 17 checks pass.

```mermaid
flowchart LR
    V{"Input valid?<br/>contract checks, per request"} -->|no| R["reject 422, count"]
    V -->|yes| D{"Input changed?<br/>calibrated drift monitor"}
    D -->|yes| DI["investigate the input source"]
    D -->|no| N1["nothing to do for inputs"]
    V -->|yes| P{"Model still good?<br/>delayed labels, as of today"}
    P -->|"not enough labels"| U["unknown: collect labels"]
    P -->|"clearly worse"| E["escalate: concept change, pipeline bug"]
    P -->|"interval straddles"| I["inconclusive: keep collecting"]
    P -->|"clearly not worse"| OK["no model action"]
```

**Task 6: replay on real data.** With your module in place:

```bash
python project/get_skab.py                                   # once
python lessons/w7d3_drift_vs_degradation/lab/replay_report.py \
    --json lessons/w7d3_drift_vs_degradation/lab/results/replay.json
```

The replay is a **construction from real parts**, stated in the script's docstring: the 20 labelled
valve recordings, one per day, three times. Period A as recorded; period B with the flow sensor
"recalibrated" to $1.08x + 2.5$ L/min; period C scored by a release whose configuration regression
doubled the threshold (14.49 instead of 7.24). Labels follow a simulated policy: every alarm
investigated (2-10 days), 60 % of missed faults reported (14-60 days), 10 % of verdicts duplicated and
half of those corrected. The drift monitor watches the flow rate with PSI, calibrated on the 16
development valve recordings of the frozen manifest v2 (99th percentile of 200 chunks: 0.660).

Reference output (authoring run):

```
67416 samples, 26 alarms, 60 faults; 29 verdict messages, 18 missed-fault reports
PSI threshold (99th percentile over 200 calibration chunks): 0.660
baseline recall (period A, all labels): 0.611
period A  day  65: drift 1/4, caught 11, missed reported 6, recall 0.65 [0.41, 0.83] (true 11/20) -> inconclusive
          day 150: drift 1/4, caught 11, missed reported 7, recall 0.61 [0.39, 0.80] (true 11/20) -> inconclusive
period B  day  65: drift 4/4, caught 11, missed reported 2, recall 0.85 [0.58, 0.96] (true 11/20) -> yes
          day 150: drift 4/4, caught 11, missed reported 4, recall 0.73 [0.48, 0.89] (true 11/20) -> inconclusive
period C  day  65: drift 1/4, caught  4, missed reported 0, recall  nan              (true  4/20) -> unknown
          day  90: drift 1/4, caught  4, missed reported 2, recall 0.67 [0.30, 0.90] (true  4/20) -> inconclusive
          day 150: drift 1/4, caught  4, missed reported 7, recall 0.36 [0.15, 0.65] (true  4/20) -> inconclusive
```

![PSI per 5-day window: period B (recalibrated sensor) sits at 6.1-8.9 against a threshold of 0.66; periods A and C stay below it except the first window of each](figures/drift_psi_windows.svg)

*Figure 3 (real recordings, constructed timeline).* The drift monitor flags all four windows of
period B. The first window of A and of C is flagged too (PSI 1.44): those five recordings
(valve1/0-4) run at a slightly different flow level from the reference, and they are also the five
whose faults the detector misses. The flag and the misses coincide; the level difference does not
cause the misses (the score is per-run normalised), which is exactly why a flag needs investigation
rather than a conclusion.

![Estimated recall against the day it is computed: all three periods start high and settle above their true values only after inspection reports arrive](figures/recall_over_time.svg)

*Figure 4 (real recordings, simulated labels).* Estimates start optimistic and settle late; all
three settle above the truth (0.61 and 0.73 against 0.55; 0.36 against 0.20) because only 60 % of
missed faults are ever reported.

What the replay shows, as found:

* **Drift without degradation (period B).** The recalibration moves PSI 9-13x past its threshold.
  The detector caught exactly the same 11 faults as in period A, because $|z|$ is invariant to
  $a x + b$ with $a > 0$. One caveat found while building this: 198 samples score *exactly* at the
  threshold (the flow sensor is quantised, and the w4d5 operating point was chosen from score quantiles),
  so the $10^{-14}$ rounding from the recalibration flips their flags and changes one alarm's extent,
  not which faults are caught. Put thresholds between distinct score values.
* **Degradation without drift (period C).** Recall fell from 11/20 to 4/20; the inputs are identical to
  period A, so the drift monitor says exactly what it said for A. The labels show it, late: unknown on
  day 65 (no missed-fault report yet), 0.67 on day 90, 0.36 on day 150.
* **Statistical power is the binding constraint.** Even on day 150, period C's interval [0.15, 0.65]
  overlaps period A's baseline of 0.61, so the rule reports "inconclusive", not "no". With 20 faults per
  period that is the honest answer. Period B on day 65 shows the opposite failure: an early, optimistic
  "yes" (0.85) before the missed-fault reports had arrived.
* **Precision says nothing here.** All 26 alarms were true faults, in every period. At this operating
  point (zero false alarms on development data) precision cannot move; the report monitors recall only.

---

## 5. Independent challenge

Write the monitoring and label-backfill plan for `flowguard`: [challenge/README.md](challenge/README.md).
No solution is given in this lesson; the rubric is in the solutions folder, to be opened after you
have written yours.

---

## 6. Progressive hints

Try each task for at least 10 minutes before opening a hint.

1. [Conceptual hint](hints/hint1_concept.md)
2. [Suggested approach](hints/hint2_approach.md)
3. [Partial implementation](hints/hint3_partial.md)

The full reference solution is in `solutions/lessons/w7d3_drift_vs_degradation/lab/`.

---

## 7. Assessment

[assessment.md](assessment.md): reasoning questions, a design-choice explanation, a rubric, and a
15-minute interview rep on delayed labels. Model answers are in the solutions folder.

---

## 8. Reflection and review

**You should now be able to, without notes:**
- distinguish covariate, prior and concept shift with $P(x)$, $P(y)$ and $P(y \mid x)$;
- explain why input drift neither implies nor is implied by performance loss, with one example each;
- compute precision and recall "as of" a date from late, duplicated, corrected labels;
- name the direction of the bias that verification and incomplete miss reporting introduce;
- size a monitoring window from the label rate and the difference you need to detect.

**Reflection prompt (5 minutes, in `progress/notes.md`).** Which of your research systems had
labels you trusted but which were produced by a selective process (who got the reference test, which
sessions were annotated)? Which direction did that bias your reported numbers?

**Retrieval question for review day.** *A recall estimate for last month reads 0.95; a month ago, the
same month read 1.00. Labels for missed faults take 14-60 days. What can you say about recall, and
what must you not say?*

**Next.** [w7d4 — Model updates: retraining triggers, shadow and canary, rollback](../w7d4_model_updates_rollback/README.md)
uses these monitors to decide *when* a model should be replaced, and then replaces it safely.

---

## Verification record

Executed on 2026-11-22, Python 3.13.18, NumPy 2.5.3, pandas 3.0.5, SciPy 1.18.1, matplotlib 3.11.2.

| What | Command | Outcome |
|---|---|---|
| Worked example | `python example/fraud_label_delay.py` | output above, verbatim |
| Lab checks vs reference | `python tools/verify_checks.py lessons/w7d3_drift_vs_degradation --part lab` | reference passes 17/17; 5 mutants rejected |
| Challenge checks vs reference | `... --part challenge` | reference passes 13/13; 5 mutants rejected |
| Shipped starters | `python -m pytest lessons/w7d3_drift_vs_degradation/checks -q` | lab: 17 failed; challenge: 8 failed, 5 passed |
| Real-data replay | `python solutions/.../lab/replay_report.py` | output above, about 2 s |
| Recalibration invariance | scripted comparison in the authoring session | same 11 faults caught; 198 flags differ, all at a score exactly equal to the threshold; max score difference 3.9e-14 |
| Figures | `python figures/make_figures.py` | 4 SVGs + `figure_data.csv`, each viewed as PNG |

Not verified: Python 3.11/3.12 locally (CI covers the checks), the time budget, and any claim about
real plants' fault or label rates (the timeline and the label policy are constructions).
