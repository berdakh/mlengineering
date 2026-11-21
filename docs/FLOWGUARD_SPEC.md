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
