---
title: Troubleshooting
parent: Guides
nav_order: 6
---

# Troubleshooting
{: .no_toc }

Every entry below happened while this course was built and run.

1. TOC
{:toc}

---

## Setup

**`ModuleNotFoundError: No module named 'tomllib'`.** Your Python is 3.10 or older. See
[Setup, step 1](setup.html#1-python-311-or-newer).

**A SQL lab says your SQLite is too old for window functions.** Python is linked against an old SQLite
library. A newer Python build (3.11+ from python.org, uv or your distribution) brings a newer SQLite.

**The SKAB files are missing.** Run `python project/get_skab.py` from the repository root. Labs and checks
never need it; worked examples and real-data results do.

**A notebook cell says it cannot find a file.** Run the notebook's first code cell: it moves into the
repository root, and every command assumes that.

## Checks

**The checks fail on a fresh starter.** That is intended: they test work you have not done yet.

**Running two check folders in one `pytest` command fails with a `conftest` name clash.** Run them one at a
time (`wb.py check` and `check()` already do).

**A check passed once and failed the next time.** Report it. A few checks are statistical or timing-based
and were hardened after exactly this happened; any remaining flakiness is a bug in the course.

## Numbers that do not match the notebook

**Tiny differences in the last digits after a CSV round trip.** pandas' default float parser is not exact.
Read with `float_precision="round_trip"` (notebook 25 explains why it matters).

**Something that took seconds takes minutes.** NumPy/scikit-learn thread oversubscription: on a busy machine
the default threading made one step 8,153 ms instead of 3.5 ms. Set `OMP_NUM_THREADS=1` for the run, and do
not run two heavy jobs at once.

**Metrics differ from the notebook on another machine.** Check that you use the frozen split manifest
(`v2.json`, 7 test experiments) and the locked versions in `requirements-lock.txt`.

## Services and containers

**`Address already in use`.** A previous server is still running. `pkill -f uvicorn`, or use another port.

**A NaN in a request returns 500 instead of 422.** FastAPI's default validation handler tries to echo the
input as JSON. The course's service uses its own handler (notebook 28).

**Latency jumps by about 40 ms with two or more uvicorn workers.** Nagle's algorithm on the socket. Notebook 34
measures it and shows the `TCP_NODELAY` fix.

**`docker: Cannot connect to the Docker daemon`.** Docker Engine is not running: `sudo systemctl start docker`,
and add yourself to the `docker` group (log out and in) to run without `sudo`.

**The container ignores Ctrl+C or takes 10 s to stop.** A shell-form `CMD` makes the shell PID 1, which does not
forward SIGTERM. Use the exec form (notebook 31).

## GitHub

**CI jobs fail within a second, with no logs.** The account has no Actions minutes left (or a spending limit).
Public repositories get free minutes; private ones have a monthly quota. Check Settings → Billing.
