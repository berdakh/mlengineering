# Data notes: SKAB as ingested (reference)

## Source and reproduction

- Source: <https://github.com/waico/SKAB>, commit `b2c0d46c2971dcbfe71e26087b6d231998bb91c2`, GPL-3.0
  (carried from `data/raw/skab/MANIFEST.json` into `provenance.json`).
- Regenerate: `python project/get_skab.py && flowguard ingest --raw-dir data/raw/skab --out-dir data/interim`
- Output (run of 2026-11-21, pandas 3.0.5): 46,806 rows, 35 experiments,
  SHA-256 `30646971eb5e8f5fd81f69311ad578e5250e4cd1bc875779c2c03a1822d365d0`. Two runs were byte-identical.

## Schema as ingested

| Column | Type | Unit | Notes |
|---|---|---|---|
| experiment_id | str | - | `<family>/<n>` from the file path |
| family | str | - | `anomaly-free`, `other`, `valve1`, `valve2` |
| t | int | rows | 0-based row index in file order; **not** seconds (see gaps) |
| datetime | datetime, naive | - | fixed format `%Y-%m-%d %H:%M:%S`; laboratory local time, no offset recorded |
| accelerometer1_rms, accelerometer2_rms | float64 | g | per-experiment baseline differs by orders of magnitude relative to within-experiment noise |
| current | float64 | A | |
| pressure | float64 | bar | quantised (as few as 5 distinct values per experiment); negative values occur (min -1.257) |
| temperature | float64 | deg C | motor body |
| thermocouple | float64 | deg C | fluid |
| voltage | float64 | V | |
| flow_rate | float64 | L/min | upstream name `Volume Flow RateRMS`; quantised, repeats up to 43 samples |
| anomaly, changepoint | int64 0/1 | - | floats in the raw files; absent in `anomaly-free`, written as 0 |

## Checks and their severity

| Check | Severity | Threshold and origin | Result on the real data |
|---|---|---|---|
| required_columns | error | spec | pass |
| no_missing_values | error | none tolerated; none exist | pass |
| labels_binary | error | {0, 1} | pass |
| unique_timestamps | error | key (experiment_id, datetime) | pass |
| time_ordered | error | non-decreasing in file order | pass |
| anomaly_free_is_clean | error | by definition of the file | pass |
| sampling_gaps | warning | > 5 s; nominal step 1 s, 5 % of steps are 2 s, 56 are 3-4 s | **fails: 9 gaps in 6 experiments, largest 247 s** |
| stuck_sensors | warning | run >= 120; longest legitimate run is 43 (flow_rate) | pass |
| plausible_ranges | warning | generous physical limits, not statistical | pass |
| one_anomaly_segment | warning | evaluation design assumes exactly one | pass |
| enough_rows | warning | >= 100; smallest experiment has 745 | pass |

## Findings that force a decision

| Finding | Decision | Owner step |
|---|---|---|
| 9 gaps > 5 s in other/13, other/2, valve1/2, valve1/4, valve1/7, valve2/1; 7 of 9 inside the anomalous segment | windows must not span a gap or must be defined in seconds; delay measured in seconds | w2d5, w3d4 |
| 34.9 % of labelled samples are anomalous | read point metrics against a 0.35 base rate; the scarce unit is the event (34) | w2d6, w3d4 |
| between-experiment SD of normal-operation means is 60-200x the within-experiment SD for 4 sensors | per-experiment causal reference for features; evaluate on unseen experiments | w2d4, w2d5 |
| valve families: flow_rate falls about 4 SD in nearly every experiment; `other`: no sensor moves in more than 57 % of experiments | hold out a family as a second protocol | w2d4 |
| pressure and flow_rate are quantised | stuck-sensor threshold far above quantisation runs; beware zero-variance windows in features | w2d5 |

## Open questions

- Is pressure gauge pressure (so negative values are physical) or noise about a zero offset? Upstream README is silent.
- Timestamps are naive. Only within-experiment differences are used, so this is harmless here; it would not be for a join against any other system.
- Why do gaps cluster inside anomalous segments? If the logger drops samples when the system is disturbed, "gap" is itself informative and a feature built from it would leak the labelling procedure rather than the physics.
