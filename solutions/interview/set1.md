# Interview set 1 - rubrics and model answers

Open after attempting. Reference code: `solutions/interview/set1/p1.py`, `p2.py`. Deliberately wrong
answers that the tests reject: `solutions/interview/set1_wrong/`.

Verified in the authoring session (Python 3.13.18, pytest 9.1.1):
`SET1_DIR=solutions/interview/set1 python -m pytest interview/set1_tests -q` gives 25 passed in under
1 s; each wrong answer fails at least one test (see the table at the end).

Scoring uses three evidence levels per prompt, not points: **Demonstrated** (meets every "must"
unaided, within time), **Partial**, **Not yet**. Record the level and the error pattern.

## P1 - RollingStats

**Must**
* A queue of held values plus a running sum for the mean.
* A **monotonic deque** for the maximum: on `push(x)` pop from the right every element smaller than
  `x`, append `x`; on expiry pop from the left if the leftmost element is the one that left the window.
  The left end is the current maximum.
* Correct amortised argument: each value is appended once and popped at most once, so `n` pushes cost
  O(n) in total even though a single push may pop many elements.
* Empty and invalid-window cases raise `ValueError`; partial windows handled.
* All tests pass, including the 300,000-value stream.

**Should**
* Says "amortised", not "O(1) worst case".
* Handles equal maxima deliberately. Either keep duplicates (pop only strictly smaller values and expire
  by comparing values), or store indices and pop `<=` values. Mixing the two conventions is the classic bug.
* States the numerical caveat: a running sum accumulates floating-point error over a long stream
  (add and subtract of different magnitudes). Mitigations: periodically recompute from the window,
  compensated (Kahan) summation, or exact `math.fsum` on demand at O(window).

**Common incorrect answers**

| Answer | Why it fails |
|---|---|
| `max(self._values)` on every call (`set1_wrong/p1_scan_window`) | Correct values, O(window) per call: 6e9 element visits on the timing test. In an interview, the follow-up "can you do better than O(w)?" is the actual question |
| A heap with lazy deletion, presented as O(1) | It is O(log n) per operation and the heap can grow beyond the window; acceptable only if stated as such |
| Expiry test off by one (`set1_wrong/p1_off_by_one`) | The maximum is dropped one push early; passes the hand-made small tests if they never place the maximum at the oldest position, fails the randomised comparison |
| Keeping only the single current maximum and "recomputing when it leaves" | Worst case (decreasing stream) recomputes on every push: O(window) again |
| `mean()` returning 0.0 or `nan` when empty | Violates the stated contract; silent sentinel values are how bad statistics reach dashboards |

**What an interviewer listens for:** you asked whether `window` counts values or time, what happens
before the window fills, whether NaN can arrive (NaN breaks the comparison-based deque; say so).

## P2 - Refactor for testability

**Must**
* Three seams: parsing (text to event), decision logic (`summarize`, pure), and effects (`main`: file,
  clock, stdout, exit code). The clock is read exactly once, at the edge, and passed in.
* The window is implemented as written: `now - 24h < ts <= now`. The legacy expression
  `(now - ts).days < 1` is different in two ways: `timedelta.days` floors, so for *future* timestamps
  the difference is negative and `.days` is `-1`, which is `< 1`, so future-dated events are counted;
  and an event exactly 24 h old has `.days == 1` (excluded, which happens to agree), while the intent
  about the upper bound is simply unstated.
* No work at import time; `main` returns an exit code instead of calling `sys.exit` internally.
* Malformed lines return `None` from `parse_line`; the legacy bare `except Exception` is replaced by the
  specific failure modes (wrong number of fields, `ValueError` from `fromisoformat`).

**Should**
* Does not mutate its input; does not depend on input order for `last_error`.
* Names the five tests in a sensible priority order: boundaries first, then "now is honoured", then
  ordering, then malformed input, then empty input and the missing-file path.
* Mentions what was deliberately not done in 15 minutes (time zones, streaming large files, logging).

**Common incorrect answers**

