---
title: "flowguard interface spec"
parent: Maintainers
nav_order: 3
---

# `flowguard` interface specification (portfolio project spine)

Lessons are authored independently, so they agree on these names. A lesson that needs an upstream
module ships a small snapshot of it in its `lab/` starter, written to this spec. The learner's own
project repository is the real thing; snapshots exist so each lab runs on its own.

Package: `flowguard`, src layout, Python >= 3.11, console script `flowguard`.
Runtime dependencies: numpy, pandas, scikit-learn (+ torch only in w4d3; fastapi/uvicorn/pydantic from Week 5).

## Data conventions

* Raw: `data/raw/skab/<family>/<n>.csv` from `project/get_skab.py` (semicolon separated).
* `experiment_id` = `"<family>/<n>"`, e.g. `"valve1/0"`; `family` in {`valve1`, `valve2`, `other`, `anomaly-free`}.
* Canonical column names (snake_case):
  `datetime, accelerometer1_rms, accelerometer2_rms, current, pressure, temperature, thermocouple,
  voltage, flow_rate, anomaly, changepoint`. `SENSOR_COLUMNS` is the eight sensor names in that order.
  `anomaly`/`changepoint` are int 0/1; for `anomaly-free` they are 0.
* Tidy table: one row per (experiment_id, timestamp), sorted by `experiment_id, datetime`, with
  `experiment_id, family, t` (0-based row index within experiment) + the canonical columns.
  Stored as `data/interim/skab.csv` (no parquet dependency).
* Checks never need the downloaded data: they use tiny SYNTHETIC frames in this schema built in
  `checks/` (labelled synthetic). Labs and worked examples use the real files and say what to run first
  (`python project/get_skab.py`); they print a clear message if the data is absent.

## Modules and signatures

| Module | Public API | Introduced |
|---|---|---|
| `flowguard.data` | `SENSOR_COLUMNS`; `load_experiment(path) -> DataFrame`; `load_raw(raw_dir) -> DataFrame` (tidy) | w1d6 |
| `flowguard.quality` | `CheckResult(name, passed, detail)`; `run_checks(tidy) -> list[CheckResult]`; raises nothing, reports | w2d3 |
| `flowguard.ingest` | `ingest(raw_dir, out_dir) -> dict` (writes `skab.csv`, `quality_report.json`, `provenance.json`) | w2d3 |
| `flowguard.splits` | `make_splits(tidy, seed=0, n_folds=4, test_fraction=0.25) -> dict`; `save_splits`, `load_splits`; `validate_splits(manifest, tidy)` raises `ValueError` on overlap/unknown ids | w2d4 |
| `flowguard.features` | `causal_rolling_features(tidy, windows=(10, 30, 60)) -> DataFrame` (past-and-present only, per experiment); `ReferenceStats.fit(train).transform(df)` | w2d5 |
| `flowguard.baselines` | scorers with `fit(train_tidy)` and `score(tidy) -> np.ndarray` (higher = more anomalous) | w2d6 |
| `flowguard.metrics` | point-level: `pr_auc`, `precision_recall_at_threshold`, `best_f1_threshold` | w2d6 |
| `flowguard.evaluation` | `extract_events(binary) -> list[(start, end)]`; `match_events(...)`; `event_recall`, `detection_delay`, `false_alarms_per_hour` | w3d4 |
| `flowguard.uncertainty` | `cluster_bootstrap(metric_fn, per_experiment_results, n_boot, seed)` | w3d5 |
| `flowguard.inference` | `Detector` bundle: `fit`, `score_batch(tidy)`, `StreamScorer.update(row) -> float`; `save(path)`, `load(path)` | w5d1-w5d3 |
| `flowguard.api` | FastAPI app factory `create_app(model_dir) -> FastAPI`; `/predict`, `/healthz`, `/readyz` | w5d4 |
| `flowguard.cli` | subcommands `ingest`, `split`, `features`, `train`, `evaluate`, `sweep`, `predict-batch`, `serve` | incremental |

Split manifest (`splits/v1.json`):
`{"version": "v1", "seed": 0, "unit": "experiment_id", "test": [...], "dev_folds": [[...], ...],
"reference_normal": ["anomaly-free/anomaly-free"], "protocol_b": {"holdout_family": "other"}}`

