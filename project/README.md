# Portfolio project: `flowguard` - fault detection on a water-circulation testbed

Status: **brief written and dataset access verified; project work starts in w1d6.**
Everything below marked "decision" is a starting position you are expected to challenge in w2d4.

## Why this dataset

The project uses the **Skoltech Anomaly Benchmark (SKAB) v0.9**: multivariate sensor recordings from
a laboratory water-circulation testbed (pump, motor, valves, tank), one CSV per experiment.

It was chosen over the alternatives because it supports the *whole* workflow of this course on a CPU:

| Need | What SKAB provides |
|---|---|
| A grouped structure, so generalisation must be evaluated across independent units | 34 labelled experiments; the experiment is the unit, as the patient is in your EEG work |
| Temporal structure, so look-ahead leakage is possible and must be prevented | about 1 Hz multivariate series, 745-1,327 rows per experiment |
| Point *and* event labels | `anomaly` (per-sample) and `changepoint` (transition markers) columns |
| Distribution shift to study | three experiment families (`valve1`, `valve2`, `other`) with different fault mechanisms |
| Fault-free reference data | one `anomaly-free` recording (9,405 rows) |
| Small enough to iterate | 35 files, about 4.3 MB in total |

Alternatives considered: NASA C-MAPSS turbofan degradation (good grouped structure, but simulated
and remaining-useful-life regression does not exercise event-level detection); UCI hydraulic
condition monitoring (per-cycle classification, little temporal structure between cycles);
physiological datasets (too close to your existing expertise to demonstrate transfer).

## Provenance and terms (verified 2026-11-21)

* Source: <https://github.com/waico/SKAB>, pinned to commit `b2c0d46c2971dcbfe71e26087b6d231998bb91c2`.
* Licence: **GPL-3.0** (upstream `LICENSE` file and README badge were opened and read).
  Consequence adopted here: the data is **not copied into this repository**. `project/get_skab.py`
  downloads it to `data/raw/skab/` (git-ignored) and writes `MANIFEST.json` with a SHA-256 per file.
  If you later publish derived data or redistribute files, re-read the licence yourself; this is not legal advice.
* Citation: Katser, I. D., Kozitsin, V. O. (2020). *Skoltech Anomaly Benchmark (SKAB)*. Kaggle.
  DOI 10.34740/KAGGLE/DSV/1693952.
* Fetch and verify:

  ```bash
  python project/get_skab.py            # executed 2026-11-21: 35 files downloaded
  python project/get_skab.py --verify   # executed: all files match MANIFEST.json
  ```

## Data dictionary (from the upstream README; units as stated there)

Files are semicolon-separated. One row per timestamp.

| Column | Meaning | Unit |
|---|---|---|
| `datetime` | time the value was written to the database | YYYY-MM-DD hh:mm:ss |
| `Accelerometer1RMS`, `Accelerometer2RMS` | vibration acceleration | g |
| `Current` | motor current | A |
| `Pressure` | pressure in the loop after the pump | bar |
| `Temperature` | motor body temperature | deg C |
| `Thermocouple` | fluid temperature in the loop | deg C |
| `Voltage` | motor voltage | V |
| `Volume Flow RateRMS` | circulation flow rate (the upstream README calls it `RateRMS`) | L/min |
| `anomaly` | 1 if the sample is labelled anomalous | 0/1, absent in `anomaly-free` |
| `changepoint` | 1 at labelled transition points | 0/1, absent in `anomaly-free` |

## Measured facts about the files (computed in the authoring session, 2026-11-21)

* 34 labelled experiments: `valve1` 16, `valve2` 4, `other` 14; 37,401 labelled rows in total.
* Every labelled experiment contains **exactly one contiguous anomalous segment**; 34 events in all.
* Mean per-file fraction of anomalous samples is about 0.35 (range 0.25-0.49). The positive class is
  therefore *not* rare at the sample level, unlike most production anomaly problems.
* 129 `changepoint` marks in total (2-4 per file).
* Median sampling interval 1 s. Seven files contain a gap longer than 5 s (largest 247 s in `other/2.csv`).
* No missing values in any column.
* Note: the upstream folder listing numbers files from 1, the actual files from 0 (`valve1/0.csv` ... `valve1/15.csv`).

These facts drive design decisions. With 34 events, any event-level metric has wide uncertainty:
this project must report intervals (w3d5) and must not claim small differences between models.

## Starting decisions (to be revisited in w2d4)

1. **Stakeholder and need.** A plant reliability engineer wants an alert soon after abnormal operation
   begins, with few enough false alerts to be trusted. Educational prototype; no claim about any real plant.
2. **Task framing.** Per-timestamp anomaly scoring from past data only, turned into alerts by a threshold.
   Primary comparison: semi-supervised detectors fitted on normal data versus supervised window classifiers.
   Whether the labels support the supervised framing across fault families is itself a question to answer.
3. **Splits.** By experiment, never by row. A fixed test set of whole experiments; development by grouped
   cross-validation. A second protocol holds out the entire `other` family to measure generalisation to
   unseen fault mechanisms. Within an experiment only causal (past-only) features are allowed.
4. **Evaluation.** Point-level (precision/recall/PR-AUC) *and* event-level (event recall, detection delay,
   false alarms per hour of normal operation), with experiment-level bootstrap intervals.
5. **Not a forecasting project.** The labels are anomaly segments, not future values; forecasting models
   appear only as a means of producing residual scores.

## Deliverables checklist

| Deliverable | Session | Done |
|---|---|---|
| Problem statement and stakeholder needs | w2d4 | [ ] |
| Dataset provenance and data dictionary | this file, extended in w2d3 | [~] |
| Versioned split definitions | w2d4 | [ ] |
| Reproducible preprocessing | w2d3, w2d5 | [ ] |
| Simple baseline | w2d6 | [ ] |
| Evidence-based model comparison | w4d2-w4d5 | [ ] |
| Error analysis | w3d6, w4d6 | [ ] |
| Training and evaluation commands | w4d4, w4d6 | [ ] |
| Packaged inference | w5d1-w5d3 | [ ] |
| Tests | from w1d6 onward | [ ] |
| Prediction API | w5d4-w5d5 | [ ] |
| Container | w6d1-w6d2 | [ ] |
| One deployment (authorisation-gated) | w6d5 | [ ] |
| Monitoring demonstration | w7d6 | [ ] |
| README, model limitations, short technical report | w8d1-w8d2 | [ ] |

## Transfer exercise (small, not a second capstone)

Two short sittings on an unfamiliar **tabular business** problem: baseline (w2d6) and a complete
leak-free evaluation in 90 minutes (w3d6). Candidate public dataset: UCI Bank Marketing. Its licence
and access have **not** been verified yet; that happens when w2d6 is authored. The diagnostic already
uses a synthetic business dataset so transfer can be probed from day one.
