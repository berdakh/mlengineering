---
title: "GitHub Actions"
parent: Tool guides
nav_order: 14
---
{% raw %}

# GitHub Actions
{: .no_toc }

GitHub Actions is the automation service built into GitHub. Its most common use is **continuous integration
(CI)**: every push and pull request starts a fresh machine that installs your project and runs its tests, and the
result appears as a green check or a red cross next to the commit. This guide is the reference for
[notebook 39](../notebooks/39_ci_github_actions.html) and [the Week 10 lab](../notebooks/40_lab_container_and_ci.html).

1. TOC
{:toc}

## What it is, and why teams use it

Tests protect a project only if they run, on every change, in a clean environment. CI makes that automatic.
Combined with **branch protection** (GitHub refuses to merge a pull request until the checks pass), it turns
"please run the tests" into a rule. Teams also use Actions to build container images, publish packages, deploy,
and run scheduled jobs (for example a nightly data check).

| Word | Meaning |
|---|---|
| **workflow** | a YAML file in `.github/workflows/` describing what to run and when |
| **event** | what starts a workflow: `push`, `pull_request`, `schedule`, `workflow_dispatch` (a button) |
| **job** | a set of steps that runs on one machine; jobs run in parallel unless one `needs` another |
| **runner** | the machine a job runs on; `ubuntu-latest` is a fresh Linux virtual machine hosted by GitHub |
| **step** | one item of a job: `uses:` an action, or `run:` shell commands |
| **action** | a reusable, versioned step published by someone, e.g. `actions/checkout@v7` |
| **run** | one execution of a workflow, with its logs, under the repository's **Actions** tab |

**Cost.** Actions is free for public repositories on GitHub-hosted runners. Private repositories get a monthly
allowance of minutes that depends on the account's plan; when it runs out, workflows stop unless a payment method
and a spending limit are set. Keep jobs short, use caching, and add `timeout-minutes`.

## Where workflows live and how they start

Put a file such as `.github/workflows/ci.yml` in the repository and push it. GitHub reads every file in that
folder on each event; nothing else needs to be switched on for a repository you own. The run appears in the
**Actions** tab within seconds, and its result shows on the commit and on any pull request.

## YAML in five rules

Workflows are YAML, a text format for nested dicts and lists:

1. `key: value` is a dict entry; nesting is done with **spaces** (never tabs), usually two per level;
2. `- item` is a list item; `[a, b]` is a list on one line;
3. `run: |` starts a multi-line string; each following, more-indented line is one line of a shell script;
4. quote values that could be misread: `"3.10"` (else the number 3.1), `"on"`, `"yes"`, text containing `: `;
5. `# comment` is ignored.

Python's `yaml.safe_load` follows YAML 1.1, in which the bare key `on` becomes the boolean `True`. GitHub reads it
correctly; Python tools that inspect workflows must look for both.

## Anatomy of a workflow

```yaml
name: CI                                  # shown in the Actions tab

on:                                       # events
  push:
  pull_request:

permissions:                              # the automatic token may only read the code
  contents: read

jobs:
  test:                                   # job id
    runs-on: ubuntu-latest                # fresh Linux VM
    timeout-minutes: 15                   # stop a hung job
    strategy:
      fail-fast: false                    # let every version finish
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v7         # get the repository's files
      - uses: actions/setup-python@v7     # install Python
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip                      # reuse pip downloads between runs
      - name: Install dependencies
        run: python -m pip install -r requirements-dev.txt
      - name: Run the tests
        run: python -m pytest -q

  docker:
    needs: test                           # only after the tests passed
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v7         # each job starts on a new, empty machine
      - name: Build the image
        run: docker build -t myservice:ci .
```

`@v7` was the current major version of `actions/checkout` and `actions/setup-python` when this course was
written; each action's page on GitHub shows its latest version. Always pin a version: an action is someone else's
code running with access to your repository.

## Events in practice

```yaml
on:
  push:
    branches: [main]            # only pushes to main
    paths: ["src/**", "tests/**", "requirements*.txt"]   # only when these files change
  pull_request:                 # every pull request
  schedule:
    - cron: "17 3 * * 1"        # Mondays 03:17 UTC (minute hour day month weekday)
  workflow_dispatch:            # a "Run workflow" button in the Actions tab
```

Scheduled runs use UTC and may start a few minutes late. Choosing an odd minute (17, not 0) avoids the busiest
time.

## Expressions, contexts and variables

`${{ ... }}` is an **expression**, filled in by GitHub before the step runs. Useful contexts:

| Expression | Value |
|---|---|
| `${{ matrix.python-version }}` | the current matrix value |
| `${{ github.ref_name }}` | the branch or tag name |
| `${{ github.sha }}` | the commit being tested |
| `${{ github.event_name }}` | `push`, `pull_request`, ... |
| `${{ secrets.NAME }}` | a repository secret (see below) |
| `${{ runner.os }}` | `Linux`, `Windows` or `macOS` |

A step can be made conditional with `if:`, for example `if: github.ref_name == 'main'` to deploy only from `main`.
Environment variables are set with `env:` at the workflow, job or step level.

## Matrix and caching

