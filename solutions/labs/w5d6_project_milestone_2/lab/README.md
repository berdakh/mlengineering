# flowguard

Fault detection on the SKAB water-circulation testbed. **Educational prototype**: no claim about any
real plant. Model: burn-in flow-rate |z| with an alert-budget threshold (decision memo: w4d5;
evaluation report: milestone 1). Version: see `src/flowguard/__init__.py` and `CHANGELOG.md`.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"            # or: export PYTHONPATH=src (the Makefile does this)
```

## Usage

`RAW` points at the SKAB files (`python project/get_skab.py` in the course repository downloads them).

```bash
make model RAW=$RAW
make test
python -m flowguard predict-batch --model models/current --raw $RAW --splits splits/v2.json --split test --out predictions/test.csv
python -m flowguard evaluate --model models/current --raw $RAW --splits splits/v2.json --split test
make serve
curl -s http://127.0.0.1:8000/readyz
curl -s -X POST http://127.0.0.1:8000/predict -H 'content-type: application/json' -d '{"burn_in": [32.1, 32.4, 31.9], "values": [32.0, 25.3]}'
```

`/predict` takes `burn_in` (the first readings of the run, 2-3600 values) and `values` (1-3600
readings, oldest first) and returns one score and one `above_threshold` flag per value. Full contract:
`GET /docs` on a running server.

## Layout

```
configs/model.toml      operating point of the shipped detector
splits/v2.json          frozen split manifest (w3d1)
src/flowguard/          scoring (the one score formula), bundle, inference, evaluation, api, cli
tests/                  unit, integration, API and parity tests
models/current/         built by `make model` (not committed)
```

## Limitations

Seven independent test experiments; one laboratory testbed; labels mark whole anomalous segments and
some duplicated rows carry contradictory labels. See the milestone-1 report.