| Answer | Why it fails |
|---|---|
| `summarize(events)` calling `datetime.now()` inside (`set1_wrong/p2_hidden_clock`) | Still untestable: the tests would need to patch the clock or build events relative to the real time, and a fixed historical `now` cannot be evaluated at all |
| Keeping `(now - ts).days < 1` (`set1_wrong/p2_legacy_days_boundary`) | Counts future-dated events; the refactor copied behaviour without reading the contract. A refactor preserves behaviour, but this prompt changes the contract explicitly, and that must be noticed |
| Wrapping the old body in `def main()` and nothing else | Removes import side effects but leaves no pure function to test: every test still needs a file and the real clock |
| `parse_line` raising on bad input | Contradicts the docstring; one corrupt line then aborts the whole report |
| Mocking `datetime` in tests instead of passing `now` | Works, but couples the tests to the implementation; dependency injection of a value is simpler and is what the signature asks for |

## E3 - "sys.path.insert is fine"

**Rubric (Demonstrated = at least four of these, stated concretely):**
1. It makes imports depend on *file location and launch method*, not on the environment: moving a
   script, running under pytest, a notebook, a worker process or a Docker `WORKDIR` changes what resolves.
2. Two copies of the same module can be imported under different names (once as `pkg.mod`, once as `mod`),
   giving duplicated state and failing `isinstance` checks.
3. Nothing declares dependencies or a version, so nobody else can install it, and the code can never be
   built into a wheel or container layer cleanly.
4. Tests pass against the working tree only; packaging mistakes are invisible until someone else installs.
5. Smallest alternative: a ten-line `pyproject.toml`, `src/` layout, `pip install -e .` once. After
   that, no path code at all, and a console entry point is available.
6. Fair concession: for a single throwaway script with no imports of its own modules, or a notebook
   used by one person for one afternoon, packaging adds nothing. The threshold is the second file
   that imports the first, or the second person.

Model answer (about 110 words): "It works until the way the code is launched changes. The path you
insert is relative to each script's location, so pytest, a notebook, a subprocess worker or a
container with a different working directory can resolve a different module or none, and you can end
up importing the same file twice under two names. It also leaves dependencies undeclared, so I cannot
reproduce your environment. The fix is small: a pyproject with the dependencies, the code under
`src/`, and one editable install; then every entry point imports the same installed package and the
`sys.path` lines go away. For a one-file throwaway analysis I would not bother."

Common weak answers: "it is not best practice" (no mechanism); "it is slow" (false); proposing
`PYTHONPATH` in everyone's shell profile (same problem moved elsewhere, now invisible).

## E4 - one afternoon with a messy training script

**Rubric: order and justification matter more than the exact list.**
1. **Record before restructuring.** Make each run write a directory with the resolved parameter
   values, the metrics, the code version (git commit), library versions and a hash of the input data.
   This is the change that makes next month's question answerable, and it needs no redesign.
2. **Gather the fourteen constants into one typed, validated config object** loaded from a file with
   command-line overrides, rejecting unknown keys; functions receive values, not the config module.
3. **Replace `np.random.seed(0)` with an explicit seed in the config threaded to each consumer**
   (splitter `random_state`, a `Generator`), and state what remains nondeterministic.
   Replace diagnostic `print` with `logging` configured once at the entry point, writing to the run directory.
* Deliberately later: tests beyond one smoke test, experiment-tracking tools, refactoring the model
  code, packaging polish, hyperparameter sweeps, seed-variance studies.

Common weak answers: starting with a framework (Hydra, MLflow) before anything is recorded; "set all
the seeds" as the whole answer (a seed fixes one draw, it does not record what was run or quantify
variation); rewriting the model code first (highest risk, no traceability gained).

## Verification table (wrong answers)

| Wrong answer | Command | Outcome observed |
|---|---|---|
| `p1_scan_window` | `SET1_DIR=solutions/interview/set1_wrong/p1_scan_window python -m pytest interview/set1_tests/test_p1_rolling.py -q` | 1 failed (timing: 30,000 of 300,000 values in 5 s), 10 passed |
| `p1_off_by_one` | same with `p1_off_by_one` | 5 failed, 6 passed |
| `p2_hidden_clock` | `... test_p2_refactor.py` | 4 failed, 10 passed |
| `p2_legacy_days_boundary` | `... test_p2_refactor.py` | 1 failed, 13 passed |
