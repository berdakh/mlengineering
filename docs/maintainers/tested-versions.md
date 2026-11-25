---
title: "Tested versions"
parent: Maintainers
nav_order: 4
---

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
| matplotlib (figures only) | 3.11.2 |
| PyTorch (w4d3 only) | 2.15.0 |
| FastAPI / Starlette / uvicorn / httpx | 0.165.0 / 1.7.0 / 0.54.0 / 0.28.1 |
| Docker Engine | 29.10.0 |
| OS | Linux x86_64, glibc 2.39 (container) |

## Continuous integration

`.github/workflows/ci.yml` runs `python tools/verify_checks.py --all` on Python 3.11, 3.12 and 3.13
with the newest package versions that satisfy `requirements.txt`. Runs passed on all three versions through Week 3; later runs did not start (see `STATUS.md`, "CI result"); check the repository's Actions tab for the current state.

## Not tested

* Pop!_OS itself (the authoring environment is a Linux container, not your machine).
* Python 3.10 and older: unsupported, because the labs use `tomllib` (standard library from 3.11).
  Pop!_OS 22.04 ships Python 3.10; lesson w1d3 explains how to obtain a newer interpreter.
* GPU execution (w4d3 ran on CPU only).
* AWS: no AWS call was ever made; deployment content is verified only against CLI example sources and API models.
