# Hint 2 — approach

**Lab, `ci.yml`.** Three jobs: `lint`, `test` (matrix), `image` (`needs: [lint, test]`). Top level:
`on` (push to main, pull_request), `permissions: {contents: read}`, `concurrency` (group on
`github.ref`, cancel in progress). Each job: `timeout-minutes`. Each `uses:` at a release tag.
In `test`: `actions/setup-python@v7` with `python-version: ${{ matrix.python-version }}`,
`cache: pip`, `cache-dependency-path: pyproject.toml`.

**Lab, `evaluate.yml`.** `on: schedule` (cron) and `workflow_dispatch`; same permissions; one job
that installs, runs `scripts/fetch_skab.py`, `scripts/evaluate.py --min-events 4`, `pytest -m perf`,
then `actions/upload-artifact@v7` with `if: always()`.

**Challenge.**
1. Flaky test: keep it, mark it `@pytest.mark.perf`, register the marker in `pyproject.toml`
   (`markers = [...]`), deselect it by default (`addopts = "-m 'not perf'"`), and add a scheduled
   workflow that runs `pytest -m perf`. Make the measurement itself less noisy while you are there.
2. Cache: replace the `actions/cache` step by setup-python's `cache: pip`, or keep `actions/cache` with
   a key built from `runner.os`, the Python version and `hashFiles('pyproject.toml')`.
3. Image: run the check from the runner (the smoke script) instead of inside the container, or install
   the tool in the image (and say why you chose which).
