# flowguard

Fault detection on the SKAB water-circulation testbed recordings. Educational prototype; no claim
about any real plant.

## Status

v0.1.0 - project skeleton: loading and summarising the raw experiments. No model yet.

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Data

SKAB v0.9 (GPL-3.0) is **not** stored in this repository. Fetch it with the course script
`python project/get_skab.py`, which writes `data/raw/skab/` and a `MANIFEST.json` with checksums.
`data/` is git-ignored.

## Use

```bash
flowguard summary --raw-dir data/raw/skab      # per-experiment row counts and anomaly fraction (JSON)
python -m pytest -q                            # tests use tiny synthetic files; no download needed
```

## Layout

```
src/flowguard/data.py   load_experiment, load_raw, summarize, SENSOR_COLUMNS
src/flowguard/cli.py    `flowguard` command
tests/                  unit tests on synthetic SKAB-format files
```

## Known facts and open questions about the data

See `NOTES.md` (things the exploratory notebook got wrong, and what was found when they were fixed).
