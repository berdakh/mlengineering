# CI failure diagnosis (REFERENCE SOLUTION, w6d3 challenge)

## 1. `01_test_job_flaky.log`: a wall-clock assertion in the per-push gate

**First explaining line.** `AssertionError: /predict took 79 ms` / `assert 0.0792... < 0.05`.

**Cause.** `test_predict_is_fast` asserts that one request finishes in 50 ms. The code did not change
between the red run and the green re-run; the machine did. A hosted runner is a shared virtual machine
whose speed varies from run to run, and a single timing sample has no margin for that variation.
Reproduced locally: with other CPU-bound work running on a 4-core machine the test failed 1 time in 12;
on the idle machine 0 times in 12. That is the signature of a flaky test, not a regression.

**Why only in CI (mostly).** Laptops are usually idle and faster than a 2- or 4-vCPU runner; a matrix
runs two jobs at once; the first request of a process pays import and warm-up costs.

**Fix.** The latency question is legitimate, so it is kept but moved to the slow lane: the test is
marked `perf` (marker registered in `pyproject.toml`), `addopts = "-m 'not perf'"` deselects it from
the default run, and the new scheduled workflow `perf.yml` runs `pytest -m perf`. The test itself was
made less noisy: one warm-up request, then the median of five, against a 200 ms budget.

**Evidence the fix works.** The default run (`pytest -q`) no longer contains any assertion on elapsed
time: it passes even when the wall clock is made to run 0.5 s per read (the slow-clock check).
`pytest -m perf --strict-markers` still collects and runs the latency test.

**"Re-run until green" is the wrong fix.** It trains the team to ignore red, and the next real
regression will be re-run too.

## 2. `02_test_job_cache.log`: a cache key that can never be hit

**First explaining line.** `Cache not found for input keys: pip-Linux-3.11-6f1c2a9e...`, on every run.

**Cause.** The key ends in `${{ github.sha }}`, the commit hash. Every push is a new commit, so every run
looks for a key that no earlier run could have saved, misses, downloads everything (69 s), and then saves
yet another entry under a new key, filling the repository's cache storage with entries nobody reads.

**Fix.** Key the cache on what determines its contents: the dependency declaration. The simplest
correct form is `actions/setup-python` with `cache: pip` and `cache-dependency-path: pyproject.toml`,
which keys on the runner OS, the Python version and a hash of that file. (Equivalent with
`actions/cache`: `key: pip-${{ runner.os }}-${{ matrix.python-version }}-${{ hashFiles('pyproject.toml') }}`
plus `restore-keys: pip-${{ runner.os }}-${{ matrix.python-version }}-`.)

**Evidence.** Static: no key contains a per-run value, and the key hashes a file that exists. The real
test is the second run after merging: it should print a cache hit, and the install step should drop
from about a minute to seconds. That cannot be checked from this repository.

## 3. `03_image_job.log`: a tool that the image does not contain

**First explaining line.** `sh: 1: curl: not found`, then `exit code 127` (command not found).

**Cause.** `docker exec app curl ...` runs curl inside the container. The image is built on
`python:3.12-slim`, which does not include curl (confirmed: `docker run --rm python:3.12-slim curl`
prints the same error). On a laptop the same check was probably run as `curl localhost:8000/healthz`
from the host, where curl exists.

**Fix.** Run the check from the runner, not inside the image: `scripts/smoke_test.py` is
standard-library Python, waits for `/readyz`, sends a request and checks the answer. Installing curl
in the image would also work (`apt-get install -y --no-install-recommends curl`), but it adds a tool to
the production image only for testing; if a container health check is needed inside the image, a
one-line `python -c` with `urllib.request` avoids the extra package.

**Evidence.** The smoke script passed against the real image built from `project/Dockerfile`
(ready, then `/predict` scored 150 samples, and an empty request was rejected with 422).
