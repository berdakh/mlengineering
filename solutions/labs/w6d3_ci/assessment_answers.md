# W6D3 assessment — model answers

## 1. `needs:` and wasted work

Without `needs`, all jobs start together: a push with a failing test still runs the 3-minute image job,
so the run takes about 4 minutes (the longest job) and spends 4 + 3 = 7 runner-minutes, 3 of them on an
image nobody will use; its smoke test may even pass and show a misleading green tick on one job. With
`needs: [test]` the image job is skipped when tests fail: about 4 minutes and 4 runner-minutes, and a
green run takes 4 + 3 = 7 minutes of wall time. For pull requests most teams accept the serial
7 minutes because the image job is only meaningful for code that passes its tests. For a release tag
the order is mandatory: you never publish an image built from code that failed its tests.

*Common wrong answers.* "needs makes it faster": it makes failing runs cheaper and green runs slower.
"Jobs run sequentially by default": they run in parallel.

## 2. `python-version: 3.10`

The workflow file is YAML. The YAML parser reads the unquoted scalar `3.10` as a floating-point number,
and the number 3.10 is 3.1; by the time `actions/setup-python` receives the input it is the string
"3.1", and there is no Python 3.1 on the runner's tool cache. `3.11` unquoted is also a float, but
3.11 printed back is "3.11", so it works by accident (as does 3.12). Quote every version string.
(Executed in the lesson: `yaml.safe_load('python-version: [3.10, 3.11, "3.12"]')` returns
`[3.1, 3.11, '3.12']`.)

*Common wrong answer.* "GitHub does not support 3.10": it does; the value never reached it as 3.10.

## 3. Gate or lane

Rule: a check belongs in the per-push gate only if, on an unchanged commit, it gives the same answer
every time (deterministic, no network, no data download, no wall clock, no secrets) and is fast.
(a) gate. (b) lane: it needs data and is an estimate from 7 experiments whose interval is wide (w3d5);
a threshold on it flips on noise and on data refreshes. (c) gate: deterministic API contract.
(d) lane: wall-clock on a shared runner varies (measured in the lesson: the same 50 ms assertion failed
0, 0, 2 and 3 times in 40 under increasing load). A *deterministic* proxy (for example, "/predict does
not reload the model per request", tested with a counter) can be in the gate. (e) gate: building is
deterministic given pinned inputs, and an image that does not build is not releasable. (f) lane:
needs production data, and drift is a report for a person, not a pass/fail for a commit.

*Common wrong answer.* Putting (b) in the gate "with a lower threshold": you trade false alarms for
missed regressions and still block pushes on noise.

## 4. Masked secrets

`***` in the log means GitHub's string-matching mask hid the exact value where it appeared. Two ways it
still leaks: a transformed value (base64, URL-encoded, split across lines, written character by
character) is not recognised by the mask and is printed in clear; and the expression is substituted into
the generated script file before the shell runs, so anything that prints or uploads that script, or a
crash that dumps the command line, exposes it. Also: a compromised or malicious step in the same job can
read it. Safer pattern: `env: TOKEN: ${{ secrets.TOKEN }}` on the step and use `"$TOKEN"` in the script,
pipe it to the tool on stdin (`--password-stdin`), never echo it, and scope it to the one job that needs
it. Better still for cloud access: short-lived OIDC credentials (w6d5) instead of stored keys.

## 5. Forks and secrets

A pull request from a fork runs code written by the fork's author. If that run received repository
secrets, anyone could open a pull request that prints or exfiltrates them; so GitHub does not pass
repository secrets to workflows triggered by `pull_request` from forks (and the `GITHUB_TOKEN` is
read-only there). Implication: the per-push gate must not need secrets, or it cannot check outside
contributions. Steps that need secrets (publishing an image, deploying) run on `push` to `main` or on
tags, after review. (Behaviour stated from GitHub's documentation as remembered; see H14.1 sources.)

## 6. Pinning

Reproducibility: SHA (exact code forever) > `@v7` (moves within the major version) > `@main` (moves on
every push to that branch). Maintenance: `@main` needs none but can break or change silently; `@v7`
needs an update per major version; SHA needs an update for every fix, usually automated by a
dependency bot. In a regulated organisation require full SHAs with automated update pull requests,
because the workflow then runs only code that was reviewed at a known commit.

## Design-choice explanation (model answer)

Check from the runner. The CI smoke test should prove that the *production artifact* starts, loads its
model and serves correct responses through the published port, the way a client reaches it. Calling
`docker exec app curl` tests from inside the container, which a client never does, and forces a test
tool into the image. Installing curl adds a few megabytes and, more importantly, another binary with
its own vulnerabilities and update cycle to every production container; slim and distroless images
exist precisely to avoid that. The standard-library smoke script on the runner needs nothing in the
image and checks more (readiness, a scored request, a 422 for a bad request). A container *health check*
is different: it is the orchestrator's probe of a running container in production, run repeatedly by the
platform (or Docker's `HEALTHCHECK`), and it must use what is inside the image. If one is needed, write
it with the interpreter already present (`python -c` with `urllib.request` against `/healthz`), not by
adding curl. Installing curl is defensible when the platform requires a shell command probe and the
team accepts the cost, but it should be a decision, not a side effect of a CI fix.

Scoring: strong answers separate CI smoke test from runtime health check and mention attack surface;
adequate answers pick one option with one reason; weak answers say "install curl, it is small".

## Interview rep — what a strong answer contains

1. **First explaining line**, not the last: which package failed to build a wheel and why (missing
   compiler or headers, or "no matching distribution").
2. **What changed**: the new 3.13 matrix entry. The other entries are green, so the code is not broken.
   A dependency without published wheels for 3.13 makes pip fall back to building from source, which
   needs a compiler and system headers that the runner image may not have, or the version constraint
   cannot be met on 3.13 at all.
3. **Laptop vs runner**: compare the resolved versions (`pip freeze` in the CI log vs locally) and
   the interpreter version; the laptop is probably on 3.12, or has a compiler installed.
4. **Unblock today**: mark the 3.13 entry `continue-on-error: true` (experimental) or remove it from
   the required checks; do not delete the tests.
5. **Durable fix**: a lockfile so CI resolves the same versions every time (w6d2); a written matrix
   policy (add a new interpreter as non-blocking until all dependencies ship wheels); a scheduled job
   that tries the newest interpreter so you learn early.

Rubric: 5 points, one per item above; 4-5 strong, 2-3 adequate, 0-1 weak. Deduct one point for
"re-run it" without a reason, or for proposing to pin to an old Python permanently.