Config and run directories follow lesson w1d4 (`configs/*.toml`, `runs/<run_id>/`).

## Amendments after Week 2 (binding for Week 3 onward)

Facts found on the real files (see `docs/guides/project.md`, "Findings from the Week 1-2 lessons"):

* Five pairs of files share identical rows (1,290 rows, 235 with contradictory labels). Overlap groups
  (connected components): `{anomaly-free/anomaly-free, other/5}`, `{other/12, other/13}`,
  `{other/2, other/3, other/4}`, `{other/10, other/11}`.
* Elapsed time / row index `t` predicts the label (anomaly starts at row 550-600 in 31 of 34 files).
  `t`, `datetime` and anything monotone in them are **forbidden as model features**.
* The fault-free recording is far from the normal regime of the labelled experiments; per-experiment
  burn-in normalisation (statistics from the first rows of each experiment, e.g. the first 300, all
  normal in every file) is the working reference.

API additions:

| Module | Addition | Introduced |
|---|---|---|
| `flowguard.splits` | `find_overlap_groups(tidy) -> list[set[str]]`; `make_splits(..., keep_together=None)` keeps each group on one side; manifest `"version": "v2"` adds `"overlap_groups"`; `validate_splits` rejects a manifest that separates a group | w3d1 |
| `flowguard.quality` | `CheckResult` has a 4th field `severity` (`"error"`/`"warning"`) | w2d3 |
| `flowguard.splits` | `save_splits(..., overwrite=False)` raises `FileExistsError` | w2d4 |
| `flowguard.features` | `burn_in_normalise(tidy, n_burn_in=300)` | w2d5/w2d6 |
| `flowguard.benchmark` | `evaluate_scores(...)` point-level table per family | w2d6 |

Week 3+ units that need a manifest build a v2 one with their snapshot and state that it supersedes v1.

## Additions in Week 4 (as built in the lesson snapshots)

| Module | Purpose | Introduced |
|---|---|---|
| `flowguard.forecast` | naive / AR one-step forecasters, residual scores, CUSUM | w4d1 |
| `flowguard.windowfeatures` | causal window features for the supervised detectors | w4d2 |
| `flowguard.detectors` | PCA (T2, Q), isolation forest, gradient-boosted trees, common fit/score interface | w4d2, w4d5 |
| `flowguard.neural` | window dataset, small conv autoencoder, early stopping (PyTorch, CPU) | w4d3 |
| `flowguard.tracking` / CLI `sweep`, `runs table`, `runs reproduce` | run registry and sweeps over w1d4 run directories | w4d4 |
| `flowguard.decision` | latency percentiles, model size, Pareto front, interval-vs-MPID reading | w4d5 |
| `flowguard.operating` | alert-budget threshold selection | w4d5 |
| `flowguard.pipeline`, `flowguard.svgplot` | `make evaluate` report pipeline; dependency-free byte-reproducible SVG | w4d6 |

All real-data results from Week 3 on use the frozen manifest
`solutions/labs/w3d1_leakage/lab/splits/v2.json` (7 test, 27 development experiments).

## Additions in Week 5 (as built in the lesson snapshots)

| Module | Purpose | Introduced |
|---|---|---|
| `flowguard.inference` | `Detector`: one object owning burn-in state, features, scoring and the input schema | w5d1 |
| `flowguard.batch`, CLI `predict-batch` | idempotent batch scoring with model version in the output | w5d1 |
| `flowguard.artifacts` | checksummed bundles without pickle (JSON + npz); registry with immutable versions and an atomic `current` pointer | w5d2 |
| `flowguard.streaming` | `StreamScorer.update(row)`, `StreamRegistry`; batch parity | w5d3 |
| `flowguard.api` | `create_app(model_dir)`: `/predict`, `/healthz`, `/readyz`, `/version`; 422/503 semantics | w5d4 |

The shipped model from w4d5 onward: burn-in flow-rate z-score, threshold 7.2441 (alert-budget operating point).
CSV round trips use `float_precision="round_trip"`; the default parser is not exact.
