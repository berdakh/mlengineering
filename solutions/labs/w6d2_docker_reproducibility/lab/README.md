# w6d2 lab: a reproducible, multi-stage image and a smoke test

The build context is the Week 5 service snapshot (given) plus what you write or generate.

| Path | What it is | You edit it? |
|---|---|---|
| `src/`, `models/`, `smoke/`, `scripts/build_bundle.py`, `scripts/make_*.py` | service, model, smoke fixture (as in w6d1) | no |
| `requirements.in` | serving dependencies as *ranges* the code supports | no (read it) |
| `requirements-dev.txt` | dev/training tools, not for the image | no |
| `requirements.lock` | every package, transitive ones included, pinned with `==` and sha256 hashes | **generate it** |
| `Dockerfile` | starts as the w6d1 reference; becomes digest-pinned and multi-stage | **yes** |
| `.dockerignore` | as in w6d1 (given) | no |
| `scripts/smoke_test.py` | waits for readiness, checks the 300 expected scores, exits 0/1/2 | **yes** |

Checks: `python wb.py check w6d2` (no Docker needed: the smoke test is graded against services the
checks start in-process). With Docker also:
`WB_DOCKER=1 python -m pytest labs/w6d2_docker_reproducibility/checks -q -k live`.
