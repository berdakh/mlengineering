# Tested versions

"Execution verified" in this repository means: executed in the authoring environment below.
Lower bounds in `requirements.txt` are intentions, not test results, unless a CI row confirms them.

## Authoring environment (2026-11-21)

| Component | Version |
|---|---|
| Python | 3.13.18 |
| numpy | 2.5.3 |
| pandas | 3.0.5 |
| scikit-learn | 1.9.1 |
| scipy | 1.18.1 |
| pydantic | 2.13.5 |
| pytest | 9.1.1 |
| SQLite (stdlib `sqlite3`) | 3.53.1 |
| OS | Linux x86_64, glibc 2.39 (container) |

## Continuous integration

`.github/workflows/ci.yml` runs `python tools/verify_checks.py --all` on Python 3.11, 3.12 and 3.13
with the newest package versions that satisfy `requirements.txt`. The result of the first run is
recorded in `STATUS.md`; check the repository's Actions tab for the current state.

## Not tested

* Pop!_OS itself (the authoring environment is a Linux container, not your machine).
* Python 3.10 and older: unsupported, because the labs use `tomllib` (standard library from 3.11).
  Pop!_OS 22.04 ships Python 3.10; lesson w1d3 explains how to obtain a newer interpreter.
* GPU execution. Nothing authored so far uses PyTorch.
* Docker, FastAPI, AWS: no material depends on them yet.
