# w6d1 lab: containerise the flowguard API

Everything in this directory is the **build context**: the service snapshot from Week 5 (given)
plus three files you write.

| Path | What it is | You edit it? |
|---|---|---|
| `src/flowguard/` | the API (`create_app_from_env` reads `FLOWGUARD_MODEL_DIR`), detector, bundle loader | no |
| `models/flowguard-z/1.0.0/` | the w4d5 model as a checksummed JSON bundle | no |
| `requirements.txt` | serving dependencies, pinned | no |
| `requirements-dev.txt` | training and test tools (scipy, pytest, httpx): **not** for the image | no |
| `scripts/` | `build_bundle.py` (rebuild the model from real SKAB data), `make_request.py`, `make_smoke_fixture.py` | no |
| `smoke/` | a SYNTHETIC request and the scores the model must return for it | no |
| `Dockerfile` | the image recipe | **yes** |
| `.dockerignore` | what the build context must not contain (create it) | **yes** |
| `run_container.sh` | build + run on the loopback interface | **yes** |

Checks: `python wb.py check w6d1` (static, no Docker needed). With a Docker daemon also:
`WB_DOCKER=1 python -m pytest labs/w6d1_docker_basics/checks -q -k live`.
