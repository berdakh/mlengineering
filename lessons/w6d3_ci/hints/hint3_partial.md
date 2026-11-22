# Hint 3 — partial implementation

A skeleton of `lab/.github/workflows/ci.yml` with the image job left to you:

```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: pyproject.toml
      - run: python -m pip install ruff
      - run: ruff check .
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
          cache-dependency-path: pyproject.toml
      - run: python -m pip install -e ".[dev]"
      - run: python -m pytest -q
  image:
    # needs: ...   (which jobs?)
    # steps: checkout; build; docker run -d ... -p 127.0.0.1:8000:8000 ...;
    #        python3 scripts/smoke_test.py --url http://127.0.0.1:8000 --timeout 60;
    #        docker logs app  if: failure()
```

Challenge, part 1, in `project/pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["perf: wall-clock performance checks; excluded from the per-push gate"]
addopts = "-m 'not perf'"
```
