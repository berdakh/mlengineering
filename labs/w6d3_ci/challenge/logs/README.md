# Three failing CI runs

Each log is one failing job of `project/.github/workflows/ci.yml`. Read them as you would read the
Actions tab: find the first line that explains the failure, then the cause, then the fix.

Provenance (be clear about what these are):

| Log | What is real | What is reconstructed |
|---|---|---|
| `01_test_job_flaky.log` | The pytest failure block was captured from a real run of `project/tests/test_latency.py` on a 4-core machine with other CPU-bound work running: 1 failure in 12 runs (0 failures in 12 runs on the idle machine). | The surrounding lines imitate GitHub Actions output; they were not captured on GitHub. |
| `02_test_job_cache.log` | The workflow file and its cache key are the real ones in `project/`. | The whole log is reconstructed in the format GitHub Actions prints; it was not captured on GitHub. |
| `03_image_job.log` | `sh: 1: curl: not found` and exit code 127 were captured by running `docker exec app curl ...` against the real image built from `project/Dockerfile` (base `python:3.12-slim`). | The surrounding lines imitate GitHub Actions output. |
