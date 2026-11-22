# Changelog

All notable changes to flowguard. Versions follow semantic versioning; the HTTP contract has its own
schema name (`flowguard-api/1`), returned by `GET /version`.

## [0.6.0] - 2026-11-22 (release candidate, milestone 2)

### Added
- `flowguard build-model`: packages `configs/model.toml` as a checksummed bundle with provenance
  (config, split-manifest and development-data hashes).
- `flowguard predict-batch`: scores experiments to CSV with the packaged inference.
- HTTP API `flowguard-api/1`: `/healthz`, `/readyz`, `/version`, `/predict`.
- Parity tests: evaluation, batch and API scores are identical.

### Fixed
- The API computed the burn-in standard deviation with ddof=1 while training and evaluation used
  ddof=0 (training/serving skew of about 0.5 % at 100 burn-in rows). All paths now call `ZScoreModel.score`.
- Package version defined once (`flowguard.__version__`); `pyproject.toml` reads it.

## [0.5.0] - 2026-11-22 (milestone 1)

### Added
- Reproducible evaluation report (`make evaluate`), decision: burn-in flow-rate |z|.