A `strategy.matrix` turns one job into several parallel copies, one per combination of values. Use it for the
Python versions you support, or for operating systems (`os: [ubuntu-latest, windows-latest, macos-latest]` with
`runs-on: ${{ matrix.os }}`). `fail-fast: false` keeps the other copies running when one fails, so you see the
whole picture.

`setup-python`'s `cache: pip` stores pip's downloads, keyed on your requirements files, and restores them on the
next run until those files change. It speeds up installation; it does not skip it.

## Reading a failed run

1. **Actions** tab → the run with the red cross → the red job → the first red step.
2. Read the log from the top of that step down to the **first** `FAILED` or `ERROR` line. For pytest, `FAILED
   tests/test_api.py::test_name - assert 200 == 422` names the test and the failing assertion; `ERROR
   tests/test_x.py` during *collection* means the file could not even be imported, often a dependency missing
   from `requirements.txt`.
3. Reproduce locally with the same command (`python -m pytest tests/test_api.py::test_name`), fix, commit, push.

The gear icon of a run offers **Download log archive**, where each line starts with a timestamp. **Re-run jobs** is
for failures with an outside cause (a network timeout), not for real test failures. Never delete or skip a
failing test just to get green.

## Secrets and permissions

- Store secrets (API keys, tokens) in **Settings → Secrets and variables → Actions**. They are never shown again,
  and GitHub masks their values in logs.
- Pass them to a step through `env:`, and refer to the environment variable in the script:

  ```yaml
        - name: Deploy
          env:
            DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
          run: ./deploy.sh            # the script reads $DEPLOY_TOKEN
  ```

  Writing `${{ secrets.DEPLOY_TOKEN }}` directly inside `run:` pastes the value into the script text, where an
  `echo`, `set -x` or an unusual character can expose it or break the command.
- Workflows triggered by pull requests from **forks** receive no secrets. Keep it that way.
- Start every workflow with `permissions: contents: read` and grant more only to the job that needs it (for
  example `packages: write` to push an image to GitHub's registry).
- Pin third-party actions to a version (or, stricter, a full commit SHA).

## Branch protection

**Settings → Branches → Add branch protection rule** (or *Rules → Rulesets*) for `main`: tick *Require a pull
request before merging* and *Require status checks to pass*, then choose your job (for example `test`). From then
on, a pull request with a red check cannot be merged. The job must have run at least once before GitHub lists it.

## Common errors and how to read them

| You see | It means | Fix |
|---|---|---|
| No run appears after a push | the file is not in `.github/workflows/`, has a YAML error, or the event does not match | check the path; the Actions tab shows a red *Invalid workflow file* message for YAML errors |
| `Invalid workflow file ... mapping values are not allowed here` | a `: ` inside an unquoted value, or wrong indentation | quote the value; align with spaces |
| `Version 3.1 with arch x64 not found` | `python-version: 3.10` without quotes | `"3.10"` |
| `ERROR: Could not open requirements file` | the job did not check out the code, or the path is wrong | add `actions/checkout` as the first step; check the file name |
| `ModuleNotFoundError` in the test step | a dependency is missing from the requirements file | add and pin it; this is CI doing its job |
| `Process completed with exit code 1` | the last command of the step failed | scroll up to the first error in that step |
| `The job running on runner ... has exceeded the maximum execution time` | a hung test or a server that never stops | add `timeout-minutes`; make tests stop their servers |
| `Resource not accessible by integration` | the token lacks a permission | grant it in that job's `permissions:` |
| The workflow runs twice per pull request | both `push` (to the branch) and `pull_request` fire | fine for small projects; or limit `push` to `branches: [main]` |

The `actionlint` tool checks workflow files locally before you push (`pip install actionlint-py`, then
`actionlint`); the GitHub Actions extension for VS Code underlines mistakes as you type.

## Cheat sheet

```yaml
on: { push: { branches: [main] }, pull_request: {}, workflow_dispatch: {} }
permissions: { contents: read }
jobs:
  JOB:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: OTHER_JOB                       # optional ordering
    if: github.ref_name == 'main'          # optional condition
    strategy: { fail-fast: false, matrix: { python-version: ["3.11", "3.12"] } }
    env: { LOG_LEVEL: info }
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with: { python-version: "${{ matrix.python-version }}", cache: pip }
      - run: python -m pip install -r requirements-dev.txt
      - run: python -m pytest -q
      - name: Use a secret
        env: { TOKEN: "${{ secrets.TOKEN }}" }
        run: ./script.sh
```

The four steps of a Python CI job, in order: **checkout → setup-python (quoted version) → pip install -r → pytest**.

## Where next

- Official: [GitHub Actions documentation](https://docs.github.com/en/actions),
  [Workflow syntax](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions),
  [Building and testing Python](https://docs.github.com/en/actions/use-cases-and-examples/building-and-testing/building-and-testing-python),
  and [Security hardening](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions).
- This course's own workflow, a real example: [`.github/workflows/ci.yml`](https://github.com/berdakh/mlengineering/blob/main/.github/workflows/ci.yml).
- In this course: [notebook 39](../notebooks/39_ci_github_actions.html), the
  [lab](../notebooks/40_lab_container_and_ci.html), [pytest](pytest.html) and [Docker](docker.html).
{% endraw %}
