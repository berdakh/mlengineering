# Checkpoint answers

Model answers to each notebook's assessment questions (and the diagnostic and review days), with
the common wrong answers and why they fail. See [README](README.md) for the confidence markers.

---

# Notebook 03 — From script to installable package: project structure and environments

✍️ Written answers: compare yours against the rubric; wording will differ.


Open only after writing your own answers. For each question: a model answer, then the
common incorrect answers and why they fail.

### Q1 — tests pass after `pip uninstall`

**Model answer.** `python -m pytest` starts Python with `-m`, so the current working
directory is `sys.path[0]`. In a flat layout the project root contains `pumpwatch/`, so
`import pumpwatch` resolves to the working tree before `site-packages` is ever consulted.
Uninstalling removes only the `site-packages` entry, which was never being used. The
tests were therefore exercising the source tree, not the installed distribution: they
say nothing about whether the packaging configuration (package discovery, included
files, entry points, declared dependencies) is correct.

**Common incorrect answers**

- *"pip uninstall doesn't remove editable installs."* It does remove the pointer and
  metadata. The import succeeds for a different reason.
- *"pytest adds the package to the path."* Closer, and pytest's rootdir/conftest
  insertion can also do this, but the general mechanism is the interpreter's own
  `sys.path[0]`; the same happens with `python -c "import pumpwatch"`.
- *"So the tests are fine."* They test the code's logic, but the claim "the thing I ship
  works" is unsupported.

### Q2 — "command not found" after adding an entry point

**Model answer.** Console scripts are generated at *install time* from the metadata. An
editable install makes code changes live, but entry points live in the installed
`dist-info` metadata and in a generated file in the environment's `bin/`; neither is
regenerated when `pyproject.toml` changes. `python -m pumpwatch.cli` works because it
only needs the module to be importable. Fix: re-run `python -m pip install -e .`. The
same applies to changed `dependencies` (and any other metadata: version, name,
`requires-python`).

**Common incorrect answers**

- *"The venv isn't activated."* Possible in general, but then `python -m pumpwatch.cli`
  would normally fail too (or use a different interpreter). The stated symptoms point at
  metadata staleness.
- *"Add `.venv/bin` to PATH" / "write a shell alias."* Works around a missing file
  instead of generating it.
- *"Editable installs don't support scripts."* They do; they are created at install time.

### Q3 — 140 exact pins in `dependencies`

**Model answer.** Exact pins are right for *reproducing an application environment*: a
deployed service image, a CI job, the environment behind a published result. In
`[project] dependencies` they do harm because that field is read by *every* installer of
the package: `numpy==2.1.3` makes the package uninstallable alongside anything that
needs a different NumPy, blocks security updates, and — since the freeze includes
transitive and incidental packages (Jupyter, linters, platform-specific wheels) — may be
unsatisfiable on another OS or Python version. Keep loose lower bounds for what the code
actually imports in `pyproject.toml`; keep the pins in a separate lock artefact
(`requirements.lock` / `requirements.txt` produced by `pip freeze` or `pip-compile`,
or `uv.lock`) that is used to build the environment.

**Common incorrect answers**

- *"Pins are always bad / always good."* The point is which artefact has which job.
- *"Use upper bounds on everything instead (`numpy<2`)."* Speculative upper bounds
  create the same resolver conflicts later; add one only when you know a version breaks you.
- *"The lock file replaces `dependencies`."* Then `pip install pumpwatch` installs
  nothing it needs. Both are required; they answer different questions.

### Q4 (design choice) — port the bug first, fix it second

**Model answer (level 3).** A refactor is verified by showing the output is unchanged;
that verification only works if nothing is *supposed* to change. Had I fixed the scaler
during the move, any difference from `golden.txt` would have two possible causes — the
intended fix or an accidental porting error (band edges, NaN handling, row order) — and
no way to separate them. In this lab the trap is sharper than usual: the fix changes
*none* of the printed metrics, so a "fix while moving" approach would have shown matching
numbers and I would have had no record that a behaviour change happened at all, while a
porting error that also left the summary metrics unchanged could hide behind it. Doing
it in two steps gives a clean equality check for the port and an explicit before/after
entry for the fix. The reviewer would be right if the faithful port were *impossible or
dangerous* — e.g. the original crashes, depends on an unavailable resource, or the bug
makes the old output meaningless as a reference (non-deterministic, or wrong in a way
that affects safety); then you characterize what you can, fix first, and say so. They
would also have a point for a throwaway script nobody else will rely on.

**Common incorrect answers**

- *"Because best practice says refactor and behaviour change go in separate commits."*
  (Level 1.) True as a slogan; the question asks why. The reason is attribution of
  differences.
- *"Because the old numbers are published and must be reproduced."* Sometimes relevant,
  but not the argument here, and it suggests never fixing the bug.
- *"To keep the git history tidy."* A consequence, not the reason.
- *"The reviewer is right, a bug is a bug."* Ignores that verification-by-equality is
  lost, exactly when it is most needed.

### Q5 — identical metrics after the fix

**Model answer (level 3).** (c). The leak existed by construction — the scaler's mean
and variance were computed from held-out units' rows — whatever the numbers say; and the
fitted model *did* change (in the reference run the train-only scaler's scales differ by
up to ~13 % and the means by up to ~0.17 SD from the all-rows scaler). The printed
metrics did not move because AUC/AP depend only on score ranking and accuracy/F1 only on
the side of 0.5, and with this very separable synthetic data neither changed. So (a)
confuses "no measurable effect on four summary statistics on one split" with "no leak":
absence of evidence from an insensitive instrument. (b) treats the metric as the
objective; the objective is an evaluation procedure that *cannot* be contaminated,
because the same code will be run on data where it would matter (fewer groups, heavier
tails, or a preprocessing step with more capacity such as feature selection or PCA).
The limitation to note: an end-to-end metric comparison cannot detect this class of
error here; the check that can is structural (the estimator owns its preprocessing —
which is what the automated check tests through unit-rescaling invariance).

**Common incorrect answers**

- *"(a): leakage always inflates performance, it didn't, so no leak."* Leakage is a
  property of the information flow, not of the result. Its effect can be zero, positive,
  or occasionally negative.
- *"(c), because pipelines are best practice."* (Level 1.) Right letter, no mechanism.
- *"(b) is fine since it's synthetic data."* The package is the thing being built; it
  will be pointed at other data.

### Q6 — `main()` returns an exit code

**Model answer.** (1) Testability: `main(["train", "--data", "x.csv"])` can be called
in-process and its return value asserted; a `sys.exit()` buried in a helper raises
`SystemExit` in the middle of a test (or kills a host process such as a notebook or API
worker that imported the function). (2) One place decides the mapping from failure to
exit code and message: library functions raise ordinary exceptions (`FileNotFoundError`,
`ValueError`) that other callers can handle differently, and only the CLI layer
translates them. Also acceptable: the generated console script is literally
`sys.exit(main())`, so the function matches the entry-point contract; resources are
cleaned up by normal stack unwinding.

**Common incorrect answers**

- *"It's faster"* / *"sys.exit is deprecated."* Neither is true.
- *"So errors are hidden."* The opposite: expected errors are reported once, at the
  boundary; unexpected ones still propagate with a traceback.

---

### Interview rep — rubric and reference

Reference implementation and tests: `interview_rep_reference.py` in this directory.
Test your own attempt with

```bash
python solutions/labs/w1d3_package_structure/interview_rep_reference.py path/to/your_file.py
```

Score one point each (max 6):

| # | Criterion | What interviewers look for |
|---|---|---|
| 1 | **Correct partition** | Every index exactly once; no group on both sides. Splits *groups*, then maps to rows. |
| 2 | **Determinism done properly** | A local generator (`random.Random(seed)`), not `random.seed(seed)` — the latter mutates global state for the caller. |
| 3 | **Order independence** | Sorts the unique group labels before sampling. Iterating a `set` of strings varies between processes (hash randomisation); first-seen order depends on row order. |
| 4 | **Edge cases** | Clamps to at least one and at most `n−1` test groups; validates fraction and group count with `ValueError`. |
| 5 | **Complexity and clarity** | One pass to assign rows, `O(n)` membership via a set — not `g in list` inside the loop; names that read. |
| 6 | **Communication** | Stated the approach and at least one edge case *before* coding; tested with a tiny example at the end. |

**Typical first attempts and what they miss**

- Shuffling *row indices* and cutting at `test_fraction` — a row split, not a group
  split; fails criterion 1. (With your background you will not do this, but it is the
  single most common answer.)
- `list(set(groups))` then shuffle — passes on one run and fails criterion 3 on another
  process because string hashing is randomised per process unless `PYTHONHASHSEED` is fixed.
- `int(test_fraction * n_groups)` — truncates to zero test groups for small inputs.
- `random.seed(seed)` — deterministic, but silently reseeds the caller's RNG.

Record your score and the time taken in `progress/` notes. This rep recurs with less
scaffolding in week 3 (grouped *k*-fold from scratch).

---

# Notebook 04 — Configuration, logging and reproducible runs

✍️ Written answers: compare yours against the rubric; wording will differ.


Open only after writing your own. Model answers are one good answer, not the only one; score with
the rubric in `labs/w1d4_config_logging/assessment.md`.

### A1

You intend to evaluate with five seeds and write `sed = 3` (or put `seed = 3` under `[model]`) in
one of the files. The loader finds no `split.seed`, returns the default 7, the run completes, and
the snapshot — if it records only resolved values — shows `seed: 7` for a run you believe used 3.
Your "five-seed mean" is the mean of four distinct seeds with one counted twice, and its spread is
understated. Prevention: the loader rejects keys it does not know and says which one
(`unknown configuration key: split.sed`).

*Common incorrect answers.* "Be careful / code review catches it" — review does not see every local
config edit, and the failure is silent by construction. "Log the config at start-up" — helps a
person who reads the log and knows what to look for; it does not stop the run. "Use a schema
library" — fine, but only if it is set to forbid extra fields (pydantic, for example, ignores
unknown fields by default unless configured otherwise — *not re-verified this session*).

### A2

(1) A command-line override (`--set model.C=0.1`): the file says 1.0, the snapshot 0.1.
(2) The file was edited without committing (the `-dirty` suffix on the recorded commit tells you),
or the file was changed in a later commit and you are reading the wrong revision. Also acceptable:
a key omitted from the file, where the snapshot shows the default in force *at that code version*.
Trust `config.json`: it was serialised by the run itself from the single object that the computation
received. The file is an *input* to that object, one of several.

*Common incorrect answer.* "Trust git, it is the source of truth." Git is the source of truth for
what was *committed*; the run may not have used exactly that.

### A3

`basicConfig` attaches a handler to the **root** logger. Executed at import, it does so in every
process that imports `pumpwatch.features`: the CLI (now double output or changed format), the test
suite (pytest's log capture is disturbed), a future web service (the service's logging policy is
overridden by a dependency). It is also unreliable for the teammate's own purpose: `basicConfig`
does nothing if the root logger already has handlers, unless `force=True`. Alternatives: (a) call
`logging.basicConfig(level="INFO")` in the *notebook* — the notebook is the application; (b) expose
`pumpwatch.logging_setup.setup_logging()` and call it explicitly from the notebook. The library
module keeps only `logger = logging.getLogger(__name__)`.

*Common incorrect answers.* "Use print instead" (loses levels and routing); "wrap it in
`if not logging.getLogger().handlers`" (still a library deciding application policy, and still at
import time).

### A4

Nothing yet. The observed change (+0.021) is about half of one seed-to-seed standard deviation
(0.044) and well inside the observed range, and seed 7 is a single split with three held-out units.
Minimal additional evidence: run *both* variants on the *same* set of seeds (say the ten already
used) and look at the paired differences — same split, with and without the feature — since pairing
removes the dominant "which units are held out" variance. With config overrides this is a shell
loop over `--set split.seed=$s` for two commits, and `compare-runs` reads off each pair. Even then:
ten units of synthetic data support a statement about this dataset only.

*Common incorrect answers.* "It improved by 2 points" (single draw). "Pick the seed where the gain
is largest" (selection on the test split). "Run unpaired seeds for each variant and compare means"
— not wrong, but far less sensitive than the paired design; score 2.

### A5

1. **Data content** — compare `data_sha256`. Same path with different bytes is the most common cause.
2. **Uncommitted code** — is either `git_commit` marked `-dirty`? Two dirty trees at the same commit
   can contain different code. (If the dirty flag is not recorded, that is the gap.)
3. **Library versions / platform** — `environment.json` `packages`, `python`, `platform`. Solver
   defaults and numerical routines change between versions.
4. **Inputs not captured by the config** — environment variables, files read implicitly, the
   current working directory for relative paths (the recorded absolute `data_path` helps).
5. **Residual nondeterminism** — threads/BLAS, GPU kernels, unordered iteration. No field records
   it; this is what the written reproducibility note is for. For today's logistic-regression
   pipeline on CPU this should be empty, so reaching step 5 means re-checking 1–4.

*Common incorrect answer.* Starting with "floating-point nondeterminism". It is the least likely and
least checkable explanation; always exhaust the recorded differences first.

### A6

- (i) `C` — experiment configuration: TOML file under version control, overridable per run.
- (ii) AWS key — a secret: never in the repo or a snapshot; supplied through the environment
  (environment variable / credentials provider) and read at the point of use.
- (iii) Band edges — part of the feature *definition*. A named constant in code while fixed;
  promote to config the day you actually vary it, because every config key is a dimension someone
  must validate, document and keep compatible.
- (iv) Log level — operational configuration: a config key with a sensible default, commonly also
  overridable by an environment variable or flag because operators change it without changing the
  experiment.
- (v) Production database URL — deploy configuration: varies between deployments, not between
  experiments, hence environment variables (Twelve-Factor); if it embeds credentials it is also a
  secret.

*Common incorrect answers.* "Everything in the config file" (leaks (ii)/(v), bloats the schema with
(iii)); "everything in environment variables" (hyperparameters then escape version control and
review).

### B1 — one defensible answer

For a command-line user the design is right: stdout carries only the JSON result, so pipelines work
at any verbosity, while the console level is theirs to choose; the DEBUG file means a quiet console
never costs diagnostic information after the fact, which matters because you cannot re-run a failure
that depended on last night's data. Attaching handlers to `pumpwatch` rather than the root logger
keeps third-party DEBUG chatter out of both destinations and avoids interfering with whatever else
is in the process. The costs: warnings logged by other libraries (and anything logged on the root
logger) do not reach `train.log`, so the file is not a complete record of the process;
`propagate = False` means a host application's own handlers do not see `pumpwatch` records at all.
Therefore `setup_logging` is strictly an *application* function — a FastAPI service embedding the
package must **not** call it; it should configure logging once for the whole service (root handlers,
probably JSON format) and leave `pumpwatch` loggers propagating, which works precisely because the
library modules only ever call `getLogger(__name__)`. A further cost is always-on DEBUG: cheap here,
but in a hot inference path the volume and the formatting work would need a level switch. A
reasonable alternative is to configure the root logger and set third-party loggers to WARNING; it
gives a complete file at the price of maintaining a list of noisy libraries.

*Common weak answers.* Describing what the code does without a cost; claiming stderr is "for
errors only" (it is the conventional channel for all diagnostics); recommending the service call
`setup_logging` too.

### C — reference

```python
import heapq
from collections import Counter

def summarise(lines: list[str], k: int) -> dict:
    levels: Counter[str] = Counter()
    durations: list[tuple[str, int]] = []
    for line in lines:
        head, sep, message = line.partition(" | ")
        parts = head.split()
        if not sep or len(parts) < 4:
            levels["MALFORMED"] += 1
            continue
        level, logger = parts[2], parts[3]
        levels[level] += 1
        for token in message.split():
            key, eq, value = token.partition("=")
            if key == "duration_ms" and eq and value.isdigit():
                durations.append((logger, int(value)))
    slowest = heapq.nlargest(k, durations, key=lambda item: item[1])
    return {"levels": dict(levels), "slowest": slowest}
```

Complexity: one pass, O(n) parsing plus O(n log k) for `nlargest`; memory O(n) as written because
all durations are kept. For 10⁹ streamed lines: accept an iterator, keep a size-*k* min-heap
(`heapq.heappushpop`) instead of the list, so memory is O(k) plus the level counter; consider
`key=value` values containing spaces (this simple format cannot represent them — a reason
production systems log JSON).

Executed on the three sample lines: `{'levels': {'INFO': 2, 'WARNING': 1}, 'slowest': [('pumpwatch.io', 41), ('pumpwatch.split', 12)]}`.

*Common mistakes.* `sorted(...)[:k]` (correct, O(n log n): score 2); splitting the whole line on
whitespace and indexing fixed positions in the message (breaks when the message has a different
number of words); `int(value)` without guarding (crashes on `duration_ms=n/a`); forgetting
malformed lines.

### Lab reproducibility note — what a good one contains

*Fixed by the config:* data path, sampling rate, split fraction and seed, `C`; given those and the
same environment, the pipeline (interpolation, features, group split, scaler + logistic regression
with the lbfgs solver) is deterministic, verified by two identical runs. *Recorded but not fixed:*
Python and library versions, platform, git commit and dirty flag, data file hash — a mismatch can be
detected but the environment cannot be recreated from the record alone. *Neither:* BLAS threading
and numerical differences across machines/builds (could change low-order digits), anything read
from the process environment, and the fact that the result is one draw over splits. A 3-point note
also says what would change the picture (a neural model, a GPU).

### Challenge note (criterion 6) — what a good one contains

A metric delta can be attributed to a modelling change only when `same_data` is true and
`config_diff` contains nothing but the intended modelling keys — in particular not `split.seed` or
`data.*` — *and* the code commits are the ones intended. Even then it is one split: you would still
want the delta's distribution over seeds (paired), the environment diff, and whether the comparison
was planned before looking at the numbers.

---

# Notebook 05 — Testing ML code with pytest: what a unit test can and cannot tell you

✍️ Written answers: compare yours against the rubric; wording will differ.


Model answers are deliberately short. Wording will differ; score against the rubric in
`labs/w1d5_testing_ml_code/assessment.md`.

### Part A

**A1. `expected = np.sqrt(np.mean(x**2))` vs `rms(x)`.**
It is a *differential* test against a one-line re-derivation. It is useful: it kills
"missing sqrt" and "mean-abs" because the test's formula is written independently from the
definition. Its weakness is that the oracle is the same formula a developer would type into
the implementation, so a shared misunderstanding (e.g. both forget to handle NaN, both use
the wrong axis for 2-D input) passes. It also says nothing an auditor can check by eye.
A sine with a closed-form answer is independent of *any* code.
- *Common incorrect answer:* "It is a tautology, therefore useless." Not so — it is
  tautological only if `expected` is produced by calling the code under test. Re-deriving
  from the definition is a weaker oracle, not a non-oracle.
- *Common incorrect answer:* "It is fine because random inputs cover more cases." Coverage of
  inputs is not the issue; independence of the expected value is.

**A2. Layers.**
(a) Unit test (structural contract of the split) — blocks a merge.
(b) Data validation — it is a statement about *today's file*, runs in the pipeline at load
time, and should stop that pipeline run (not a code merge; the code did not change).
(c) Statistical performance check — belongs to model evaluation/promotion, reported with
uncertainty; it should gate *promoting a model*, not merging code, because it can fail by
chance and pass with defects.
(d) Integration/smoke test — deterministic by construction, blocks a merge.
- *Common incorrect answer:* putting (c) in the unit suite "because model quality is what
  matters". It matters, and that is why it deserves an instrument with known variance; see
  the 0.946–1.000 spread from `example/metric_variability.py`.
- *Common incorrect answer:* calling (b) a unit test. Unit tests run on fixed inputs chosen
  by the author; data validation runs on inputs chosen by the world.

**A3. 0.4911 instead of 0.5.**
Cause: with `N=128`, `fs=256` the bins are 2 Hz apart; 25 Hz lies between bins (12.5
periods in the window), so the tone's energy leaks into neighbouring bins, some of them
outside 10–40 Hz, and the window no longer holds whole periods of the mean-removed signal
(its variance is 0.4993, not 0.5). The function is right; the test input does not have the
property the oracle assumes.
Good repair: use a frequency on a bin (24 or 26 Hz) so the closed-form answer is exact, keep `rel=1e-9`.
Bad repair: widen to `rel=0.05`. That admits real defects of up to 5 % and hides the reason.
(A legitimate third option: keep 25 Hz and assert a *bound* you can justify, labelled as such.)
- *Common incorrect answer:* "Floating-point error." Rounding error here is ~1e-14; a 1.8 %
  discrepancy is physics of the DFT, not arithmetic.
- *Common incorrect answer:* "`band_power` should apply a window function." Possibly a
  reasonable feature request, but it changes the function's contract; it is not a reason for
  the test to fail.

**A4. 100 % coverage ≠ correct.**
The `runs_without_error` suite (in `mutants/`) executes every feature function and all 14
injected defects survive it; e.g. `rms` without the square root still returns a positive
float. Coverage counts executed lines, not verified results.
- *Common incorrect answer:* "Coverage is useless." Low coverage is strong evidence of
  missing tests; high coverage is weak evidence of anything.

**A5. "Same seed → same split" passes; what can still be wrong?**
(1) The `seed` argument is ignored (hard-coded `random_state`): the split is perfectly
reproducible. Detect by varying the seed and requiring more than one distinct test set.
(2) The split leaks units (row-level shuffle with a fixed seed is also reproducible).
Detect with the disjointness assertion on group ids. (Also acceptable: wrong test fraction.)
- *Common incorrect answer:* "Non-determinism." That is the one thing this test *does* detect.

**A6. Why the scaler leak resists unit testing.**
From outside, `train_and_evaluate` returns metrics; whether the scaler's statistics included
test rows changes them only slightly (in w1d3 the printed metrics were identical). There is
no observable contract to assert without reaching into internals. The effective control is
*design*: put preprocessing inside the estimator (`Pipeline`) so the leak cannot be
expressed, and review experimental design. (A test is possible — e.g. make test rows
extreme outliers and assert that training-set scaling statistics are unaffected — but it is
contrived and couples the test to internals.) Lesson: tests are one control among several
(types, API design that makes misuse impossible, review, evaluation protocol); choose the
cheapest control that actually closes the failure mode.
- *Common incorrect answer:* "Assert the metric did not change." Circular, and the metric
  did not change in the first place.

### Part B

**B1. Why unit tests must not read the repository's data file.**
Level-3 answer contains these points:
1. *Diagnosis.* A unit test's value is that a failure localises a code defect. If the test
   reads a shared file, a failure can also mean the file changed, moved, or is absent — the
   test now detects three things and identifies none.
2. *Oracle.* On real data nobody knows the right RMS of window 17. The only possible
   assertion is "same as last time", a characterisation test, which pins bugs as firmly as
   correct behaviour.
3. *Portability and speed.* Tests must run from any directory, in CI, in a container, and
   in seconds; a 1 MB CSV today is a 20 GB table next quarter.
4. *What to do for realism.* Keep a tiny, hand-checkable fixture (a few rows written by the
   test into `tmp_path`); add a separately marked integration test that runs the pipeline on
   a small committed sample; and move "is today's real data sane?" into data-validation
   checks that run in the pipeline (Week 2).
5. *Boundary of the rule.* A committed golden file is appropriate for *regression* tests of
   a parser or a serialisation format, where "byte-identical to last release" is the contract.
- *Common incorrect answer:* "Because it is slow." True, but the weakest reason; it suggests
  a fast real file would be fine.
- *Common incorrect answer:* "Real data should never be used in tests." Too strong — see
  points 4 and 5.

### Part C — interview rep

Reference: `interview_rep/merge_intervals.py` and `test_merge_intervals.py` (12 tests, executed).
Boundary cases a strong answer lists *before* coding: empty list; single interval; touching
(merged, by the prompt); gap of one (not merged); containment (`(1,10),(2,3)` — the bug is
taking the later `stop` instead of the max); unsorted input; duplicates; whether the input
may be mutated. Complexity: O(n log n) from the sort, O(n) merge pass.
Most frequent defects: `merged[-1] = (merged[-1][0], stop)` without `max`; `<` instead of
`<=` for touching; sorting the caller's list in place.

### Retrieval-practice key (lesson §8)

The two problems: (1) the oracle is the code's own earlier output, so the test can only
detect *change*, not error — if the notebook run had the factor-of-two bug, the test
enforces it; (2) `rel=0.2` is not derived from anything: it is far above numerical noise and
its relation to the defects of interest is unknown (a factor of two happens to exceed it,
a 15 % normalisation error does not).
Redesign: input = pure tone at a bin frequency inside 8–12 Hz with amplitude `A` (choose
`fs`, `N` so that e.g. 10 Hz is a bin); expected power `A²/2` from theory; tolerance
`rel≈1e-9`; add Parseval on noise for the normalisation, and a tone at exactly 12 Hz to pin
the half-open edge.

### Notes on the lab and challenge solutions

- Lab reference: `lab/tests/` (39 tests, ≈ 2 s). See `lab/README.md` for what to compare.
- Challenge reference: `challenge/eventkit/events.py` and `challenge/tests/test_events.py`.
  The three planted defects in the shipped file: (1) an event still open at the end of the
  array is dropped; (2) `>=` instead of `>` (which also changes nothing for NaN but admits
  ties); (3) short runs are filtered *before* merging, so a fragmented event disappears.
- Weak-suite mutants with measured survivors: `mutants/*/MUTANT.md`, `mutants_challenge/*/MUTANT.md`.

---

# Notebook 06 — Independent refactor: a real exploratory notebook becomes the project skeleton

✍️ Written answers: compare yours against the rubric; wording will differ.


Open after writing your own. Numbers are from runs on the real data in the authoring session
(2026-11-21); details in `lab/NOTES.md`.

### A. Reasoning questions

#### Q1. Order dependence

Run top to bottom, `df` was last assigned in the cell "look at one experiment":
`df = all_df[all_df.experiment_id == "other/2"]`. So the "normal" mean and standard deviation come
from one labelled experiment, 1,190 rows, **including its anomalous segment**, and because of the
positional-id bug that experiment is really `other/11.csv`. The comment says "against normal"; no
fault-free data is involved, and in fact none is left in `all_df` (it was dropped by `dropna()`).

Third outcome: in the live kernel, if the author ran this cell before the "look at one experiment"
cell, `df` was whatever the last loading loop left behind, i.e. the last file of the `other/` loop
(`9.csv`, raw and unsorted into the table), and the printed medians were different again. The
exported file cannot tell you which of these the author saw.

*Common incorrect answers*

- "`df` is the whole table." No: `all_df` is the whole table; `df` is assigned in four different cells as a scratch name.
- "It uses the anomaly-free data because that was loaded last." That frame is called `free`, never `df`.
- Stopping at "it is the wrong experiment" without noticing it contains anomalies, which is what makes it conceptually wrong rather than just mislabelled.

#### Q2. What the cleaning step removed

The 9,405 rows are the entire fault-free recording. Its file has nine columns (no `anomaly`,
`changepoint`), so after `pd.concat` those two columns are NaN for all of its rows, and `dropna()`
removes any row containing a NaN. Nothing else in the dataset has missing values, so *only* that
recording goes.

Why 37,401 is dangerous: it is exactly the number of labelled rows, a figure that appears in the
project brief. A wrong number that matches a known-correct number
for a different quantity passes every sanity check by eye. The loss is also total for one group, not
a thinning of all groups, so no per-experiment statistic looks odd. The only reference data for
semi-supervised detectors disappears with no error.

*Common incorrect answers*

- "Rows with sensor dropouts." There are none (no NaN in any sensor column); the question said "without running anything else", and the two shapes plus the nine-column file are sufficient.
- "Duplicates were removed." `dropna` does not deduplicate. (Duplicated rows do exist across files, 1,290 of them, and they are still there.)

#### Q3. Design choice: unlabelled file

A defensible answer picks one option, argues against two others, and names a cost.

**(a) Fill with 0** (the reference choice). For: the upstream description states the recording is
fault-free, so 0 is a label, not an imputation; the tidy table keeps integer label columns and one
schema for every experiment; semi-supervised training ("fit on normal") can select `anomaly == 0`
without special cases. Against (b): nullable labels propagate NaN into every mean, metric and
`groupby`, and invite exactly the `dropna()` that caused the original bug. Against (c): raising makes
the most important reference recording unloadable and pushes a special case into every caller.
Cost of (a): the table no longer distinguishes "labelled normal by an annotator" from "normal by
construction of the experiment"; if that file ever contained an unrecorded disturbance, the label
would be confidently wrong. Makes easier: fitting reference statistics (w2d5), semi-supervised
baselines (w2d6). Makes riskier: event-level evaluation (w3d4), if someone includes this recording
in the denominator of false alarms per hour without noticing it has no events by design.

**(d) `is_labelled` column** is also defensible, usually combined with (a): explicit provenance at
the cost of one more column every consumer must remember. **(b)** is defensible only with a strict
rule that metrics are computed on `is_labelled` rows and with nullable integer dtype; say so.
**(c)** is defensible only if the loader takes an explicit `labelled=False` argument for that file.

*Common incorrect answers*

- "Fill with 0 because it is simplest" (no argument about meaning; Partial at most).
- "NaN is more honest" without saying how every downstream mean and metric will treat NaN.
- Any answer that does not record the decision somewhere (docstring, `NOTES.md`): an undocumented labelling decision is a defect regardless of which option was chosen.

#### Q4. Commit boundaries

1. *Extract `load_raw` exactly as the notebook does it* (ids from `enumerate`), with the notebook's
   output unchanged. Evidence: unchanged characterization output or an unchanged per-experiment table.
2. *Add a failing test*: a constructed folder with `0.csv`, `2.csv`, `10.csv` of different lengths,
   asserting row counts per id. It can be committed marked as expected-to-fail, or together with 3.
3. *Fix: ids from file names (BEHAVIOUR CHANGE)*, with the test passing and `NOTES.md` recording
   that 28 of 34 ids change. Evidence: the test, and the changed table.

If the fix rides inside the extraction commit, the extraction can no longer be shown to be
behaviour-preserving (the output moved), and the id change cannot be attributed: a reviewer sees
40 lines of moved code and a different table, and has to re-derive which line did it. If you wrote
the package as new code rather than by editing the notebook, the equivalent discipline is: the
commit adding `load_raw` carries the hostile test, and `NOTES.md` attributes the disagreement with
the recorded notebook output.

*Common incorrect answers*

- "Fix it immediately, it is obviously a bug." Obvious bugs are the ones whose effects are least examined; here the fix renames most experiments, which every later artefact (split manifest, error report) depends on.
- "One commit with a good message is enough." The message can attribute; it cannot make the structural part verifiable.

#### Q5. Limits of characterization tests

Any two of:

- **Output is known to be wrong in ways that make it not worth preserving** (today's notebook: most tables depend on the id bug). Use: hand-checkable unit tests on constructed inputs, and a discrepancy table against the old output.
- **Non-deterministic output** (unseeded randomness, timestamps, thread ordering, GPU nondeterminism). Use: fix seeds and inject the clock first (w1d4); or assert invariants and tolerances instead of exact text.
- **Output too large or too coupled to formatting** (plots, long tables). Use: pin intermediate *data* (a small frame, summary statistics with tolerances) rather than rendered output.
- **Inputs you ran do not exercise the code path** (a branch only taken for a file type you do not have). Characterization gives false confidence; construct the input.
- **Numerical code across library versions.** Exact-text goldens break on a last-digit change; use `pytest.approx` with a justified tolerance (w1d5).

*Common incorrect answer:* "when the code is simple". Simplicity is not the criterion; whether the current output is a meaningful reference is.

### B. Scoring your `NOTES.md`

Demonstrated: at least four discrepancies, each with both numbers, the mechanism (the specific line
or habit), and a statement of which value is right *with a reason independent of the new code* (for
example "46,806 equals the notebook's own first shape print" or "the file `other/2.csv` has 780
lines"). Partial: discrepancies listed with numbers but mechanisms missing or generic ("the notebook
had a bug"). Not yet: fewer than three, or the package's numbers asserted as right because they come
from the package.

### D. Interview rep (debugging)

#### What a strong answer looks like

**Hypothesis ordering** (this is what is scored first). The symptom is *order dependence between
calls in one process*. So the first hypothesis is **shared mutable state that outlives a call**. Two
candidates are visible: the module-level `_CACHE` and the mutable default `overrides={}`.

1. *Is state shared across calls?* Experiment: call with an override, then without; compare.
   (`demo_order_dependence.py`: second default call returns `pressure: 1.5`.)
2. *Which object is being mutated?* Experiment: print `load_thresholds.__defaults__` and `_CACHE`
   after the calls. Result: the default is still `{}`; `_CACHE[path]` has changed.
3. *Is the returned object the cached object?* `load_thresholds(p) is load_thresholds(p)` is `True`.

**The defect.** `thresholds = _CACHE[path]` binds a second name to the cached dict; it does not copy.
`thresholds.update(overrides)` therefore writes the override into the cache permanently, and
returning that same dict lets any caller corrupt the cache by mutating the result. Two failure
routes, one cause: aliasing of a cached mutable object.

**The red herring.** `overrides={}` is the famous mutable-default pattern, and it is bad style, but
it is not the cause: the function never mutates `overrides`, only reads it. Evidence:
`load_thresholds.__defaults__` is still `({},)` after any sequence of calls. Naming it as the cause
without checking is the most common wrong answer. (It should still be changed to `None`: the next
edit that does mutate it would create a second bug.)

**Fix** (`thresholds_fixed.py`): cache the parsed file, return a new dict each time:
`return {**_CACHE[key], **(overrides or {})}`. Note for nested structures a shallow copy is not
enough; say so if the thresholds could be nested (`copy.deepcopy`, or cache an immutable form).

**Tests** (`test_thresholds.py`, four tests, run against both versions: 4 passed, 2 xfailed,
2 xpassed, i.e. the buggy version fails exactly the two below):

- an override in one call does not affect a later call without it;
- mutating the returned dict does not affect a later call.

Each test needs a fresh cache (`_CACHE.clear()` in a fixture); without that the *tests* are
order-dependent, which is the colleague's first symptom.

**Link to the lesson.** A module-level cache and a notebook kernel are the same thing: state that
persists between invocations and is invisible at the call site. `df` reused across cells and
`_CACHE[path]` aliased across calls fail for the same reason.

#### Rubric

| Level | Description |
|---|---|
| **Demonstrated** | Starts from "shared mutable state", proposes cheap discriminating experiments before reading line by line, identifies aliasing of the cached dict, explicitly clears the mutable default with evidence, fixes with a copy while keeping the cache, gives both tests and mentions cache isolation between tests |
| **Partial** | Finds the cache mutation but only one failure route; or blames the default argument first and corrects after testing; fix removes the cache entirely (correct but changes the stated requirement) |
| **Not yet** | Blames the mutable default and stops; fix is `overrides=None` only (the bug remains: verify by running the tests); no test proposed |

#### Common incorrect answers and why they fail

- **"The bug is the mutable default argument."** `overrides` is never mutated. Changing it to `None` leaves both tests failing.
- **"Tests fail together because of test ordering in pytest."** That names the symptom. Order matters *because* state leaks; pytest is behaving correctly.
- **"Remove the cache."** Fixes it but violates "parse each file once"; in a service this is a per-request disk read. Acceptable only if stated as a tradeoff.
- **`thresholds = _CACHE[path].copy()` and then caching the updated copy back.** Reintroduces the leak through a different door.
- **Deep-copy everything always.** Correct, and a cost worth mentioning; for a flat dict a shallow copy suffices.

---

# Week 1 review day — Review and catch-up (light)

✍️ Written answers: compare yours against the rubric; wording will differ.


Open only after all twelve questions have a written attempt. Each answer gives the mechanism a
"solid" answer must contain, then the common wrong answers and why they fail. Wording will differ;
score the mechanism.

### 1. Tests pass locally, the wheel is missing a subpackage

**Mechanism.** `python -m pytest` puts the current directory at the front of `sys.path`, so in a flat
layout (or with a path hack) the tests import the package *from the working tree*, where every
directory is present. The wheel contains only what the build backend was told or able to discover.
A subpackage is left out when, for example, packages are listed explicitly and the new one was not
added, automatic discovery skipped it (a directory without `__init__.py` under a configuration that
finds regular packages only), or `where`/`include` points at the wrong place. The tests exercised the
source tree, not the artefact, so both observations are consistent.

**Two independent changes that expose it:** (a) the `src` layout: the project root no longer contains
the importable package, so tests can only pass against an *installed* copy; (b) testing the built
artefact: build the wheel, install it non-editably into a fresh virtual environment, and run the
tests (or at least the entry point) from a directory outside the repository. Also acceptable:
listing the wheel's contents (`python -m zipfile -l dist/*.whl`) in CI.

| Common wrong answer | Why it fails |
|---|---|
| "Their environment is broken / wrong Python version" | Does not explain a single missing subpackage from an otherwise working install |
| "An editable install would have caught it" | An editable install also points at the source tree, so it hides the same problem |
| "Add the path with `sys.path.insert`" | Repairs the symptom on one machine and keeps the wheel wrong |
| Naming two variants of the same change (e.g. "use src layout" and "move code under src") | The question asks for independent checks: one structural, one that tests the artefact |

### 2. What an editable install does

It installs the project's **dependencies**, its **metadata** (`*.dist-info`) and its **console-script
launchers** as usual. It does **not copy the import packages**; it installs a pointer (with
setuptools a `.pth` entry or an import hook) that makes Python find them in your source tree, so edits
to existing modules are live in the next interpreter start.

Reinstall is required after changing: **dependencies**, **entry points / console scripts**,
**version or other metadata**. (Non-Python data files may also be a snapshot from install time.)

| Common wrong answer | Why it fails |
|---|---|
| "It symlinks the repository into site-packages" | Not how current tools do it, and it leads to the wrong expectation that *everything* is live |
| "Nothing needs reinstalling, that is the point" | A new `[project.scripts]` entry or dependency does not exist until reinstall; a frequent source of "command not found" |
| "It is how you deploy during development" | It is a development device; anything shipped gets a regular install of a built artefact |

### 3. Declared dependencies versus a lock

*Declared dependencies* state what the package needs to work, as **ranges** (`numpy>=1.26`): they are
a compatibility claim, consumed by an installer that must combine them with other packages'
requirements. A *lock* (pinned, ideally hashed, complete transitive list) records **exactly** what one
environment contained: it is a reproducibility record for an application, a training run, a container.

Libraries need declarations; applications and experiments need both (declarations to state intent, a
lock to rebuild the environment). If a library publishes exact pins, any two libraries that pin
different versions of a shared dependency become impossible to install together, and users cannot
receive security or bug-fix releases without the library author acting.

| Common wrong answer | Why it fails |
|---|---|
| "`pip freeze > requirements.txt` is the dependency declaration" | A freeze mixes direct and transitive packages and pins everything; it is a (weak) lock, not a declaration |
| "Lower bounds mean the old version was tested" | A bound is a claim; only a tested matrix is evidence (the course states which versions were executed) |
| "Recording versions in the run directory pins the environment" | Recording tells you what was installed; rebuilding it requires an installable lock |

### 4. Seed 3 versus seed 7, +0.04 F1

**Reason 1: the comparison is confounded by the split draw.** `split.seed` selects which units are held
out. The two runs were evaluated on different test units, so the difference mixes the feature change
with the split. In the lesson's own numbers, F1 across seeds 0-9 with *nothing else changed* ranged
from 0.778 to 0.930 (s.d. 0.044): a 0.04 difference is the size of the seed-to-seed noise.
Inspect `config.json` (resolved config: the seed and every other setting) and `metrics.json`
(held-out units, test size) in both run directories.

**Reason 2: other things may differ besides the feature change.** Different code commit, data file or
library versions would also move the number. Inspect `environment.json` (`git_commit`, `data_sha256`,
package versions) in both.

A supported claim needs the same seeds for both variants (paired comparison), several seeds, and a
difference that is large relative to the paired spread. Week 3 formalises this.

| Common wrong answer | Why it fails |
|---|---|
| "0.04 is small, so it is not significant" | Smallness is not the argument; the argument is the measured seed-to-seed spread and the confound |
| "Use the same seed and the comparison is fair" | Necessary, not sufficient: one seed is one draw; the effect may reverse on another split |
| "Both reasons are 'randomness'" | The question asks for two distinct reasons: sampling variation of the split, and uncontrolled differences in code/data/environment |
| "Check the log file" | The log narrates; the structured files (`config.json`, `metrics.json`, `environment.json`) are what make runs comparable |

### 5. Precedence and strictness

Order: **built-in defaults < config file < environment variables < command-line flags**; the source
closest to the single invocation wins. Merge the raw values first and **validate once at the end**,
so that what was validated is exactly what runs; validating per layer duplicates rules and lets a
later layer introduce an invalid value unchecked. **Unknown keys must be errors** because a lenient
lookup turns a typo (`sede = 3`) into a silently different experiment that still "runs" with the default.

| Common wrong answer | Why it fails |
|---|---|
| "File overrides CLI, because the file is the record" | Reverses the convention; the record is the *resolved* config saved after merging, not the input file |
| "Unknown keys can be ignored with a warning" | Warnings scroll past; the run then carries a result under the wrong settings |
| "Dataclass type annotations validate the types" | Annotations are not enforced at runtime; `seed="7"` constructs without complaint unless you check |

### 6. Libraries and logging configuration

Logging configuration (handlers, levels, formats) is **global process state** and belongs to the
**application**, which knows where output should go. A library that configures at import time
overrides or duplicates the application's choice, fires as a side effect of `import`, can leave the
application's own later `basicConfig()` call without effect because the root logger already has a
handler, and cannot be silenced or redirected by the host. A library module does one thing:
`logger = logging.getLogger(__name__)` and emits records. The entry point (`main`) configures
logging once: handlers on the root (or the package's top) logger, e.g. console to stderr and a file
in the run directory.

| Common wrong answer | Why it fails |
|---|---|
| "Because it is slow" | Not the reason |
| "Libraries should use `print` instead" | `print` has no levels, no routing, and pollutes stdout that may carry machine-readable output |
| "Each module should set its own level and handler" | Produces duplicated lines through propagation and scatters configuration |

### 7. Tests for `rms`

**Known answer:** a sine of amplitude `A` sampled over a whole number of periods has
RMS = `A/√2`, because the mean of `sin²` over full periods is 1/2. (A constant `c` has RMS `|c|`.)
Catches a wrong formula: missing square root (gives `A²/2`), mean absolute value (gives `2A/π`),
standard deviation instead of RMS on a signal with non-zero mean.

**Invariance:** `rms(a·x) = |a|·rms(x)` (homogeneity of degree 1); also invariance to reordering the
samples, or `rms(-x) = rms(x)`. It needs no expected constant, so it applies to arbitrary random
input and catches defects that depend on the data (sign handling, an accidental offset removal,
integer overflow or dtype truncation), but it cannot detect an error that preserves the property:
mean-abs is also homogeneous, and a constant factor error survives every scaling test. The
known-answer test catches exactly those. That complementarity is the point of having both.

| Common wrong answer | Why it fails |
|---|---|
| `assert rms(x) == np.sqrt(np.mean(x**2))` | Re-derives the implementation; a shared misunderstanding passes. It is a differential test, weaker than an independent oracle |
| "Check it returns a float / does not crash" | Kills no numerical defect |
| Sine over a non-integer number of periods with a tight tolerance | The expected value is no longer `A/√2`; the test fails for the wrong reason or gets a loosened tolerance |
| Expected value copied from a previous run | Detects change, not error |

### 8. `assert auc > 0.95` as a unit test

It is a **statistical performance check**, not a unit test: the quantity is a random variable of the
split, seed, data version and library versions, so the assertion can fail when the code is correct
and pass when the code is wrong (a factor-of-two error in a feature leaves a scaled-feature linear
model's AUC unchanged). It localises nothing when it fails, and the threshold was read off one run.
It belongs in the **evaluation layer**: computed on a fixed held-out set, reported with its
variability, compared against a baseline. In the unit suite the defensible minimum is a **smoke
check** on a tiny synthetic problem with an engineered large margin: training runs end to end,
outputs have the right shape and range, and the metric is well above chance by a margin many times
the observed seed-to-seed spread (e.g. `> 0.8` where chance is 0.5 and observed values are 0.95-1.0),
with the seed fixed and the rationale in a comment.

| Common wrong answer | Why it fails |
|---|---|
| "Lower the threshold until it stops flaking" | A tolerance chosen by loosening measures nothing |
| "Fix the seed and it is deterministic, so it is fine" | Determinism does not make it informative about correctness, and it breaks on any legitimate change of data or library version |
| "Unit tests should never involve a model" | A fast smoke test of the training path is valuable; the objection is to using a metric threshold as the correctness oracle |

### 9. Tolerances

A relative tolerance scales with the expected value, so it **vanishes when the expected value is 0**
(for example "no power outside the band"): then an **absolute** tolerance is needed, chosen relative
to the scale of the other quantities in the test. `pytest.approx` accepts when
`|actual - expected| <= max(rel·|expected|, abs)`, defaults `rel=1e-6`, `abs=1e-12`.

Choosing the size: estimate the numerical noise `η` of the computation (of order `N·ε` for a sum of
`N` terms, `ε ≈ 2.2e-16`, more under cancellation) and the smallest defect `δ` you want to detect;
choose `η ≪ tol ≪ δ`. For the window features `η ~ 1e-14` and interesting defects are `~1e-1`, so
`1e-9` is comfortable. Results that should be identical (integers, two runs of the same arithmetic)
are compared exactly.

| Common wrong answer | Why it fails |
|---|---|
| "Increase `rel` until the test passes" | Unprincipled; may exceed the defects of interest |
| "Always use `==` for floats / never use `==`" | Both absolutes are wrong: determinism checks should be exact, derived quantities need tolerance |
| "Relative tolerance is fine near zero if it is large enough" | `rel·0 = 0` whatever `rel` is |

### 10. `NOT IN` with NULLs

`tickets.customer_id` contains NULLs (anonymous tickets). `x NOT IN (a, b, NULL)` is
`x <> a AND x <> b AND x <> NULL`; the last term is **UNKNOWN**, so the whole predicate is never
TRUE: it is FALSE if `x` matches a value and UNKNOWN otherwise. `WHERE` keeps only TRUE, hence
zero rows. Executed on the diagnostic database: the `NOT IN` form returns 0 customers; each correct
form returns 350.

Correct formulations:

```sql
-- anti-join with NOT EXISTS (NULL-safe by construction)
SELECT c.customer_id FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM tickets t WHERE t.customer_id = c.customer_id);

-- LEFT JOIN ... IS NULL
SELECT c.customer_id FROM customers c
LEFT JOIN tickets t ON t.customer_id = c.customer_id
WHERE t.ticket_id IS NULL;
```

(Also valid: `NOT IN (SELECT customer_id FROM tickets WHERE customer_id IS NOT NULL)`.)

| Common wrong answer | Why it fails |
|---|---|
| "The subquery is too large / an optimiser bug" | It is three-valued logic working as specified |
| "`NULL <> x` is TRUE" | Any comparison with NULL is UNKNOWN |
| "Use `LEFT JOIN` and filter `t.customer_id IS NULL`" without care | Works here, but filtering on a nullable non-key column in general can confuse "no match" with "matched a row whose column is NULL"; test the joined table's primary key |

### 11. Scaling before the split

The scaler's mean and standard deviation were computed from **all** rows, including the held-out
units. Every training row was therefore transformed using statistics of the test set: information
from the evaluation data entered the fitted pipeline. An evaluation is supposed to estimate
performance on data the entire fitted procedure has never seen; this one cannot guarantee that.

That the printed metrics did not change on this synthetic data does not make it acceptable. The size
of a leak's effect depends on the data: with strong between-unit shifts, few units, or a
preprocessing step that uses more information (feature selection, target encoding, imputation), the
same construction inflates results materially, and you cannot know which case you are in without
doing it correctly. The property you need is **correct by construction**: put preprocessing inside
the estimator (`Pipeline`) so it is fitted on training rows only, every time, including inside
cross-validation.

| Common wrong answer | Why it fails |
|---|---|
| "It is not leakage because the labels were not used" | Leakage is about any information from evaluation data, not only labels |
| "No change in metrics, so it was harmless and can stay" | An empirical null on one dataset is not a guarantee; the procedure is wrong regardless of the outcome |
| "Fit the scaler on the test set separately" | Different problem: train and test are then scaled inconsistently, and deployment has no test set to fit on |

### 12. Characterisation tests; what stays out of Git

A **characterisation test** records what the existing code *currently outputs* on fixed inputs
(the golden numbers or files), without judging whether that output is right. You write it **before**
restructuring because it is the only oracle available for legacy code: after each small step, an
identical output shows that behaviour was preserved, so structural changes and behaviour changes are
never mixed in one commit. It is **replaced** as functions acquire real contracts: once a piece has
tests with independent oracles (known answers, invariances), the corresponding pin can go. It must be
**updated deliberately**, in its own commit with the reason recorded, whenever you intentionally
change behaviour (such as removing the scaling leak): the pin never justifies keeping a bug.
Its limit (`w1d6`): it covers only the inputs it was run on, so a path those inputs never exercise is
unprotected; state which inputs the golden output covers.

**Why not mix the two kinds of change in one commit** (the `w1d6` rule): a structural change is
verified by an *unchanged* characterisation output; a behaviour change is verified by a *changed*
output that you can explain, plus a new or updated test. A commit containing both can be verified by
neither kind of evidence, and it cannot be reverted or bisected cleanly.

Keep out of Git, with reasons:

1. **Secrets and credentials** (`.env`, keys, cloud credential files): history is permanent and widely copied; a pushed secret must be treated as compromised.
2. **Raw and derived data, model artefacts, run outputs** (`data/raw/`, `runs/`, checkpoints): large, regenerable, sometimes licence-restricted; version them by hash, manifest and download script.
3. **Environments and build products** (`.venv/`, `__pycache__/`, `*.egg-info/`, `build/`, `dist/`): machine-specific and reproducible from declarations.
4. **Editor, OS and tool caches; notebook checkpoints and outputs** (`.ipynb_checkpoints/`, `.pytest_cache/`): noise in diffs, and notebook outputs can embed data.

| Common wrong answer | Why it fails |
|---|---|
| "A golden test proves the code is correct" | It proves the code is unchanged; a bug present at pinning time is enforced |
| "Write the tests after the refactor" | Then nothing verifies that the refactor preserved behaviour |
| "Delete the secret in the next commit" | It remains in history; rotate the secret |
| "Commit the dataset so results are reproducible" | Reproducibility needs identity (hash, source, version), not a copy in the repository; licences such as SKAB's GPL-3.0 are a further reason this course downloads instead |

*Answer 12 was re-checked against the final `w1d6` lesson and handbook H2.3 (2026-11-21).*

---

# Notebook 07 — SQL I: grain, joins, aggregation and NULL semantics

✍️ Written answers: compare yours against the rubric; wording will differ.


Open after writing your own. Numbers were measured on `data/maintenance.db` (SYNTHETIC).
Reference queries: `lab/queries/`, `challenge/queries/`. Reference bug report: `lab/FANOUT_REPORT.md`.

### A. Reasoning questions

**A1.** Let `L` be the machine's true labour hours and `D` its true downtime hours.

| | `SUM(labor_hours)` | `SUM(hours)` | `COUNT(DISTINCT wo_id)` | `COUNT(wo_id)` |
|---|---|---|---|---|
| (i) `a, b ≥ 1` | `b·L` | `a·D` | `a` (correct) | `a·b` |
| (ii) `a ≥ 1, b = 0` | `L` (correct) | NULL | `a` (correct) | `a` (correct) |

With `b = 0` the LEFT JOIN adds one NULL-extended downtime row per work order, so nothing is
multiplied. A reviewer who spot-checks a machine without downtime (or with exactly one event) sees
correct labour and concludes the query is right. Machine 2 in the data is such a case (6 orders, no
downtime); machine 1 (4 orders, 5 events) shows 92.0 instead of 18.4. The error is proportional to
the *other* child's row count, so it is largest for the busiest, most important machines.

*Common incorrect answers.* "Both sums are multiplied by `a·b`" (each is multiplied by the other
child's count only). "`COUNT(DISTINCT)` shows the query is fine" (it repairs identifier counts and
nothing else). Forgetting that `SUM` over only NULLs is NULL, not 0.

**A2.** (1) The inflation is not uniform: each work order is repeated once per part line, so the
factor differs per order (1 to 6 here) and therefore per site. Per site the ratio of reported to true
labour is 1.07, 0.85, 1.46, 2.00 and 1.40. (2) The query also *drops* rows: the inner join to
`parts_used` removes the 36 work orders without parts (11, 5, 10, 4 and 6 per site) and the site with
no machines. Site 2 is under-reported (80.7 against 95.5) because it loses more through dropped
orders than it gains through duplication. Two opposing errors of different size per group cannot be
undone by one constant; 32 % is only their net effect on the grand total.

*Common incorrect answers.* "Divide by the average number of parts per order" (ignores dropped
orders and per-order variation). Stating only the over-count: the under-count is the part that makes
the tile misleading in both directions.

**A3.** After the join the rows are at the part-line grain, one row per `(wo_id, part_id)`.
`quantity * unit_cost` is defined at exactly that grain, and every part line appears once, so its sum
is right. `labor_hours` is defined at the coarser work-order grain and is repeated on every part
line. Rule: *in a joined result, a column may be summed only if the result's rows are at the grain
at which that column is defined, and no row of that grain was dropped.* Before running anything, find
the finest-grained table in the join chain; only its measures are safe. (The inner join did not drop
part lines, because every part line has a work order, a machine and a site.)

*Common incorrect answer.* "Because parts were joined correctly": the join is the same one that
breaks labour. Correctness is a property of the measure–grain pair, not of the join.

**A4.** For the 13 machines whose `criticality` is NULL both comparisons evaluate to UNKNOWN, and
`WHERE` keeps only TRUE. The two queries are not complements. "Not known to be high":
`WHERE criticality <> 'high' OR criticality IS NULL` (25 rows). Engine-specific null-safe forms exist
(`IS DISTINCT FROM 'high'` in PostgreSQL and DuckDB; `criticality IS NOT 'high'` in SQLite); the
portable version is the explicit `OR … IS NULL`. `COALESCE(criticality, 'unknown') <> 'high'` also
works and states the intent.

*Common incorrect answers.* "NULL is treated as false" (the predicate is UNKNOWN, which is why `NOT`
does not rescue it: `NOT (criticality = 'high')` still excludes the NULLs). "`!=` instead of `<>`"
(same operator).

**A5.** `AVG(labor_hours)` = 7.64 is the mean over the 83 orders with recorded hours.
`AVG(COALESCE(labor_hours, 0))` = 6.82 is the mean over all 93 orders *assuming the 10 unrecorded
ones took zero hours*, which is almost certainly false. Which to report depends on the missingness
mechanism. If hours are missing at random with respect to duration, 7.64 estimates the mean hours per
order. If they are missing because the order is still open, or because short jobs are not booked, the
recorded subset is biased and neither number is the population mean; you would report 7.64 with the
coverage (83 of 93) and investigate. Zero-filling is right only when NULL genuinely means "no work
done". Report the denominator with any average over a nullable column.

*Common incorrect answer.* "COALESCE is safer because it handles NULLs": it replaces a visible
unknown with an invisible wrong value.

**A6.** Defect 1 (NULL): `work_orders.tech_id` is NULL for unassigned orders, so the subquery
contains NULL and `NOT IN` can never be TRUE; the query returns no rows whatever the data says.
Defect 2 (logic): the subquery lists technicians who worked at a site *other than* 3. Excluding them
answers "technicians who worked only at site 3, or nowhere", not "never worked at site 3". The
negation belongs outside, the positive condition inside:

```sql
SELECT t.tech_name FROM technicians t
WHERE NOT EXISTS (SELECT 1 FROM work_orders w JOIN machines m USING (machine_id)
                  WHERE w.tech_id = t.tech_id AND m.site_id = 3);
```

This returns four technicians (ids 1, 10, 11, 12). "No rows" was read as an answer when it was a
symptom; an anti-join that returns nothing deserves the check `SELECT COUNT(*) - COUNT(col)` on the
subquery column.

*Common incorrect answer.* Fixing only the NULL (`WHERE w.tech_id IS NOT NULL` in the subquery) and
keeping `<> 3`: the query then runs, returns rows, and answers the wrong question.

### B. Design choice

**B1 (model answer).** I would use design (2): one CTE per source, each aggregated to the machine
grain, left-joined to `machines`. Correctness: each join is one-to-at-most-one, so the row count is
fixed at the number of machines by construction, and no measure can be multiplied by a sibling
table's row count. Design (1) is correct only while every aggregate happens to be fan-out-safe;
adding one `SUM` later breaks it silently. Reviewability: each CTE can be read and run alone, and its
grain is one `GROUP BY` line. Testability: I can assert `COUNT(*) = (SELECT COUNT(*) FROM machines)`,
uniqueness of `machine_id`, and that each feature total reconciles with its source table; in design
(1) there is no intermediate to test. Cost: (2) scans each child once and joins small aggregates,
usually cheaper than building the multiplied intermediate. I would accept (1) only for a single
child table, where no sibling exists to multiply against. Either way the feature windows must end
before the label period starts, which is a separate (temporal) leakage question.

*Common incorrect answers.* "(1), with DISTINCT where needed": works today, has no protection
against the next edit. "They are equivalent if written carefully": true of results, false of
failure modes. Ignoring that machines with no activity must be present with zeros (they are likely
negatives).

### D. Interview rep — worked answer and rubric

Executed reference: `python solutions/labs/w2d1_sql_joins_grain/interview_rep/country_summary.py`
(prints the model answer and the usual wrong answer on a six-user toy table).

```sql
WITH s AS (SELECT user_id, COUNT(*) AS n_sessions FROM sessions GROUP BY user_id),
     p AS (SELECT user_id, SUM(amount) AS revenue FROM purchases GROUP BY user_id)
SELECT COALESCE(u.country, 'unknown')                  AS country,
       COUNT(*)                                        AS n_users,
       COUNT(p.user_id)                                AS n_buyers,
       COALESCE(SUM(p.revenue), 0)                     AS revenue,
       1.0 * COALESCE(SUM(s.n_sessions), 0) / COUNT(*) AS sessions_per_user
FROM users AS u
LEFT JOIN s ON s.user_id = u.user_id
LEFT JOIN p ON p.user_id = u.user_id
GROUP BY COALESCE(u.country, 'unknown');
```

Reasoning to say aloud: result grain is country; users is the driving table; sessions and purchases
are two independent children of user, so each is reduced to one row per user first; after the joins
the rows are still one per user, so `COUNT(*)` is users and `COUNT(p.user_id)` is buyers.
`AVG(s.n_sessions)` would be wrong: it skips users with no sessions. Convincing the reviewer:
the revenue column must sum to `SELECT SUM(amount) FROM purchases`, and `n_users` to
`SELECT COUNT(*) FROM users`; both are one-line checks.

On the toy data the naive two-join query reports revenue 120 for KZ (true 40) and 3.5 sessions per
user (true 2.0), while its `n_users` and `n_buyers`, protected by `DISTINCT`, are right.

| Criterion | Meets | Not yet |
|---|---|---|
| Grain stated before writing | Says "one row per country; one row per user before grouping" | Starts typing joins |
| Fan-out avoided | Pre-aggregates both children, or uses correlated subqueries | Joins both children and sums |
| NULL handling | `unknown` group; zero-session users in the denominator; revenue 0 not NULL | `AVG` over joined sessions; NULL country row left as NULL |
| Integer division | `1.0 *` or a cast | integer result |
| Verification | Names at least one reconciliation total unprompted | "I would look at the output" |
| Time | Working answer within 15 minutes | — |

*Common incorrect answers.* `COUNT(DISTINCT …)` for the counts and plain `SUM(amount)` for revenue
(the classic); `AVG(n_sessions)` after the left join (drops zero-session users from the mean); leaving the
NULL country as a NULL group when the prompt asks for `'unknown'`; integer division in the average.

---

# Notebook 08 — SQL II: CTEs, window functions and time-series queries

✍️ Written answers: compare yours against the rubric; wording will differ.


Open after writing your own answers. Numbers quoted for the lab database were read from runs on
2026-11-21 (SQLite 3.53.1). The data is SYNTHETIC.

### Q1 — frames by hand

| id | (a) default frame | (b) explicit ROWS, total order | (c) empty OVER |
|---|---|---|---|
| 1 | 10 | 10 | 36 |
| 2 | 35 | 30 | 36 |
| 3 | 35 | 35 | 36 |
| 4 | 36 | 36 | 36 |

(Executed: these are the values SQLite returns.) With `ORDER BY` and no frame, the frame is
`RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`, and under RANGE the current row extends to its
last peer, so rows 2 and 3 (both `t = 2`) each include the other. (c) has no `ORDER BY`, so every
row is a peer of every other and the frame is the whole partition.

*Common incorrect answers*

- **(a) = 10, 30, 35, 36.** Assumes rows. This is the belief the lesson exists to remove.
- **(a) = 10, 30, 30, 36 or "undefined".** The result is fully defined; it is the *order of ties in
  (b) without `id`* that would be undefined.
- **"They differ because of ROWS vs RANGE" with no mention of peers.** True but not an explanation:
  with no ties the two frames give identical results, which is why the bug hides in testing.

### Q2 — evaluation order

`WHERE alert = 1` is applied before the window is computed, so the partition contains only alerting
readings and `LAG` returns the previous *alerting* reading. The query returns the time since the
previous alert, not since the previous reading. Fix: compute the gap over all readings in a CTE,
filter afterwards.

```sql
WITH gaps AS (
    SELECT reading_id, alert,
           ts_epoch - LAG(ts_epoch) OVER (PARTITION BY device_id ORDER BY ts_epoch) AS gap_s
    FROM readings_dedup
)
SELECT reading_id, gap_s FROM gaps WHERE alert = 1;
```

On the lab database both versions return 546 rows; the median is 322.5 s for the wrong version and
304 s for the right one. The medians are close because most alerting readings sit inside runs, where
the previous reading is also an alert. The difference is concentrated at the first reading of each
run, where the wrong version reports the time since the previous episode. A bug that is right
for most rows is the usual shape of window-function errors.

*Common incorrect answers*

- **"Add `PARTITION BY`"** — it is already there; the problem is the row set, not the partition.
- **"Use `HAVING`"** — `HAVING` also runs before windows.
- **"`LAG` skips NULLs"** — unrelated; `LAG` reads the physical previous row of the partition.

pandas has the same hazard: `df[df.alert == 1].groupby("device_id").ts_epoch.diff()`.

### Q3 — "latest row"

- (i) and (ii) return **every** row tied at the maximum timestamp: two rows for each device in the
  lab data (verified: all six devices have two). A join on `device_id` then duplicates every
  downstream row for those devices; counts and sums inflate.
- (iii) returns one row per device, but *which* of the tied rows is not determined by the query.
  It can change with the query plan, an index, or the engine. One row, unstable content.
- Accept none as written. Require `ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY ts_epoch DESC,
  event_id DESC)`: a total order, justified by a domain rule ("log order"). Also ask for a test that
  `COUNT(*) = COUNT(DISTINCT device_id)` in the result.

*Common incorrect answers*

- **"(iii) is fine, ROW_NUMBER guarantees one row."** It guarantees one row, not the right one.
- **"Use `SELECT DISTINCT` to remove the duplicates."** The tied rows differ in `status`, so they
  are not duplicates; `DISTINCT` keeps both.
- **"Use `MAX(status)`"** — picks alphabetically; `running` beats `fault`.

### Q4 — merging runs separated by one reading

The grouping stays; only the start condition changes. Number each device's readings 1, 2, 3, ...
in time order (`pos`). Among alerting rows, a row starts a new episode unless the previous
*alerting* row is at most two positions back:

```sql
WITH seq AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY ts_epoch) AS pos
    FROM readings_dedup
),
alerts AS (
    SELECT *,
           CASE WHEN pos - LAG(pos) OVER (PARTITION BY device_id ORDER BY pos) <= 2 THEN 0 ELSE 1 END AS starts
    FROM seq
    WHERE alert = 1          -- deliberate: here "previous alerting row" is exactly what LAG should see
),
numbered AS (
    SELECT *, SUM(starts) OVER (PARTITION BY device_id ORDER BY pos
                                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS episode_no
    FROM alerts
)
SELECT device_id, episode_no, MIN(ts) AS start_ts, MAX(ts) AS end_ts, COUNT(*) AS n_alert_samples
FROM numbered
GROUP BY device_id, episode_no;
```

Executed on the lab database: 110 episodes instead of 113, covering the same 546 alerting readings.
Note that this is the Q2 mechanism used on purpose: the `WHERE` restricts the window to alert rows.
The first alerting row of a device has `LAG(pos)` NULL, the comparison is NULL, and `CASE` falls to
`ELSE 1`, which is the intended start.

Relation to detection work: this is the merge-gap rule (join detections closer than a refractory
interval). Differences worth stating: the gap here is measured in **rows**, so a 2-hour outage
between two alerts counts as "adjacent"; a time-based rule (`ts_epoch - LAG(ts_epoch) <= 600`) is
usually what the requester means, and you should ask. A minimum-duration rule would be a `HAVING`
on the grouped result.

*Common incorrect answers*

- **Changing `GROUP BY`** or post-merging episodes with a self-join: works, but quadratic and much
  harder to get right than changing the start mark.
- **`LAG(alert, 2) = 1`** on all rows as the only condition: mishandles the pattern 1, 0, 0, 1 vs
  1, 0, 1 unless combined carefully, and breaks at partition starts.

### Q5 — is it point-in-time correct?

- **(a) leaks.** For a label on the 10th, the monthly mean includes the 11th to the 31st. Any
  aggregate over a period that contains the label time, and extends past it, reads the future.
- **(b) leaks,** more subtly: the normalising constants are computed from all rows, including
  those after `t` (and, in a train/test setting, from test rows). The effect is often small, as you
  saw with the scaler in W1D3; the fix is by construction, not because a metric moved.
- **(c) can leak.** `readings_dedup` keeps the transmission with the highest `reading_id`, the
  *corrected* value, which arrived after the measurement and possibly after `t`. At prediction
  time only the first transmission existed. The measurement timestamp is in the past; the
  information is not. Detecting this needs an ingestion timestamp per row (bitemporal data:
  event time and knowledge time), and the feature rule becomes "ingested_at <= t". The lab
  database lacks that column, so this cannot be fixed there, only named.

*Common incorrect answers*

- **"(a) is fine because it's the same device."** Entity match is necessary, not sufficient.
- **"(c) is fine, it passed the future-invariance check."** The check edits rows by *event* time. It
  cannot see late-arriving corrections. No test replaces knowing how the table is written.

### Q6 — design choice (model answer)

Design 2. Converting the 2,000 calibration rows to half-open intervals `[valid_from, valid_to)`
with `LEAD(valid_from) OVER (PARTITION BY device_id ORDER BY valid_from)` is cheap and makes the
rule explicit and unit-testable on the small table: intervals of one device must not overlap and
must tile the time axis from its first `valid_from`; the last interval has `valid_to` NULL, meaning
open. The fact-side join then matches **at most one** row per reading by construction, so there is
no fan-out followed by a 500-million-row `ROW_NUMBER` sort, which is what design 1 costs: every
reading first joins to *all* earlier calibrations of its device and the excess is discarded.
Boundaries are visible in the predicate: `valid_from <= ts AND (valid_to IS NULL OR ts < valid_to)`
makes `valid_from` inclusive, matching the specification. A `LEFT JOIN` keeps readings older than
the first calibration. Ties cannot occur if `(device_id, valid_from)` is unique, which should be
enforced as a constraint or a data-quality check rather than assumed. Design 3 moves 500 million
rows out of the warehouse to do what the warehouse can do in place, and creates a second
implementation for the serving path to diverge from; `merge_asof` is the right tool for testing the
SQL on a sample. Tests: row count equals the reading count; no reading matches two intervals; the
lab's comparison against an independent implementation on a sample; future-invariance (appending a
later calibration row changes no earlier reading). I would revisit the choice if the engine has a
native as-of join, which is usually both clearer and faster than either pattern.

(Executed: the interval form returns exactly the same table as the reference `q6` on the lab database.)

*Common weak answers*

- **"Design 1 because it is the one from the lab."** No cost reasoning.
- **"Design 3 because pandas is easier to test."** Ignores data volume and the duplicated logic.
- **Design 2 with `BETWEEN valid_from AND valid_to`.** `BETWEEN` is closed on both sides, so a
  reading exactly at a change time matches two intervals.

### Interview rep — reference and rubric

Reference query: [`interview_rep/longest_streak.sql`](labs/w2d2_sql_windows_timeseries/interview_rep/longest_streak.sql), verified by
`python solutions/labs/w2d2_sql_windows_timeseries/interview_rep/check_longest_streak.py`.

The idea: after de-duplicating to one row per (user, day), consecutive days have consecutive
`ROW_NUMBER()` values, so `day_number − row_number` is constant within a streak. Group by it.

| Criterion | What a good answer shows |
|---|---|
| Grain first | de-duplicates to (user, day) before anything else and says why |
| Island key | date minus row number (or start-mark and running sum) with correct partitioning |
| Date arithmetic | converts dates to day numbers; does not subtract text; month and year ends work |
| Final selection | one row per user via `ROW_NUMBER` ordered by length descending then start; not `MAX` joined back (ties) |
| Verification | builds a tiny table including a duplicate day, a month boundary, a single-day user, a tied pair of streaks |
| Communication | states grain at each step; answers the follow-ups |

Follow-ups: grain after step one is (user, day). Month boundaries work because the day number is a
count of days, not a `YYYYMMDD` integer (a frequent bug: 20260131 + 1 is not 20260201). Allowing
one missed day means switching to the start-mark form: a new streak starts when
`day − LAG(day) > 2`.

*Common incorrect answers*

- **Skipping the de-duplication.** Two logins on one day get row numbers n and n+1 with the same
  date, which splits the streak.
- **`ROW_NUMBER` without `PARTITION BY user_id`.** Row numbers run across users.
- **Final step `WHERE streak_days = (SELECT MAX(...))`.** Returns two rows for a user with tied streaks.

### Challenge — what the feature table shows

Reference: [`challenge/features.sql`](labs/w2d2_sql_windows_timeseries/challenge/features.sql). Point-in-time correctness rests on one
condition per source, each placed in a join's `ON` clause: `r.ts_epoch <= l.label_ts_epoch` (twice)
and `e.ts_epoch <= l.label_ts_epoch`.

ROC AUC of each raw feature against `failed` on the shipped database (38 labels, 15 failures;
missing values filled with the median; for `seconds_since_fault` the sign is flipped and missing
means "long ago"):

| Feature | Correct query | With the named leak |
|---|---|---|
| `last_temperature` | 0.484 | 0.670 (nearest reading instead of last prior) |
| `mean_temp_60m` | 0.441 | 0.971 (window of 60 minutes on both sides) |
| `n_alerts_24h` | 0.514 | — |
| `seconds_since_fault` | 0.458 | 1.000 (nearest fault at any time) |

How to read this honestly:

- With 15 positives and 23 negatives, the standard error of an AUC near 0.5 is roughly 0.10
  (Hanley–McNeil approximation), so the correct features are **indistinguishable from chance** on
  this data. The generator contains a weak precursor, but it does not show at this sample size.
  That is a legitimate result: "no usable signal in these features with 38 labels".
- Each leaky variant looks like a breakthrough. `seconds_since_fault` reaches 1.000 because the
  fault event *is* the failure, logged minutes later. An AUC that jumps from about 0.5 to about 1.0
  from one feature should trigger an audit of that feature before anything else.
- The tempting wrong conclusion is "the honest features are useless, so the centred window is
  better". The centred window is not a better feature; it is not available when the prediction is
  made.
- This is SYNTHETIC data built to show the mechanism. It says nothing about how predictable real
  refrigeration failures are.

*Common incorrect submissions* (kept as mutants; all rejected by the checks):

| Mutant | Mistake |
|---|---|
| `centered_window` | `ABS(r.ts_epoch - l.label_ts_epoch) <= 3600` for the hourly mean |
| `nearest_reading` | orders candidate readings by absolute time distance |
| `fault_any_time` | joins fault events without a time bound and takes the nearest |

Two further mistakes the specification check catches without reading the future: putting the time
bound in `WHERE` after a `LEFT JOIN` (labels without history disappear), and `>=`/`<` slips at the
interval ends (a reading exactly at the label time must be included).

---

# Notebook 09 — pandas ingestion, schemas and data-quality checks (project data arrives)

✍️ Written answers: compare yours against the rubric; wording will differ.


### Q1

Sorting and de-duplicating in the loader makes the time-order and key-uniqueness checks impossible
to fail, so the pipeline can no longer tell a healthy feed from one whose logger writes retries or
appends out of order. The fault persists upstream and reappears in every later delivery. The repair
is also arbitrary: `drop_duplicates` on the key keeps whichever conflicting row happens to come
first, and nobody chose that. If duplicates were common, the loader would stay faithful, the check
would stay an error by default, and a separate, named transformation ("keep the last-written row per
key", justified by how the logger works) would run after detection, report how many rows it changed,
and have its own test. Better still, fix the source.

*Common incorrect answers.* "It costs performance" (irrelevant at this size and not the point).
"Sorting might change results" (true but vague: the issue is that the evidence of a fault is
destroyed). "Keep it but log a message" (a log line is not a control; nothing fails).

### Q2

(a) **Error.** Missing sensor values make window statistics undefined or silently shortened; the
contract says none are tolerated. If such data had to be accepted, that is a contract change with an
explicit missing-value policy, not a quiet downgrade.
(b) **Warning.** Every row is valid; the *evaluation design* (one event per experiment) is what is
affected, so event matching must handle it or exclude the experiment knowingly.
(c) **Neither check in the reference would fire**, and that is the instructive part: within the file
the differences are intact, and timestamps are naive. It matters only if experiments are ordered or
joined in absolute time. Classify as warning-worthy *if* a cross-experiment order is ever used (for
a temporal split, say); otherwise document. The wrong answer is "error because the time is wrong".
(d) **Warning by the stuck-sensor rule; arguably an error.** Zero voltage for 400 rows is a dead
channel or a powered-down motor. The rows are valid as recorded, so the mechanical answer is
warning plus a plausibility-range failure. Promoting it to error is defensible when a later step
would treat the channel as informative. Credit goes to the argument, not to the label.
(e) **Not an error for reading** (all required columns are present), but it should not pass
unnoticed: an unexpected column means the source changed. Report it as a warning and do not carry
the column into the tidy table. "Error, reject the file" is too strict; "ignore silently" is the
failure this lesson is about.

*Common incorrect answers.* Ranking by alarm ("zero voltage is terrible, so error; duplicates are a
few rows, so warning") — the criterion is whether downstream computation becomes silently false.

### Q3

1. **Different library version formats a float or datetime differently** (most likely: CI installs
   the newest pandas satisfying a lower bound). Discriminate: compare the `code` block of the two
   `provenance.json` files; diff the two CSVs and look at which characters differ.
2. **Row or file order differs**, e.g. directory listing order used without sorting, or a `set`
   iterated. Discriminate: the diff shows whole lines moved; sort both files and re-hash.
3. **Line endings or encoding** (`\r\n` on another platform, or a locale-dependent default).
   Discriminate: byte counts differ by exactly the row count; `file`/hexdump of the first line.

Then pin what mattered: explicit `lineterminator`, explicit sort key, and locked dependency
versions for the environment that produces artefacts (Week 6).

*Common incorrect answers.* "Floating point is non-deterministic" (the same operations on the same
platform are deterministic; name the mechanism). "The data changed" (excluded by the premise that raw
hashes match). Proposing to compare with a tolerance instead of finding the cause.

### Q4

(i) **Nightly training: fail closed** (the reference design). Training on yesterday's table while
the report says today's feed is broken produces a model whose inputs nobody intended, and a stale
table next to a failing report is indistinguishable, to the next job, from a fresh one. The job
should stop and alert; skipping one retrain is cheap. What the design must add: an alert that a
human sees, and a retry path.

(ii) **Online scoring: fail stale, explicitly.** A service that loses its reference statistics
cannot score at all, and an outage is usually worse than statistics that are a day old. So keep the
last *validated* table, but (a) promote new tables atomically — write to a temporary path, validate,
then rename, so a failed run never touches the published one — and (b) expose the age and identity
of the table in use (a hash, a "validated at" marker in the *log or metadata*, an alert when age
exceeds a limit). Without (b), "still have something to run on" becomes silently serving week-old
data.

The general point: neither design is right in the abstract. What is wrong is having no stated
behaviour, or a table whose freshness cannot be read off.

*Common incorrect answers.* "Always keep the last good table, availability matters" with no
staleness signal. "Always delete" for a service that then crashes at 03:00. Not noticing that the
reference's delete-then-raise is itself not atomic for concurrent readers.

### Q5 — reference report

See `challenge/QUALITY_REPORT.md` in this solutions folder.

### Interview rep — rubric and a model answer outline

| Element | Strong answer |
|---|---|
| Starts with *why* it is missing | Asks how missingness arises before proposing any method |
| Names the mechanisms with a pump example each | MCAR (random packet loss); MAR (older firmware drops readings — depends on an observed variable); MNAR (sensor saturates or disconnects under high vibration — depends on the unobserved value itself) |
| Proposes how to find out | Missing rate by unit, time, firmware, operating state; does missingness predict the label?; runs versus scattered; ask the owners |
| Draws the consequence for training **and** serving | Whatever is done offline must be computable online from past data only; missingness will also occur at inference |
| Chooses a treatment conditionally | MCAR and short gaps: causal forward-fill/interpolation with a maximum gap; MAR: impute conditional on the observed driver, or model per group; MNAR: keep an explicit missing indicator, never impute to the mean, treat missingness as signal *if it will exist the same way in production* |
| Guards against leakage | Imputation statistics fitted on training data only; no interpolation using future samples; if missingness is caused by the failure or by the maintenance process, an indicator can leak the label |
| States what to monitor | Missing rate per sensor as a monitored quantity with an alert |

Outline of a good three-minute answer: "First I would not impute anything until I know the
mechanism, because the right treatment and even the sign of the bias depend on it. I would look at
the missing rate per pump, over time, by firmware and operating regime, and check whether
missingness is associated with the label. If it is scattered and unrelated to anything — packet loss
— I fill short gaps causally and drop windows with long ones. If it tracks something observed, say
one firmware version, I handle it per group and tell the owners. If it tracks the value itself — the
sensor cuts out when vibration is extreme — then the missing rows are the interesting ones: mean
imputation would erase exactly the signal, so I keep a missing indicator. But I check whether that
indicator would exist identically in production and whether it is produced by the failure or by the
repair, because then it leaks. Whatever I choose is fitted on training data, uses only the past, runs
identically at serving time, and the missing rate becomes a monitored metric."

*Common weak answers.* Opening with "I would use KNN/MICE imputation". Treating 8 % as a threshold
question ("below 10 % so drop the rows"). Dropping rows without asking whether dropped rows differ.
Forgetting that the model will meet missing values at inference. Using bidirectional interpolation
on a time series that will be scored online.

---

# Notebook 10 — Problem framing and versioned split definitions

✍️ Written answers: compare yours against the rubric; wording will differ.


Open only after writing your own answers.

### Q1

**First question:** *what was a fold made of: rows or whole experiments?* Rows one second apart in the
same recording are near-duplicates (same operating point, same slowly varying temperatures), so a
row-level fold lets the forest look up the neighbours of each test row.

**Expected change:** a clear drop and a much wider spread across folds. Measured in this lesson on the
25 development experiments (`example/skab_row_vs_experiment.py`): row-level 4-fold ROC-AUC 0.986
(folds 0.982-0.987), experiment-level 4-fold 0.849 (folds 0.740-0.936); PR-AUC 0.980 versus 0.841.

*Common incorrect answers.*
* "Ask which hyperparameters were used" or "ask whether the scaler was fitted inside the folds." Real
  issues, second-order here: a forest does not need scaling, and no tuning explains 0.99.
* "The number will drop to chance." Not what happens: the sensors do carry transferable signal. The
  honest statement is "lower and far more variable", and the variability is itself a finding.
* "ROC-AUC is the wrong metric." True (prevalence 35 %, and the decision is event-level), but it is
  not the *first* question; a correct metric on a leaking split is still meaningless.

### Q2

| Case | Unit of generalisation | Split |
|---|---|---|
| (a) seizure detector for unseen hospitals | hospital (patients nested inside) | hold out whole hospitals; patient-wise is necessary but not sufficient (site effects: amplifiers, montage, annotators) |
| (b) same 200 shops, next quarter | time | temporal: train on the past, test on a later period; grouping by shop is *not* required because the shops recur. A random split by shop would answer a question nobody asked |
| (c) card fraud | time, and the entity that carries the pattern (card; ideally also merchant/ring) | temporal first; within the evaluation period report separately for cards seen and not seen in training; be aware that ring-level leakage via merchants survives a card-level split |
| (d) one pump retrained monthly | time, within that pump | temporal (walk-forward) on that pump's history. Cross-pump splitting would measure something irrelevant |

*Common incorrect answer:* "always split by group." The unit is derived from the deployment
situation. (b) and (d) are the cases experienced cross-subject researchers get wrong by reflex.

### Q3

1. **Logging gap in two test experiments.** The manifest does not change. A data-quality fact about
   test data is handled by a rule decided without looking at model results (for example: "segments
   after a gap longer than 5 s restart the feature warm-up"), applied to *all* experiments. Removing
   test experiments because they are inconvenient is selection on the test set.
2. **Four new experiments.** `v1` stays as it is, so old results remain interpretable. Either leave
   the new recordings unassigned and use them as an additional, later test set (the most valuable use:
   they are genuinely post-hoc), or create `v2` that adds them, and recompute and relabel every
   result. `validate_splits` should fail until one of these is done.
3. **Disappointing result, another seed looks better.** Nothing. This is exactly what freezing is for.
   Re-drawing the split after seeing results turns the test set into a tuning knob; the estimate is
   then optimistic by an unknown amount. If family balance is a real concern it had to be raised
   before results (and stratification already addresses it).

*Common incorrect answers:* "regenerate with the same seed after adding the files" (the worked
example, part 2, shows membership changes); "drop the two gappy experiments from test."

### Q4

| Framing | Labels needed | Right when |
|---|---|---|
| (a) forecast next minute of pressure | none beyond the signal itself (self-supervised) | the decision depends on a future *value* (for example scheduling against a limit), or as an intermediate step whose residual becomes an anomaly score |
| (b) classify windows normal/faulty | reliable positive and negative labels covering the fault types you expect to meet | faults recur in known forms and there are enough labelled episodes per form; fails silently on fault mechanisms absent from training |
| (c) anomaly detection on normal data | plenty of verified-normal operation; fault labels only for *evaluation* | faults are rare, varied or new; the price is that "abnormal" includes harmless novelty (a new operating mode), so false alerts rise after any process change |

For SKAB: (a) is not the goal because no decision uses a forecast value; (b) is possible (35 %
positives) but protocol B tests whether it survives unseen fault families; (c) matches the stakeholder
need and has a designated fault-free recording. The labels and sampling structure decide, not the
model family one prefers.

*Common incorrect answer:* "forecasting needs no labels so it is always the safest." It needs no
*fault* labels, but then nothing in training tells the model which deviations matter.

### Q5 (design choice)

**For a fixed test set plus grouped development folds.** One untouched set of experiments gives a
final estimate that no modelling decision has influenced, at the cost of a single evaluation; it is
simple to explain and to audit ("these nine files were never used"), it mirrors how a model is
actually accepted before deployment, and it cannot be eroded by the dozens of small choices
(features, thresholds, which baseline to keep) that nested CV only protects against if *every* choice
is inside the inner loop, which in practice it never is.

**Strongest argument against, at this size.** Nine experiments means nine events: event recall moves
in steps of 0.11 and its interval is very wide; `valve2` is represented by a single test experiment.
Nested cross-validation would use all 34 events for the estimate and so be far less noisy.

**What to report so the weakness is visible.** The test estimate *with* an experiment-level bootstrap
interval; the grouped cross-validation estimate on the development pool next to it (if they disagree
strongly, say so); per-family results; and the count of events behind every number.

*Rubric.* 2 points: both sides argued with a mechanism, and a concrete reporting remedy. 1 point: one
side only, or "nested CV is more rigorous" without saying what it costs. 0: treats the choice as
arbitrary. *Common incorrect answer:* "a fixed test set wastes data, so use all of it for CV and
report the CV score of the tuned model" - that is the selection-optimistic number.

### Interview rep: model answer

Prioritised checks (strongest first):

1. **Label availability / censoring.** Customers who signed up in the last 12 months cannot have a
   12-month label. If they were kept and labelled by current status, recent sign-ups are "retained" by
   construction; if rows were kept only when the outcome was known, recent cohorts contain churners
   only. *Test:* tabulate label by sign-up month; restrict to cohorts at least 12 months old.
   *Direction:* unpredictable sign, usually down, and the base rate changes.
2. **Split does not match deployment.** The model will score *future* sign-up cohorts; a random
   customer split mixes cohorts, so pricing changes, product changes and seasonality are shared between
   train and test. *Test:* train on cohorts up to month M, evaluate on later cohorts (only those with
   matured labels). *Direction:* down; report how AUC varies by cohort.
3. **Features that are not truly "first 30 days".** Lifetime totals, current plan, "last login", account
   status, support-ticket counts computed at extraction time all encode the outcome. *Test:* rebuild
   features from event logs with a hard cut-off at day 30; look for single features with implausible
   importance. *Direction:* down, sometimes dramatically.
4. **Hidden groups.** Re-subscribers, household or company accounts, shared payment methods appear as
   several customers. *Test:* group by payment method or address hash and re-split. *Direction:* down, usually modestly.
5. **Is AUC the right evidence?** What action follows, at what capacity, compared with what rule
   (for example "fewer than 3 active days in the first 30")? *Test:* precision in the top k % against
   that rule on the temporal test set. *Direction:* may reveal that 0.91 buys little over the rule.

*Scoring.* Strong: 1 and 2 both raised with a concrete test, at least one of 3-5, and directions
stated. Adequate: 2 and 3. Weak: only generic items ("check for overfitting", "try more models",
"use nested CV"). *Common incorrect emphasis:* worrying about the 5-fold tuning procedure. Tuning
inside the 80 % is fine; the problems are all in what the rows and labels *are*.

---

# Notebook 11 — Reproducible feature generation without look-ahead

✍️ Written answers: compare yours against the rubric; wording will differ.


Open after writing your own answers. Numbers in Q1 were computed, not estimated.

### Q1

(a) `delay ≈ w·θ/Δ = 40 × 0.6 / 1.2 = 20` samples.
(b) `σ/√w = 0.8/√40 = 0.126`. The threshold 0.6 is 4.74 of these: a one-sided Gaussian tail of
about 1 in a million per sample.
(c) Positive autocorrelation inflates the variance of the mean by about `(1+φ)/(1−φ) = 9`, so the
standard deviation rises by about 3 (exact value for *w* = 40: 2.83, giving 0.358). The same
threshold is now only 1.68 standard deviations away; the per-sample exceedance probability goes
from about 1e-6 to about 0.047. The delay in (a) is unchanged. A threshold set from the
white-noise formula would alert constantly.

*Common incorrect answers.*
- "Delay is w/2 = 20 because the window is half full." Right number, wrong reason: it is 20
  because θ/Δ happens to be 1/2. With θ = 0.3 the delay is 10.
- "Autocorrelation reduces noise in the mean because neighbouring samples agree." It is the
  reverse: agreeing neighbours carry less independent information, so averaging removes less.
- Answering (c) by re-deriving σ/√w with a smaller σ. The marginal σ is unchanged; the
  *effective sample size* is what shrinks (40 × 0.2/1.8 ≈ 4.4).

### Q2

The perturbation test covers one function. Future information can still enter through:

1. **Statistics fitted on future or held-out rows**: reference means, a scaler, a PCA basis or
   a threshold estimated on the whole table, including validation/test experiments or the
   later part of the same recording.
2. **Selection**: windows, feature subsets or thresholds chosen by looking at test-period
   performance.
3. **Labels and preprocessing upstream**: a tidy table whose values were interpolated across
   gaps, de-trended over the whole recording, or filtered zero-phase before the feature step.
4. **The split itself**: random row splits with overlapping windows put near-duplicates of test
   rows in training.

Any two, with the mechanism, is a solid answer. *Common incorrect answer:* "the model could
still overfit" — true and unrelated to temporal leakage.

### Q3

Two faults. (1) `s.mean()` and `s.std()` are computed over the *whole* experiment, so the
z-score at time *t* depends on everything after *t*, including the anomalous segment itself;
it cannot be computed while the experiment is running. (2) Because the anomalous segment is
about a third of each recording, it shifts the mean and inflates the standard deviation that
normalise it: the feature partly removes the very effect to be detected, and the amount removed
depends on the label. It also makes every experiment's z-scores average exactly zero, erasing
information about experiments that are abnormal throughout.

Causal alternatives: calibrate on the first *k* seconds of each experiment and hold those
statistics fixed (assumes the start is normal and representative; costs *k* seconds without
scores), or an expanding/long-EWMA baseline (assumes slow drift is not the fault; a slowly
developing fault is absorbed into the baseline). Naming the assumption is required for "Solid".

*Common incorrect answer:* "it's fine because the groupby prevents leakage between experiments".
The groupby fixes cross-group contamination only; the leak is along time, inside the group.

### Q4 (design choice)

(i) Offline training table: NaN is defensible. Partial windows have a different variance from
full ones, so early rows would be systematically noisier examples of "normal" and a model or
threshold would learn the row index. Dropping 5 % of rows is cheap; `rows_since_reset` makes
the drop explicit and lets you report how much was dropped. The cost is that the model is never
evaluated on start-up behaviour, so nothing can be claimed about it.

(ii) Online service that must answer from the first reading: NaN cannot be the final answer.
Acceptable designs: return an explicit "warming up" status instead of a score for the first
*w* seconds (honest, but the service is blind after every restart and after every gap);
or score with the shortest full window available, with thresholds scaled for that window
(always answers, more code and more thresholds to validate); or partial windows with a variance
correction `×√(n/w)`. Whatever is chosen must be what the training table did, otherwise
training and serving differ. A strong answer notes that restarts and gaps make warm-up a
recurring state, not a one-off, and that it should be monitored.

*Common incorrect answers:* "fill with 0" (after standardisation 0 means perfectly normal);
"forward/backward fill" (backward fill is look-ahead).

### Q5

Stale: someone changes `std` from ddof=1 to ddof=0, or fixes a bug in the slope, and forgets to
bump `FEATURE_VERSION`. Keys are unchanged, the old table is served, and a model is trained on
features the current code would not produce. Nothing fails.

Commit hash worse: a README edit or a change to the API module produces a new commit; every
feature table is recomputed (minutes here, hours at scale) and, more seriously, two runs that
*should* be comparable now carry different feature keys, so "same features?" can no longer be
answered by comparing keys. Uncommitted changes are also invisible to a commit hash.

For this project either can be defended. A reasonable choice: explicit version in the key,
*plus* the commit hash recorded in `meta.json` for audit, *plus* a test that pins a small
golden feature table so that a semantic change without a version bump fails CI. Hashing the
source of `features.py` is a middle path (changes on any edit to that file, including comments).

### Q6

The proposal confuses "does not move this metric" with "is computable". Pooled sample-level
average precision is dominated by the hundreds of samples deep inside each anomalous segment,
whose ranking a half-window shift does not change; only samples near the edges move. The
quantity centring corrupts is *when* the score rises relative to onset, which that table does
not measure (the synthetic example shows the shift is −w/2 samples). So the table cannot show
that causality "does not matter"; it shows the metric is insensitive to it. Independently of
any metric, a centred feature cannot be produced by the service, so a model trained on it has
no deployable counterpart. The comparison with the reference-row effect is still worth keeping:
it tells you where the larger modelling risk on this dataset is.

*Common incorrect answer:* "0.014 is within noise, so both are equivalent." No interval was
computed, and equivalence of an offline metric is not the criterion.

### Interview rep — rubric

| Aspect | Solid answer |
|---|---|
| `sliding_max` | Monotonic deque of indices; each index pushed and popped at most once, hence O(n) time, O(w) space. Heap-based O(n log n) with lazy deletion earns partial credit if the complexity is stated correctly. Recomputing `max` per window is O(n·w) and does not meet the task. |
| `StreamingStats` | Ring buffer or deque plus running sum and sum of squares; subtract the value leaving the window. O(1) per update. |
| Numerical risk | Catastrophic cancellation in `E[x²] − mean²` when the mean is large relative to the spread; drift from repeated add/subtract over long streams. Mitigations: subtract a reference offset, Welford-style windowed update, periodic recomputation from the buffer, clamp at zero. |
| Tests | Brute-force comparison on random input; decreasing input (deque stays full); ties; `w = 1`; `w > len`. For the stats: comparison with recomputation; a large-offset input. |
| Communication | States the invariant ("values at the deque's indices are decreasing") before coding. |

Reference implementation and tests: `interview_rep/sliding.py`, `interview_rep/test_sliding.py`
(7 tests pass). Connection to the unit: `StreamingStats` is the online form of the rolling mean
and standard deviation, and its state is exactly what a `StreamScorer` must hold in Week 5.

---

# Notebook 12 — Strong simple baselines and metrics that match the decision

✍️ Written answers: compare yours against the rubric; wording will differ.


### Reasoning questions

**1.** precision = πr / (πr + (1−π)f). At π = 0.30: 0.27 / (0.27 + 0.014) = **0.951**. At π = 0.001:
0.0009 / (0.0009 + 0.01998) = **0.043**, about 22 false alarms per true one. ROC AUC is unchanged:
it is built from recall and FPR, each a rate *within* one true class, so the class ratio cancels.
Average precision changes (and so does its floor, 0.30 versus 0.001) because precision mixes the two
classes in proportion to their sizes.

*Common incorrect answers.* "Precision stays 0.9-ish because the classifier is the same": confuses
recall with precision. "ROC AUC drops because the problem got harder": the ranking problem did not
change. "Average precision is unaffected because it is threshold-free": threshold-free is not
prevalence-free.

**2.** A constant score flags every row at any threshold it can reach, so recall = 1 and precision =
π. F1 = 2π / (1 + π) = 0.746 / 1.373 = **0.544**. With 37 % positives, F1 has a free floor of 0.54:
"F1 = 0.6" is barely above doing nothing, and F1 values on SKAB cannot be compared with F1 values on a
benchmark with 1 % positives (floor 0.02).

*Common incorrect answers.* "The floor of F1 is 0" (true only as π → 0). "0.544 means it found half
the anomalies" (it found all of them and half-drowned them).

**3.** 31 of the 34 experiments start their single anomalous segment between t = 550 and 600 (median
572); the dev-selected threshold is t ≥ 572. Flagging "everything after the usual onset time" catches
nearly every anomalous row (recall 0.99). Precision is 0.72 because the anomaly usually *ends*
(median t ≈ 970) while the recording continues to about t ≈ 1,140, so the late rows are false alarms.
PR-AUC is poor for the same reason: ranking by t puts those late normal rows at the very top of the
list, so precision is low exactly where average precision weights it first. A learned model can find
the clock through (a) anything that drifts monotonically during a run, such as motor or fluid
temperature warming up, cumulative or long-window features, an explicit time or position feature;
(b) sequence position itself in a recurrent or attention model, or window index. This is a protocol
regularity, not physics: a deployed detector does not get faults on a schedule.

*Common incorrect answers.* "The clock is a strong baseline we should build on" (it is a leak
detector; its success is a property of how SKAB was recorded). "PR-AUC shows it is useless, so
ignore it" (the F1 it reaches at one threshold is the highest in the table; a model tuned on F1 would
be rewarded for learning it).

**4.** Dev PR-AUC is computed on pooled dev rows and reflects ranking *within and across* dev
experiments. The frozen threshold (about 10.95) is below essentially every test row's score: test
experiments sit at a different distance from the global reference than dev experiments do, because
operating regimes differ between experiments far more than within them (the fault-free recording has
`flow_rate` near 125 L/min with standard deviation 1.6; the normal rows of labelled experiments
average about 63 with standard deviation about 42). So the scores are not on a common scale across
experiments. Lesson: a threshold transfers only if the score distribution of normal data is stable
across the units you deploy on. A ranking metric pooled over units can hide that. Check per-unit
score distributions and per-unit alarm rates, not only pooled PR-AUC.

*Common incorrect answer.* "The test set is harder." Its ranking is not notably worse per family; the
calibration of the score across experiments is what failed.

**5.** Balanced weighting makes the model behave as if positives were about half the data. Its
outputs are inflated (in the worked example the mean prediction is 0.33 at 4 % prevalence), so
"p ≥ 0.08" selects most of the population and the campaign loses money. Ranking metrics are unchanged,
so nothing warned them. Ways forward: (i) fit unweighted and use its probabilities; (ii) keep the
weighted model but recalibrate on held-out data (Platt or isotonic), or correct the prior
analytically (subtract the log of the odds inflation from the logit); (iii) abandon the probability
rule and choose a threshold on the *score* directly by maximising net value on validation data.

*Common incorrect answer.* "Lower the threshold to compensate." Without recalibration there is no
principled value to lower it to.

**6.** No. Brier score decomposes into reliability (calibration), resolution (discrimination) and
uncertainty. New features probably improved resolution; calibration may be the same or worse. Look
at a reliability table on held-out data (equal-count bins), the mean predicted versus observed rate,
and if needed the decomposition itself. Also ask whether 0.003 is distinguishable from noise at this
sample size.

### Design-choice explanation: what a strong answer contains

* **Choice:** per-experiment burn-in on a single sensor (`flow_rate` abs z) as the bar: test PR-AUC
  0.805 and F1 0.748, close to the supervised row (0.827 / 0.783) and requiring no fault labels.
  Choosing the supervised row is also defensible if the answer says it assumes future faults resemble
  labelled ones and points to family `other` (0.751) as the place that assumption is weakest.
* **Evidence used honestly:** global-reference thresholds do not transfer (Q4); burn-in max-abs-z and
  Mahalanobis are *not* better than one sensor; differences of a few hundredths between rows are not
  claimed because the test set has 9 experiments and no intervals yet.
* **Assumption:** each unit starts in a healthy state and a 100-second calibration period is
  acceptable; rows in it are unmonitored.
* **Failure scenario:** a restart while the fault is already present (the fault becomes "normal"), or
  a legitimate set-point change after burn-in (everything alarms).
* **Monitoring:** alarm rate per unit after restarts; drift of the burn-in mean relative to fleet
  history; an absolute sanity limit alongside the relative one.
* **The clock:** any model must be shown to beat the clock *and* not to be using it (w3d1).

Weak answers: pick the highest number; do not name an assumption; treat the global reference as
"the correct semi-supervised setup" because the benchmark ships it.

### Interview rep - worked answer and rubric

**(a)** With $z_i = w^\top x_i + b$ and $\sigma$ the logistic function:
$\min_{w,b} \; -\sum_i \big[y_i \log \sigma(z_i) + (1-y_i)\log(1-\sigma(z_i))\big] + \tfrac{\lambda}{2}\lVert w \rVert^2$
(intercept not penalised; scikit-learn parameterises $C = 1/\lambda$ and multiplies the data term).

**(b)** Keeping each negative with probability β = 0.1 multiplies the odds of the positive class in
the sample by 1/β = 10 at every x. For a well-specified logistic model that changes only the
intercept: $b_{\text{sample}} = b_{\text{true}} + \log(1/\beta) = b_{\text{true}} + \log 10$; the
slopes estimate the same quantities, with larger variance because data was discarded. To correct:
subtract log 10 from the intercept, equivalently
$p = \dfrac{\beta p_s}{\beta p_s + (1 - p_s)}$. Nuances worth a sentence each: with L2 the relative
weight of the penalty grows when rows are dropped, so λ should be retuned; if the model is
misspecified the slopes do shift; the ranking barely changes, so downsampling is a compute decision,
not an accuracy one. Class weights have the same effect on the intercept as resampling.

**(c)** Not accuracy: 99 % is free. ROC AUC is fine for comparing rankers and is stable if prevalence
drifts, but it will not reveal that precision is unusable at 1 %. PR-AUC (with its 0.01 floor stated)
or, better, precision/recall at the operating point the business can afford. Limits: PR numbers are
not comparable across prevalences; all three ignore calibration; and the right answer depends on the
action taken on a positive.

| | Not yet | Adequate | Strong |
|---|---|---|---|
| (a) | no regulariser or wrong sign | correct loss | notes the unpenalised intercept and C = 1/λ |
| (b) | "it helps the model learn the minority class" | intercept shifts by log 10, correct it | derivation via odds, variance cost, penalty interaction, misspecification caveat |
| (c) | recommends accuracy or ROC AUC only | PR-based metric with reason | ties the metric to the decision and states what none of them measure |

*Common incorrect answers.* "Downsampling removes bias towards the majority class": the unweighted
model is not biased; its probabilities are correct and its default 0.5 threshold is simply the wrong
operating point. "After downsampling use threshold 0.5": that is an implicit, uncontrolled choice of
operating point. "The coefficients change by a factor of 10."

Sources for (b): King and Zeng (2001), "Logistic regression in rare events data" (prior correction);
cited from memory, not re-opened in this session.

---

# Week 2 review day — Review and catch-up (light)

✍️ Written answers: compare yours against the rubric; wording will differ.


Open only after all twelve questions have a written attempt. Each answer states the mechanism a
"solid" answer must contain, then common wrong answers and why they fail.

These answers were re-aligned with the final Week 2 lessons on 2026-11-21. Project numbers are the
ones reported in those lessons from runs on the real SKAB files. Where a statement was confirmed by running
code, that is said explicitly; everything else is reasoning, not a measurement. The diagnostic
database is **synthetic**: numbers quoted from it illustrate mechanisms only.

### 1. Grain and fan-out

The **grain** is what one row represents: "one row per customer", "one row per charge attempt".
A query result has a grain too, and stating it before writing the query is the main defence against
wrong aggregates.

Joining `customers` to `invoices` (many per customer) and to `tickets` (many per customer) produces
one row per *(invoice, ticket) pair* for each customer: a customer with `m` invoices and `k` tickets
contributes `m × k` rows, so `SUM(invoices.amount)` is multiplied by `k`. Executed on the diagnostic
database: for customer `C00679`, one of two customers with the most tickets (6), the three-table join sums to 2758.62 where the
true invoice total is 459.77, exactly six times too large. Customers with no ticket vanish entirely
under an inner join, which is the opposite error in the same query.

Two structurally different fixes:
* **Aggregate each child table to the target grain first** (one CTE per child, each `GROUP BY
  customer_id`), then join the pre-aggregated results to `customers` with `LEFT JOIN` and `COALESCE`.
* **Correlated scalar subqueries** in the select list, one per measure.

(`SUM(DISTINCT amount)` is not a fix: two invoices with the same amount collapse into one.)

| Common wrong answer | Why it fails |
|---|---|
| "Add `DISTINCT`" | `DISTINCT` on rows does not undo multiplication inside `SUM`; `SUM(DISTINCT ...)` removes legitimately equal amounts |
| "Use `LEFT JOIN` instead of `JOIN`" | Fixes the vanishing customers, not the multiplication |
| "Group by more columns" | Changes the grain of the output without removing duplicated measures |
| "The data has duplicates" | The tables are fine; the join created the duplication |

### 2. `ON` versus `WHERE` in a left join

A condition on `B` in the **`ON`** clause decides *which rows of `B` may match*; rows of `A` without
a match are kept, with NULLs for `B`. The same condition in **`WHERE`** is evaluated *after* the join:
for unmatched rows the `B` column is NULL, the predicate is UNKNOWN, the row is discarded, and the
left join has silently become an inner join. Executed on the diagnostic database: `customers LEFT
JOIN tickets ON ... AND t.category = 'billing'` keeps all 900 customers; moving the category
condition to `WHERE` leaves 210.

Use `ON` for "which matches count", `WHERE` for "which left rows do I want". The anti-join idiom
(`WHERE b.key IS NULL`) is the deliberate use of the post-join filter.

| Common wrong answer | Why it fails |
|---|---|
| "They are equivalent; the optimiser treats them the same" | True for inner joins only |
| "`WHERE` is just slower" | It is a semantic difference, not a performance one |

### 3. Counting and averaging with NULLs

* `COUNT(*)`: number of rows.
* `COUNT(col)`: number of rows where `col` is not NULL.
* `COUNT(DISTINCT col)`: number of different non-NULL values.
* `AVG(col)`: sum of non-NULL values divided by the count of non-NULL values; NULLs are ignored, not
  treated as zero. (Confirmed in SQLite: for values NULL, 2, 4 the results are 3, 2, and 3.0.)

Business examples: "customers billed this month" as `COUNT(*)` over invoices counts charge attempts
(retries inflate it; in the diagnostic data January 2025 gives 670 rows for 651 distinct customers);
"average resolution time" as `AVG` over a column that is NULL for open tickets describes resolved
tickets only, which looks better exactly when the backlog is growing; `AVG(COALESCE(col, 0))` answers
a different question again.

| Common wrong answer | Why it fails |
|---|---|
| "`COUNT(col)` counts distinct values" | It counts non-NULL rows |
| "`AVG` treats NULL as 0" | It excludes them from numerator and denominator |
| "`COUNT(DISTINCT a, b)` works everywhere" | Not portable (SQLite rejects it); pre-aggregate instead |

### 4. Default window frame, ties, and `WHERE`

With `ORDER BY` and no explicit frame, the frame is `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT
ROW`. `RANGE` works on *values of the sort key*, so "current row" includes all **peers** (rows with
the same `t`): every tied row gets the total including all of its peers. Confirmed in SQLite: for
`(k, v)` = (1,10), (1,20), (2,5) ordered by `k`, the default gives 30, 30, 35, while
`ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` gives 10, 30, 35.

To make a running total independent of ties: state `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`
**and** make the ordering total with a tie-breaker (`ORDER BY t, id`); `ROWS` alone gives a
well-defined frame but an arbitrary order among peers.

Window functions are evaluated after `FROM`, `WHERE`, `GROUP BY` and `HAVING`, on the rows that
survive them; `WHERE` therefore cannot refer to a value that does not exist yet. Compute the window
in a CTE or subquery and filter outside. Corollary: a `WHERE` in the same query changes what the
window *sees* (filter-before-window), which is the January-has-no-previous-month error.

| Common wrong answer | Why it fails |
|---|---|
| "The default frame is the whole partition" | That is the default *without* `ORDER BY` |
| "The default is `ROWS ... CURRENT ROW`" | It is `RANGE`; the difference appears only with ties, which is why it survives testing on clean data |
| "Use `HAVING` to filter on the window function" | `HAVING` is also evaluated before window functions |

### 5. Gaps-and-islands; as-of joins

**Technique A (row-number difference).** Within each experiment, among rows with the same `anomaly`
value, `t - ROW_NUMBER() OVER (PARTITION BY experiment_id, anomaly ORDER BY t)` is constant along a
contiguous run and changes when a run is interrupted. Group by `(experiment_id, that difference)`,
keep `anomaly = 1`, take `MIN(t)` and `MAX(t)`.

**Technique B (change flag + running sum).** Mark a row as a segment start when `anomaly = 1` and
`LAG(anomaly)` is 0 or absent; a running `SUM` of the start flags numbers the segments; group by it.

Both were executed on a small synthetic table and returned the same segments. Technique A requires
`t` to be a gap-free row index (true for the project's `t`, not for raw timestamps with sampling
gaps); technique B does not, and extends naturally to "treat a gap longer than N seconds as a break".

An **as-of join** attaches to each row of the left table the *most recent row of the right table at
or before the left row's time* (per key). Features need it because a feature for time `t` must use
the latest information that was actually available at `t`: an equality join finds nothing when
timestamps differ, and a join on "nearest" may pick a future row.

| Common wrong answer | Why it fails |
|---|---|
| "`GROUP BY experiment_id` and take min/max of `t` where anomaly = 1" | Merges separate segments into one; correct on SKAB only because each file has a single segment, a property you would be relying on silently |
| "Self-join each row to the next row" | Finds boundaries but does not number segments; quadratic if done without an index |
| "As-of means nearest in time" | Nearest can be in the future: look-ahead |

### 6. Data validation versus model evaluation; checks for SKAB

*Data validation* asks whether the **input is what the code assumes** (well-formed, plausible,
complete), before any model exists and again on every new batch and every request. *Model evaluation*
asks whether **predictions are good** on held-out data. A model can score well on corrupted data and
badly on valid data; neither substitutes for the other. Validation failures are data or pipeline
incidents; evaluation shortfalls are modelling results.

Three categories with examples (canonical names from `docs/maintainers/flowguard-spec.md`):
* **Schema / structure:** exactly the eight sensor columns plus `datetime`, `anomaly`, `changepoint`;
  numeric dtypes; `anomaly` in {0, 1}; no missing values; `experiment_id` and `family` well-formed.
* **Value plausibility:** physical ranges and units (voltage near mains level, non-negative
  vibration RMS and flow rate, temperatures in a plausible band); no constant or all-zero channel.
* **Temporal and structural integrity:** timestamps strictly increasing within an experiment, no
  duplicated timestamps, expected median sampling interval of 1 s, gaps reported; exactly one
  contiguous anomalous segment per labelled file; 34 labelled experiments plus the anomaly-free file.

"Fail loudly": the command exits non-zero with a message naming the check, the file and the offending
values, and writes a machine-readable report (`quality_report.json`); it never drops or repairs rows
silently. Per the spec, the check functions themselves *report* (`CheckResult(name, passed, detail,
severity)`) and the command decides: **error**-severity failures stop ingestion, **warning**-severity
findings are recorded and ingestion continues. The reference ingest on the real 35 files reports
11 checks, 0 errors and 1 warning (the sampling gaps).

**The gaps.** Ingestion should *detect, measure and record* them (per experiment: count, positions,
durations) and carry enough information forward (the timestamps, or a gap flag) for later steps to
decide. It should **not** interpolate across them, silently re-index as if sampling were uniform, or
discard the affected experiments: each of those is a modelling decision with consequences for rolling
windows (a 60-row window spanning a 247 s gap is not 60 s of history) and belongs in the feature
step, visibly. A gap is a *warning-level* finding here, not an error: the data is valid as recorded,
merely irregular (nine gaps longer than 5 s, in six experiments; about 5 % of all steps are 2 s). A
warning is a debt assigned to a later step, not something to ignore: detection delay must be measured
in seconds, not rows.

| Common wrong answer | Why it fails |
|---|---|
| "Validation is checking the model on validation data" | Confuses the two meanings of "validation" |
| "Fix the gaps by forward-filling during ingestion" | Invents data in the layer that is supposed to preserve the source |
| "Wrap ingestion in try/except and skip bad files" | Silent partial data; downstream numbers change without anyone knowing why |
| "Range checks from this dataset's min/max" | Circular: derived from the data they are meant to check, they pass by construction and encode outliers |

### 7. Provenance of an ingestion step

Record: the **source** (URL and the pinned upstream commit), the **licence** and citation, a
**SHA-256 per raw file** (the manifest written by `project/get_skab.py`), the **code version** that
ran (git commit) and its parameters, **row and experiment counts** in and out, the **hash of the
output** (`skab.csv`), the quality report, and the time of the run. With that, a second person can
establish identity of inputs, code and outputs, and a difference can be attributed.

The raw data is downloaded rather than committed because (a) its licence is GPL-3.0 and
redistribution inside this repository is a decision the course avoids, (b) Git is poor at large
binary or bulk data and history is permanent, and (c) identity is given by hashes and a pinned
source, which is stronger than "the copy that happened to be committed".

| Common wrong answer | Why it fails |
|---|---|
| "The download date is enough" | Upstream can change; only a pinned revision and hashes identify content |
| "Commit the CSV so everyone has the same file" | See (a)-(c); also invites silent local edits |
| "Record the path on my machine" | A path identifies a location, not content |

### 8. Units, splits and the manifest

*Unit of prediction:* one **timestamp** (a per-sample anomaly score computed from data up to that
time), later turned into alerts/events. *Unit of independence:* the **experiment** (`experiment_id`):
samples within an experiment are strongly autocorrelated and share its conditions, as samples within
a patient do. Splitting by row would put near-duplicates of each test sample in the training set and
estimate interpolation within a recording, not generalisation to a new one. `w2d4` measured it on the
development experiments: a random forest on raw sensor values scores ROC AUC 0.986 with rows shuffled
into folds and 0.849 with whole experiments held out (PR AUC 0.980 versus 0.841).

The manifest (`splits/v1.json`) contains: `version`, `seed`, `unit` (`experiment_id`), the list of
**test** experiments, the **development folds** (lists of experiment ids), the `reference_normal`
recording (`anomaly-free/anomaly-free`), and `protocol_b` (hold out the whole `other` family to
measure generalisation to unseen fault mechanisms). `validate_splits` rejects overlap between test
and folds and unknown ids. The frozen reference `v1` has 9 test experiments (4 `valve1`, 1 `valve2`,
4 `other`) and 25 development experiments in four folds (7/6/6/6).

`v1` has a known defect found after it was frozen: five pairs of files share identical rows
(1,290 rows; 235 with contradictory labels), and `v1` does not keep those experiments on the same
side. The correct response is the one the versioning exists for: do not edit `v1`; issue `v2` with
overlap groups kept together (`w3d1`) and treat earlier numbers as not comparable.

It is a versioned file rather than a seed because the split is part of the **experimental protocol**:
it must be identical across models, machines, library versions and months; it must be reviewable
(you can read which experiments are in the test set); and a change must be an explicit event (`v2`)
that invalidates comparison with earlier results. A seed gives none of that: library updates can
change what a seed produces, and every script can use its own.

| Common wrong answer | Why it fails |
|---|---|
| "The unit of prediction is the experiment" | The model scores timestamps; experiments are what must not be shared across splits |
| "Random row split with stratification handles it" | Stratification balances labels; it does nothing about dependence within an experiment |
| "`random_state=0` everywhere is a fixed split" | Until the data order, the library version or one script's seed differs; and nobody can inspect it |
| "Regenerate the split when results look odd" | That is selecting the test set on the outcome |

### 9. Point versus event labels; 35 % and 34

A **point-level** label says whether each *sample* lies inside an anomalous period (`anomaly`
column); metrics count samples. An **event-level** label treats each contiguous anomalous period as
*one* event; metrics ask whether and how quickly each event was detected, and how many false alerts
were raised per unit of normal operating time. A detector can be excellent on one and poor on the
other: long events dominate point metrics; one early hit per event satisfies event recall.

* **About 35 % anomalous samples:** the positive class is not rare at the sample level. "Always
  normal" has accuracy about 0.65 and "always anomalous" has precision about 0.35 with recall 1, so
  accuracy is uninformative and every point metric must be reported next to these trivial baselines
  (an uninformative scorer has average precision about 0.35 here). It also means sample-level
  prevalence is unlike most production monitoring, where anomalies are rare: results do not transfer
  to that regime without re-weighting or event-level reporting.
* **34 events:** event-level quantities are estimated from 34 units (fewer in any test split). The
  resolution of event recall on a test set of, say, 9 experiments is 1/9, and intervals are wide;
  differences between models of one or two events are not evidence. Results need intervals computed
  by resampling experiments (Week 3), and claims must be sized accordingly.

| Common wrong answer | Why it fails |
|---|---|
| "37,401 samples is plenty of data for tight intervals" | The independent units are 34 experiments, not 37,401 rows |
| "35 % positives means the problem is balanced, use accuracy" | Accuracy still hides the trade-off the stakeholder cares about and is dominated by segment length |
| "Point and event metrics are the same thing at different resolution" | They answer different questions and can rank models differently |

### 10. Causal features and look-ahead

A feature value for time `t` is **causal** if it is a function only of data with time `<= t` (or
strictly `< t`, if the current sample is not available when the prediction is made) within the same
experiment. That is the condition for the feature to be computable online, in the same way, at
serving time.

* Violates causality: `rolling(w, center=True)`, `shift(-k)`, `bfill()`, interpolation across a gap
  using the next value, a global or per-experiment z-score (`(x - x.mean()) / x.std()` over the whole
  recording), or a rolling window not grouped by experiment (history from the previous recording).
  Executed: with `center=True` and window 3, changing only later values changed the feature at
  position 5 from 5.0 to 36.3; with a trailing window it stayed 4.0.
* Leaks across the split without violating causality: fitting normalisation statistics
  (`ReferenceStats`), a scaler, PCA or feature selection on **all** experiments, including test ones.
  Each value still uses only its own past, but the transformation was estimated with test data. Fit on
  training experiments (or the anomaly-free reference) only.

**What mattered on SKAB (`w2d5`).** Centring the window raised pooled average precision by only
0.002-0.014; the choice of reference rows moved it from about 0.50 to about 0.73. Two lessons, and
they point in different directions. First, a small effect on one offline number does not make
look-ahead acceptable: the centred feature cannot be computed at serving time at all, so the reason
to forbid it is construction, not the size of the gain (the same argument as the scaler leak in
`w1d3`). Second, the largest lever was a quiet modelling decision (what "normal" is measured
against), which deserves the scrutiny usually spent on model choice.

**Implementation-independent test (prefix invariance):** compute features on a full series; then
alter or delete everything after time `t` (or truncate to the first `t+1` rows) and recompute; the
features for all times `<= t` must be **exactly equal**. Use several `t` and random data. Compare
exactly, not approximately: a tolerance could hide a small dependence on the future. Add the
companion test that altering experiment B leaves experiment A's features unchanged.

| Common wrong answer | Why it fails |
|---|---|
| "Read the code and check there is no `shift(-1)`" | Does not scale and misses indirect look-ahead (centred windows, global normalisation, interpolation) |
| "Check the output shape and for NaNs" | Unrelated to causality |
| "Causal features cannot leak" | Causality is within a series; train/test leakage is across series. They are separate conditions |
| "Compare to a slow reference implementation" | Useful differential test, but a reference with the same look-ahead passes |

### 11. Baselines, chance levels, thresholds

A trivial baseline (constant prediction, prior-only, a one-line rule such as a z-score threshold on
one sensor) answers "what does *no modelling* achieve under exactly this protocol?" It calibrates
the metric (what is a bad number here?), catches pipeline bugs (a model below the trivial baseline
signals an error; a trivial baseline scoring very high signals leakage or a degenerate metric), and
gives the denominator for any claim of improvement. Without it a number such as 0.72 has no meaning.

For an uninformative (random) scorer at prevalence `p`: expected **ROC AUC = 0.5**, independent of
`p`; expected **average precision ≈ p**, since precision is about `p` at every recall. (Simulated
with 200,000 samples at `p = 0.35`: AP 0.348, ROC AUC 0.498.) Consequences: an AP of 0.40 is barely
above chance at `p = 0.35` and enormous at `p = 0.01`; AP values are not comparable across
prevalences; ROC AUC can look comfortable under heavy imbalance while precision at any usable recall
is poor, because the false-positive *rate* divides by the very large number of negatives.

A **threshold** is a fitted parameter. It is chosen on training or validation data (within the
development folds), frozen, and then applied once to the test set. Choosing it on the test set
selects the best of many candidates using test labels, so the reported operating point is optimistic
and unavailable in deployment, where test labels do not exist. Threshold-free metrics (AP, ROC AUC)
do not excuse this: the shipped system makes decisions at one threshold.

**The clock baseline (`w2d6`).** On the 9 test experiments: constant score PR AUC 0.373 (the test
prevalence), burn-in z-score on flow rate 0.805, supervised logistic regression 0.827; and a scorer
that uses only elapsed time `t` reaches test F1 0.835, above every sensor baseline. The reason is the
experimental protocol: in 31 of 34 files the anomaly starts at row 550-600. So (a) the dataset lets a
model score well by learning *when in the recording it is*, which is worthless on a real plant;
(b) `t`, `datetime` and anything monotone in them are forbidden as features, and features that
accumulate over the recording (cumulative sums, expanding statistics, slow drifts) must be suspected
of encoding the clock; (c) the clock scorer stays in every results table as a *leakage probe*: a
model that does not clearly beat it has not shown that it detects faults.

| Common wrong answer | Why it fails |
|---|---|
| "PR AUC of a random model is 0.5" | That is ROC AUC; for PR it is the prevalence |
| "Baseline = logistic regression" | Useful as a *simple model* baseline, but the trivial baseline comes first and is what calibrates the metric |
| "Report best-F1 on the test set" | The maximisation over thresholds used test labels |
| "A high ROC AUC means the alerts will be precise" | Not under imbalance; look at precision at the recall you need |

### 12. The `band_power` test (delayed question from w1d5)

The two independent problems: (1) the **oracle is the code's own earlier output**, so the test can
only detect *change*, not error: if the notebook run had the factor-of-two bug, the test enforces
it; (2) **`rel=0.2` is not derived from anything**: it is far above numerical noise and has no
stated relation to the defects of interest (a factor of two happens to exceed it; a 15 %
normalisation error does not).

Redesign: input is a **pure tone at a bin frequency inside 8-12 Hz** with amplitude `A` (choose `fs`
and `N` so that, for example, 10 Hz is exactly a bin); the expected power is **`A²/2` from theory**;
tolerance about `rel=1e-9`; add **Parseval** on noise (total band power over `[0, fs/2]` equals the
variance) to pin the normalisation, and a tone at exactly 12 Hz to pin the half-open upper edge.

(This key is the one at the end of `solutions/labs/w1d5_testing_ml_code/assessment_answers.md`.)

| Common wrong answer | Why it fails |
|---|---|
| "Tighten the tolerance to 1e-6" and keep the copied value | Fixes problem 2, not problem 1: still a change detector |
| "Compare with `scipy.signal.welch`" | A different estimator with different scaling conventions; agreement needs its own derivation, and disagreement does not say who is wrong |
| "Use random noise and check the result is positive" | Detects almost nothing |

---

# Notebook 13 — Leakage: a taxonomy and prevention by construction

✍️ Written answers: compare yours against the rubric; wording will differ.


### 1. `hours_since_last_maintenance`

It is a temporal-aggregate leak if "last maintenance" is looked up in today's log for historical rows:
for a row at time *t* it may pick a maintenance event that happened *after t* (often *because* of the
fault being predicted, so it is target-correlated). It is legitimate if it is computed as of the row's
timestamp, using only maintenance events dated before *t* and recorded (entered into the log) before *t*.
Check: recompute it point-in-time for a sample of rows and compare; any difference is leakage. The
second condition (recorded before *t*) matters because logs are often back-filled.

*Common incorrect answers.* "It is a normal feature, maintenance is in the past" (ignores how the export
was computed). "Drop it" (it is probably one of the most useful legitimate features once computed
correctly).

### 2. Scaling versus selection

Scaling estimates a mean and a standard deviation per column. Including test rows shifts those slightly;
the label is not involved, and for a scale-equivariant downstream model the effect is only through the
slightly different transform, so it is numerically tiny when *n* is moderate. Selection uses the
**labels**: it picks the columns whose correlation with the label is largest in a sample that includes
the validation rows, so the chosen columns are correlated with the validation labels by construction.
That is why it grows with *p*/*n*. The rule is applied to both because (i) you cannot know in advance
which regime you are in (small *n*, heavy-tailed columns, target encoding sit in between), (ii) a served
model never has the test period's statistics, so fitting on them makes training and serving inconsistent,
and (iii) the correct version costs nothing with a `Pipeline`.

*Common incorrect answer.* "Scaling leakage does not matter." The worked example shows it did not matter
*here*; that is a measurement on one dataset, not a rule.

### 3. "Removing the leak improved the model by 0.07"

* The test set changed: v1 has 9 test experiments, v2 has 7 (`other/11` and `other/12` moved to
  development). PR-AUC over a different set of experiments is a different quantity; with seven to nine
  experiments, swapping two can move it by this much on its own.
* On the 7 experiments that are test under both manifests, training with v1 or v2 gives 0.899 versus
  0.900: no measurable difference attributable to the leak for this model.
* Also: the duplicate leak, if anything, should *inflate* v1 (test rows seen in training). That v1 is
  lower is explained by the 178 contradictory labels on shared rows and by composition, which shows the
  difference is not a leak effect.
* And: "improved the model" is wrong in kind. The model was not changed; the estimate was.

### 4. Clock probe near prevalence

No. It shows that *elapsed time alone* does not predict the label at point level. Protocol leaks can be
carried by other variables: position relative to a recording event (start of a test step), time of day,
operator, batch or session id, file order. Check: single-feature probes on all metadata; per-group onset
distributions; whether labels cluster by acquisition session; `time_monotone_columns` on engineered
features (a cumulative feature can be a clock even if `t` is excluded); and ask how the labels were
produced.

### 5. Components, not pairs

A shares rows with B, B shares rows with C, A and C share nothing. With pairs, a splitter that keeps each
listed pair together may put {A, B} in fold 1 and then treat {B, C} as "B is already placed, C can go
anywhere", or process pairs independently and end with A in test, B in development and C in test. B
carries information about both. Only the component {A, B, C} as one unit guarantees no shared rows across
sides. SKAB has this case: `other/2`-`other/3`-`other/4`.

### 6. Deleting duplicated rows instead of grouping

*Advantage:* keeps more experiments available for the test set (more independent units for the estimate).

*Problems:* (i) The rows are not just duplicates, 235 have **contradictory labels**; deleting one copy
picks a label arbitrarily and hides a labelling problem that should be reported to the data owner.
(ii) A copied segment is evidence that the two files are not independent recordings (shared
acquisition, the same run exported twice, or concatenation); experiments that share 37 % of their rows
likely share more than the exact copies (operating point, adjacent unexported samples), so deleting
exact matches does not make them independent. (iii) It changes the experiments' time series (gaps),
which interacts with rolling features.

### 7. Design choice (model answer)

The test set exists to give one estimate that no decision has touched. Every development experiment has
been seen while choosing features, baselines, thresholds and (from w3d3) hyperparameters; its test
result would be optimistic by an amount we cannot measure, because the selection happened informally
across several sessions. Moving it into test would trade an unknown bias for a smaller variance, and the
bias does not shrink with more data. Cost on the real data: the test set falls from 9 to 7 experiments
(4 `valve1`, 1 `valve2`, 2 `other`), so `other` is represented by two experiments and every interval in
w3d5 will be wider. Report: the manifest version, the reason for the change, the new composition, and a
sentence that conclusions about the `other` family rest on two experiments.

### Interview rep rubric (self-score, 0-2 each, 10+ is strong)

| Point | 2 | 1 | 0 |
|---|---|---|---|
| Prediction moment | States "at ticket creation" and judges every feature against it | Mentions timing for some features | Not mentioned |
| Target leakage | Names number of agent replies and satisfaction score as post-creation (satisfaction is usually collected after resolution: near-proxy of the outcome) | Names one | None |
| Assigned team | Asks whether assignment happens at creation or after triage, possibly after escalation | Treats it as fine or as leaky without asking | Not mentioned |
| Grouping | Customers with many tickets; split by customer or check performance on new customers | Mentions grouping vaguely | Not mentioned |
| Time | Train on earlier months, test on later; text and products drift | Mentions time | Not mentioned |
| First action and expected number | Single-feature probes, refit with creation-time features and a time split; expects a large drop, e.g. "0.94 is not credible for routing at creation; I would expect something like 0.7-0.8 and would not be surprised by less" | Proposes a fix without measuring | Accepts 0.94 |

*Common weak answers.* Arguing about the model class (BERT versus logistic regression) before the
features; proposing cross-validation "to be more robust" (does not address any of the leaks).

---

# Notebook 14 — Group-aware and temporal validation

✍️ Written answers: compare yours against the rubric; wording will differ.


### 1. New machines next quarter

Grouped by machine **and** later in time: train on machines A and on data up to a cut-off; validate on
other machines after the cut-off (the "new units, later" combination of section 2.6). If only one
condition can be met, grouping matters most when machine identity is learnable; time matters most
when there is drift. Stress test: leave-one-category-out on whatever defines regimes (machine model,
site, firmware). A large drop means the model's performance depends on the regime and the rollout plan
must say which regimes it covers.

*Common incorrect answers.* "TimeSeriesSplit" alone (validation machines are in training). "Grouped
K-fold" alone, when the data span long periods with drift.

### 2. Buffer

$w - 1 + h = 60 - 1 + 15 = 74$ rows each side. It guarantees no raw sample is shared between a training
row and a validation row. It does not protect against: autocorrelation of the raw signal beyond 74 rows,
slow drift, machine identity (validation machine is in training under within-machine blocking), and
protocol effects (e.g. faults always injected at the same time).

*Common incorrect answers.* 60 (forgets the label horizon), 75 (off by one: adjacent rows need $w-1$),
"purge only before" (the embargo is needed in blocked K-fold because later training rows' windows reach
back into the block).

### 3. 0.985 versus 0.818

The gap is mostly **group leakage**, not overfitting in the usual sense: under row splits, validation
rows' experiment-mates are in training, and raw sensor levels identify the experiment. The forest is
not failing to generalise to new rows of a known experiment (it does that very well); it is
generalising to new experiments that is hard. Distinguish: (a) regularise strongly (min_samples_leaf,
max_depth) and rerun both schemes; if it were classic overfitting, scheme 4 would rise substantially; if
it is experiment memorisation, scheme 1 falls toward scheme 4 and scheme 4 barely moves. (b) A
fingerprint probe: train a classifier to predict `experiment_id` from the features; near-perfect
accuracy confirms that rows identify their experiment.

### 4. Design effect

$\mathrm{deff} = 1 + (m-1)\rho_e = 1 + 999 \times 0.1 \approx 101$. The naive standard error
$\sqrt{0.9 \cdot 0.1 / 25{,}000} \approx 0.0019$ (half-width ±0.004) becomes about $0.0019 \times \sqrt{101}
\approx 0.019$, half-width about ±0.04: ten times wider. Effective sample size about 250 rows, i.e. on the
order of the number of experiments.

### 5. `TimeSeriesSplit(gap=0)`

It orders folds so validation follows training, but the last training rows' labels (and the first
validation rows' feature windows) overlap the boundary. `gap` drops that many rows between training and
validation; it corresponds to the **purge** $w - 1 + h$. There is nothing after the validation block in
forward chaining, so no embargo is needed. It also knows nothing about groups.

### 6. "Young" stores

Validation must estimate the error on stores the model *has not seen*. A store opened 20 weeks before
the cut-off has 16 weeks of training rows; a model that memorises stores through `fp_*` predicts it well.
Counting it as new pulls the "new store" error toward the known-store error and hides the cost of a
genuinely unseen store. The business definition is useful for *reporting* (how many deployment stores
will be unseen) but not for building the validation sets. Mutant `young_stores_as_new` is this mistake.

### 7. Reply to the manager (model answer)

"The six schemes do not give more or less cautious versions of one number; each answers a different
question. Scheme 6 asks whether a model trained on earlier recording days works on later ones, but in
this dataset the day determines the fault family, there are only two folds, and the first validates on
three copies of one recording, so its 0.49 tells us almost nothing. The question the product depends on
is whether the detector works on runs it has not seen, and the best estimate of that is 0.82 ROC-AUC
(range over folds 0.63-0.94), with intervals to follow in w3d5. The real risk the review should hear
about is a fault family the detector has never seen: holding out the `other` family, performance falls to
about 0.53-0.65. I recommend we state that the detector is validated for the known families only and
treat new families as out of scope until we have data."

### Interview rep rubric (0-2 each; 9+ is strong)

| Point | 2 | 1 | 0 |
|---|---|---|---|
| Deployment sentence | "24-hour forecast for buildings never seen, starting next month" | mentions new buildings or future, not both | none |
| Withhold both | validation buildings absent from training **and** validation period after training | one of the two | random 5-fold accepted |
| Gap | 24 h horizon + longest lag feature (e.g. 168 h) → gap at least the horizon, plus care for lag windows | mentions a gap without size | none |
| Seasonality | folds span seasons, or the evaluation period matches the rollout season; warns that one month of validation misses winter peaks | mentions seasons | none |
| Reporting | separate errors for known vs new buildings, per horizon hour, with uncertainty across buildings | one pooled number with an interval | one pooled MAPE |

*Typical weak answer.* "Use TimeSeriesSplit" (misses the 2,000 new buildings and the horizon gap) or
"MAPE 3 % is great" (MAPE also misbehaves for near-zero demand, a bonus point if raised).

---

# Notebook 15 — Hyperparameter and threshold selection without fooling yourself

✍️ Written answers: compare yours against the rubric; wording will differ.


### Reasoning questions

**1.** Upward. 0.891 is the maximum of 24 noisy estimates; the configuration was chosen partly because its
fold scores were favourable. The bias grows with the noise of each estimate (σ, about the SE ≈ 0.015-0.03
here), with the number of candidates K (≈ σ·E[max of K], roughly σ√(2 ln K) for many near-equal
candidates), and shrinks with the correlation between candidates' errors (√(1−ρ); shared folds make it
smaller) and with real spread in true quality. In the lab's real run the best trial's dev score was 0.891;
the nested estimate of the procedure was 0.850 ± 0.032.
*Common wrong answer:* "it is unbiased because CV is unbiased" - CV is (nearly) unbiased for a *fixed*
configuration, not for one selected by the same CV.

**2.** The outer loop does not wrap the selection: every fold used to report the score also voted for the
configuration. The procedure estimates the CV score of the configuration selected on these same folds,
i.e. the optimistic number of question 1 again (with a fresh fold-assignment noise added if the folds
differ). The mutant `outer_fold_in_inner_search` implements exactly this and is rejected by the poisoned-
fold test.

**3.** Not a bug. Each outer fold runs the search on different inner data; the choice changes because the
candidates are not separable with 18-19 development experiments: their differences are within the noise.
The report should give the nested estimate of the *procedure* and say the choice was unstable; quoting the
dev score of the finally selected configuration would hide that.

**4.** With 32 trials a grid over 5 dimensions gives 2 values per dimension (2^5 = 32), so an important
dimension is explored at two points; random search gives 32 distinct values in every dimension, which
matters because typically only one or two dimensions drive performance. Log scale: regularisation
strength C or alpha, learning rate, minimum samples per leaf (often), tolerance; linear scale: fractions
such as subsample in [0.5, 1].

**5.** In-sample scores are separated more cleanly than scores on new experiments (the model has fitted
those rows), so the best-F1 threshold is miscalibrated for new data, typically too extreme. The lab scores
every development row by a model trained without that row's fold (`out_of_fold_scores`), chooses the
threshold on those, freezes it, and applies it once to test.

**6.** That the test set was used twice and the reported score was obtained after a change prompted by
the first test result; it is therefore optimistic (a selection between "before" and "after" on test) and
is no longer an unbiased estimate. Fixing a genuine bug is right; the honest options are to report both
numbers with that statement, or to re-evaluate on data not yet used. Silently replacing the number is
the failure.

### Design-choice explanation - what a strong answer contains

* In the real run the top trials' SEs (~0.015) are as large as the gap between the top means (0.891 vs 0.878),
  so their ordering is noise; the one-SE rule picked trial 12 (50 boosting iterations) over trial 17 (200).
* Complexity ordering justified operationally: linear before boosted (latency, interpretability, simpler
  artifact), shorter windows before longer (less warm-up and shorter delay online, w5d3), stronger
  regularisation and fewer/shallower trees first (variance, inference cost).
* What it does not fix: the chosen candidate's dev mean is still optimistic; the reported number comes
  from the nested estimate. It also does not protect against the test set being looked at more than once.
* A strong answer notes that with four folds the SE itself is noisy.

### Interview rubric (ML fundamentals)

| Level | Description |
|---|---|
| Strong | L2: penalty is rotation-invariant and strictly convex, so for correlated features the minimiser spreads weight across them (identical features get equal weights); L1: the diamond's corners lie on axes, so the solution tends to land where one coefficient is zero; mentions the elastic net as a compromise. Bias rises and variance falls with regularisation; choose by grouped CV with the one-SE rule, noting the SE with few groups. |
| Adequate | Correct qualitative answers without the geometric or optimality argument. |
| Not yet | Claims L2 zeros coefficients, or chooses the strength on the test set. |

### Challenge: reference reading

See `challenge/REPORT.md` in this directory for numbers (trial 54, pre-look estimate 0.736, one look
0.7083, the optimism table). Rubric for the written parts:

| Element | Demonstrated when |
|---|---|
| Rule | Stated before looking; justified by the noise level of the table (SE vs spread of top means), not by the test score. |
| Estimate | Not the chosen trial's dev mean; computed by re-applying the whole rule without each fold (or an equivalent bias correction) and justified. |
| The look | Exactly one; the gap to the estimate is put in numbers and compared with plausible noise; no switch after looking. |
| Simulation | An expectation is written before running; the table varies K and ρ (or σ); the result is compared with the expectation. |
| Limits | At least two: one table proves nothing about a procedure; the generator's assumptions (exchangeable trials, noisier complex models) need not hold for real searches. |

---

# Notebook 16 — Point-level versus event-level evaluation for detection

✍️ Written answers: compare yours against the rubric; wording will differ.


### Reasoning questions

**1.** (a) Metric: point F1 counts rows; it ranks by the share of anomalous rows covered and is blind
to fragmentation and timing. The operator-relevant columns are events found (B 7/7 vs A 6/7), delay
and false alarms per hour, and they do not agree with the F1 ordering. (b) Data: seven events; one
event is 14 percentage points of event recall, and 239 vs 262 false alarms per hour come from 1.22
hours (290 vs 319 alarms). Neither difference is established without intervals (w3d5). Also both rates are
operationally unusable, so the comparison is moot until post-processing is tuned.
*Common wrong answers:* "F1 balances precision and recall so it is fine" (it balances row counts);
"6/7 vs 7/7 is a big difference" (it is one event).

**2.** The start-based count (3/7). The clock's alarm for an experiment is a single run that starts at
the frozen threshold (row 570) and lasts to the end. When the onset is a few rows after 570 (four of
the seven test experiments, onsets at rows 571-577), the alarm
starts in normal operation and runs into the event: any-overlap credits it with a detection at delay 0;
the start-based rule calls it a false alarm, because it told the operator nothing at onset. Both
numbers are inflated by the protocol leak (test onsets lie between rows 557 and 577); neither is evidence about
sensors.
*Common wrong answer:* "any-overlap is more lenient so it is fairer to the detector" - fairness to the
detector is not the goal; matching what the alarm communicated is.

**3.** The point-adjusted F1 of a random (or trivially periodic) flag stream with the same flag rate,
on the same data. On SKAB a random detector flagging 1 % of rows scores 0.984 after point-adjust. If
0.96 is not clearly above that reference, it means nothing. (Equivalent acceptable answers: the
non-adjusted F1, or the event-level false-alarm rate.)

**4.** They change which alarms exist and when they are raised; tuning them on test is selecting on
test (w3d3). The confirmation wait is real latency: an alarm requiring 10 rows is raised 9 rows after
its first flag. Omitting it understates delay by exactly that amount and makes long confirmation
windows look free.

**5.** Rate ≤ -ln(0.05)/1.22 ≈ 3.0/1.22 ≈ 2.46 per hour (one-sided 95 %, Poisson). To claim ≤ 0.125 per
hour with zero false alarms: 3.0/0.125 ≈ 24 hours of normal operation. Assumes a constant rate; with
regime changes (the fault-free recording behaves differently) even that is optimistic.
*Common wrong answer:* "0 false alarms per hour, so the budget is met".

**6.** With seven delays, two of them infinite, the median is the 4th smallest value, which is a finite
delay larger than the reported 40 s (the median of the five detected ones is their 3rd value; over all
seven it is the 4th). Report the all-events median, with missed events counted as
infinite, because dropping misses rewards a detector for failing on the hardest cases. If more than
half are missed, the median is "missed".

### Design-choice explanation - what a strong answer contains

* Detection: alarm *starts* within a window around the ticket time, with an early tolerance of about
  30 minutes (the documented lag) and a late grace limited by the operational requirement; start-based
  because an alarm that began in normal operation conveys nothing about the surge.
* Repeated alarms within one event are redundant (not TP, not FA); report them separately as operator
  load.
* False alarms: starts outside every window; exposure is time outside all windows, from timestamps.
* Delay resolution is limited by label jitter (5-30 min): report delay as "within the window" or with
  that resolution, not to the second.
* Cannot measure: true onset delay below ~25 min; event ends (tickets have no end time), so alarm
  clearing behaviour is unmeasured.
* A good answer also says how the tolerance would be validated (a sample of events with sensor-based
  onset annotation).

### Interview rubric

| Level | Description |
|---|---|
| Strong | Sorts once, merges in one pass with `start <= last_end`, ignores empty intervals, two-pointer overlap after merging; O(n log n); writes tests for touching, nested, empty and disjoint inputs; explains point recall = overlap(alarms, events) / total event length. |
| Adequate | Correct merge; overlap by nested loops O(nm) with correct result; some edge cases untested. |
| Not yet | Materialises arrays of all integers (fails for large coordinates) or mishandles touching/nested intervals. |

Reference: `interview_rep/intervals.py`, tests `interview_rep/test_intervals.py` (5 pass).

### Lab and challenge: what the reference readings contain

See `lab/EVENT_EVAL.md`, `challenge/REPORT.md` and `challenge/OUTAGE_RULE.md` in this directory. Rubric
for the challenge's written parts:

| Element | Demonstrated when |
|---|---|
| Budget claim (A) | States counts and hours, the 95 % upper bound, and does not claim the budget is met from a zero count over ~1.2 h. |
| Fault-free recording (A) | Notices that the same setting raises false alarms on a different regime and says the rate is not one number. |
| Domain analysis (B) | Names label lag/jitter, event length vs detector latency, and event spacing as the reasons the SKAB rule fails. |
| Parameter justification (B) | Each parameter tied to a domain property (lag, latency requirement, spacing), none chosen by score. |
| Limits (B) | States delay resolution equal to the jitter and one way to game the rule (random alarms in wide windows, held alarms) with a check. |

---

# Notebook 17 — Uncertainty: cluster bootstrap, paired comparisons, small-n honesty

✍️ Written answers: compare yours against the rubric; wording will differ.


Open after writing your own answers. Numbers quoted here were computed in the authoring session
(Wilson limits with the formula of README section 2.4; the 1 − 0.95^k figure by arithmetic; the
interview-rep demo by running `interview_rep/paired_precision.py`).

### Q1. "F1 = 0.812 ± 0.006" from a row bootstrap of 12,000 rows from 10 experiments

**Model answer.** The resampling unit is wrong. Rows of one experiment are correlated, so a row
bootstrap produces replicate test sets that are far more alike than two real test sets of ten new
experiments would be. The interval is too narrow, typically by a factor of several (3 to 7 on SKAB
in the lab), and the "±" also hides that the interval need not be symmetric. Smallest change: resample
the 10 experiments (or overlap groups) with replacement, keep the threshold frozen, recompute F1 on the
concatenated rows, and report the percentile interval with "10 clusters" beside it. Add that with 10
clusters even that interval undercovers somewhat.

**Common incorrect answers.**
* "Use more bootstrap replicates." The Monte Carlo error is not the problem; the unit is.
* "Use a t-interval instead." Still treats 12,000 rows as independent.
* "The interval is too wide because F1 is unstable." Wrong direction.

### Q2. Cluster-bootstrap recall interval [0.71, 0.93] on 7 clusters

**Model answer.** (1) With few clusters the bootstrap variance is biased low by roughly (G − 1)/G
and the percentile interval undercovers: in the worked example a nominal 95 % interval covered about
87-88 % of the time with 7 or 9 clusters. (2) The interval conditions on the fitted model and the
frozen threshold; training-set sampling, seed noise and the selection of this model (and threshold)
are not in it, so the uncertainty about the method is larger. A third acceptable reason: the
resampling distribution has only 1,716 distinct resamples and cannot exceed the most extreme
cluster. **Why any width can mislead:** an interval describes sampling variation only. Leakage, a
label that the clock predicts, overlap between "independent" clusters, or a test bench that differs
from deployment all bias the point estimate, and no interval widens for bias.

**Common incorrect answers.** "Use BCa and it will be fine" (BCa is second-order accurate but cannot
create information that 7 clusters do not contain); "the interval is fine because recall is a mean"
(it is a ratio of sums over clusters, and the cluster count still governs).

### Q3. Overlapping intervals, same 30 experiments

**Model answer.** Overlap of two marginal intervals is not the test for a paired design. Each
marginal interval contains the between-experiment variance that both models share (hard experiments
are hard for both). The difference cancels that shared part: Var(d̄) = (σ_a² + σ_b² − 2rσ_aσ_b)/G.
If the correlation across experiments is high, the paired interval for the difference can exclude
zero while the marginal intervals overlap almost entirely (worked example: overlapping intervals,
paired interval [+0.0155, +0.0191]). The number that settles it is the **paired interval of the
difference** (or equivalently the per-experiment differences: their mean and spread, or the number of
experiments on which A wins).

**Common incorrect answers.** "Overlap means no difference" (too conservative under pairing). "No
overlap is required for a claim" (same mistake). "Compute a two-sample t-test on the 30 + 30 scores"
(ignores the pairing).

### Q4. Eight of eight events detected

**Model answer.** Write "8 of 8 held-out events detected (95 % interval for the detection rate: 68 %
to 100 %, Wilson)". The exact Clopper-Pearson interval is 63 % to 100 %. One sentence for a
non-statistician: "Eight successes in eight tries is what you would also see fairly often from a
detector that catches only seven faults in ten, so we can say it is good, not that it is perfect."
Add what "detected" meant (matching rule, delay) and that false alarms are a separate number.

**Common incorrect answers.** "100 % ± 0 %" (Wald collapses at the boundary). "Bootstrap it" (every
resample gives 1.0). "Detection is 100 % on the test set, which is all we claim" (true, and useless
for the decision: stakeholders will read it as a property of the detector).

### Q5. Five seeds 0.84, 0.86, 0.81, 0.87, 0.85 against a deterministic 0.84

**Model answer.** The seed mean is 0.846 with sd 0.023 over seeds. (a) Not supported: the mean
exceeds the baseline by 0.006, a quarter of one seed-sd, and seed variation is only one of the
sources; the test-set sampling uncertainty (which neither number includes) is likely larger.
(b) Not supported either in the sense of a demonstrated non-inferiority; it is merely *consistent*
with the data. (c) True and meaningless: picking the best seed is selection on noise. (d) is the
honest answer. Next: evaluate the neural model's seed-average score (or each seed) and the baseline
on the same test clusters, form per-cluster differences, and compute a paired cluster-bootstrap
interval for the difference; report seed mean ± sd separately. If the interval is wide, say what
difference the test set could resolve (section 2.7).

**Common incorrect answers.** Reporting 0.87 ("the method can reach 0.87"). Averaging seeds and
then bootstrapping over the five seeds as if they were test samples.

### Q6. Six comparisons, one p = 0.03

**Model answer.** Weak. If none of the six is better and the tests were independent, the chance of
at least one p ≤ 0.05 is 1 − 0.95⁶ ≈ 0.26. The comparisons share the baseline and test set, so they
are positively correlated and the true figure is somewhat lower, but still far from 0.05. p = 0.03 is
also above the Holm threshold for the smallest of six p-values (0.05/6 ≈ 0.0083). Remedies: pre-register
the one comparison that matters; apply Holm (or Bonferroni) across the six; or confirm the winner on a
fresh set of experiments that played no part in the choice. Also report the effect size and interval:
a "significant" 0.01 PR-AUC would not change a decision.

**Common incorrect answers.** "p = 0.03 < 0.05, so it is better." "Multiple comparisons only matter
for hundreds of tests."

### Q7. Design choice: overlap group as unit, threshold frozen inside the bootstrap

**Model answer (strong).** The bootstrap must imitate how the test set came to exist. What was sampled
was a set of experiments; but five pairs of SKAB files share identical rows, so `other/2`, `other/3`,
`other/4` are not three independent draws of "a fault experiment". Treating them as separate clusters
would count shared information twice and narrow the interval; resampling overlap groups is resampling
the actual independent units: the 34 labelled experiments are 30 of them, not 34 (the frozen
v2 test set happens to contain no overlap group, so its 7 experiments are 7 clusters). The opposite choice (rows or
files) estimates variability under a sampling process that never happened; it is never what we want
for a claim about new experiments, though a file-level bootstrap would be acceptable if files were
known to be independent. The threshold was chosen on development data and is part of the deployed
artifact; re-choosing it inside each replicate would estimate the variability of the *procedure*
"tune a threshold on the test set, then score it" (and leaks test labels into the threshold). That
procedure-level quantity is sometimes wanted (how much does the tuned operating point move with the
data?), but then the tuning must happen on resampled *development* clusters, in a nested design, not
on the test set. Limits: with 7 clusters the percentile interval undercovers, and neither choice
addresses bias from leakage or from the unrepresentative testbed. Decision consequence: claims are
restricted to differences the 7 or 30 clusters can resolve (about 0.25 and 0.10 PR-AUC).

**Common incorrect answers.** "Experiments, because they are separate files" (misses the overlap);
"threshold frozen for speed"; "re-tuning the threshold gives a more realistic interval" (it answers a
different question, and on test labels).

Rubric: the table in `labs/w3d5_uncertainty/assessment.md`.

### Interview rep: "Is B better? 0.912 vs 0.904 on 50,000 windows from 20 machines"

**Rubric (score each 0/1/2).**

| Element | 0 | 1 | 2 |
|---|---|---|---|
| Unit | treats 50,000 windows as independent | mentions machines | resamples machines, explains why (shared machine state, label policy) |
| Pairing | compares two separate intervals | mentions same windows | paired difference per machine, one resample used for both models |
| Precision specifics | ignores the denominator | notes it depends on flags | handles resamples with nothing flagged; ratio of sums vs mean of ratios stated |
| Beyond sampling | none | asks about threshold/operating point | asks whether the thresholds were tuned on this set, whether recall/alert volume changed, label quality |
| Decision | "significant / not" | gives interval | relates the difference to cost (fewer false alerts per week) and proposes shadow running if unresolved |

**Worked answer (read only after a second attempt).** Precision is a ratio of TP to flagged windows.
First check that the comparison is at comparable operating points: a precision gain bought by flagging
fewer windows may cost recall, so look at recall and alert volume too, and confirm the thresholds were
not tuned on this test set. Then compute per machine TP and flagged counts for both detectors. The
independent unit is the machine: windows from one machine share its noise floor, mounting and fault
history. Bootstrap machines (20 of them) with replacement, using **one** draw per replicate for both
detectors, and compute precision(B) − precision(A) as a ratio of summed counts in each replicate;
drop and count replicates where a detector flags nothing. Report the difference, its percentile
interval, and on how many machines B is better; add a sign-flip permutation test on per-machine
differences if a p-value is requested. With 20 machines the interval undercovers somewhat. If it
includes zero, the statement is "not resolved with 20 machines", and the next step is a shadow run on
more machines, not a launch decision on 0.008.

Reference code (`solutions/labs/w3d5_uncertainty/interview_rep/paired_precision.py`), SYNTHETIC
demo run on 2026-11-22: precision(B) − precision(A) = +0.0110, machine-level paired 95 % interval
[+0.0017, +0.0196], 0 undefined replicates. The edge case the code must handle is a resample in which
a detector flags nothing (precision undefined): it is dropped and counted, never set to 0.

**Common incorrect answers.** "50,000 windows, so any difference is significant" (row-level
thinking); "run a two-proportion z-test" (same); "B is better because 0.912 > 0.904" (no uncertainty);
"bootstrap A and B separately" (unpaired, too wide).

---

# Notebook 18 — Error analysis and timed transfer exercise

✍️ Written answers: compare yours against the rubric; wording will differ.


### Reasoning questions

**1.** Pooled recall weights each experiment by its number of anomalous rows; the experiment mean
weights them equally. They agree when experiments have similar numbers of positives (SKAB development: 265-586,
mostly about 400) and disagree when sizes differ and correlate with difficulty (planted data: one
600-row success, three 30-row failures). (a) The reliability engineer cares about faults, so the
per-experiment view, and really the distribution: "7 of 27 below 0.5". (b) Alert storage scales with
flagged rows, so the pooled, row-level figure.

*Common incorrect answers.* "The mean is more robust" (to what? it answers a different question).
"Pooled is the correct recall" (it is one of two estimands). Reporting either without sizes.

**2.** Frequency: fragments are 50 % of wrong rows, late 4 %. Cost per case: a late detection costs
the delay the stakeholder named, 32-80 s each on five events; fragments cost recall on paper
and, operationally, hundreds of separate notifications per fault (alert fatigue), which also erodes
trust in the alerts that matter. Fixability: fragments about 0.6 with hysteresis, a known and cheap
change; late detections about 0.3 with this sensor. Product puts fragments first. It reverses if the
operator already merges alerts within an event (then fragments cost little) or if a missed 60 s is
safety-relevant. Note the interaction: the fragment remedy adds delay, so the two cannot be ranked
and fixed independently.

*Common incorrect answers.* Ranking by row count alone. Ranking late first "because the stakeholder
said delay" without sizing it (5 events, all detected). Ignoring that the fixes trade off.

**3.** (i) It is defined from the labels (mean flow during the anomalous segment), so it is not
available at prediction time and cannot be a routing rule or feature. (ii) It is close to a
tautology: a detector built on flow deviation has low recall where flow deviates little; the slice
restates the metric. Also acceptable: (iii) it was the fifth slice examined, on 6 experiments, with
no correction. A legitimate version: a slice computable before or without the outcome (fault family
from the maintenance log, operating regime at burn-in), stated in advance, confirmed on held-out
experiments.

*Common incorrect answer.* "It's significant because the intervals barely overlap." Overlap is not
the issue; the definition is.

**4.** Cannot conclude: that the detector raises many false alarms on normal operation. The rows it
flags before the labelled onset of `other/13` include rows that `other/12` labels anomalous, so at
least part of the "pre-onset alarm" is the detector agreeing with the other file's label. Can
conclude: the label for this physical stretch of data is contested, and any per-experiment figure for
these two files has an irreducible component. Presentation: keep both in the table, flag them, and
give headline figures with and without the contradictory-label group. Do not delete them silently and
do not let them drive a family comparison (they produce most of `other`'s false-alarm excess).

*Common incorrect answers.* "Drop the bad experiments" (changes the benchmark invisibly). "The model
is bad on `other`" (two files).

**5.** `flow_rate` is quantised, so within an experiment the burn-in z-score takes few distinct
values. Moving the threshold by 0.0017 (from the tuned 2.4044 to the next distinct score value, 2.4061) crosses
one of those values and flips every row sitting on that level at once (here 28 anomalous rows of
`valve1/3`, recall 0.834 to 0.765). Survives: the ranking of failure kinds (fragment
about 50 % at both thresholds), zero missed events, the lack of a family effect. Does not survive:
any statement about an individual experiment's recall or delay to two decimals, and anything inferred
from "the best threshold". General lesson: a tuned threshold on a discrete score is a point on a
staircase; report sensitivity to it.

**6.** The ceiling for this quarter is 0.751 (ranking by the true probabilities); the rule is at
0.727 and the model's interval is 0.65-0.78. The most a perfect model could add is about 0.02, well
inside the interval, so no model can be shown "clearly ahead" with 209 calls; a boosting model that
appears to be is more likely to have found a leak or noise. Instead: ship the rule; spend effort on
(a) whether calls change payment (randomised hold-out), (b) the no-history customers the policy never
calls, (c) a second cut-off date to check stability. In a real project the ceiling is unknown; the
interval alone already says the comparison cannot be resolved.

*Common incorrect answers.* "Try more models and pick the best on test." "Collect more features"
without asking what decision changes.

**7.** Because on the training day those labels do not exist. An evaluation is a rehearsal of
deployment; if the rehearsal uses information the deployment lacks, its number is not an estimate of
anything, whether or not the number moves. They differ a lot when the excluded window is informative
about the test period: fast drift (the late rate was rising here, mildly), a regime change just
before the cut-off, or a small training set where the last three months are a large share. They also
differ when label delay depends on the outcome (lates are known *later* than on-times, so the freshest
"known" labels are biased towards on-time; restricting by a fixed decision date avoids that).

### Design-choice explanation - model answer

Choose `h` and the lower threshold by grouped cross-validation over the 27 development experiments
(overlap groups kept together), never on test. For each candidate compute, on held-out folds,
fragment rows, pre-onset short runs, and detection delay per experiment; pick the smallest `h` after
which fragment rows stop falling, not the F1 maximum, since F1 on this benchmark rewards anything
that fills the event. Fix the candidate grid in advance (say `h` in {5, 10, 20, 40}, lower threshold
in {1.5, 2.0}) so the search is eight configurations. Expected side effect: delay rises by up to `h`
rows and post-event alarms lengthen. Abandon if fragment rows fall by less than 20 % at `h = 20`, or
if median delay rises by more than the stakeholder's tolerance (to be asked; it is not in the brief).
Report per-experiment changes, not only means, and run the chosen setting once on test at the end.

*Common weak answers.* Tuning `h` to maximise dev F1 on all 27 experiments and reporting that F1.
Omitting the delay cost. Having no abandon criterion.

### Interview rep - rubric (read after your first attempt)

| Aspect | Weak | Adequate | Strong |
|---|---|---|---|
| Opening | proposes a fix (retrain, more data) | lists possible causes | asks first what differs between the two measurements: population, time, label definition, feature pipeline |
| Ordering | random order | cheap checks first | orders by prior probability x cost of checking, and says so |
| Coverage | one hypothesis | two or three of: leakage in validation, train/serve feature skew, label definition or delay differences, population shift, sample size of the production estimate | all five, plus "0.97 was never real" stated as the leading hypothesis |
| Concreteness | "look at the data" | names a comparison | names the query: e.g. per-feature distribution train vs serving logs; AUC of validation recomputed with a temporal split; AUC with each feature group removed |
| Uncertainty | treats 0.71 as exact | asks sample size | asks how the labelled production sample was selected (only reviewed transactions? only flagged ones?) and what interval 0.71 has |
| Communication | monologue | structured | interacts: asks the interviewer for facts, states what each answer would rule out |

### Interview rep - worked answer (open only after a second attempt)

Outline of a strong answer. "Two numbers disagree, so first I check they measure the same thing.
(1) How was the production sample chosen and how large is it? If labels exist only for transactions
that were investigated, the sample is selected by the model itself and AUC on it is biased downward;
with a few hundred positives the interval could be wide. (2) My leading hypothesis is that 0.97 was
inflated. For fraud, 0.97 is high. I would recompute validation with a split by time and by account,
since random splits put the same card or merchant on both sides, and look for features computed
after the fact: chargeback flags, account status snapshots, aggregates over a window that includes
the transaction. Check: drop feature groups one at a time; a single group carrying 0.2 of AUC is a
suspect. (3) Train/serve skew: compare each feature's distribution in training data against serving
logs for the same period; look for defaults, units, nulls encoded differently, a join that returns
stale values online. (4) Label definition: validation labels may be mature (90 days of chargebacks),
production labels two weeks old, so many frauds are still labelled clean. (5) Real shift: new fraud
pattern, new merchant category; check by slicing production AUC by segment and time. I would do (1)
and (4) today because they are questions, not analyses; (2) and (3) each need a day. What I would
not do is retrain before knowing which of these it is."

---

# Week 3 review day — Review and catch-up (light)

✍️ Written answers: compare yours against the rubric; wording will differ.


Open only after all twelve questions have a written attempt. Each answer states what a "solid"
answer must contain, then common wrong answers and why they fail.

**Alignment.** Checked against the final Week 3 lessons and handbook sections H6.1, H6.3-H6.7, H7.2
and H7.3 on 2026-11-22. Project numbers are quoted from those lessons' recorded runs on the real SKAB
files, all on the frozen split manifest `v2` (7 test, 27 development experiments). Where a statement
was confirmed by running code here, that is said explicitly; everything else is reasoning.

### 1. Kinds of leakage

The w3d1 taxonomy sorts leaks by *where* the unavailable information sits: in a feature, in which rows
are on which side, in a fitted step, or in a choice. Eight kinds:

| Kind | One-line example | Detection probe |
|---|---|---|
| **Target / proxy** | `reminders_sent` on an invoice, written after the payment was late | single-feature AP/AUC near 1; ask *when is this column written?* |
| **Temporal aggregate** | a customer's late-payment rate computed over the whole export, including later invoices | recompute point-in-time; old rows change when new data arrives |
| **Shortcut / protocol** | elapsed time in SKAB (onset near row 570); ledger-number range; EEG session or site | single-feature probe; **clock probe**; `time_monotone_columns` |
| **Group** | windows of one experiment, machine or patient on both sides | grouped versus random split gap |
| **Duplicate / near-duplicate** | the 1,290 SKAB rows that appear in two files | row hashing across sides; nearest-neighbour distance test-to-train |
| **Temporal** | training rows later than test rows; windows crossing the boundary | forward versus random split; purge test (w3d2) |
| **Preprocessing** | scaler, imputer, selector or PCA fitted on all rows | change evaluation rows and see whether anything else moves |
| **Selection** | threshold, hyperparameters or best seed chosen on test | count test looks; best-of-N against a fresh hold-out |

A grouped split prevents **group leakage only**, and duplicate leakage only if duplicated units are
grouped together (which is why v2 keeps overlap groups on one side). It leaves target, temporal
aggregate and shortcut features in every group, preprocessing fitted before the split, and selection
on the test set in place. The clock shortcut is the clearest SKAB case: it is shared by every
experiment, so no split removes it; it must be forbidden by name (`audit_features`) and checked for in
disguise.

| Common wrong answer | Why it fails |
|---|---|
| "Leakage means the label is among the features" | One kind of eight |
| "We split by patient/experiment, so there is no leakage" | Addresses one mechanism |
| "Leakage always inflates the metric visibly" | The w1d3 scaler leak changed no printed metric, and w3d1's v1/v2 comparison on the shared test experiments moved 0.899 to 0.900. The procedure is wrong regardless |
| "No probe fired, so there is no leak" | Probes find known kinds; the feature-availability audit is the real defence |

### 2. Prevention by construction

A `Pipeline` passed to `cross_val_score`/`GridSearchCV` is **refitted on each training fold**: every
step's `fit` sees training rows only, and the fitted transformation is then applied to the held-out
rows. Correctness no longer depends on anyone remembering the order of operations, and the same
object does preprocessing and prediction at serving time.

Inside it must go everything that **learns from data**: scaling, imputation statistics, encoders
(especially target encoding), feature selection, dimensionality reduction, resampling for class
balance (which must apply to training folds only), and any learned threshold if it is tuned in the
search. Stateless row-wise transforms (a log, a ratio of two columns) are safe outside.

What a pipeline cannot prevent: **target leakage** (a column that should not exist at prediction
time), **temporal leakage created upstream** when the feature table was built, a **wrong splitter**
(row-wise where groups are needed), and **selection on the test set** by the person running it.

| Common wrong answer | Why it fails |
|---|---|
| "Pipelines make leakage impossible" | They fix one mechanism |
| "Fit the scaler on train, transform test by hand; same thing" | Correct once; inside cross-validation and search it must happen per fold, which is what gets forgotten |
| "Oversample before splitting so both sets are balanced" | Copies or interpolations of test rows enter training |

### 3. Duplicated rows with contradictory labels

*Splits.* Files that share rows are not independent. Experiments connected by shared rows form
**overlap groups** (`{anomaly-free, other/5}`, `{other/12, other/13}`, `{other/2, other/3, other/4}`,
`{other/10, other/11}`), and each group must stay on one side of every split and inside one fold. The
v1 manifest of w2d4 broke this: 370 test rows were also in development, 178 of them with the opposite
label.

*Achievable performance.* Where identical inputs carry both labels, no function of the sensors is
right on both copies. Labels near segment boundaries are noisy, so point-level metrics have a ceiling
below 1 and small differences near segment edges are not meaningful. The labels are the experimenters'
markings, not ground truth (w3d6 reports such units separately).

*Why `v2`, and why move rather than redraw.* Results already computed refer to `v1`; editing it in place
would make old and new numbers silently incomparable under one name. The repair moved only what had to
move (`other/11` and `other/12` left the test set; `other/4` changed development fold) and kept every
other test experiment, so the test set was not re-chosen after results had been seen. Redrawing would
have been a fresh look at a new test set, chosen by someone who already knew how models behave: a form
of selection. `validate_splits` now rejects any manifest that separates a group.

What the comparison showed (w3d1): v2 test PR-AUC is higher than v1 (logistic regression 0.900 vs
0.827), but on the seven experiments that are in test under both manifests the difference is 0.899
vs 0.900. The headline change comes from the test set changing, not from removing the leak; v1 was
wrong by construction, and the size and sign of its error depend on the model.

| Common wrong answer | Why it fails |
|---|---|
| "Drop the duplicated rows" | Breaks the time series and leaves the same physical period on both sides |
| "1,290 of 46,806 rows is under 3 %, ignore it" | The unit is the experiment: 8 of the 14 `other` experiments and the fault-free reference are involved |
| "Fix v1, the old numbers were wrong anyway" | Then nobody can tell which numbers used which split |
| "Draw a fresh v2 with the overlap constraint" | Re-chooses the test set after results were seen |
| "The leak cost 0.07 PR-AUC" | Compares different test sets |

### 4. What each validation scheme asks

* **Grouped** (hold out whole experiments, machines, patients, customers): *how well does the
  procedure work on a new unit from the same population?* This is "a detector trained on past
  experiments is run on a new experiment".
* **Temporal / forward-chaining** (train on the past, test on the following period): *how well does
  a model trained now work later, on the same units, as conditions drift?* This is "the same machine
  next month".
* **Combined** (test units are new *and* later): *a new unit installed in the future.* The most
  demanding and the smallest in data; often what deployment really is.

Choosing a scheme is choosing which claim you make. Random K-fold answers "how well do I interpolate
among rows I have already seen the neighbours of", which is rarely a deployment question.

| Common wrong answer | Why it fails |
|---|---|
| "Temporal validation is stricter, so always use it" | It does not hold out units; on data with strong unit identity it can be more optimistic than a grouped split |
| "Grouped K-fold handles time automatically" | A fold can train on later experiments and test on earlier ones; fine if experiments are exchangeable, wrong if there is drift across them |

### 5. Purging and embargo

When train and validation rows come from the **same continuous series**, a feature over a window of
`w` rows and a label over a horizon of `h` rows make rows near the boundary share raw samples. For a
validation block `[a, b]` (w3d2, section 2.5):

* **purge** the training rows in `[a - (w-1+h), a-1]`: their features and labels reach into the block;
* **embargo** the training rows in `[b+1, b + (w-1+h)]`: their feature windows reach back into it.

So each side removes `w - 1 + h` rows (`required_purge(30) == 29`, `required_purge(40, 30) == 69`), in
rows of a regular series or the equivalent *time* where sampling has gaps. In forward chaining there is
nothing after the block to embargo, and the purge is the `gap` argument. In the w3d2 demonstration on
unpredictable labels, a one-sided buffer still left an AUC of 0.518; both sides at `w-1+h` gave about
0.50: the embargo is not optional in blocked K-fold.

This project splits by whole experiment and computes features per experiment, so no window crosses a
split boundary and no purge is needed between experiments. It becomes necessary when one experiment's
timeline is split (blocked folds within an experiment, as in w3d2's within-experiment scheme with purge
= embargo = 29), when features are computed across concatenated experiments, or when the same physical
period appears in two files (the overlap groups again).

| Common wrong answer | Why it fails |
|---|---|
| "Purging is only for finance" | Needed wherever windows or labels cross a boundary |
| "A gap of one sample is enough" | The gap must cover `w - 1 + h` |
| "Purging removes temporal leakage" | It removes shared raw samples; slow drift and protocol shortcuts remain |
| "Shuffle after windowing to decorrelate" | Shuffling spreads the overlap to both sides; it is the cause |

### 6. Nested cross-validation

The **inner loop** runs the whole selection procedure (search, one-SE choice, refit, threshold) on the
outer training folds only. The **outer score** is computed on the outer fold, which never fitted a
model, scored a candidate or moved a threshold, so the mean outer score estimates the performance of
*the procedure*. Different outer folds may select different configurations (on SKAB: boosting in
three folds, logistic regression in one); that is information about stability, not a bug.

You **ship** the result of running the same procedure once on all development data, then look at the
test set once with its threshold frozen. No outer-fold model is special.

The best inner score is a maximum over noisy estimates, so it is biased upward (question 7).

| Common wrong answer | Why it fails |
|---|---|
| "Report the best cross-validated score from the grid search" | Selection optimism |
| "Ship the model from the best outer fold" | Chosen by its own test score, trained on less data |
| "Nested CV gives the performance of the final model" | It estimates the procedure; the final model is one draw from it |
| "Outer folds chose different settings, so the method is broken" | Often the candidates are indistinguishable; say so and prefer the simplest |

### 7. Thresholds are fitted; optimism grows with K

A threshold is chosen by looking at scores **and labels** to optimise a criterion; it is a
one-parameter model. It is chosen on development (out-of-fold) scores, frozen, and the test result is
reported at that frozen threshold, never at the test-optimal one.

For `K` equally good candidates with independent errors `N(0, σ²)`, the optimism of the best is `σ`
times the expected maximum of `K` standard normals: 0.56σ for K = 2, 1.54σ for K = 10, 2.25σ for
K = 50, growing like `σ√(2 ln K)` (w3d3, section 2.2). With correlation `ρ` between candidates the
shared part does not change the winner, and the optimism shrinks by about `√(1−ρ)`. With few test
units `σ` is large, so even a modest search manufactures several points.

On SKAB (w3d3): best development CV PR-AUC 0.891, one-SE choice 0.878, **nested estimate 0.850 ±
0.032**. The nested estimate is the number for the procedure; the 0.891 is the best of 24 noisy
estimates. The single test look gave 0.922, above the nested estimate: with 7 test experiments that is
within noise, and it does not mean the nested estimate was pessimistic.

| Common wrong answer | Why it fails |
|---|---|
| "The threshold is post-processing, not a parameter" | It is chosen using labels; that is fitting |
| "AP/ROC AUC are threshold-free, so no problem" | The deployed system uses one threshold, and choosing a model by AP on test is still selection |
| "Optimism grows linearly with the number of trials" | Slowly, like `√ln K`; the first trials cost most |
| "The one-SE rule removes the optimism" | It changes the choice, not the bias of the number attached to it |
| "Test came out higher, so report test" | One look at 7 experiments; report it as the test result next to the nested estimate |

### 8. Matching, event metrics, and why point metrics mislead

*The course's default matching rule (w3d4, section 2.4).* An alarm is judged by its **start**. It
detects an event if it starts inside the event (or at most `early_tolerance` rows before it; default
0). The earliest such alarm is the **hit**; later alarms in the same event are **redundant** (neither
true nor false). An alarm that starts during normal operation is a **false alarm**, even if it runs on
into the event: it carried no news when the fault began. An alarm starting before the labelled onset is
therefore a false alarm unless a stated tolerance covers it.

* **Event recall** = detected events / true events.
* **Event precision** = hits / (hits + false alarms); redundant alarms excluded.
* **Detection delay** per event: from the true onset to the moment the hit is raised (including the
  confirmation time of a minimum-duration rule), and **infinite for a missed event**. Report the
  median and a high percentile over *all* events, misses included; averaging over detected events
  only rewards missing hard cases.
* **False alarms per hour of normal operation** = false alarms / hours outside true events, with the
  count and hours reported, and an upper bound: zero false alarms in the 1.22 test hours is still
  compatible with 2.46 per hour.

*Point and event disagree.* In w3d4's synthetic example, "long event only" has the best point F1
(0.899) and finds 1 of 10 events; "onset only" has point F1 0.066 and finds 10 of 10 at zero delay. On
SKAB the flow-rate z-score finds all 7 test events but as 469 separate alarms, 290 of them false. With
a minimum duration and gap merging it drops to 17 alarms and finds only 3 of 7, because at its low
threshold the merged alarm often starts before the onset and becomes a false alarm; Mahalanobis, worst
on point F1, is the best post-processed detector (5 of 7 events). Post-processing and threshold must be
chosen together.

*Timestamps.* Six SKAB files have gaps up to 247 s, so row counts are not durations: hours from rows
come out too small by about a factor 1.1 on SKAB, and an operator's requirement is stated in time.

| Common wrong answer | Why it fails |
|---|---|
| "Any overlap counts as detection" | Credits an alarm that started before the fault with a zero-delay detection |
| "Report mean delay over detected events" | Censoring error: missing hard events lowers the delay |
| "False alarm rate = FP rows / normal rows" | Point-level FPR; an operator counts interruptions per hour |
| "Point-adjust is the standard protocol" | It credits a whole segment for one hit; a random scorer looks strong on long segments (w3d4, 3.2) |
| "Event metrics fix leakage" | The elapsed-time clock finds 3 of 7 test events (7 of 7 under any-overlap) |

### 9. Cluster bootstrap with seven experiments

Procedure (w3d5): keep per-experiment scores and labels. Repeat `B` times (say 2,000): draw 7
experiment ids **with replacement** from the 7 test experiments; build the pseudo-test set from all
rows of the drawn experiments (an experiment drawn twice appears twice); recompute the metric on it;
store it. Report the estimate on the real test set with the percentile interval, and state "unit of
resampling: experiment, 7 clusters". If an overlap group were in the test set, the group would be the
cluster; the frozen v2 test set has none, so 7 experiments are 7 clusters.

Resampling rows is wrong because rows within an experiment are strongly correlated: the effective
sample size is close to the number of clusters, not the number of rows. On SKAB the row bootstrap gave
intervals about 3-7 times too narrow.

What remains doubtful: with `G = 7` there are only `C(13, 7) = 1,716` distinct resamples, any one
experiment is missing from about 34 % of them (`(6/7)^7 = 0.340`), and in w3d5's simulation a nominal
95 % percentile interval covered the truth only about 87-88 % of the time with 7 or 9 clusters. BCa
helps a little (it moved the lower limit by about 0.025 for the flow-rate baseline) and cannot rescue 7
clusters. The interval is a lower bound on the honest uncertainty, and the report says so.

| Common wrong answer | Why it fails |
|---|---|
| "Bootstrap the test rows" | Ignores dependence; far too narrow |
| "With 2,000 resamples the interval is precise" | More resamples reduce Monte Carlo error, not the error from having 7 units |
| "Report mean ± std over CV folds" | Folds share training data; not an interval for the test estimate |
| "A resample with no positives is an error; drop it" | It is a property of having few clusters; handle and document it (w3d5 lab) |

### 10. Paired comparison

Both models are scored on the same experiments, and experiments differ in difficulty: an easy one is
easy for both. The scores are correlated, so the variance of the *difference* is much smaller than the
two separate intervals suggest (w3d5's synthetic example: unpaired interval for the difference
[−0.063, +0.090], paired [+0.0155, +0.0191]).

Report the interval for **Δ = metric(A) − metric(B)**: in each bootstrap replicate draw one set of
cluster ids and apply it to both models; store the difference; take the percentile interval. A
sign-flip permutation test on per-cluster differences is an exact alternative for small `G` (with 7
clusters its smallest possible p-value is 2/128 = 0.016).

If the interval contains zero: "A and B are not distinguishable on these 7 experiments (Δ = x, 95 %
interval [l, u])", then decide on other grounds and say so. If methods disagree, report both. On SKAB
the Mahalanobis versus flow-rate comparison had a bootstrap interval excluding zero (−0.125
[−0.278, −0.013]) while the sign test (p = 0.45) and permutation test did not reject; w3d5 reports it as **not established**. The minimum detectable
difference with 7 clusters is about 0.25 PR-AUC; with 30 about 0.10.

| Common wrong answer | Why it fails |
|---|---|
| "The two intervals overlap, so there is no difference" | Ignores the pairing |
| "A t-test on per-row errors" | Rows are not independent |
| "A won on 5 of 7 experiments, so A is better" | A sign count on 7 units has almost no power |
| "Not significant, therefore equal" | With 7 clusters almost nothing is significant; absence of evidence is weak evidence |

### 11. From errors to an error analysis

An error analysis produces a short **ranked list of failure modes**, each with a size, a cost and a
hypothesis about its cause (w3d6). Steps:

1. **Work on development data** (out-of-fold predictions). Reading test errors and then changing the
   model turns the test set into a second development set.
2. **A unit table:** one row per experiment with its metrics; every later step is a group-by on it,
   and an undefined metric is missing, not zero.
3. **Slices written before looking** (family, regime, time since start, gaps, label conflicts),
   with sizes and cluster-aware intervals or counts.
4. **Error kinds** from runs of wrong rows: miss, late, boundary, fragment (alarm dropped out),
   pre-onset, post-event, false alarm. Each points to a different fix.
5. **Separate label noise from model error:** report units with contradictory labels separately.
6. **Rank by frequency × cost × fixability**, stating the assumptions; frequency caps the gain.
7. **A hypothesis and a test per top mode**, on other development units.

Two ways it misleads. *Slice hunting is multiple testing:* in w3d6's simulation, 24 machines with
identical recall 0.80 and 80 slices produced a "worst slice" averaging 0.729, and 45 % of searches found
one at least that bad. *Simpson's paradox:* a detector can be better in every regime and worse pooled.
(And the leak: error analysis on the test set.)

| Common wrong answer | Why it fails |
|---|---|
| "Plot the confusion matrix" | One aggregate; no slices, causes or ranking |
| "Look at the 20 highest-loss samples" | Dominated by one or two experiments and by label noise |
| "We found a slice at 0.73, fix it" | Expected by chance after 80 slices; test it on other units first |
| "We fixed every error we found on the test set" | The reported test number is now optimistic |

### 12. `NOT IN` with a NULL (delayed question from w2d1)

`technicians.site_id` is NULL for external contractors. `x NOT IN (a, b, NULL)` means
`x <> a AND x <> b AND x <> NULL`. The last comparison is UNKNOWN, so the conjunction is never TRUE
(it is FALSE if `x` equals a listed value, UNKNOWN otherwise), and `WHERE` keeps only TRUE rows.
One NULL in the subquery empties the result. *(Confirmed on the `w2d1` database `maintenance.db`, SQLite 3.53.1: 2 of 12
technicians have a NULL `site_id`; `NOT IN` returns 0 rows, `NOT EXISTS` returns 2.)*

Rewrites:

```sql
-- anti-join with NOT EXISTS: NULLs in the subquery simply never match
SELECT s.* FROM sites s
WHERE NOT EXISTS (SELECT 1 FROM technicians t WHERE t.site_id = s.site_id);

-- left join and keep the unmatched rows
SELECT s.* FROM sites s
LEFT JOIN technicians t ON t.site_id = s.site_id
WHERE t.tech_id IS NULL;
```

(`NOT IN (SELECT site_id FROM technicians WHERE site_id IS NOT NULL)` also works, but depends on
everyone remembering the filter.) In the left-join form, test a column that cannot be NULL in a
matched row, such as the primary key.

| Common wrong answer | Why it fails |
|---|---|
| "The data must have no such sites" | The query, not the data |
| "`NULL <> x` is true" | It is UNKNOWN; three-valued logic |
| "Use `IN` and negate the result set with `EXCEPT`" | Workable, but misses the mechanism, and `EXCEPT` also de-duplicates |

---

# Notebook 19 — Time-series fundamentals and forecast-residual detectors

✍️ Written answers: compare yours against the rubric; wording will differ.


### Q1
The factor √30 ≈ 5.5 assumes independent samples. With lag-1 autocorrelation 0.95 the 30 values are
nearly copies of each other. For an AR(1) with φ = 0.95 the variance of a 30-sample mean is
`σ²/n² [n + 2 Σ_{k=1}^{n−1} (n−k) φ^k]` ≈ 0.64 σ², so the standard deviation drops by a factor of
about 1.25, not 5.5 (computed in the authoring session). The window is far shorter than the
decorrelation time; to reduce noise materially the window must span many decorrelation times — or the
"noise" is really slow signal and should be modelled, not averaged.

*Common incorrect answers.* "It is fine because the CLT applies" (it needs many effectively
independent terms); "the reduction is √(n_eff) with n_eff = n(1−φ)/(1+φ) ≈ 0.8" — that large-n
formula breaks down when the window is shorter than the memory; use the exact sum.

### Q2
Σφ close to 1 means the fitted process is nearly a random walk: the implied mean `c/(1−Σφ)` is poorly
determined and the forecast hardly pulls towards it. The model behaves like the naive forecaster: the
residual spikes at the fault onset and returns to noise while the fault persists, so point-level
scores during the fault are low. It also signals that 100 rows were too few, or contained a drift,
for that sensor.

### Q3
An AR(2): PACF cutting off after lag 2 with a decaying ACF is the AR(2) signature. After fitting,
check the residual ACF (inside the noise band at all small lags), that the coefficients describe a
stationary process (roots outside the unit circle; for AR(2) e.g. |φ₂| < 1, φ₁ + φ₂ < 1, φ₂ − φ₁ < 1),
and that the residual scale is stable across the fit window (no variance change).

### Q4
No. With independent residuals, ARL₀ for this chart is about 460 samples (simulated in the lesson), so
an 8-hour shift (28,800 samples) has about 60 false alarms, against a budget of 1. With positively
autocorrelated residuals it is worse: the running sums accumulate correlated noise, whose variance is
inflated (by about (1+φ)/(1−φ) = 3 for φ = 0.5 over long stretches), so `h` is crossed far more often.
Remedies: larger `h` (chosen by simulation or on development data against the budget), whitening the
residuals with a better model, or alarming on a slower time scale.

*Common incorrect answer.* "ARL₀ of a few hundred sounds large, so it is fine" — always convert run
lengths into alarms per shift at the actual sampling rate.

### Q5
When the event of interest is a *change* and the signal level itself is uninformative or wanders:
e.g. detecting step changes in a random-walk-like quantity (inventory level after a mis-scan, a
sensor recalibration, a sudden jump in a price series), or detecting onsets when another system
handles the sustained state. The naive forecast is optimal for a random walk and needs no fitting, so
it cannot be wrong about the level; it only reports changes.

### Q6
Example: after a sustained level shift, the naive forecaster's RMSE is low (it follows the new level
after one sample) while an AR model anchored to the normal mean has a persistent error. Lowest RMSE
selects the naive model, which is blind to the sustained fault (figure 2 and the SKAB table). More
generally RMSE rewards adaptation to *any* change, including the anomalies the detector should report;
detectors must be selected by detection metrics on held-out units under the deployment protocol.

### Q7 (key points for the rubric)
* **Avoids:** the reference recording is at a different operating point from most labelled
  experiments (project/README findings; w2d5/w2d6), so a global model of "normal" flags entire
  experiments, normal parts included. Burn-in normalisation conditions on each experiment's own
  operating point; it is also what was found to work in w2d5/w2d6 and keeps comparisons fair.
* **Costs:** only 100 rows per sensor (for persistent sensors that is a handful of effective samples;
  coefficients and sigma are noisy; quantised sensors give degenerate scales); assumes the first 100
  rows are normal (true in SKAB by construction, which is itself a property of the protocol, not of
  the world); the first 100 rows cannot be scored; nothing is learned across experiments.
* **Wrong when:** faults can be present at start-up (a machine restarted with a bad bearing); faults
  develop slowly from start-up so the burn-in already drifts; or the fleet runs at a few known
  operating points, where a model per operating point trained on many machines is better estimated and
  easier to validate and govern than thousands of per-run fits.

### Interview rep — what a strong answer contains
1. Random K-fold puts rows adjacent in time on both sides; with autocorrelation the held-out rows are
   predictable from their neighbours, so the estimate measures interpolation, not forecasting or
   detection on new periods. Use blocked or forward-chaining splits with a gap (purging/embargo, w3d2),
   or split by independent unit (experiment, machine).
2. Code and tests: `solutions/labs/w4d1_timeseries_fundamentals/interview_rep/` (executed: 3 tests
   pass). Unreliability for short series: each `r_k` has sd about 1/√n, and summing many lags adds
   their noise; truncating `max_lag` too early ignores long memory, too late adds noise.

---

# Notebook 20 — Classical detectors: PCA/T2-Q, isolation forest, boosted trees on window features

✍️ Written answers: compare yours against the rubric; wording will differ.


### Q1
Q alarms first: the fault breaks a relationship (vibration no longer tracks current), so the row leaves
the subspace spanned by normal co-variation while each sensor may stay in its normal range — T² measures
position inside the subspace and changes little. If `k` is raised until 99.9% of the variance is kept,
the retained subspace starts to include the small, noise-like directions, including the one along which
the fault moves; the fault is then "explained" by the model, Q shrinks towards noise, and T² (now divided
by tiny eigenvalues in those directions) becomes erratic. Choose `k` on detection performance, not on a
high variance share.

*Common incorrect answer.* "T², because the fault makes the vibration large." Early in a decoupling
fault the vibration is not large; it is inconsistent.

### Q2
`contamination` only set the threshold of `predict` so that 2% of the *training* rows are flagged. They
chose an operating point by assumption: the share of fraud is not the share of rows that should be
flagged (it depends on how the scores separate the classes and on the alarm budget). Instead: use the
continuous scores, report threshold-free metrics (average precision) on held-out labelled data, and pick
the threshold on development data from the business constraint (review capacity, cost of a miss).

### Q3
(a) The fault signature differs: the model learned what separates *those* faults (here, valve faults
move the flow rate directly) and a new mechanism moves other sensors. (b) The normal behaviour differs:
the new family's normal rows sit elsewhere (noisier flow in `other`), so the model's decision regions
cut through normal data. To tell them apart: look at false positives on the unseen family's *normal*
rows versus misses on its *fault* rows (a per-class error breakdown), or compare score distributions of
normal rows across families. On SKAB, both appear: `other` normal rows have higher |z| (1.25 vs 0.55
median for flow) and its faults move flow less (3.58 vs 5.22).

### Q4
* Were the budgets equal (trials, features, data)? If not, part of the 0.05 is selection optimism.
* Is 0.05 a nested or held-out estimate, or the best inner score (w3d3)?
* Same features and the same rows (did the forest get normal rows only, the GBT all rows)?
* Same threshold rule and evaluation unit; uncertainty on the difference, ideally paired by unit (w3d5);
  how many independent units.
* A second protocol (unseen family, later period) and the false-alarm rate at a usable operating point.

### Q5
It shows that the fitted model's average precision *on the training rows* depends heavily on that
feature — i.e. the model uses card age to recognise the five fraudulent accounts it was trained on. Card
age is constant per customer, so it acts as an account identifier. It says nothing about whether card
age predicts fraud for new customers; the grouped estimate (0.042, actual 0.159 on new customers)
suggests the model's knowledge is mostly account memory. Importance must be measured on held-out
*customers*, and even then it describes the model, not causation.

### Q6
A random 10% of rows puts rows from the same experiment (adjacent, autocorrelated, sharing a fault) in
both the training and the stopping set, so the stopping point is chosen on leaky validation data and
tends to over-fit. Cheapest correct alternative: turn early stopping off and treat `max_iter` (with the
learning rate) as a hyperparameter selected by the grouped out-of-fold procedure already in place; or
supply a validation set of whole held-out experiments.

### Q7 (key points for the rubric)
Equal footing answers "which *model family* is better for this data, other things equal": features,
budget, threshold rule and evaluation are held fixed so that differences can be attributed to the model.
The colleague's design answers a different, legitimate question: "which complete *system* is best?"
— but then the comparison confounds the model with the feature set and the search effort, and a larger
search inflates the winner's development score (optimism of the max, w3d3) unless the estimate is
nested. The right response is to run both as separate, labelled experiments: equal footing as the
controlled comparison, and "each at its best" with a nested estimate and with the budgets stated. If the
forest on raw sensors is genuinely better, that is a finding about features, and it should be tested by
giving the same raw sensors to the GBT as well.

### Interview rep — what a strong answer contains
1. Bagging averages models trained on bootstrap samples: it reduces variance, leaves bias. Random forests
   add feature subsampling at each split so that the trees' errors are less correlated; the variance of an
   average of correlated predictors is `ρσ² + (1−ρ)σ²/B`, so lowering `ρ` matters more than adding trees.
   Boosting fits each model to the residual errors (gradients) of the current ensemble: it reduces bias,
   and can over-fit; the learning rate shrinks each step so that many small steps generalise better
   (regularisation), at the cost of more iterations.
2. Code and tests: `solutions/labs/w4d2_classical_detectors/interview_rep/` (executed: 3 tests pass).
   Key points: sort once, cumulative positive counts give each split's child impurities in O(1), skip
   positions between equal values.

---

# Notebook 21 — A neural comparison, where it is justified

✍️ Written answers: compare yours against the rubric; wording will differ.


### A. Reasoning questions

1. **Objective.** With 27 development experiments and one segment each, a classifier has 27 positive
   examples of "a fault" in effect (thousands of rows, but highly dependent), from three families. It will
   learn those faults; nothing pushes it to flag a new kind. Reconstruction and forecasting learn
   *normal* behaviour from all normal rows, so any departure can raise the score. Switch to a classifier
   when faults are many, of known recurring types, labelled reliably, and the cost of missing a *known*
   type dominates (for example a fleet of 5,000 pumps with hundreds of labelled bearing failures).
   *Common wrong answer:* "classifiers need balanced classes". Balance is not the issue (SKAB is ~35%
   anomalous at row level); the number of independent fault instances and families is.

2. **Early stopping.** The returned model holds the epoch-10 weights (the best validation loss; patience
   4 means epochs 11-14 did not improve). Reporting the epoch-30 TEST score would describe a model nobody
   chose by the stated rule; and choosing between epoch 10 and epoch 30 *by their TEST scores* would be
   selection on test. *Common wrong answer:* "it contains the epoch-14 weights" (that is the last-epoch
   mutant).

3. **Whole-experiment standardisation.** The mean and sd then include the fault rows: a level shift from
   row 600 raises the mean and inflates the sd, so the standardised fault is smaller and the normal part is
   shifted the other way. It is also look-ahead: at row 650 in deployment the statistics of rows 651-1,100
   do not exist yet. Offline scores are computed with information the live detector cannot have, so the
   offline precision will not hold. *Common wrong answer:* "it is fine because no labels are used". Leakage
   of future inputs does not need labels.

4. **Better reconstruction, worse detector.** A model with more effective capacity can reconstruct
   *anything* well, including fault windows, so the error gap between normal and fault rows shrinks.
   Detection needs the error on faults to be large relative to the error on normal rows, which validation
   loss on normal rows does not measure. (The classic over-complete autoencoder problem; the bottleneck is
   the regulariser.) *Common wrong answer:* "seed 3 overfitted". Its validation loss is the lowest, so it
   did not overfit in the usual sense.

5. **Different numbers on another machine.** Thread count (parallel reductions reorder floating-point
   sums; 2.6 measured a change in the third decimal of PR-AUC), torch / BLAS / NumPy versions, CPU
   instruction set (different kernels), a different SKAB download (check the manifest hashes), a
   different manifest. Record: seed, thread count, device, library versions, data and manifest hashes,
   code commit, exactly what w4d4 automates.

### B. Design choice: one thread

For this model (3,658 parameters, batches of 256 windows of 16 x 8) the work per operation is tiny and
thread synchronisation dominates: on the authoring container a 6-epoch fit took 1.6 s on one thread and
94.5 s on four. One thread also fixes the order of floating-point reductions, so two runs with the same
seed are bitwise identical on the same machine. Both properties are recorded in the output so the
choice is visible. For a large production model this choice is wrong: it would waste most of the
hardware. There you would use many threads or a GPU, accept that runs are reproducible only up to
numerical noise, quantify that noise by repeating seeds, and pin library versions and hardware type in
the run record instead of relying on bitwise equality.

**Rubric:** strong answers give the measured reason (overhead versus work), the reproducibility reason,
and the production caveat; solid answers give one reason and the caveat; weak answers say "for
reproducibility" only.

### C. Rubric usage

Use the table in `assessment.md`. "Strong" on uncertainty requires naming both the seed spread and a
test-set interval and saying which question each answers.

### D. Interview rep — worked answer and rubric

A strong narrative goes from cheapest-and-most-likely to expensive, and says why:

1. **Validation windows are not held out.** `train_test_split` on windows splits *overlapping* windows
   of the *same experiments* at random: almost every validation window has near-copies in training (31
   of its 32 rows shifted by one). Validation loss near zero is the symptom. Fix: split by experiment
   (dev folds), as in w3d1/w3d2.
2. **Anomalous rows are in training.** Nothing filters `anomaly == 0` or the burn-in rows; the model
   learns to reconstruct faults, which explains misses in deployment. Fix: train on normal, post-burn-in
   rows only.
3. **Windows cross experiment boundaries.** `make_windows` over the concatenated frame produces windows
   that end in one experiment and start in the previous one. Fix: window per experiment.
4. **Normaliser fitted on all training rows including faults**, and later probably on the scored data.
   Fix: fit on the usable training rows, store it, never refit.
5. **`best_state = model.state_dict()` without a copy**: the "best" weights are the live tensors, so the
   restored model is the last epoch's. Fix: `copy.deepcopy`.
6. **No seeds, `num_workers=4`, `shuffle=True` without a generator**: runs are not reproducible, so
   "it worked offline" cannot be re-checked. Fix: seed model, generator and workers; record threads.
7. Only then: deployment-side differences (causal scoring, sensor scaling in production, the live
   normaliser).

| | Weak | Solid | Strong |
|---|---|---|---|
| Finds the leak | misses it | names random window split | explains overlap and why validation loss collapses |
| Training data | misses faults in training | names it | connects it to the shadow-deployment misses |
| Code-level bugs | none | state_dict or boundary windows | both, with fixes |
| Order and reasoning | list without order | rough order | cheapest/most likely first, says what each check would show |

---

# Notebook 22 — Experiment tracking and reproducibility at the experiment level

✍️ Written answers: compare yours against the rubric; wording will differ.


### A. Reasoning questions

1. **Same config, different metrics.** (a) Different code: `environment.json: git_commit` differs, or ends
   in `-dirty` (uncommitted changes). (b) Different data at the same path: the data fingerprint differs.
   (c) Different library versions or platform (numerics, defaults changed between versions):
   `environment.json: packages`, `platform`. (d) Non-determinism not controlled by the seed (threads, GPU
   kernels, unordered iteration): nothing in the record differs, which is itself the diagnosis; rerun twice
   on one machine to confirm, and record thread count and device. *Common wrong answer:* "the seed
   differed". Then the configs, which include the seed, would differ too.

2. **Seed in the id.** Identity means "this exact computation". Two seeds are two computations with
   different results; if they shared an id, the second would be skipped as already complete (or overwrite
   the first), and the table would show `n = 1` where you asked for several. Selection ignores the seed;
   identity cannot.

3. **Keeping only the index.** Lost: the full resolved configs (the index flattens them but a CSV loses
   types), the environment and data fingerprints, the error records of failed runs, any artifacts, and the
   ability to reproduce or rebuild the table if the CSV is wrong. Keep the small files (`config.json`,
   `environment.json`, `metrics.json`, `status.json`, typically kilobytes) for every run and delete only
   large artifacts of runs that were never selected, recording that they were deleted.

4. **Excluded run.** Failed (the task raised; `status.json` holds the error) or partial (no
   `status.json`: the process died, or is still running). A failed run needs a diagnosis: if the failure
   depends on the configuration (for example a numerical error at extreme hyperparameters) it is a
   *result* to report, not something to hide by rerunning until it passes. A partial run should be
   re-executed (the sweep does so automatically) once you know it is not still running. Until then the
   configuration has fewer seeds than the others, which should be visible.

5. **Different scored rows.** Configurations with a shorter burn-in would be evaluated on more rows,
   including rows 100-199, which are close to the start of each experiment and almost always normal, so
   their metrics would be computed on an easier, different set. The comparison would mix the effect of the
   parameter with the effect of the evaluation set. Fixed evaluation rows make the configurations
   comparable.

### B. Design choice: directories versus database

Directories as truth are better for a single researcher or a small team on shared storage: no service to
run, results travel with `cp`/`rsync`, the record is human-readable, and the index can always be rebuilt.
They make it easy to have *several* inconsistent copies (two machines each with half the runs) and they
scale poorly to millions of runs or concurrent writers. A database (MLflow's backend store) is better for
many people and many concurrent runs, with queries and a UI; it makes it easy to lose the link between
the database row and the actual artifacts (a database restored from backup while the artifact store moved
on) and harder to inspect or repair by hand. Either way, the record must be immutable once complete.

### C. Rubric

See `assessment.md`. "Strong" on provenance requires naming the dirty flag and a data fingerprint, and
what each would catch (uncommitted code; a changed file at the same path).

### D. Interview rep

Reference with tests: `interview_rep/config_diff.py`. Complexity: `diff_configs` is O(n) in the total
number of leaves of both configs (flattening plus set operations on hashed keys); `best_per_group` is
O(R · g) for R records and g grouping keys (one pass, constant work per key lookup).

| | Weak | Solid | Strong |
|---|---|---|---|
| Correctness | misses nested keys or removed keys | passes the examples | also handles a table replaced by a scalar, ties, non-complete runs |
| Design | ad-hoc recursion with global state | a flatten helper | flatten helper reused by both functions, no mutation of inputs |
| Complexity | not stated | stated | stated with the reason (hashing, single pass) |
| Testing | none | runs the examples | adds an edge case of their own |

---

# Notebook 23 — Choosing complexity on evidence

✍️ Written answers: compare yours against the rubric; wording will differ.


### Reasoning questions

**1.** It is **inconclusive**. The interval excludes zero, so B is probably somewhat better. But its
lower end (+0.004) is below the MPID (+0.02), so the data do not show that the gain is large enough
to matter. For the product owner: "B is probably a little better, but we cannot show it is better by
enough to change outcomes; on this evidence it does not earn its extra cost."
*Common wrong answers:*
* "Better, because it excludes zero." This confuses detectable with important.
* "Equivalent." The interval reaches above +0.02, so it is not wholly inside the band.

**2.** If the MPID is chosen after seeing the results, it becomes a free parameter that can be set
to deliver the preferred conclusion. With an interval of [+0.03, +0.09], for example, choosing an
MPID of 0.025 lets you declare B "practically better". The MPID should come from the decision (what
change in outcome is worth acting on) and from someone who has not seen the numbers. This is the
same garden-of-forking-paths problem as tuning on the test set (w3d3).
*Wrong:* "So the result looks objective." That is a reason, but not the mechanism.

**3.** Right: no candidate off the front should be chosen, because each is beaten on every
objective by some candidate on the front. Wrong: the front does not make the remaining candidates
interchangeable. Choosing among them needs a preference (MPID, hard constraints, complexity
ranking), and the candidates differ in ways the objectives may not capture: retraining needs,
interpretability, dependencies.

**4.**
* The mean hides the tail: p95 and p99 are what hit timeouts.
* Warm-up calls (lazy imports, allocation, cold caches) are mixed into the sample.
* The loop measures a different workload: a hot loop on one host with no contention, no
  serialisation and no network. Batch size may differ from production, and thread oversubscription
  on a busy host can change the result by orders of magnitude (the worked example went from 3.5 ms
  to 8 s).
* Also acceptable: the clock used (`time.time` is not monotonic), and measuring a different object
  from the one deployed.

**5.**
* (a) The test set is for one look at the *chosen* model; choosing by test results turns it into
  selection data (w3d3).
* (b) The difference (0.017) is below the MPID of 0.05.
* (c) With 7 test experiments the interval for such a difference is very wide (w3d5), so the
  ordering could easily flip.
* (d) The choice also rests on costs and retraining needs, which the test score does not change.

**6.** `sys.getsizeof` returns the size of the Python object header, not of the objects it refers
to (arrays, trees, dictionaries). Serialise the deployed artifact the way it will be shipped and
measure the file (`model_size_bytes`). For memory at run time, measure resident memory after loading
it, for example with `tracemalloc` or the process RSS.

### Design choice: a model answer

The ordering ranks what is expensive to *own*, not what is expensive to compute. The isolation
forest is large and slow, but it retrains itself from the first 100 normal rows of every run:
nobody has to do anything, and its cost is mostly CPU, which is cheap at one sample per second. The
logistic model is tiny, but retraining it needs labelled faults. In maintenance these are the
scarcest data: each label comes from an incident someone investigated. Its behaviour also changes
whenever the fault mix in the labels changes, so every retrain needs a fresh validation like this
lesson's. The supervised model also brings a labelling pipeline, a training job and a model
registry entry, which the per-run detectors do not need. A defensible alternative ranks by run-time
cost (forest above logistic) when the deployment target is a constrained edge device. The point of
the exercise is that the ranking must be argued from the operational context and written down
before the results.

*Common weak answers:*
* Ranking by parameter count or file size alone.
* Not mentioning where retraining labels come from.

### Interview rep: rubric and worked answer

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Opens with the decision rule, not the numbers | no | partly | "we fixed an MPID and a complexity ranking before comparing" |
| Uses the interval correctly | quotes point estimates | mentions an interval | "+0.07 [+0.02, +0.13]: detectable, not shown to exceed +0.05" |
| Names costs beyond accuracy | none | one | labels for retraining, interpretability for the engineer, extra pipeline |
| Keeps the test set clean | uses test to argue | unclear | "the test set confirmed the chosen model once" |
| Says what would change it | nothing | vague | "15 more labelled faults and an interval wholly above +0.05" |
| Time | > 3 min or < 45 s | 2-3 min | 1-2 min |

*Worked answer (about 90 s).* "Before comparing, we fixed a minimum difference worth acting on,
+0.05 PR-AUC, and a complexity order, with models that need labelled faults to retrain at the
expensive end. On development data, with a paired bootstrap over experiments, the logistic model was
+0.07 better, but the interval went down to +0.02. So it was not shown to be better by enough to
justify needing labelled faults for every retrain, and the alarms would have been harder for the
engineer to interpret. The rule then says: take the simplest candidate not shown to be worse, which
was the flow-rate z-score. We looked at the test set once, for that model. (a) +0.07 is the point
estimate; the evidence is the interval. (b) I'd switch when we have about 15 more labelled faults
and the interval is wholly above +0.05, or if we meet a fault family that flow rate does not see."

---

# Notebook 24 — Project milestone 1: evaluation report

✍️ Written answers: compare yours against the rubric; wording will differ.


### Reasoning questions

**1.** You edit the manifest, for example to move an overlap group. `make evaluate` compares
`results.json` with its prerequisites: the tidy CSV and the code are unchanged, so make reports
nothing to do. The old report, built on the old split, remains. It carries the old manifest hash in
its Provenance section, but nobody compares hashes by eye. Later someone quotes the report as
describing the new split. The fix is to list `$(SPLITS)` as a prerequisite: every input that can
change an output must be a prerequisite.
*Wrong answers:*
* "make detects that the JSON content would change." It does not; it compares timestamps.
* "It errors." It does not; it silently does nothing.

**2.** A script can still compute numbers in the rendering step (a mean, a percentage, a ratio), or
read some values from another source. Those numbers cannot be traced to or diffed in the results
file. Requiring every shown number to be a stored value makes the results file the single source of
truth. You can then compare two versions of the evaluation by diffing JSON, and re-style the report
without any risk of changing a number.

**3.** Nothing reruns: `make` does not track variable values, so `results.json` is up to date by
timestamp and the report still shows 2000 replicates (stated in its Protocol table, which is the one
saving grace). To track parameters, write them to a stamp file, for example
`results/params.txt` containing `N_BOOT=... BURN_IN=... SEED=...`. Rewrite it only when its content
changes (compare first), and list it as a prerequisite of `results.json`. Alternatively, use a tool
that tracks content hashes (DVC, Snakemake).

**4.**
* Iterating over a `set`, whose order is arbitrary across processes for strings because of hash
  randomisation.
* A sort that is not stable or not total: ties in the sort key broken by input order that differs
  between runs, for example a dict built from a `groupby` without `sort=True`.

Also acceptable: a `sorted(..., key=...)` whose keys contain NaN. Fixes: sort with a total key (add
the name), and avoid iterating sets when building output.

**5.** In a separate, explicitly host-labelled artifact: the w4d5 decision memo, or a
`reports/benchmarks/<host>.json` produced by its own target, which is not part of the byte-identity
contract. Latency depends on the machine, its load and its thread settings (w4d5 saw 3.5 ms against
8 s). Inside the main report it would break reproducibility, and readers would take it as a
property of the model.

### Design choice: a model answer

Keep the stages.

* **Rebuild cost.** With intermediate files, make reruns only what is stale. Changing the report's
  wording takes a second instead of a full evaluation (about a minute here, hours on a large
  benchmark).
* **Reviewability.** `results.json` is a diffable record of every number. Comparing two evaluations
  is a JSON diff, and the traceability check (every table number appears in the JSON) is only
  possible with the file in between.
* **Diagnosis.** When something breaks, the stage boundary localises it. A wrong tidy table points to
  ingestion; right results with a wrong report point to rendering.

The "fewer moving parts" argument is real when stages are trivial, so do not split a five-line
script into three files. Here, though, each boundary carries information. The intermediates must be
build outputs (never edited, removed by `make clean`, git-ignored), or they become another source of
stale data.

*Weak answers* argue from code length alone, or keep the intermediates without saying how they are
kept fresh.

### Interview rep: rubric and worked answer

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Problem and stakeholder first | starts with models | brief | budget and who acts on alarms |
| Unit of independence | rows | "experiments" | experiments grouped by shared rows, 23 dev / 7 test clusters |
| Leakage prevention named | none | one | frozen split, burn-in calibration, dev-only choices, clock shortcut ruled out |
| Uncertainty | none | intervals mentioned | paired cluster bootstrap and Wilson, with what they omit |
| Result and decision | leaderboard | numbers | rule plus decision plus one test look |
| Reproducibility | none | "scripted" | one command, byte-identical, hashes |
| Time | > 6 min | 5-6 | 4-5 |

*Worked answer (about 4 minutes).*

"The goal was an alarm on a lab pump loop with at most one false alarm per eight hours. Each SKAB
file is one experiment, and some files share rows, so the independent unit is a group of
experiments: 23 clusters for development and 7 for test, frozen before any model work.

Every detector calibrates on the first 100 rows of a run, and those rows are excluded from scoring.
I also checked that elapsed time alone does not predict the label in my features. The protocol picks
operating points and the model on development data only, and looks at the test set once.

I compared four candidates with paired cluster-bootstrap intervals for PR-AUC against the simplest,
a single-sensor z-score, with a minimum practically important difference of 0.05 fixed in advance.
The supervised logistic model was +0.07, but its interval reached down to +0.02, so not shown to
matter. The isolation forest was shown worse. The rule took the simplest model. On test it caught 5
of 7 faults with no false alarms; with 7 events that recall interval runs from 0.36 to 0.92, and I
say so.

Misses were in valve1/8 and valve2/0. On development data the 'other' family is the weakest, with 3
of 12 detected at the strict budget. That is the next thing to work on.

All of it is one `make evaluate` from the raw files, and a clean rebuild is byte-identical; the
report carries the hashes of the manifest and the data."

---

# Week 4 review day — Review and catch-up (light)

✍️ Written answers: compare yours against the rubric; wording will differ.


Open only after all twelve questions have a written attempt. Each answer states what a "solid"
answer must contain, then common wrong answers and why they fail.

Aligned with the final Week 4 lessons on 2026-11-22. Every real-data number is copied from those
lessons' authoring runs on the frozen manifest v2 (7 test, 27 development experiments; test
prevalence 0.373). Numbers marked *(SYNTHETIC)* come from the lessons' synthetic illustrations.

### 1. Stationarity, departures, effective sample size

**Weakly stationary:** mean, variance and autocovariances do not depend on time. Forecasters and
control limits fitted on one stretch are valid on another only if that holds.

Departures and usual remedies (w4d1, 2.2), three of:

| Departure | Remedy |
|---|---|
| Trend (temperatures warming through a run) | difference, detrend, or a trend term |
| Level shift | often *is* the anomaly; otherwise re-baseline after a known change |
| Seasonality / machine cycle | seasonal differencing or seasonal terms |
| Variance change | model the scale (rolling sigma), transform |
| Regime / operating point | condition on the regime, or fit per regime |

The tension: the fault is a non-stationarity. A model that adapts quickly (naive forecast, short
rolling baseline) absorbs the fault into "normal" within a few samples; one that never adapts alarms
forever after a benign change. Adaptation speed is a design decision with a false-alarm cost on one
side and a missed-state cost on the other.

Effective sample size for the mean of AR(1): `n_eff = n(1 − φ)/(1 + φ)`; with `φ = 0.9`, 300 rows
are worth about **16** independent observations (w4d1, 2.1). Consequence: rows are not the unit, so
row bootstraps and shuffled folds are over-confident (w3d2, w3d5).

| Common wrong answer | Why it fails |
|---|---|
| "Stationary means constant" | A noisy, autocorrelated series can be stationary |
| "Standardise the whole recording and it becomes stationary" | Changes units, not the time-dependence; and uses the future |
| "300 rows, so the standard error is σ/√300" | Ignores autocorrelation; about four times too small here |

### 2. Naive versus AR residual; why the numbers

* **Naive** (`x̂_t = x_{t−1}`): the residual is the first difference. After a level shift `Δ` it is
  `Δ` at the step and back to noise one sample later. It detects *changes*, not *states*.
* **AR(p) with intercept**: the forecast pulls towards the fitted mean `μ = c/(1 − Σφ)`, so after the
  shift the residual keeps an offset of about `(1 − Σφ)Δ` for as long as the shift lasts. The more
  persistent the fitted process (`Σφ → 1`), the more it behaves like the naive forecaster.

On the 7 test experiments: the naive residual's PR-AUC **0.401** is at the no-skill floor **0.373**
(the test prevalence) and it detected 1 of 7 events: almost every row inside a fault looks normal to it,
because the fault is a sustained state. AR(2) scored **0.809** (6/7 events): it keeps part of the offset
for the whole fault. Forgetting the intercept is the classic error: the coefficients then absorb the
mean and drift towards a unit root, which turns AR back into a naive forecaster.

A lower forecast error can be a worse detector because one-step error is minimised by adapting fast,
and a forecaster that adapts fast forecasts the fault too. In figure 2 of w4d1 the AR model forecasts
the shifted series *worse* than naive, which is exactly why its residual detects the shift.
Forecasters here are judged by detection metrics on held-out experiments, never by RMSE.

| Common wrong answer | Why it fails |
|---|---|
| "Choose the forecaster with the lowest RMSE" | Optimises the wrong quantity |
| "The naive residual failed because of noise" | It failed by design: it cannot see a state |
| "AR(2) needs no intercept; I standardised first" | The fit data's mean is not the scored data's mean; the intercept carries the level |

### 3. CUSUM

```
S⁺_t = max(0, S⁺_{t−1} + z_t − k)      S⁻_t = max(0, S⁻_{t−1} − z_t − k)      alarm if max(S⁺, S⁻) > h
```

`z_t` are standardised residuals (divided by the one-step residual SD on the fit data, not the series
SD). `k` is the reference value (half the shift to detect fastest); `h` the decision interval. The floor
at zero forgets evidence *against* a shift. Delay after a shift of `δ` SDs ≈ `h / (δ − k)` samples,
good above `δ ≈ 1`; it breaks down at `δ = k` (simulated median 27 samples there) *(SYNTHETIC)*.

`ARL₀ ≈ 460` samples (simulated, `k = 0.5, h = 5`, independent standard-normal input; median 330)
means one false alarm every six to eight minutes at 1 Hz, and only if residuals are independent and
correctly standardised; autocorrelated residuals make it much worse. Chart parameters are meaningful
only next to an alarm budget.

On SKAB the detector (AR(2) residual) is unchanged; CUSUM changes the **operating point**: 3.3 false
alarms per hour instead of about 223, at the cost of 4/7 events instead of 6/7 and a median delay of
111 s instead of 2 s. Its point-level PR-AUC is lower (0.605), because point metrics reward flagging
early rows that the accumulation delays. Which is better is decided by the alert budget, not by PR-AUC.

| Common wrong answer | Why it fails |
|---|---|
| "CUSUM is a better detector than AR(2)" | Same residual; different trade-off between delay and false alarms |
| "ARL₀ 460 means it is safe" | At 1 Hz that is several false alarms per hour, and only under i.i.d. assumptions |
| "CUSUM detects any shift" | Shifts well below `k` accumulate very slowly |

### 4. PCA T² and Q

With standardised `x`, loadings `P` (`d × k`), component variances `λ_j`, scores `t = xP`:

* **T² = Σ_j t_j²/λ_j**: distance *inside* the retained subspace. Large when the row is extreme along
  directions normal data varies in (everything moving together, but too far).
* **Q = ‖x − xPPᵀ‖²**: squared distance *from* the subspace. Large when the usual relationships between
  sensors break. *(SYNTHETIC figure 1 of w4d2: point A has T² 7.0 above its limit 6.7 and Q 0.00; point
  B has T² 0.0 and Q 2.07 against a limit of 0.22.)*

Limits in the lab: **empirical 99th percentiles on the fit rows** (the F and χ² approximations assume
multivariate normality, which sensor data does not satisfy). `k`: start from the share of variance on
normal data, then choose by detection metrics on development folds (the lab chose variance share 0.8).
Too few components push normal variation into Q; too many absorb faults into the subspace.

On SKAB, **Q was the weakest detector on both protocols** (protocol A 0.626, protocol B 0.699). The
faults mostly move the operating point, inside the subspace where T² looks, rather than break sensor
relationships. That is a property of these faults, not of Q.

| Common wrong answer | Why it fails |
|---|---|
| "T² and Q carry the same information" | They measure orthogonal parts of the deviation |
| "Use reconstruction error only" | Misses large in-pattern excursions |
| "Keep 99 % of the variance" | Can retain the directions faults appear in; choose `k` by detection on development data |

### 5. Isolation forest

Random feature, random split between the node's min and max, recursively, on subsamples of `ψ` rows;
anomalies are isolated in few splits. Score `s(x) = 2^(−E[h(x)]/c(ψ))`; scikit-learn's `score_samples`
returns `−s`, so the lab negates it to make higher mean more anomalous.

`contamination` does **not** change the trees or the scores; it sets the cut-off used by `predict` so
that that share of the *training* rows is flagged. The worked example shows identical scores for
contamination 0.01, 0.05 and 0.2 while the share flagged moved from 9 % to 32 %. Setting it from the
test prevalence or the best test F1 is choosing a threshold with test labels; the lab uses the scores
and a threshold chosen on development data.

Weakness: axis-aligned splits isolate anomalies visible only as broken correlations (oblique
directions) slowly, unless a feature exposes them (residuals, ratios). Anomalies present in the
training sample look normal.

| Common wrong answer | Why it fails |
|---|---|
| "It measures distance to neighbours" | No distances are computed |
| "`contamination` sets sensitivity" | It moves a threshold on fixed scores |
| "It needs no labels" | It needs labels to evaluate and usually to choose normal training rows |

### 6. Protocol A versus protocol B; which framing

* **Protocol A** (frozen test set, all families on both sides): performance on *new experiments of
  fault mechanisms seen in training*.
* **Protocol B** (train on `valve1` + `valve2`, score the 12 `other` experiments, 8 independent
  clusters): performance on *a fault family never seen in training*.

Reading: GBT 0.920 → 0.636 and the flow-rate z-score 0.886 → 0.640 fall; isolation forest 0.831 →
0.783 and PCA T² 0.762 → 0.761 hold. The GBT learned what separates *valve* faults. On protocol A its
interval overlaps the flow-rate z and isolation forest, so even its win there is not established; on
B, eight clusters make the intervals wide, so the drop is a warning, not a measured size.

Labels support a **supervised model for the valve families** (many labelled experiments each), not for
mechanisms outside them. Defensible design: a supervised model plus a semi-supervised safety net,
with protocol B reported next to protocol A. Maintenance differs too: the GBT needs labelled faults of
every kind to stay good; semi-supervised detectors need a clean normal reference.

| Common wrong answer | Why it fails |
|---|---|
| "Ship the GBT, it has the best test score" | Protocol B reverses the ranking for unseen faults; and the A ranking is not established |
| "Protocol B proves the GBT is bad" | Eight clusters; wide intervals; it shows a risk, not a size |
| "Semi-supervised detectors need no labels" | Evaluation and the selection of normal rows use labels |

### 7. A fair neural comparison

Held equal (w4d3, 2.4): same FIT/VAL/TEST experiments with TEST read once; rows `t ≥ 100` scored for
everyone; the same per-experiment burn-in calibration; four configurations per family chosen on VAL
PR-AUC; early stopping on VAL loss only; the same metric and cluster-bootstrap interval; five seeds for
the neural model. **Not** equal, and to be said: the training loop's own settings (learning rate, batch,
optimiser, hidden size) were fixed, not tuned; a reviewer could argue it deserved more budget. The answer
is to report the budget, not to tune until it wins.

Conclusion: the classical Mahalanobis score (0.768) lies inside the neural seed range (0.682-0.837), and
the paired difference for the median-by-VAL seed, −0.057 [−0.194, +0.104], contains zero: **no evidence
that either is better under this protocol**. The flow-rate z-score (0.884) is ahead of the median neural
seed by 0.173 [0.035, 0.327], with the multiple-comparisons caveat of w3d5. Report all five seeds (or mean,
sd, range), the test interval for one fitted model, and the cost (3,658 parameters, PyTorch dependency,
about 6.5 versus 1.7 ms per 1,000 rows on the authoring host). The claim is narrow: one architecture, one
budget, 21 training experiments.

Seed 3 had the lowest VAL reconstruction loss (0.550) and the lowest TEST PR-AUC (0.682): reconstruction
loss is a training signal, not the detection metric. Select on the detection metric on VAL.

| Common wrong answer | Why it fails |
|---|---|
| "Best seed 0.837 > 0.768: neural wins" | Best of five chosen on test |
| "Mean 0.754 < 0.768: classical wins" | A 0.014 gap against a seed sd of 0.068 and 7 test experiments |
| "Fix the seed and one run is enough" | Reproducible is not representative; on CPU even thread count changed the result |

### 8. What a run records; identity; status; reproduce

Record (w4d4, 2.1): resolved configuration including seed; code version (commit with `-dirty`);
data fingerprint (SHA-256); environment (Python, libraries, platform, threads/device for numerically
sensitive work); metrics; completion status; artifacts.

**Run id** = first 12 hex of SHA-256 of the **canonical** JSON of the config (sorted keys). Without
canonical serialisation the same config built in a different key order hashes differently (the worked
example shows two hashes for one config). The seed is part of the identity.

**`status.json` last, atomically** (temporary file, then `os.replace`): a reader never mistakes a
half-finished run for a finished one; "metrics.json exists" is not a completion signal. Partial and
failed runs are cleared and retried; complete ones are immutable and skipped.

**Index derived from directories:** it is a cache. Deleting a bad run, copying runs from another
machine, or repairing a partial one is reflected automatically; a hand-maintained index drifts.

**Reproduce** must re-run the stored config and compare every metric within a tolerance stated in
advance. Comparing stored metrics with themselves, or with a cached copy, proves nothing. The lab's
isolation-forest run `0668c9c60359` reproduced with `max_abs_diff` 0.0.

| Common wrong answer | Why it fails |
|---|---|
| "Seed and commit hash are enough" | Not without config, data identity and environment |
| "The index CSV is the registry" | It is a view; the directories are the record |
| "Name runs by timestamp" | Re-running a sweep cannot skip completed work, and duplicates are invisible |

### 9. What a sweep may report

May appear: the search space and budget; development scores of every configuration (the 12-row table,
with `n`, mean, sd over seeds and excluded runs counted); the selection rule; the selected configuration.
In the lesson: 200-row burn-in beats 100 rows by about 0.025 for every shrinkage, shrinkage moves the
result by at most 0.005, and the isolation forest is about 0.08 below Mahalanobis.

0.735 is the maximum of noisy development estimates, so it is optimistic for its configuration
(the optimism of the maximum, w3d3); the honest estimate of the *procedure* needs nested validation or
the one test look of the frozen choice. Mechanically, the sweep task evaluates on development rows only
(`dev_pooled_pr_auc`, the same 24,642 rows `t ≥ 200` for every configuration so a longer burn-in is not
also an easier evaluation set); test metrics do not belong in sweep runs; a separate command scores the
frozen choice once.

| Common wrong answer | Why it fails |
|---|---|
| "Report the best of the 12 on test" | Selection on test |
| "Report all 12 test scores for transparency" | Invites choosing by them; the test set is then spent |
| "One seed per configuration is enough for isolation forest" | Seed sd ≈ 0.009 is comparable to the differences being compared |

### 10. MPID, interval readings, the decision

**MPID** (minimum practically important difference): the smallest improvement that would change what
the business does, fixed **before** results. For flowguard, +0.05 PR-AUC.

Readings of an interval for (candidate − reference), higher better: **better** (wholly above +MPID);
**worse** (wholly below −MPID); **equivalent** (wholly inside the band); **inconclusive** (anything else).

Logistic +0.069 [+0.022, +0.128]: it excludes zero but reaches inside the band, so **inconclusive**: a
detectable difference not shown to matter. No candidate is "better", so the rule chooses the simplest
candidate not shown worse, per the complexity ranking fixed in advance: **flow-rate |z|** (one sensor,
no training). The supervised model ranks last on complexity because retraining needs new labelled
faults, the scarcest input in maintenance. The isolation forest was the only candidate shown to differ,
and it was worse (−0.203 [−0.299, −0.120]).

Do **not** switch after the test look: logistic 0.901 vs 0.884 is one look at 7 experiments; the choice
is made on development data and the test set confirms the chosen model once (choosing by test is
selection on test, w3d3). The difference is below the MPID; on test the paired interval for logistic minus
flow-rate was +0.016 [−0.003, +0.049] (w3d5). The chosen model caught 5/7 test events (Wilson 95 %
[0.36, 0.92]) with no false alarms at its frozen operating point. Record logistic as the challenger and
state what evidence would change the decision.

| Common wrong answer | Why it fails |
|---|---|
| "Interval excludes zero, so logistic is better" | Not shown to exceed the MPID |
| "Inconclusive means equivalent" | Equivalent needs the whole interval inside the band |
| "Test says logistic is higher, switch" | Selection on the test set; and smaller than the MPID |

### 11. What a regenerated report guarantees

Guarantees (w4d6, 2.1): one command rebuilds every number, table and figure from raw data and the frozen
manifest; nothing typed by hand (the render step formats, it does not compute; every number in the report
occurs in `results.json`); a rebuild from the same inputs gives the **same bytes**, checkable with
`sha256sum`; the report states its inputs (hashes, code version, library versions).

Does **not** guarantee correctness: a leak or a wrong split is reproduced faithfully every time.

No timestamp, because it makes every rebuild unique and byte identity uncheckable (when it ran belongs in
a log). No latency, because it depends on the host; it lives in the separately labelled w4d5 memo. `make`
tracks **timestamps, not contents or variable values**: changing `N_BOOT` on the command line does not
make results stale (the optional stamp file fixes that), and a checkout that touches a file without
changing it triggers a rebuild anyway.

Sections besides results (three of): problem, data, protocol (split version, resampling unit, MPID,
"development chooses, test confirms"), error analysis, decision, limitations, provenance.

| Common wrong answer | Why it fails |
|---|---|
| "Reproducible means correct" | It means regenerable |
| "Add a timestamp for provenance" | Destroys byte identity; record input hashes instead |
| "`make clean` should delete `data/`" | Raw data is an input, not a build output |

### 12. Bootstrap over rows (delayed question from w3d5)

Full key: answer 9 of `solutions/labs/w3d7_review/retrieval_answers.md`. In brief: rows within an
experiment are strongly autocorrelated (answer 1: 300 rows at `φ = 0.9` are worth about 16), so a row
bootstrap is far too narrow (3-7 times on SKAB). Resample the **7 test experiments** with replacement and
recompute the metric each time; for comparisons, resample the same experiments for both models (paired).
Doubts: only 1,716 distinct resamples; each experiment missing from about 34 % of them; in w3d5's
simulation nominal 95 % percentile intervals covered about 87-88 % with 7-9 clusters. Report the unit and
`n` and treat the interval as a lower bound on the honest uncertainty.

---

# Notebook 25 — Research experimentation versus production inference

✍️ Written answers: compare yours against the rubric; wording will differ.


### Reasoning questions

**1. 1.4e-14 on scores near 8.** Not skew. A relative difference of about 2e-15 is one or two units in
the last place of a double. It came from reading the CSV with pandas' default float parser, which is
not round-trip exact: 2,017 of 6,659 scores changed in the last digit, the largest by a relative
5.9e-16. With `float_precision="round_trip"` the difference is exactly 0. It would become skew if
any alarm decision changed (a score within 1e-14 of the threshold, which is possible but has to be
checked), or if the difference grew with the score in a way that pointed to a different formula, for
example a constant factor of sqrt(100/99) from ddof=1.
*Common incorrect answers.* "Any difference is skew" turns floating-point order of operations into
false alarms in CI. "It is tiny, so ignore it" with no tolerance and no decision check is how a
0.5 % ddof skew also gets ignored.

**2. Per-batch standardisation.** The detector measures distance from the run's own start-up level.
Standardising by the batch puts the fault inside the reference: the mean moves towards the faulty
level and the standard deviation grows. In the lesson's synthetic run, a 6-SD step gives a median score of
5.67 calibrated on burn-in, against 0.93 calibrated on the whole run. Maximally wrong: a batch made
entirely of faulty rows (a late chunk of a long fault). Its own z-scores are noise around 0, so the
detector reports health during the fault.
*Common incorrect answer.* "It only removes drift." It removes the signal the detector exists to see.

**3. Column order.** For selecting by name: every column is named, and name-based selection is immune
to order. For refusing: a producer that changed the order changed its export code, so other
assumptions may have changed too (units, sensor mapping). A loud refusal is cheaper than a quiet
assumption. Selecting by name is safe only if every consumer downstream also works by name. Ship
the strict version with a versioned schema, and relax it only when the producer is under the same
team's control and has its own contract tests. The real danger is matching by *position*, which is
what the mutant did.

**4. Per-run errors.** A short run is a property of one run's data, not of the file's format, and the
other runs' predictions are still correct and needed. Stopping the batch would let one truncated
upload silence every machine. Stop everything when the failure means the input cannot be trusted as
a whole: a schema error, a file from the wrong plant, or more than a set fraction of runs failing,
which suggests an upstream outage rather than bad runs.

**5. Refusing to overwrite.** It prevents silently replacing yesterday's predictions (which may
already have been acted on or audited) with predictions for a different input, for example a
scheduler retry that points at the wrong date. Cost: a re-run with a corrected input needs
`--force` or a new output directory. That is a deliberate step, and the manifest records what
replaced what.

### Design-choice explanation: model answer

The operating point is the one decision made with labels. It is only valid for the exact function
that produced the scores it was chosen on. If it were chosen with the evaluation code and served with
another implementation, the two would agree today and could diverge after any refactor of either. The
threshold would then be applied to a different score than the one it was tuned on. Choosing it with
`Detector.score_batch` makes the served object the evaluated object. The parity test keeps the w4d5
code honest: it scores the same synthetic runs through `flowguard.detectors` and through `Detector`
and requires agreement within 1e-12 and identical alarms. That test runs in CI, so neither path can
change alone.

### Interview rep rubric (debugging: fewer alerts than offline)

| Level | What the answer contains |
|---|---|
| Strong | Starts from "the served function or the served data differs from the evaluated one", not from "the model is bad". In order: (1) replay a sample of logged production inputs through the offline pipeline and compare scores row by row (parity; finds skew); (2) compare the input distributions and the score distribution in production against the evaluation set (finds population shift or a broken feature: constant, all-null, unit change); (3) check what threshold and model version are actually loaded (config skew). Notes that "alerts are good" means precision is fine, so the score is probably shrunk or shifted, not random. Mentions feature order, defaults for missing values, per-batch normalisation and stale reference statistics as usual causes. |
| Adequate | Proposes comparing offline and online scores and checking feature distributions, without an order of checks or a hypothesis about what "fewer but good alerts" implies. |
| Weak | Retrains the model, lowers the threshold, or blames concept drift before checking that the served function is the evaluated one. |

Worked answer, abridged. "Fewer alerts with good precision means production scores are shrunk relative
to offline ones. I'd take yesterday's logged inputs and score them with the offline pipeline. If the
scores differ row by row, it's skew. Then I'd diff the feature vectors and find the first feature
that differs: usually a default for missing values, a re-implemented scaler, or a feature computed
over the request batch instead of the user's history. If the scores agree, the inputs moved, and I
compare feature distributions against the evaluation period. Last, I'd confirm the threshold and
model version the service actually loaded. Whatever it is, the fix includes a parity test in CI."

---

# Notebook 26 — Model artifacts, metadata and versioning

✍️ Written answers: compare yours against the rubric; wording will differ.


### Reasoning questions

**1. "The bucket is private."** (a) Access control protects against outsiders, not against a
compromised CI job, a mistaken upload from another project, or a colleague's laptop with write access.
Any of them puts code on every machine that loads the model. (b) Even untampered, a pickle couples
the artifact to the exact class layout and library versions of the code that wrote it. A refactor or
library upgrade breaks loading or, worse, changes behaviour silently. Acceptable: a short-lived cache
written and read by the same process and version, never shared, or a library whose format is a pickle
(some torch checkpoints) loaded with the library's restricted loader (`torch.load(weights_only=True)`)
and only from your own pipeline.
*Common incorrect answer.* "Pickle is fine if you checksum it." A checksum proves the bytes are the
ones that were saved, not that what was saved is harmless.

**2. Checksums next to the files.** They protect against *accidental* change: partial copies, sync
conflicts, a hand edit, bit rot, a file added by a well-meaning script. Against a deliberate attacker
they protect nothing, since the attacker rewrites them. That is what the `rewrite_checksums` helper
in the checks does. Against tampering, add a signature over `checksums.json` with a key the
attacker does not have (e.g. Sigstore/cosign, GPG), or keep the digests in a separate system the
attacker cannot write (the registry database, an append-only log), and verify against that.

**3. Immutability.** Predictions, audit logs, evaluation reports and incident reviews record "made by
flowguard-flowrate 1.0.0". If 1.0.0 can change, every such record silently refers to a different
function, and rollback to 1.0.0 may not restore what was running before. The pointer answers "what
is live now"; the immutable version answers "what was live then". Rollback is then a one-line pointer
change to a known artifact.

**4. Format vs model version.** The bundle *format* describes how files are laid out and interpreted.
Adding a field that old loaders ignore is a backwards-compatible format change. Either keep
`format_version` 1 and document the optional field, or adopt `MAJOR.MINOR` for the format and bump
MINOR, so old loaders still accept it and new ones can rely on it. A field that changes meaning
requires a MAJOR format bump, so old loaders refuse. The model version (1.0.0) changes only if the
model changes: a re-save with identical scores is at most a PATCH.

**5. Cost of the safe format.** About 2.2 KB and 0.2 ms per load. That matters only if models are
loaded per request (never do that; load once at start-up) or if thousands of per-entity models are
loaded in a loop. Then batch the loads, or keep weights in one array file with an index, but still
without pickle. For a service that loads at start-up, the cost is irrelevant.

### Design-choice explanation: model answer

The logistic candidate's state is 16 coefficients and an intercept. Together with the calibration
rule, the clip and the feature layout, they are the whole decision function. Storing exactly that:

* makes loading incapable of running code;
* makes the artifact independent of scikit-learn's internal object layout, so a library upgrade
  cannot break loading;
* lets the loader check the feature layout by name, which `joblib.dump` would not record;
* makes the artifact readable in a diff.

The cost is a 30-line loader that re-implements `decision_function`, plus a parity test against the
trained object (identical to 0 on the real test runs). For a model whose state is a large tree
ensemble or a neural network, re-implementing inference is error-prone. There I would use a
restricted, inspectable format (skops for scikit-learn, `state_dict` + `torch.load(weights_only=True)`,
or ONNX for a cross-runtime graph), pin the training library version, and keep the same checksums,
format version and parity test.

### Interview rep rubric (system design: model registry)

| Level | What the answer contains |
|---|---|
| Strong | A registered model = immutable versioned artifact (weights + preprocessing state + threshold + input schema + model card with metrics and intervals + training data hash + code commit + library versions), checksummed and ideally signed. A registry service or bucket layout `name/version/`, metadata in a database, aliases or stages (`current`/`production`, `staging`) as mutable pointers. Services resolve the alias at start-up (or on a signal), log the resolved version with every prediction, and expose it on a health endpoint. Promotion goes through gates: offline evaluation against the current model on frozen data, then shadow or canary. Rollback = repoint the alias, with no rebuild. Retraining writes a new version and never overwrites. Lineage: the version links to the data snapshot and code commit, so "which model made prediction X" is a log lookup. Mentions access control and who may promote. |
| Adequate | Versioned artifacts and a "latest" pointer, rollback by pointer, but no input schema or lineage in the artifact, or no logging of the version per prediction. |
| Weak | "Save the model to S3 with a timestamp and load the newest one": no immutability, no promotion step, no way to answer the audit question. |

Worked answer, abridged. "Every training run produces a bundle: weights, preprocessing state,
threshold, input schema, model card, data and code hashes. CI registers it under `name/version` with
checksums and a signature, and it is never overwritten. Promotion moves an alias after an offline
comparison with the current model and a shadow period; rollback moves it back. Services resolve the
alias at start-up, refuse a bundle whose schema or format they do not support, and log the version with
each prediction. A month later, the log gives the version and the version gives everything."

---

# Notebook 27 — Online inference on streams: state, warm-up and parity

✍️ Written answers: compare yours against the rubric; wording will differ.


### 1. Pressure in pascals, `n`, `Σx`, `Σx²`

`μ/σ ≈ 1e5 / 3 ≈ 3.3e4`, so `(μ/σ)² ≈ 1.1e9` and the lower bound `ε(μ/σ)² ≈ 1.2e-7`. Summing 10,000
values adds accumulated rounding: a simulation (20 draws of 10,000 SYNTHETIC samples, mean 1e5, SD 3,
run while authoring this answer) gave a median relative error of 3.0e-6 and a maximum of 1.3e-5. The SD
is off by about half of that, so z-scores are off by ~1e-6 relative: for threshold 7 an alarm decision
changes only if a score lies within ~1e-5 of 7. **For detection it does not matter; for a parity test
with tolerance 1e-9 it fails**, and the fix (Welford, or shift by the first sample) costs nothing.

*Common wrong answers.* "float64 has 16 digits, so no problem" (ignores cancellation). "The error is
1e-16" (confuses machine epsilon with the error of a difference of large numbers).

### 2. Returning 0.0 during warm-up

* Every consumer reads it as "measured and perfectly normal": a monthly mean of scores, an SLO such as
  "fraction of samples with score < 3", or a model-monitoring drift statistic (week 7) is biased toward
  normal by every restart.
* An alert rule `score < 0.5 for 10 min -> sensor stuck` fires on every warm-up. More generally,
  downstream code cannot tell "no information" from "good news", so no consumer can handle warm-up
  correctly even if it wants to.

The honest representation is `null` plus a status, so a dashboard can draw a gap and label it.

### 3. Rejections must not change the state

If the Welford update ran before the out-of-order check, the late value would be inside `mean` and
`M2` although the caller was told it was rejected. The client then (correctly) re-sends it later in the
right order, and it is counted twice; or the client gives up and the state contains a value no record
says was accepted. Either way the scores no longer equal `score_batch` of any sequence of accepted
samples, and nobody can reproduce them. The general rule: validate everything, then mutate.

### 4. Gap reset and parity

The reset policy is not wrong; it implements a different batch function: "split the run at gaps longer
than `max_gap_s` and score each segment with `score_batch`". Parity must be stated against *that*
function (the checks test exactly this). The point is that every streaming policy has a batch
definition, and that definition is what you evaluate offline. If offline evaluation used
`score_batch(run)` and production uses reset, the offline numbers describe a different system.

### 5. Score parity vs decision parity

No. A score within the tolerance of the threshold can fall on different sides in the two paths. Test
it directly: compare the boolean exceedances as well as the scores, and report the smallest distance of
any score to the threshold (0.036 on the real replay, so no decision can differ there). If decisions
must match exactly, use the same arithmetic in both paths (one code path, as `hysteresis_batch` does in
the challenge) rather than two implementations.

### 6. Restart during the burn-in

* **No snapshot**: the new process starts a fresh burn-in at sample 61. Its `mu`/`sigma` come from
  samples 61-160, scores start at 161, and they differ from batch for the whole run. If a fault starts
  around sample 120, it is absorbed into the calibration and may never be detected.
* **Snapshot with only `mu`/`sigma`**: both are `None` at sample 60, so the restored scorer has no
  accumulators and restarts the burn-in from zero: the same failure as no snapshot, but with the false
  confidence of "we checkpoint". (This is the `restore_restarts_burn_in` mutant.)

### Design choice: duplicate policy (model answer)

Under at-least-once delivery a client that times out re-sends; it cannot know whether the first copy
arrived. An identical `(timestamp, value)` is therefore expected traffic, and answering it with the
previous result makes the operation idempotent: the state is the same whether the message arrived once
or five times, and the client gets the answer it would have got. A different value at the same
timestamp is not a retry but a contradiction (two writers, a clock problem, a corrupted message); the
service cannot know which is right, so it refuses and says so, which lets the client or an operator
investigate. "Last write wins" would silently change history: the burn-in or a past score would no
longer correspond to the data the client believes it sent, and two replicas could diverge depending on
arrival order. "Always error" is safe for the state but turns every network hiccup into a client error,
pushing every client to implement its own deduplication, usually inconsistently. The chosen policy puts
idempotency in one place, the server, and keeps errors for real contradictions.

### Rubric for the interview rep

| Level | Evidence |
|---|---|
| Strong | ring buffer for eviction + sorted structure (bisect) or two heaps with lazy deletion; correct even-`w` median; `None` before `w` values; states O(w) memory and O(w) (bisect/list) or O(log w) (heaps) time per push; tests compare with `numpy.median` on random data **with ties** and check the first `w-1` outputs |
| Adequate | correct but recomputes `sorted(window)` on every push (O(w log w)), says so, tests only a hand-made example |
| Weak | upper median for even `w`; removes the wrong element when values repeat; no tests |

Reference: `solutions/labs/w5d3_online_inference/interview_rep/sliding_median.py` and its tests
(`python -m pytest solutions/labs/w5d3_online_inference/interview_rep -q`: 11 passed). An
upper-median version fails 2 of them.

---

# Notebook 28 — FastAPI I: endpoints, schemas and input validation

✍️ Written answers: compare yours against the rubric; wording will differ.


### 1. `"flow_rate": NaN`, from bytes to response

Uvicorn passes the body to FastAPI, which parses it with Python's `json` module; that module accepts
the non-standard token `NaN` and produces `float("nan")`. Pydantic validates the `Sample`: with
`allow_inf_nan=False` it records an error of type `finite_number` at `["body", "samples", i,
"flow_rate"]`. FastAPI raises `RequestValidationError`; the handler builds the 422 body with
`code="validation_error"` and the details; the middleware adds the request id header. The endpoint
never runs.

Without range limits and without `allow_inf_nan=False`, NaN passes validation, `score_batch` raises
`ValueError("flow_rate contains missing or non-finite values")` (the detector's own guard), and the
client gets a 500 for what is the client's error. Without that guard in the detector, a NaN in the
burn-in would make `mu` NaN and every score of the run NaN, and serialising a NaN score fails (JSON
has no NaN): a 500 again, or a silently wrong answer in other stacks. Each layer protects the next.

*Common wrong answers.* "JSON cannot contain NaN, so it cannot happen": the standard forbids it, the
parser accepts it. "The range check already rejects it": it does, but with the misleading type
`less_than_equal`, and only for fields that have a range.

### 2. Non-increasing timestamps: 400 or 422?

In this design the schema describes one sample at a time; ordering is a property of the list as a
whole, checked by the endpoint after validation, so it is reported as a domain error (400,
`invalid_sequence`) with the offending indices. It would legitimately be a 422 if the ordering rule
were part of the schema, e.g. a pydantic `model_validator` on `PredictRequest`: then it is one more
schema constraint, appears in the same error list as field errors, and arguably documents itself
better. Both are defensible; what matters is consistency and that the client can find the offending
sample from the response.

### 3. `/healthz` 200, `/readyz` 503

The process is alive but cannot serve: the orchestrator should **not route traffic** to it (take it out
of the load balancer) and **not restart** it immediately (the model may still be loading, or the
problem is the bundle, which a restart does not fix; repeated restarts just hide the cause). If
`/healthz` were used for readiness, traffic would go to an instance that answers 503 to every
prediction; if `/readyz` were used for liveness, a missing bundle would cause a restart loop.

### 4. `async def` and a slow `/healthz`

An `async def` endpoint runs on the event loop. `score_batch` is CPU-bound and never awaits, so while
it runs no other request on that worker is served, `/healthz` included; under load the loop is busy
most of the time and every request queues. A plain `def` endpoint is run in a thread pool, so the
loop stays free (the GIL still limits parallel CPU work within one process; more workers or processes
scale that). The FastAPI documentation states the thread-pool behaviour for `def` path operations.

### 5. `flow_rate = 300`

The API accepts it: 300 L/min is physically possible for some pump, so it is not a broken input. The
detector scores it: with a burn-in mean near 32 and SD near 0.5, the |z| is in the hundreds, far above
the threshold, so it alarms. That is the right division: the API rejects impossible or mis-scaled
values (negative flow, 9,999, NaN), the detector judges plausible values, and monitoring (week 7)
notices that inputs have moved outside the training range. Putting the training range into the schema
would turn every real fault into a 422 and hide it from the detector.

### 6. Request ids

The customer quotes the request id from the response body or header; the server logs every request and
every exception with the same id (`logger.exception(..., request_id)`), so one search finds the
traceback, the input size, the model version and the timing. For it to work the id must be in the
response (body and header), in every log line of that request, and logs must be kept and searchable.
Accepting a client-provided id (validated) lets the id span several services.

### Design choice: start without a model rather than fail fast (model answer)

Starting without a model keeps the process observable: `/healthz` answers, `/readyz` explains (503 and
a log line naming the bundle problem), and `/version` shows what is deployed, so an operator can see
*why* the instance is useless instead of watching it crash-loop. It also supports deployments where
the model arrives after the process (mounted later, downloaded on start) and keeps the readiness
semantics honest: not ready, not dead. Its risk is an instance that never becomes ready and nobody
notices; readiness probes and alerts on "not ready for N minutes" cover that.

The strongest argument for fail fast: a service without a model has no purpose, and an immediate,
loud failure at deploy time (the new version never becomes healthy, the rollout stops) is the safest
signal, with no chance of partially serving. Choose fail fast when the model is baked into the image,
there is no legitimate "loading later" state, and the deployment system treats a crashing new version
as a failed rollout and keeps the old one. In this course the model lives next to the code in a
bundle, so either works; the lab uses the observable variant because it teaches readiness.

### Interview rep: rubric and model answer

| Level | Evidence |
|---|---|
| Strong | (a) request: transaction id, amount + currency, merchant and card identifiers (tokenised), timestamp with timezone, channel; schema rejects missing, non-finite, negative amounts, unknown currencies, extra fields, oversize batches. (b) response: score, decision or threshold version, model version, request id, possibly reason codes. (c) 200; 422 schema; 400 domain (e.g. timestamp in the future beyond tolerance); 409 for a transaction id already scored with different content; 429 rate limit with Retry-After; 503 not ready, retry elsewhere; 500 report with request id. (d) idempotency key = transaction id: same content -> return the stored previous answer; different content -> 409 |
| Adequate | sensible fields and codes, idempotency mentioned without a mechanism |
| Weak | "return the score"; status codes 200/500 only; duplicates scored twice (and possibly counted twice in velocity features) |

Model answer, (d) in particular: a retried transaction must not be scored as a new one, because
velocity features ("transactions in the last hour") would count it twice and raise the next score.
Store `(transaction_id -> content hash, response)` for a retention window; a retry with the same hash
gets the stored response; a different hash gets 409.

---

# Notebook 29 — FastAPI II: API tests, integration tests and model lifecycle

✍️ Written answers: compare yours against the rubric; wording will differ.


### 1. 95 % coverage, 7 of 12 defects killed

Coverage counts lines *executed*; a defect is killed only when an *assertion* depends on the line's
result. A status-code-only suite executes the scoring, threshold and response-building lines on
every 200 request, so coverage is high, but it never looks at the numbers: signed scores, a strict
threshold, the sample std, a missing model version and the concurrency race all leave the status at
200 (Figure 2: 7/12). Two kinds of assertion close the gap: **content assertions** (exact expected
scores, flags, version for constructed inputs, including a negative value, a value exactly at the
threshold, and a burn-in where ddof matters) and a **concurrency assertion** (many distinct requests
in parallel, each response matching its own request).

*Common wrong answer:* "add more tests". More tests of the same kind (more status codes) do not kill
content defects.

### 2. TestClient without `with`

The lifespan (startup and shutdown) runs only when `TestClient` is used as a context manager. Without
`with`, `create_app` has built the routes but never loaded the bundle, so `app.state.model` is `None`:
exactly the state of a real process between "started" and "ready". That makes it a free, deterministic
test of the readiness contract: `/readyz` must be 503 in that state. The pitfall is writing *other*
tests without `with` and then concluding the service is broken (or, worse, adjusting expectations).

### 3. 500 instead of 422 for NaN

Client: 422 means "your request is invalid; do not retry it unchanged"; 500 means "server fault; a
retry may succeed". A client with retry-on-5xx will resend the same poisoned request several times,
multiplying load and delaying its own error handling. Operators: 5xx responses count against the
service's error budget and page the on-call engineer (w7d1); bad client input should not page anyone.
Also, the 500 here comes from a second failure (serialising NaN), which hides the first one in the logs.

### 4. Race test passes 1 run in 50

The test is not wrong; a passing concurrency test is weak evidence, a failing one is strong evidence.
To make it more sensitive: more requests, more threads, distinct values per request, and keep the
per-request work small so requests overlap. But races are best removed by design: the review checklist
should flag any write to module-level, app-level or model-level state inside a request handler, and
any cache must be keyed by request content and safe for concurrent use (or per request).

*Common wrong answer:* "mark it flaky and rerun". That hides the 1-in-50 production failure the test
is reporting.

### 5. ddof=1 is a defect

The contract is training/serving parity: the threshold was chosen in w4d5 on scores computed with the
population std (ddof 0). The sample std is larger by sqrt(n/(n-1)), so served scores are smaller than
training scores and the alert threshold silently becomes less sensitive. The difference is largest
when n is small: with two burn-in values it is a factor sqrt(2) = 1.414 (burn-in `[0, 2]`: score 3 vs
2.12), with 100 values about 0.5 %, which a loose tolerance might not see. Which test caught it: the
test with burn-in `[0.0, 2.0]` asserting score 3.0 for value 4.0 (`test_population_std_is_used`).

### 6. v1 -> v2

Breaking: `site_id` newly required (every v1 request gets 422); `scores` renamed to `score` (a removed
response field; v1 clients read a missing key); `burn_in` `maxItems` 3600 -> 600 (v1 requests with long
calibrations now get 422). Compatible: `explain` (optional, defaults to the old behaviour), `latency_ms`
(new response field; clients ignore unknown fields), `GET /sites` (new endpoint), `version` changes.

`T -> T | None`: in a request the server now accepts *more* (old clients never send `null`, so they are
unaffected); in a response the server may now *return* `null`, which an old client does not expect
(a `float(value)` call fails). Compatibility is about what the other side sends or reads.

### Design choice: start degraded vs crash

**For degraded start:** the process stays observable: `/healthz` and `/readyz` explain the failure
(`reason`), logs and metrics keep flowing, and the orchestrator simply does not route traffic to an
unready instance. In a rolling deployment the old version keeps serving; the new one sits unready and
the rollout stalls visibly instead of crash-looping. It also allows loading a model later (hot reload)
without restarting the process.

**For crashing:** a missing or corrupt bundle is a deployment error that will not fix itself; failing
fast makes the deploy fail immediately and loudly, and avoids a fleet of processes that look alive
but never serve. A degraded instance that nobody alerts on is worse than a crash.

**Setting decides:** with an orchestrator that uses readiness probes, alerts on "unready for > N
minutes" and does rolling updates (Kubernetes, ECS with health checks), degraded start is better. With
a plain process supervisor, no readiness checks, or a batch job, crashing is better, because nothing
would ever notice the unready state.

### Interview rep: the flaky suite

**Hypotheses, cheapest first.** (1) Order dependence through shared state: run the failing test alone
(`-k scores`): it passes, so another test changes something it relies on. (2) A timing issue in the
lifespan: rerun the single test several times; it always passes, so timing is unlikely.

**Cause.** `BUNDLE` is created once at import time in a module-level temporary directory and shared by
both tests. `test_tampered_bundle_is_not_ready` edits `model.json` in place, so every later test loads
a bundle whose checksum no longer matches: the service (correctly) refuses it and `/predict` answers
503. Alone, `test_scores` sees the original bundle and passes. (Failure observed in the authoring run:
`assert 503 == 200`.)

**Fix.** A fixture that builds a fresh bundle in `tmp_path` per test
(`solutions/labs/w5d5_api_testing/interview_rep/test_flaky_fixed.py`, 2 passed). Do not "fix" it by
reordering tests or by restoring the file at the end of the tampering test: the next failure mode
(an exception before the restore) would bring the flakiness back.

**General rule.** Tests must not share mutable state; each test creates what it changes. **Safeguards:**
run tests in random order with a plugin such as `pytest-randomly` (not installed or tested here; named
from memory),
run each test file in isolation in CI occasionally, and avoid module-level setup that writes files.

### Rubric notes

A level-3 answer to question 4 separates *detection* (the test) from *prevention* (design and review).
A level-3 debugging narrative states hypotheses before running anything, uses `-k` to bisect, and
names a rule that would have prevented the bug, not only the fix.

---

# Notebook 30 — Project milestone 2: packaged inference + API

✍️ Written answers: compare yours against the rubric; wording will differ.


### 1. Why three-way parity

Two paths that share code agree even when the shared code is wrong. Example (the
`batch_global_burn_in` mutant): `score_experiments` calibrates every experiment on the first 100 rows of
the *whole table* instead of its own first 100 rows. `experiment_scores` calls `score_experiments`, so
evaluation and batch agree to the last bit; the report and the nightly batch job are both wrong in the
same way. The API receives a per-experiment burn-in from the client and computes the correct score, so
only a comparison that includes the API sees the difference. Comparing all three (or each path against
an independent reference) closes this gap.

*Common wrong answer:* "two-way is enough if the tests are good". Unit tests of the shared function with
a single experiment cannot see a per-experiment selection bug either.

### 2. Tolerance and the CSV round trip

The checks use an absolute tolerance of 1e-9 on scores of order 1-100; any real skew (ddof: 0.5 % at
n = 100) is many orders larger, while representation noise is about 1e-14. On the real data, reading the
batch CSV with pandas' default float parser gave differences up to 5.7e-14 on 20,708 of 46,806 rows even
though the file holds 17 significant digits; `float_precision="round_trip"` made them exactly 0. Either
choose a tolerance far above representation noise and far below meaningful skew, or make the round trip
exact and compare exactly; know which you are doing.

### 3. The manifest hash in the bundle

It answers "was this model built from the same split, and hence the same development data and the same
untouched test set, as the evaluation report?" The milestone-1 report prints `a9f4e243...5314`; the
bundle records the same value. Reviewers use it to accept the release; an on-call engineer or auditor
uses it months later to tie the deployed artifact to its evidence; the team uses it to notice that a
rebuilt model was silently built from an edited manifest.

### 4. Chunking

The score of each value depends only on that value and on the burn-in statistics (mean, population
std); values do not interact. Sending the same burn-in with every chunk therefore gives exactly the
batch scores (verified: maximum difference 0.0 on all 35 experiments). Chunking breaks for any model
with state across values: rolling-window features, AR residuals, CUSUM, a recurrent network, or
event post-processing (`min_duration`, `merge_gap`). There the client must send overlapping context or
the server must keep per-stream state (w5d3, streaming scorer), and parity must be tested at chunk
boundaries.

### 5. Three versions

* **Package** (semantic version of the code): a new CLI subcommand or a bug fix in the loader -> 0.6.0 to
  0.6.1 or 0.7.0; the model and API schema do not change.
* **API schema** (`flowguard-api/1`): renaming `scores` or making a new field required -> `flowguard-api/2`,
  served alongside v1 (w5d5 policy); the model can stay the same.
* **Model** (`flowrate-z-2026.11`): a new threshold for a stricter alert budget -> new model version; code
  and API unchanged.

### Design choice

**For packaging a reviewed configuration:** the threshold is a decision with evidence (w4d5 memo,
milestone-1 report); rebuilding should reproduce that decision, not make a new one silently. Builds are
fast and deterministic, and a reviewer approves one number. Provenance must then record the config file
and its hash, and the manifest hash that links it to the report.

**For re-choosing at build time:** the threshold is a function of data and the alert budget; computing
it in the build keeps code, data and decision in one reproducible step, and a data update produces an
updated threshold without hand edits. Provenance must then record everything the choice depended on:
manifest hash, a hash of the development data, the alert budget, the selection rule and code version,
and the chosen value, and the build must fail if the chosen value differs from the reviewed one without
an explicit approval.

**A good answer** says the choice depends on how often the data changes and who must approve a new
operating point, and notes that in both cases the evaluation report must be regenerated from the same
artifact.

### Interview rep: checklist for a strong answer

1. Client sends `POST /predict` with `burn_in` and `values` (JSON); uvicorn passes it to the ASGI app.
2. pydantic validates: types, finite numbers, sizes, no unknown fields; invalid -> 422 with
   `{loc, msg, type}`, nothing echoed.
3. The endpoint checks the model is loaded (else 503) and the batch size (else 413).
4. The model was loaded once at startup from a bundle whose checksums were verified; `/readyz` reported
   ready only after that.
5. `ZScoreModel.score` computes |x - mean(burn_in)| / population std; flags are score >= threshold 7.24.
6. Response: model version, threshold, one score and flag per value.
7. **How I know it matches the report:** the same function computes evaluation, batch and API scores; a
   parity test runs on every change; on the real data the three agree exactly over 46,806 rows; the bundle
   records the split-manifest hash printed in the report.
8. Limits: it trusts the client's burn-in to be normal operation; point flags, not events (post-processing
   is not in the API); seven test experiments.

Points 1-6 alone describe a working API; point 7 is what distinguishes an engineer who has thought about
training/serving skew.

---

# Week 5 review day — Review and catch-up (light)

✍️ Written answers: compare yours against the rubric; wording will differ.


Open only after all twelve questions have a written attempt. Each answer states what a "solid"
answer must contain, then common wrong answers and why they fail.

Written against the final Week 5 lessons on 2026-11-22. Every real-data number is copied from those
lessons' authoring runs on the frozen manifest v2 (7 test, 27 development experiments). Numbers marked
*(SYNTHETIC)* come from the lessons' synthetic illustrations. Section references are to the lesson
named in each heading.

### 1. Training/serving skew versus numerical noise (w5d1, 2.2)

**Skew:** with *f* the function evaluated offline and *g* the function deployed, any deployment input
*x* for which *g(x) ≠ f(x)* by more than numerical noise, or for which the two lead to different
decisions. **Numerical noise:** two correct implementations that sum in a different order differ by a
few units in the last place (about 1e-16 relative per operation).

Five sources: re-implemented preprocessing (pandas `std()` ddof=1 versus NumPy ddof=0); different
defaults (a constant burn-in or fill value in the serving script); feature order; stale or recomputed
statistics (including "normalise the batch"); types and parsing (decimal comma, time zone, a CSV float
parser that is not round-trip exact).

The parity test also requires **identical decisions**. A tolerance on scores says nothing about a score
that sits within the tolerance of the threshold; the decision is what an operator acts on.

| Common wrong answer | Why it fails |
|---|---|
| "Skew is when the model file differs" | The file is a fraction of the function; skew lives in the code around it |
| "Parity means bit-identical" | Fragile across summation order, BLAS builds and CSV readers; and not sufficient without decisions |
| "Any difference is skew" | 1e-15 differences are arithmetic, not a different function |

### 2. Fit-time configuration versus per-run state (w5d1, 2.3; Figure 5)

**Frozen at fit time** (`model.json`): sensor, `n_burn` (100), threshold (7.2441), `min_duration`,
`merge_gap`, name and version. Everything learned from labelled development data.

**Computed per run at serving time:** the run's calibration, the mean and *population* standard
deviation of flow rate over the **first 100 rows of that run** only. Never from the rows being judged.

Calibrating on all rows of the run moved the median score after a 6-SD fault from **5.67 to 0.93**
*(SYNTHETIC)*: the fault inflates the run's own standard deviation and divides itself away, so the
detector reports health during the fault. It is also an unevaluated new model: recomputing statistics
is legitimate only if it is part of the method and was evaluated that way.

| Common wrong answer | Why it fails |
|---|---|
| "More data for the statistics is always better" | The extra rows contain the deviation you are trying to detect |
| "The threshold is per-run state" | It was chosen on development data and must not change at serving time |
| "Use the development burn-in statistics for every run" | The method calibrates per run; a different calibration is a different model |

### 3. Batch command design; more alarms without skew (w5d1, 2.5 and section 8)

Four of the design choices and the property each buys:

| Choice | Property |
|---|---|
| chunks of runs, output independent of chunk size | bounded memory |
| one output row per input row, input order, a `status` column | joinable; burn-in and failed rows explicit |
| model name, version, threshold in every row and in `manifest.json` | traceability |
| `input_sha256`, `predictions_sha256` in the manifest | provenance |
| no wall-clock time in outputs | idempotence: same model + same input = byte-identical files |
| temporary file then `os.replace` | atomicity: no half-written output |
| refuse an output directory holding another input's predictions (unless `--force`) | a retry cannot overwrite acted-on results |
| per-run failure, exit code 3 | one bad upload does not silence every machine |

**Twice the alarms, no skew.** Two explanations that are not skew:

1. **The inputs differ from the 7 test experiments**: another operating regime, noisier sensors, more
   or longer faults. The function is the same; its input distribution is not.
2. **The offline estimate was a different quantity**: 7 experiments give a very uncertain false-alarm
   rate (the test set showed 0.00 per hour, which bounds little), or production counts raw exceedances
   per hour while the offline metric counted post-processed alarm events per hour of normal operation.

The check that separates them: recompute the offline metric with exactly the production counting rule
on the offline data. If it still shows about half the alarm rate, compare the production input
statistics (burn-in means and standard deviations per run) with the development reference that the
bundle stores in `reference.npz` for monitoring; a shift there points to (1). Week 7 builds this.

| Common wrong answer | Why it fails |
|---|---|
| "It must be skew somewhere" | Parity to 1e-15 on the same inputs rules out a different function |
| "Retrain on production data" | Before knowing which explanation holds, retraining changes two things at once |

### 4. Bundle anatomy and refusals (w5d2, 2.1 and 2.3)

| File | Answers |
|---|---|
| `model.json` | what function: kind, parameters, threshold, post-processing, input columns, `format`, `format_version` |
| `reference.npz` | named numeric arrays serving needs (development burn-in statistics for monitoring) |
| `card.json` | intended use, limitations, training data (manifest hash), evaluation with intervals, code and library versions |
| `checksums.json` | SHA-256 of every other file |

Checksums match, load refused, two reasons:

* **Format**: `format` or `format_version` is not one this loader reads (for example a bundle from a
  newer release): `BundleCompatibilityError`.
* **Content**: the model `kind`, feature layout, array shapes or input schema are not what the loader
  implements: `BundleCompatibilityError`.
* (Also acceptable) an **unlisted extra file** in the directory, such as a `model.pkl`, while every
  listed checksum matches: `BundleIntegrityError`.

Checksums detect **accidents**: partial copies, sync conflicts, hand edits. They do not stop an
attacker who can also rewrite `checksums.json`; that needs signatures or digests stored elsewhere, and
access control on who may register and promote.

| Common wrong answer | Why it fails |
|---|---|
| "If the checksums match it must load" | Integrity says the bytes are as saved, not that this code can interpret them |
| "Checksums make the bundle secure" | They are recomputable by whoever can write the directory |

### 5. Pickle and the alternatives (w5d2, 2.2 and 3.2)

A pickle is a program for a small stack machine: `STACK_GLOBAL` imports any importable callable by
name and `REDUCE` calls it with arguments from the stream. Rebuilding an estimator works that way, and
so does a malicious payload: loading is executing.

| Model | Safe choice |
|---|---|
| (a) linear model, threshold detector | JSON + `.npz` loaded with `allow_pickle=False`: store the mathematics |
| (b) large scikit-learn ensemble | skops (allow-listed types), with the training library version pinned |
| (c) PyTorch network | `state_dict` loaded with `torch.load(weights_only=True)`; architecture in code |
| (d) another language or runtime | ONNX |

Cost measured in the lesson: pickle and joblib files 547 to 1,073 bytes, loading in 0.006 to 0.12 ms;
the JSON + npz bundles about 2.2 to 2.5 kB, loading in about 0.2 ms including checksum verification.
Paid once at service start. Pickle is acceptable for short-lived caches written and read by the same
code in the same trust boundary.

| Common wrong answer | Why it fails |
|---|---|
| "Pickle is only unsafe from the internet" | Any file that crosses time, machines or people crosses a trust boundary |
| "joblib is a safe pickle" | joblib uses pickle |

### 6. Four versions; the registry (w5d2, 2.4 and 2.5)

* **Model version** (semver of the model's contract): PATCH = same scores (card edited, re-saved);
  MINOR = retrained on new data, same features, inputs and score meaning; MAJOR = consumers must react
  (features, input contract, score scale; downstream thresholds must be revisited).
* **Data version**: the split manifest and its SHA-256 (a new manifest).
* **Code version**: the git commit, flagged if the tree had uncommitted changes (any code change).
* **Format version**: how the bundle is laid out (`format_version: 1`; a new file layout).

Registry: `register` refuses an existing version, so a version string names one function forever
(**immutability**). `promote` writes `current.tmp` and `os.replace`s it onto `current`, so a starting
service reads the old or the new version, never an empty pointer (**atomicity**). **Rollback** is a
promote of the previous version: no rebuild, no retraining. Logs record the resolved version, never
"current".

| Common wrong answer | Why it fails |
|---|---|
| "Overwrite 1.0.0 with the fixed model" | Every prediction logged as 1.0.0 becomes ambiguous; rollback is impossible |
| "`latest` is our version" | It is a pointer that changes meaning over time |

### 7. Welford; O(1) state (w5d3, 2.1 and 2.3; worked example)

```
n     <- n + 1
delta <- x - mean
mean  <- mean + delta / n
M2    <- M2 + delta * (x - mean)        # uses the NEW mean
population variance = M2 / n
```

`E[x²] − E[x]²` subtracts two huge, nearly equal numbers when the mean is large relative to the
standard deviation (catastrophic cancellation). In the worked example *(SYNTHETIC, 10,000 values,
SD 0.5)* it was already 0.8 % off at an offset of 1e6 and returned a variance about 3,450 times too
large at 1e9; Welford's relative error grew far more slowly (1.7e-8 at 1e9), and shifting by the first
sample kept it near 1e-13.

O(1) state: a pump monitored for a year must not hold a year of samples. For this detector: the
Welford accumulators during warm-up, then the frozen mean and standard deviation, the last accepted
timestamp, and the last value and result (to answer retries). A few floats per machine.

| Common wrong answer | Why it fails |
|---|---|
| "Keep a list and call `np.std` each time" | O(n) memory and time per sample |
| "Sample variance M2/(n−1)" | The detector was calibrated with the population SD; that is skew (answer 8) |

### 8. Five streaming decisions; 0.5 % lower (w5d3, 2.4 and section 8)

| Decision | Lab's choice |
|---|---|
| Warm-up | `score = None`, `status = "warming_up"`; never 0.0, which reads as "measured and normal" |
| Late sample (earlier timestamp) | reject with `OutOfOrderError`, state unchanged |
| Repeated sample | same timestamp and value: return the previous result, change nothing (idempotent); same timestamp, different value: `ConflictingDuplicateError` |
| Gap over `max_gap_s` (5 s) | a visible policy: `flag` (keep scoring; batch parity holds) or `reset` (new burn-in) |
| Restart | `snapshot()` to plain JSON; `restore()` refuses a snapshot from another model version |

**0.5 % lower everywhere:** the streaming calibration uses the **sample** standard deviation (ddof=1,
`M2/(n−1)`, or pandas' default) instead of the population one. Scores are multiplied by
`sqrt((n−1)/n)` = 0.995 for `n = 100`. Fix: divide `M2` by `n` (or `np.std(..., ddof=0)`).

| Common wrong answer | Why it fails |
|---|---|
| "Floating-point error" | Rounding is not a constant 0.5 % on every machine |
| "Different threshold" | A threshold changes decisions, not the score values |

### 9. Three gates, decision order, liveness versus readiness (w5d4, 2.1-2.3; section 8)

Gates: **transport and syntax** (malformed JSON: 422 in FastAPI; oversize body: 413 from a proxy or
`max_body_size`); **schema** (422, with the path of every bad field); **domain** (400, or 404/409 in the
challenge, with a stable error code).

Order the lab implements: route and method (404/405) → JSON and schema (422) → model loaded? (503) →
domain rules (400) → scoring raises? (500, logged, nothing leaked) → 200.

An invalid request to an unready service gets 422 because validation runs first: the answer "your
request is wrong, fixing it is your job" is true regardless of the server's state, and a client must
not retry an invalid body hoping the server recovers.

The load balancer case: **`/readyz`** is wrong. It must return 503 while the model is not loaded, so
traffic is routed elsewhere. `/healthz` returns 200 (the process is alive; restarting it would not
help if the model file is missing).

| Common wrong answer | Why it fails |
|---|---|
| "Return 500 when the model is missing" | 500 says "our bug"; 503 tells clients and balancers to go elsewhere or retry later |
| "Make /healthz fail too" | The orchestrator then restarts a process that cannot be fixed by restarting |

### 10. NaN, sync handlers, lifespan (w5d4, 2.2, 2.4 and 2.7)

Without `allow_inf_nan=False`, `NaN` fails both `ge=0` and `le=500` (every comparison with NaN is
false) and pydantic reports **`less_than_equal`**: the client is told the value is too large. With it,
the error is **`finite_number`**, which is true, and fields with no range are protected as well.
Python's JSON parser accepts `NaN` and `Infinity`, so clients really can send them.

The handler is a plain **`def`** because scoring is CPU-bound: FastAPI runs `def` handlers in a thread
pool, while an `async def` handler doing NumPy work blocks the event loop and every other request.

The model is loaded once in the **lifespan** handler, before the app accepts requests. Loading inside
the handler repeats I/O and verification on every request (latency), and a broken bundle would surface
as per-request 500s instead of a clear not-ready state.

| Common wrong answer | Why it fails |
|---|---|
| "`async def` is always faster" | Only for code that awaits I/O |
| "Range checks already catch NaN, so nothing to do" | They reject it with the wrong explanation and leave range-free fields open |

### 11. Test layers, kill matrix, concurrency, contracts (w5d5, 2.1-2.7)

Layers: **unit** (the arithmetic and the loader) → **API** (`TestClient`: status codes and bodies) →
**integration** (a real bundle on disk, loaded at startup) → **contract** (OpenAPI of the candidate
against the last release) → **smoke** (a running process after deployment).

Kill matrix: the starter and a happy-path suite killed 0 of 12; a **status-code-only suite killed 7**
(it misses every defect inside a 200 response); the reference suite **without its concurrency test
killed 11**; the full reference suite killed 12.

A concurrency test sends many *different* requests from several threads and checks that each response
belongs to its own request. A sequential test never runs two handlers at once, so shared mutable state
is never overwritten between write and read.

The 500 trap: FastAPI's default validation handler **echoes the offending input** in the 422 body; a
`NaN` there cannot be serialised as strict JSON, so the 422 becomes a 500. The service installs its own
handler that returns `loc`, `msg`, `type` without the input.

Contracts: adding a **required request field** is breaking (old clients do not send it). Widening a
**response** field to allow `null` is breaking (clients now receive `null`). Requests and responses are
asymmetric.

| Common wrong answer | Why it fails |
|---|---|
| "High coverage means the API is tested" | The starter's smoke test executes most lines and kills nothing |
| "A passing concurrency test proves there is no race" | Races are probabilistic; design shared state out |
| "Adding a field is never breaking" | True for optional response fields only |

### 12. Three-way parity; 1.0541; round-trip CSV (w5d6, 2.1 and 2.2; section 8)

Two-way checks miss defects shared by the pair compared. Lab example (`batch_global_burn_in`): batch
inference takes one burn-in for the whole table instead of one per experiment, and evaluation reuses
the batch function; evaluation and batch agree perfectly and are both wrong. Only the API, which
receives a per-experiment burn-in, disagrees.

Factor 1.0541 = `sqrt(n/(n−1))` with **n = 10** (sqrt(10/9) = 1.0541). Cause: one side uses the sample
standard deviation (pandas `Series.std()`, ddof=1), the other the population one (NumPy, ddof=0). The
side with the **larger** scores divides by the smaller, population SD, which is the training-time
convention the evaluation report used, so it is the consistent one.

`float_precision="round_trip"`: pandas' default float parser is not round-trip exact. Reading the batch
CSV back differed from the in-memory scores by up to 5.7e-14 on 20,708 of 46,806 rows even though the
file held 17 significant digits; with the round-trip parser the difference is exactly 0. Either use it
or compare with a stated tolerance, never `==` on floats read from a file without knowing which.

| Common wrong answer | Why it fails |
|---|---|
| "Parity between evaluation and API is enough" | Misses defects shared by evaluation and batch |
| "1.0541 means n = 100" | That ratio is 1.0050 |
| "The smaller scores are right because they are conservative" | Consistency with the evaluated function decides, not caution |

---

# Notebook 31 — Docker I: images, layers and a correct Dockerfile

✍️ Written answers: compare yours against the rubric; wording will differ.


### Reasoning questions

**1. A changing build argument near the top.** The Dockerfile reference ("ARG: impact on build
caching") says that every `RUN` after an `ARG` uses the variable implicitly as an environment variable,
so a changed value is a cache miss for each later `RUN`. Measured on this lab with `ARG BUILD_DATE` and
`LABEL build-date=$BUILD_DATE` right after `FROM`, two builds with different dates: `COPY
requirements.txt` stayed `CACHED`, but `RUN pip install` ran again (about 13 s), and so did everything
after it. The `LABEL` itself is image metadata; the reinstall comes from the `ARG` being in scope of the
`RUN`. Fix: declare volatile build arguments (dates, commit hashes) and their labels at the end of the
Dockerfile, after the expensive steps (w6d2 declares `ARG REVISION` in the final stage, after the
dependency install happened in the builder stage). *Common wrong answers:* "labels are metadata, so
nothing changes" (the `RUN` still misses), and "every layer after the LABEL is rebuilt" (the `COPY` of
requirements.txt was cached; only `RUN` instructions see the argument).

**2. Exec form and still 10 s / 137.** PID 1 is now the program itself, and the kernel does not apply
the default action of SIGTERM to a namespace's PID 1: if the program installs no handler, it ignores
SIGTERM (the worked example measures exactly this: 10.24 s with the handler switched off). Fixes:
install a SIGTERM handler that shuts the server down (uvicorn has one; for your own scripts,
`signal.signal(signal.SIGTERM, ...)`), or run with `docker run --init` (or a `tini` entrypoint), which
makes a tiny init PID 1 that forwards signals to the program. Another consistent cause: the handler
exists but shutdown takes longer than 10 s (long requests); then raise `--stop-timeout` or shorten
shutdown. *Common wrong answer:* "use exec form", which is already the case.

**3. Healthy but unreachable.** The server listens on `127.0.0.1` inside the container. The healthcheck
runs *inside* the container, where that address works, so it reports healthy; traffic from the host
arrives on the container's `eth0` interface, where nothing listens, so the connection is reset. Fix:
`--host 0.0.0.0` in the command. *Common wrong answer:* the host firewall; a firewall would give a
timeout or "connection refused", and would not explain the healthy status.

**4. `RUN rm -rf /app/data` at the end.** No. The data is in the layer created by `COPY . .`; the
`rm` adds a new layer that hides the files but the earlier layer is still part of the image and is
pushed and pulled. Fix: keep the data out of the context (`.dockerignore`) and copy only what is
needed (`COPY src/`, `COPY models/`). If something must be created and removed during the build, do
both in the same `RUN`, or build it in another stage (w6d2).

**5. `__pycache__` and `*.pyc` in `.dockerignore`.** Both are anchored at the context root, so
`src/flowguard/__pycache__/*.pyc` and `scripts/__pycache__/*.pyc` still reach the context (as do any
`.pyc` below the root). The reference Dockerfile copies `src/`, so the `src` caches would be copied
into the image: harmless for correctness here, but they are stale bytecode built on your machine,
they make the layer change when nothing in the source changed (so the cache is invalidated more often),
and they are exactly the kind of local residue the image should not contain. Use `**/__pycache__`.

**6. User created after the COPYs.** The copied files stay owned by root and readable by everyone, so
the server (running as `app`) can read but not modify its code and model. A compromised or buggy
process cannot rewrite them. If the files were owned by `app` (`COPY --chown=app` or a `chown -R`),
the server could modify its own code, which defeats part of the point of not running as root. Order
also matters for the cache: `useradd` after the COPYs re-runs on every code change, but it takes 0.1 s.

### Explain a design choice: model baked in, location from the environment (model answer)

Baking the 1 kB bundle into the image makes the image tag a complete description of behaviour: the
same tag always means the same code *and* the same model, which makes deployments reproducible and
rollback trivial (run the previous tag). The cost of baking, a rebuild to change the model, is small
here because the model is tiny and changes as rarely as the code.

Reading the location from `FLOWGUARD_MODEL_DIR` keeps the code independent of the image layout and
lets operators point the same image at a different bundle without a rebuild, for example a candidate
model mounted read-only for a comparison (w6d2 uses this to show a smoke test failing). Hard-coding
the path couples the code to one directory structure and makes tests outside the container awkward.

Mounting only (a) makes the image incomplete: its behaviour depends on what is mounted, so "which
model served this request?" must be logged and checked separately, and the container needs storage
or credentials at start-up. I would switch to (a) when models are large (hundreds of MB to GB), change
much more often than code (daily retraining), or when one image must serve many models; then the
model version must be part of every response and log line, which the API already does.

*Rubric notes.* Strong answers mention both reproducibility/rollback and flexibility, and give a
concrete switching condition. Weak answers argue only "simpler".

### Interview rep: "the container exits immediately" - what a strong answer contains

1. `docker ps -a` (not `docker ps`): the container exists with status `Exited (1)`; `--rm` would have
   removed it, so run without `--rm` while debugging.
2. `docker logs <id>`: the traceback. In this lab the common ones are `ModuleNotFoundError: No module
   named 'flowguard'` (exit 1; PYTHONPATH or install missing) and an import error from a missing
   dependency.
3. `docker inspect --format '{{.State.ExitCode}} {{.State.Error}}' <id>`: 1 = the program failed;
   126/127 = the command is not executable / not found (typo in `CMD`, exec form with a missing
   binary); 137 = killed (memory limit or `docker kill`).
4. Reproduce interactively: `docker run --rm -it --entrypoint sh <image>`, then run the CMD by hand,
   check `echo $PYTHONPATH`, `ls /app`, `python -c "import flowguard"`.
5. Only after it runs: "connection refused" is a separate question (published port, `--host 0.0.0.0`).
6. Before leaving it running at a conference: `-p 127.0.0.1:8000:8000` instead of `-p 8000:8000`
   (otherwise it listens on every interface of the laptop, reachable from the conference Wi-Fi, and
   Docker's rules bypass ufw); `--rm` and a `--name`; never pass credentials on the command line.

| Criterion | Strong | Weak |
|---|---|---|
| Order | starts with `ps -a` and logs before changing anything | rebuilds and retries |
| Exit codes | interprets 1 / 126-127 / 137 | does not use them |
| Interactive reproduction | `--entrypoint sh`, runs the command by hand | none |
| Separates "won't start" from "can't reach" | yes | conflates them |
| Network exposure | loopback publishing, names the Wi-Fi/ufw risk | none |

---

# Notebook 32 — Docker II: pinned dependencies, multi-stage builds, smoke tests

✍️ Written answers: compare yours against the rubric; wording will differ.


### Reasoning questions

**1. Two correct builds, two numpys.** `RUN pip install -r requirements.txt` is cached on its text and
on the layers above it, not on what the index contains. The laptop reuses the layer it built weeks
ago, when the newest numpy matching the range was, say, 2.5.3. The CI runner starts with a cold cache,
runs the instruction now, and resolves the same ranges to today's newest release (2.5.5 in this
lesson's resolution). Both satisfy every specifier, so both are "correct" builds of the commit; they
are simply different environments. The cure is to make the build *read* a lock instead of resolving.
*Common wrong answer:* "Docker is nondeterministic". Docker did exactly what the recipe says.

**2. Several hashes, one file.** A released version consists of several distribution files: wheels
for each platform and Python version (manylinux x86_64, aarch64, macOS, Windows, ...) and usually an
sdist. The lock lists the sha256 of every file that is acceptable for that version, so the same lock
works wherever a matching wheel exists. pip picks the file it would install, downloads it, computes
its sha256 and refuses to install if it is not in the list. This prevents a tampered mirror or a
compromised index from serving different bytes under the same name and version, and it prevents
accidental substitution (a re-uploaded file, a private index shadowing PyPI). It also forces the lock
to be complete: in hash-checking mode every requirement must be pinned with `==`.
*Common wrong answer:* "hashes pin the version". `==` pins the version; the hash pins the *file*.

**3. Platform manifest digest.** `python:3.12-slim` is a multi-platform *index* whose entries are
per-architecture manifests. Pinning the amd64 manifest digest makes `FROM` resolve to the amd64 image
everywhere. On an arm64 machine (Apple Silicon laptop, ARM CI runner, Graviton cloud host) the build
either fails or runs the amd64 image under emulation, slowly. Pin the index digest; each platform then
pulls its own variant of the same release.

**4. Why multi-stage is larger here.** (a) The lock resolved pandas 3.1.1 (82.4 MB installed) where
w6d1's top-level pins got 3.0.5 (74.1 MB): +8 MB. (b) The runtime venv has no pip, saving 6.9 MB, but
nothing else: every dependency installs from wheels, so the builder needed no compiler or headers
that could be left behind. Net +7 MB. Changes that would really reduce size: serve without pandas (it
is 48 % of the installed packages and the service uses it for a few lines; numpy alone suffices), or a
smaller base (distroless or a custom minimal image), not more stages.

**5. What a passing smoke test does not establish.** (a) Model quality: the fixture is 300 synthetic
samples; detection performance is the evaluation of Weeks 3-4 on held-out experiments. (b) Performance:
latency and memory under concurrent load (w6d4). (c) Behaviour on inputs unlike the fixture: invalid,
extreme or long requests (the API tests of w5d4-w5d5) and distribution shift in production (Week 7
monitoring). (d) Operational behaviour such as graceful shutdown (w6d1's live check) and correct
configuration in the target environment (w6d5, w6d6).

**6. `ARG REVISION` in the runtime stage, late.** The Dockerfile reference: an `ARG` declared inside a
stage is visible in that stage and in stages based on it, not in unrelated stages; an `ARG` declared
before the first `FROM` is visible only to `FROM` lines unless redeclared (without a value) inside a
stage. The runtime stage is not based on the builder, so it must declare `ARG REVISION` itself to use
it in a label. Late, because every `RUN` after an `ARG` sees it as an environment variable, so a new
commit hash would bust the cache of every later `RUN`; declaring it in the runtime stage, after the
expensive work (done in the builder), keeps the dependency install cached. In the reference the only
`RUN` after it is `useradd` (0.1 s).

### Explain a design choice: pin, and update deliberately (model answer)

The colleague is right that a pinned environment does not receive fixes by itself: a lock pins known
vulnerabilities as faithfully as it pins good versions. Running "the newest" every build, however,
means that the code that is evaluated, tested and approved is not the code that is deployed: any
nightly rebuild can change numerical behaviour (the challenge is a small version of a real class of
incidents) and an incident cannot be reproduced because the environment no longer exists.

Pinning buys three things: what was tested is what runs; any image can be rebuilt equivalently later
(debugging, audits, rollbacks); and every change of a dependency becomes a reviewable diff.

Both goals are met by making updates frequent and routine instead of implicit: a scheduled job (or a
bot) recompiles the lock and bumps the base digest weekly, opens a pull request, CI builds the image,
runs unit tests, the smoke test and an evaluation on held-out data, and a person merges it. Security
advisories are checked against the lock (it is the inventory) and trigger the same pipeline out of
schedule. Rollback is deploying the previous image tag, which still exists unchanged.

*Rubric notes.* Strong answers concede the staleness risk, name reproducibility and reviewability, and
describe an automated, tested update path with a time bound.

### Challenge: what the reference report contains, and common mistakes

The reference `DRIFT_REPORT.md` is in `solutions/.../challenge/`. Points a strong report makes: the
build resolves a range at build time; 1.1.0 appeared in the index; it changed `calibrate` from the
population SD (divide by n) to the sample SD (n - 1), shrinking every z-score by 1/sqrt(20/19) (about
2.5 %) with the 20-sample burn-in; the fix pins 1.0.0 with its hash and installs with
`--require-hashes`; and an upgrade to 1.1.0 must be a deliberate change that re-validates the operating
point (the threshold was chosen with the population SD).

| Mistake | Why it fails |
|---|---|
| Compile the lock today and commit it | pins 1.1.0, the newest, not the validated version: reproducible, but reproducibly wrong |
| `zscorelib==1.0.0` without a hash | pip in hash-checking mode refuses: "Hashes are required in --require-hashes mode, but they are missing from some requirements" |
| Hash copied from the other wheel | "THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE ... Expected sha256 c09a... Got 693c..." |
| `zscorelib>=1.0,<1.1` with a hash | "In --require-hashes mode, all requirements must have their versions pinned with ==" |
| A correct lock that build.sh does not use | the build still resolves requirements.in and still installs 1.1.0 |
| "Update the expected scores to the new output" | makes the test pass by redefining correct; the operating point was validated with 1.0.0 |

### Interview rep: reproducible model images - what a strong answer contains

* **Artifacts:** `requirements.in` and a hash-locked `requirements.lock` in Git; the base image pinned
  by index digest; the model bundle with its own version and checksum (w5d2); the image pushed to a
  registry under an immutable tag (commit SHA plus model version) with OCI labels; the evaluation report
  and smoke fixture tied to that tag.
* **Build:** only from the lock (`--require-hashes`), multi-stage, non-root, no secrets; build arguments
  for revision and version.
* **CI:** unit tests, image build, container smoke test against recorded outputs, evaluation on the
  frozen test set for model changes, vulnerability scan against the lock; a regular cache-free build to
  surface hidden drift.
* **Updates:** weekly automated PR that recompiles the lock and bumps the base digest, with the same
  checks; emergency path for critical advisories; review of the lock diff.
* **Rollback:** redeploy the previous immutable tag; never rebuild an old commit to roll back.
* **Retraining:** a new model is a new bundle version; the image either bakes it (new tag) or loads it
  by version, and every prediction reports the model version.

| Criterion | Strong | Weak |
|---|---|---|
| Pins all three moving inputs (base, closure, files) | yes | "pin requirements" |
| Separates code, environment and model versions | yes | one version for everything |
| Tested, scheduled updates | yes | "update when needed" |
| Rollback by immutable artifact | yes | "rebuild the old version" |

---

# Notebook 33 — Continuous integration with GitHub Actions

✍️ Written answers: compare yours against the rubric; wording will differ.


### 1. `needs:` and wasted work

Without `needs`, all jobs start together: a push with a failing test still runs the 3-minute image job,
so the run takes about 4 minutes (the longest job) and spends 4 + 3 = 7 runner-minutes, 3 of them on an
image nobody will use; its smoke test may even pass and show a misleading green tick on one job. With
`needs: [test]` the image job is skipped when tests fail: about 4 minutes and 4 runner-minutes, and a
green run takes 4 + 3 = 7 minutes of wall time. For pull requests most teams accept the serial
7 minutes because the image job is only meaningful for code that passes its tests. For a release tag
the order is mandatory: you never publish an image built from code that failed its tests.

*Common wrong answers.* "needs makes it faster": it makes failing runs cheaper and green runs slower.
"Jobs run sequentially by default": they run in parallel.

### 2. `python-version: 3.10`

The workflow file is YAML. The YAML parser reads the unquoted scalar `3.10` as a floating-point number,
and the number 3.10 is 3.1; by the time `actions/setup-python` receives the input it is the string
"3.1", and there is no Python 3.1 on the runner's tool cache. `3.11` unquoted is also a float, but
3.11 printed back is "3.11", so it works by accident (as does 3.12). Quote every version string.
(Executed in the lesson: `yaml.safe_load('python-version: [3.10, 3.11, "3.12"]')` returns
`[3.1, 3.11, '3.12']`.)

*Common wrong answer.* "GitHub does not support 3.10": it does; the value never reached it as 3.10.

### 3. Gate or lane

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

### 4. Masked secrets

`***` in the log means GitHub's string-matching mask hid the exact value where it appeared. Two ways it
still leaks: a transformed value (base64, URL-encoded, split across lines, written character by
character) is not recognised by the mask and is printed in clear; and the expression is substituted into
the generated script file before the shell runs, so anything that prints or uploads that script, or a
crash that dumps the command line, exposes it. Also: a compromised or malicious step in the same job can
read it. Safer pattern: `env: TOKEN: ${{ secrets.TOKEN }}` on the step and use `"$TOKEN"` in the script,
pipe it to the tool on stdin (`--password-stdin`), never echo it, and scope it to the one job that needs
it. Better still for cloud access: short-lived OIDC credentials (w6d5) instead of stored keys.

### 5. Forks and secrets

A pull request from a fork runs code written by the fork's author. If that run received repository
secrets, anyone could open a pull request that prints or exfiltrates them; so GitHub does not pass
repository secrets to workflows triggered by `pull_request` from forks (and the `GITHUB_TOKEN` is
read-only there). Implication: the per-push gate must not need secrets, or it cannot check outside
contributions. Steps that need secrets (publishing an image, deploying) run on `push` to `main` or on
tags, after review. (Behaviour stated from GitHub's documentation as remembered; see H14.1 sources.)

### 6. Pinning

Reproducibility: SHA (exact code forever) > `@v7` (moves within the major version) > `@main` (moves on
every push to that branch). Maintenance: `@main` needs none but can break or change silently; `@v7`
needs an update per major version; SHA needs an update for every fix, usually automated by a
dependency bot. In a regulated organisation require full SHAs with automated update pull requests,
because the workflow then runs only code that was reviewed at a known commit.

### Design-choice explanation (model answer)

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

### Interview rep — what a strong answer contains

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

---

# Notebook 34 — Latency, throughput and resource use

✍️ Written answers: compare yours against the rubric; wording will differ.


### 1. Mean 35 ms, two distributions

(a) Every request takes 30-40 ms: mean 35, p99 about 40 ms, meets "p99 <= 100 ms".
(b) 97 % of requests take 10 ms and 3 % take 843 ms: mean 0.97 x 10 + 0.03 x 843 = 35 ms, p99 = 843 ms,
misses badly. (The lesson's open-loop simulation is this shape: p50 10 ms, p99 710 ms.) The dashboard
should show p50, p95 and p99 over a stated window, the request rate and the error rate, and ideally a
latency histogram or heat map, never the mean alone.

*Common wrong answer.* "Show the max": one request decides it; it is useful as an alarm, not a summary.

### 2. Closed loop and a 2 s pause every minute

Each of the 8 virtual users has at most one request outstanding. During the pause each user's request
waits, so 8 requests record about 2 s, and then the users resume; the requests that independent clients
would have sent during those 2 s were never sent, so they are never measured. Out of a minute's
requests (say 8 users x ~60 s / ~20 ms = ~24,000), 8 are slow: 0.03 %, invisible at p99. In an open-loop
test at the same average rate, every request scheduled during the pause is delayed (by up to 2 s, then
by the backlog draining), so at least 2/60 = 3.3 % of requests are delayed, which puts p99 inside the
pause. The closed loop's p99 is wrong by two orders of magnitude.

### 3. Little's law

L = 120 x 0.050 = 6 requests in the system on average. With W = 2 s: L = 240. Those 234 extra requests
are held somewhere (accept queue, event loop, thread pool, request bodies in memory), so memory grows in
proportion; with large payloads that is how a container is killed for exceeding its memory limit (the
lab's overloaded worker grew from 90 MB to 2.1-2.8 GB). Rising L at constant lambda is also a cheap
early warning: monitor in-flight requests.

### 4. Threads vs processes

Threads in one process share one interpreter and its GIL: only one thread runs Python bytecode at a
time, so CPU-bound endpoints gain nothing in throughput; threads help when requests wait on I/O (database,
another service), and they keep one slow request from blocking the event loop. Worker processes are
separate interpreters: up to one core each of Python work, so capacity scales with cores for CPU-bound
code, at the cost of memory per process (model, libraries) and of per-process state (caches,
connections). For this service, processes; threads only matter if the endpoint starts waiting on I/O.

### 5. Timing checks in CI

(1) The runner is a shared VM whose speed varies run to run, so the check fails on unchanged code
(w6d3 measured 0-3 failures in 40 runs as load changed). (2) A p95 needs many requests at a controlled,
realistic offered load, which a unit test does not create; a test-suite timing is a closed-loop,
cold-cache, tiny sample. Deterministic proxy for CI: "the model is loaded once at startup, not per
request" (count loads with a test double), or "the endpoint does not call X per sample".

### 6. Laptop measurement with a co-located generator

Overstates: service time and latency (generator and server compete for 4 cores; the lab's shared machine
made it worse); understates or ignores: network round trips, TLS, multiple client hosts and connection
counts, other tenants on production hosts, larger or varied payloads, long-run effects (memory growth,
GC pauses, log rotation). The biggest bias: CPU contention between generator and server; run the
generator on a separate machine (or at least pin it to separate cores) and measure on the production
host type.

### Design-choice explanation (model answer)

Overload must be turned into fast, visible rejection rather than slow collapse. Concretely: (1) a
concurrency limit per worker slightly above the number it can serve within budget (with 12 ms per request
and a 100 ms p95 budget, a handful in flight per worker); requests beyond it get an immediate 503 with
`Retry-After`, which costs microseconds and keeps memory bounded; (2) request time-outs on the server
shorter than the client's, so abandoned work is cancelled; (3) clients retry with jittered exponential
back-off, so a burst spreads out; (4) autoscaling on utilisation or in-flight requests for sustained
increases, accepting that it reacts in minutes, not seconds. For the reliability engineer this is better
than queueing: queued requests come back late (an alarm for a fault at 10:00 arriving at 10:03 is
worse than useless if the dashboard looks current), and an overload outage takes every machine's alarms
down with it, while explicit rejections show up as a measurable error rate on the service dashboard,
tell clients to retry, and keep the requests that are served on time. Scoring: strong answers name
bounded queues/limits, explicit rejection and why late answers are harmful for alerting; adequate answers
propose autoscaling only; weak answers "add more workers".

### Interview rep — what a strong answer contains (rubric, 1 point each)

1. **Work backwards from the user requirement**: 2 s, 99 % of the time, end to end; allocate the budget
   across ingestion, queueing, network, the model service and the dashboard (for example 300 ms p99
   for the model service), and say the allocation is a decision to revisit.
2. **Load**: 2,000 machines x 1 window per 60 s = about 33 requests/s on average; ask about
   synchronisation (all machines on the minute boundary gives a 2,000-request burst each minute) and
   propose client jitter.
3. **Size with Little's law and a utilisation target**: measure service time for a 60-sample request
   open loop on the target host; workers = ceil(lambda x S / 0.7); add N+1.
4. **Measure correctly**: open-loop load at and above the expected peak, percentiles, warm-up, generator
   on separate hosts, burst test of the minute-boundary pattern.
5. **Production**: server-side latency histogram per route, in-flight requests, error rate, end-to-end
   latency from window timestamp to dashboard update (the user's actual metric), alerts on SLO burn,
   overload protection (limits, 503s).

4-5 strong, 2-3 adequate, 0-1 weak. Deduct for quoting a mean, or for sizing from a closed-loop test.

---

# Notebook 35 — One small cloud deployment on AWS (authorisation-gated)

✍️ Written answers: compare yours against the rubric; wording will differ.


### 1. Order

Budget first because it is the only control that tells you when something is costing money; any resource
created before it can bill unobserved, and a failure half-way through the script leaves billed resources
behind with no alert. Task definition before service because `create-service` references a registered
task-definition family; in the wrong order the call fails (the service has nothing to run). The service
also needs the image pushed, the role and the log group to exist, or the task fails to start and ECS keeps
retrying (each attempt pulling the image).

*Common wrong answer:* "the budget limits spending." It does not stop anything; it notifies. (AWS Budgets
actions can apply policies, but that is not what this lesson configures.)

### 2. Teardown order

`delete-cluster` fails while the cluster still has an active service (the API returns an error; the
cluster stays). Deleting the security group while a task's network interface uses it fails with a
dependency violation. The script stops at the first failure (`set -euo pipefail`), so everything after it
is left running: the order is what makes a teardown complete.

*Common wrong answer:* "it doesn't matter, AWS deletes dependents." Most AWS delete calls refuse rather
than cascade; `ecr delete-repository` needs `--force` for exactly this reason.

### 3. Rotated keys versus SSO

(a) The key is valid until it is rotated: a leak today is usable for up to a month; SSO credentials expire
within hours on their own. (b) A key on disk is readable by every process running as you (a malicious
package, a debugging tool that uploads the home directory) and gets copied into backups and images;
SSO credentials are short-lived and tied to a sign-in with MFA. (c) Keys belong to an IAM user, which tends
to accumulate permissions; Identity Center permission sets are managed centrally. Any two with mechanisms.

*Common wrong answer:* "SSO is more secure because it is newer." No mechanism, no points.

### 4. Exposure

Reachability is decided by the security group's inbound rules, not by the address. With no inbound rule,
packets to the public IP are dropped. The public IP exists so the task can reach ECR (and Logs) without a
NAT gateway. The setting that makes it public: an inbound rule with a CIDR wider than one address (e.g.
`0.0.0.0/0`), i.e. `allowed_cidr` wider than `/32` with `allow_public = true`.

*Common wrong answer:* "it is not public because it has no DNS name." Scanners use addresses.

### 5. `latest` on an immutable repository

Immutability then makes the *second* push of `latest` fail, so the pipeline breaks at the next release,
and the tag still says nothing about which build it is. The fix is a tag that identifies the build (the
git SHA) on an immutable repository; then the tag is a permanent name, and rollback means "deploy the
previous SHA".

### 6. `/readyz` versus `/healthz`

With `/healthz`, a task whose model failed to load (missing bundle, checksum mismatch) is reported healthy:
the process is up. ECS keeps it running and the service is "stable" while every `/predict` returns 503.
With `/readyz` the task becomes unhealthy, ECS stops and replaces it, the deployment does not reach a
steady state, and `services-stable` times out: the failure is visible during deployment, not after.

### 7. Cost reasoning

The alert. Cost is proportional to running time; a forgotten deployment runs 730 hours a month. Halving
task size halves vCPU and GB charges but not the per-hour public IPv4 charge, and still bills for 730
hours. An alert after one day caps the running time at roughly 24 hours plus your reaction time: about a
30-fold reduction for the month. (Both together are better; the question asks which matters more.)

*Common wrong answer:* "halving size halves the bill." Not the IPv4 part, and it ignores time.

### 8. Design choice: printed script versus SDK calls (model answer, about 200 words)

For this project the printed script is better. The reason is review: the person paying for and
authorising the deployment can read every command, with every value substituted, before anything runs,
and the live run is guaranteed to be that text. That makes the dry run a real artefact (it can be
attached to a pull request or a change ticket) and keeps the learning visible: each line maps to one AWS
API call the learner can look up. It also needs no extra dependency beyond the AWS CLI.

What I give up: error handling and idempotency. A script stops at the first failure and cannot easily
resume, check whether a resource already exists, or roll back what it created; it parses outputs with
`--query` strings; and it is bash, which is hard to test. An SDK program can check state before acting,
retry with backoff, and clean up on failure. Beyond one service, neither is the industry answer:
infrastructure as code (CloudFormation, CDK, Terraform) declares the desired state and computes the plan,
which combines a reviewable plan with idempotent execution.

*Rubric:* 2 points for a choice justified by this project's needs (review, gating, learning); 2 points
for a real cost (idempotency, partial failure, testing) or for placing both against IaC. Answers that
claim one option "has no downside" get at most 2.

### Challenge rubric (review of the colleague's plan)

The checks cover the facts; score the writing here (2 points each, 14 total; 10+ is a pass):

1. Credentials: identifies the committed administrator key as the most severe issue, says to delete the
   key and user, and to scan history because the key may be in old commits (treat as leaked).
2. Budget: budget first, with alert thresholds, and a stated expected cost structure.
3. Registry: explains why `latest` blocks rollback and attribution; turns scanning back on.
4. Artifacts: private bucket with Block Public Access and a task role, or the model baked into the image.
5. Network: replaces 0.0.0.0/0 with specific addresses; says what to do if that is not enough (VPN,
   authentication), rather than widening the rule.
6. Teardown: a dated teardown of every resource and an independent not-billing check.
7. Tone and decision: specific, actionable, not condescending; a clear decision with conditions.

Common weak reviews: listing problems without the risk ("bucket should not be public"); proposing a
`/16` "company network" range as a fix; rotating the key instead of removing it; a decision of "go" with
the stored administrator key still in place.

### Interview rep rubric (deploy a model service, 10 minutes)

| Element | Strong answer contains |
|---|---|
| Clarify | who calls it, how many requests, latency need, data sensitivity, two-week lifetime |
| Artifact | one immutable image per release, tagged by git SHA, scanned; model inside or fetched with a role |
| Identity | short-lived credentials for people; a minimal execution role; no keys in code or image |
| Compute | a managed container service, one or two tasks, health check on readiness, sized from measurement |
| Exposure | private by default; restricted ingress or authentication; TLS if anything leaves a trusted network |
| Cost | budget and alert first; expected cost structure; teardown date |
| Observability | structured logs with release id; service metrics (rate, errors, latency); a check that predictions are sane (distribution), not only that the service is up |
| Rollback | redeploy the previous digest; keep the last good release |

Scoring: 1 point per element covered with a specific mechanism (8 total). 6+: good; 4-5: revisit
sections 2.2-2.5 and redo the rep in a week; below 4: re-read H13.1 and H13.2 first. The most common gap
at this stage is the last observability item: everything above says whether the service is *up*, not
whether its predictions are *right* (week 7).

---

# Notebook 36 — Delivery and operational debugging; project milestone 3

✍️ Written answers: compare yours against the rubric; wording will differ.


### 1. Rebuilds

Staging tested one artifact; a rebuild is another artifact with the same source. Differences can be
harmless metadata (timestamps, which is what changed the digests here) or not: a dependency resolved to a
newer version, a base image tag that moved, a build argument. "Passed in staging" is evidence about a
digest. Promotion redeploys that digest, so the evidence carries over exactly.

*Common wrong answer:* "the code is the same, so the image is the same." The authoring run's three digests
for one tree are the counterexample.

### 2. Rollback scope

* **Bad promotion (checksum mismatch):** fixed: the image changed, and the previous good digest has a valid
  bundle.
* **Wrong `FLOWGUARD_MODEL_DIR`:** not fixed. The current digest was good before, so the tool skips it and
  picks the release before it, which fails with the same environment file *and* undoes a good release.
* **Memory 64m:** not fixed, for the same reason: the older image needs the same memory.

### 3. Two validation layers

An unknown variable name or a malformed value is a bug in the deployment's configuration that cannot
become right by waiting; exiting with status 2 and the variable's name stops a bad deployment at once and
tells the reader exactly what to fix. A missing directory is a fact about the filesystem: the process can
run, log, answer `/healthz` and report through `/readyz` that it must not get traffic. Keeping it alive
keeps the evidence (logs, `/version`) accessible, and the platform's readiness logic does the rest.

*Common wrong answer:* "check that the directory exists at startup and exit." Defensible for this service,
but you lose the running process's diagnostics and conflate "configured wrong" with "model unavailable",
which for a model fetched at startup can be transient.

### 4. Exit 137

From the container runtime: `docker inspect` shows `OOMKilled=true` and exit code 137 (128 + 9, SIGKILL).
The kernel's out-of-memory killer sends SIGKILL, which a process cannot catch; it has no chance to log.
Platform events (Docker events, ECS stopped-task reasons, Kubernetes `OOMKilled` status) carry the cause.

### 5. "Good" too early

Mark a deployment good only after the container has stayed healthy for a soak period longer than the
slowest failure mode (here, at least two health-check intervals; in practice minutes, or until a number of
real requests succeed). The cost is slower deployments and slower rollbacks, and a soak period that is too
short still misses failures that need load (memory growing with traffic).

### 6. Sorting by time

The history is written by several tools (deploy, promote, rollback marking entries), may be merged from
two machines or edited by hand to annotate an incident, and could be appended to concurrently. Any of these
breaks "last element = current". Time is the order that means something; list position is an accident.

### 7. Design choice: environment in the image (model answer)

Against, for this service. The point of one image per release is that the artifact tested in staging is the
artifact that runs in production. A separate production image built with production configuration is, by
construction, never tested before production: staging tested a different digest. It also multiplies images
(one per environment per release), and turns every configuration change, including emergency ones, into a
rebuild and push. Keeping configuration in version-controlled env files outside the image, validated at
startup, gives one artifact and a reviewed, diffable configuration (`git diff -- ops/env` solved incident 1).

The strongest point of the other side: with configuration outside the image, "what is running" is the pair
(digest, configuration), and the deployment record must capture both. Here it captures only the digest,
which is why incidents 1 and 3 needed `git diff` rather than the history. The right answer to that is to
record a hash of the configuration in each history entry, not to bake configuration into images.

*Rubric:* 2 points for a position with a reason specific to promotion or testing; 2 for stating the
opposing side's real strength (traceability of configuration) and answering it.

### Challenge rubric (postmortem)

The checks cover structure, facts and language. Score the analysis (2 points each, 12 total; 9+ passes):

1. **Root cause is about the system:** a unit mismatch between a new client and training data, with no
   unit contract at the boundary; not "someone made a mistake".
2. **Explains why every check passed:** fixture written with the same wrong assumption; smoke test checks
   status codes; dashboards show service health, not prediction quality.
3. **Impact is measured from the right start:** 14:02, when production served the release, not 14:09 when
   someone noticed; business impact in orders (212, 37).
4. **Action items cover detect and prevent**, and at least one targets prediction quality (distribution
   alert, shadow or replay comparison before promotion), not only process.
5. **Mitigation thinking:** something that limits damage when detection is slow (delay automatic orders
   after a model release).
6. **Tone:** describes conditions, not people; "what went well" is real (prediction log by release,
   digest rollback in four minutes, the analyst's report taken seriously).

Common weak postmortems: "root cause: the test was wrong" (stops one step early); action items that are
all "be more careful" or "add more tests"; impact counted from detection; no action that would detect
wrong predictions in a service that is otherwise healthy.

### Interview rep rubric (debugging narrative)

| Element | Strong answer contains | Points |
|---|---|---|
| Symptom | what was observed, by what signal, and when | 1 |
| First hypothesis | stated honestly, including if it was wrong | 1 |
| Discriminating test | the one check that separated hypotheses, and its result | 2 |
| Cause | mechanism, not just component ("the kernel killed it at 64 MiB", not "memory issue") | 2 |
| Fix | and why that fix (rollback versus revert) | 1 |
| Prevention | a change that removes the class of failure or detects it earlier | 2 |
| Delivery | under 5 minutes, chronological, no unexplained jargon | 1 |

8+ of 10: interview-ready for this question. The most common gap is the discriminating test: candidates
describe what they tried, not what told them which hypothesis was right.

---

# Week 6 review day — Review and catch-up (light)

✍️ Written answers: compare yours against the rubric; wording will differ.


Open only after all twelve questions have a written attempt. Each answer states what a "solid" answer must
contain, then common wrong answers and why they fail.

Written against the final Week 6 lessons on 2026-11-22. Every number is copied from those lessons' authoring
runs (Docker Engine 29.10 on a 4-core authoring machine) or from their synthetic examples, marked
*(SYNTHETIC)*. Section references are to the lesson named in each heading.

### 1. Ten seconds to stop, exit 137 (w6d1, 2.5; section 3.2, figure 1)

`docker stop` sends **SIGTERM** to the container's PID 1, waits **10 s** (default), then sends **SIGKILL**;
exit code 137 = 128 + 9 (SIGKILL). Two independent causes:

1. **Shell-form `CMD`/`ENTRYPOINT`.** PID 1 is `/bin/sh -c "..."`; Debian's `dash` neither forwards SIGTERM to
   its child nor replaces itself with it, so the server never hears the signal. Fix: exec form
   (`CMD ["uvicorn", ...]`), or a wrapper script that ends with `exec uvicorn ...`.
2. **PID 1 installs no SIGTERM handler.** The kernel does not apply default signal actions to a PID
   namespace's PID 1, so a program that relies on the default "terminate on SIGTERM" ignores it in a
   container. Fix: install a handler (`signal.signal(signal.SIGTERM, ...)`), or use a server that has one
   (uvicorn does), or run an init (`docker run --init`).

Measured: exec form stops in **0.5 s** (exit 0, "Finished server process"); either shell form
**10.2-10.4 s** (exit 137). In an orchestrator that restarts containers routinely, the shell form means
dropped in-flight requests and 10 s delays on every deployment.

| Common wrong answer | Why it fails |
|---|---|
| "Increase the stop timeout" | Hides the symptom; requests are still killed mid-flight, just later |
| "137 means out of memory" | 137 is SIGKILL from any source; OOM is one of them (`docker inspect` shows `OOMKilled`), here it is the stop timeout |
| Only one of the two causes | Fixing the exec form does not help a script without a handler as PID 1, and vice versa |

### 2. Layer order, `.dockerignore`, ports (w6d1, 2.3-2.6; figures 2 and 4)

A change to the input of one instruction rebuilds that layer **and every layer after it**: rebuild cost
= Σ<sub>i ≥ k</sub> c<sub>i</sub> for a change hitting layer *k*. Order from rarely to often changing:
`FROM` → `COPY requirements.txt` (or the lock) → `RUN pip install` → `COPY src/` → `COPY models/`. Measured:
a code edit rebuilt in **1.8 s** with dependencies first, **20.9 s** with `COPY . .` before `pip install`.

`.dockerignore` patterns are **anchored at the context root**: `__pycache__` excludes only
`./__pycache__`; every one needs `**/__pycache__`. The robust form is an allow-list (`*`, then `!src`,
`!models`, `!requirements.txt`, then `**/__pycache__`). BuildKit transfers only referenced paths, so with
targeted COPYs a 344 MB pile of local data cost 72 kB; with `COPY . .` it sent 360 MB and the compressed image
grew from 90 MB to 450 MB.

Ports: **inside** the container the server must listen on `0.0.0.0`; `127.0.0.1` there is the container's
own loopback. Symptom measured: `curl: (56) Recv failure: Connection reset by peer` from the host while the
in-container healthcheck still said `healthy`. **On the host**, `-p 8000:8000` publishes on every interface
(anyone on the Wi-Fi can call the model, and Docker-published ports bypass `ufw`); use
`-p 127.0.0.1:8000:8000`.

| Common wrong answer | Why it fails |
|---|---|
| "`.dockerignore` works like `.gitignore`" | Unanchored patterns match at any depth in `.gitignore`, not in `.dockerignore` |
| "Put `--host 127.0.0.1` in the CMD for security" | Makes the service unreachable; restrict exposure with `-p 127.0.0.1:...` on the host instead |
| "Use `--no-cache` to make builds correct" | Correctness comes from the lock; `--no-cache` makes every build pay full cost |

### 3. Build drift, hash-checking mode, what still changes (w6d2, 2.3-2.4; section 8)

| Source of drift | Pin |
|---|---|
| Base image tag | `FROM python:3.12-slim@sha256:...` |
| Direct dependencies | `==` in a lock |
| Transitive dependencies | the whole closure in the lock |
| The file behind a version | `--hash=sha256:...` per distribution file |
| Build cache (an old layer hides that a fresh build would differ) | build from the lock; build without cache regularly in CI |
| apt packages | pin or avoid; prefer Python-only images |

In `pip install --require-hashes -r requirements.lock`, a dependency missing from the lock is **an error, not
a silent resolution** (measured: "all requirements must have their versions pinned with ==" for `starlette`
from a top-level-only lock). Desired, because a silently resolved package is exactly the untested version.
The lab's lock pins 18 packages with 294 hashes.

Behaviour can still change with a fully pinned build: (a) **configuration and inputs outside the image**:
environment variables, a mounted model directory (w6d1, 2.7), data and clients; caught by logging the model
version and configuration at startup, validating configuration (w6d6) and a smoke test against the image as
shipped; (b) **the platform underneath**: CPU instruction set and thread counts change numerical results and
speed (BLAS, OpenMP), the kernel and container runtime differ between hosts; caught by the smoke test's score
comparison with a tolerance and by the scheduled performance lane; (c) a **deliberate update** of the lock or
base digest, which must go through the same smoke test (that is the point of making updates explicit).

| Common wrong answer | Why it fails |
|---|---|
| "`pip freeze` is a lock" | Pins whatever is installed on your platform, without hashes, including tools the service does not need |
| "Fully pinned means byte-identical images" | Timestamps and generated `.pyc` files differ; behaviour is reproducible, bytes are not |
| "Pinned means secure" | Pinned also freezes unpatched vulnerabilities; update on a schedule, through the smoke test |

### 4. Multi-stage builds; the smoke test (w6d2, 2.5-2.6; section 3.3)

Multi-stage builds keep build-time things (compilers, headers, pip caches, source trees, mounted secrets for
private indexes) in a discarded stage; only `/opt/venv` crosses into the runtime image. **Measured: 402 MB
multi-stage against 395 MB single-stage slim.** Not smaller, because every dependency ships as a wheel (the
builder needed nothing extra); the runtime venv lacks pip (about 7 MB) but the lock resolved pandas 3.1.1,
8 MB larger than w6d1's 3.0.5. What shrinks this image: the **base** (`python:3.12` 1.9 GB against `-slim`
0.4 GB) and **the dependency list** (pandas and numpy are 87 % of 172 MB of packages).

The smoke test starts the container, polls `/readyz` until 200 or a timeout, posts a fixed request
(300 SYNTHETIC samples) and compares all scores, decisions and the model version with recorded expectations
(relative 1e-9). It proves: the image starts, loads *this* model, has a working dependency stack, and computes
inside what the package computes outside. It does not prove detection quality, performance under load, or
behaviour on inputs unlike the fixture. Exit codes: **0** pass, **1** wrong answer (look at the model,
dependencies or code), **2** never ready (look at start-up and configuration).

| Common wrong answer | Why it fails |
|---|---|
| "Multi-stage always makes images small" | Only when building needed things running does not; measured here it did not |
| "The smoke test passed, so the model is good" | It checks plumbing on 300 samples it was calibrated on |
| "One exit code for failure is enough" | CI's reader must know whether to look at start-up or at results |

### 5. Gate or scheduled lane; the F1 gate; the flaky timing test (w6d3, 2.5; section 8)

The test: **would a red result on this commit, with no code change, be possible?** If yes (noise, network,
a slow runner, a new day's data), it does not belong in the per-push gate.

The F1 gate fails it twice: (1) F1 on a validation set is an **estimate with sampling noise** (w3d5); a
threshold of 0.01 flips on noise and on data refreshes, so the gate turns red without a regression, gets
lowered or bypassed, and then lets a real regression through; (2) it needs **data** (a download, possibly
secrets) and minutes of evaluation in the gate, which also cannot run on pull requests from forks. Instead:
deterministic unit, API and smoke tests in the gate; a **scheduled evaluation job** on the frozen test set
that reports the metric with an interval and a trend, with an owner who investigates a red run.

Measured: the identical single-request "under 50 ms" test failed **0, 0, 2 and 3 times out of 40** with 0, 2,
4 and 6 competing CPU-bound processes. Same code; a shared runner is a coin with an unknown bias.

| Common wrong answer | Why it fails |
|---|---|
| "Use a looser threshold, e.g. 0.05" | Still a statistical test with an unknown false-alarm rate, in the wrong place |
| "Re-run until green" | A re-run is a diagnostic; a pass on re-run identifies a flaky test to fix or move |

### 6. Four workflow defects; pinning actions; forks (w6d3, 2.2-2.4 and 2.6)

(a) **No `permissions:`**: the job's `GITHUB_TOKEN` gets the repository or organisation default, which may
include write. Fix: `permissions: contents: read` at the top, more per job only where needed.
(b) **`${{ secrets.TOKEN }}` inside `run:`**: expressions are substituted **before** the shell runs, so the
secret becomes part of the generated script (and a transformed secret escapes log masking). Fix: pass it via
`env:` and reference `$TOKEN`; better, keep the gate free of secrets.
(c) **Cache key with `github.sha`**: a new key on every commit, so it never matches an earlier save; every run
misses and stores another unused entry. Fix: key on OS, Python version and a hash of the dependency file
(`setup-python` with `cache: pip` does this). Measured install: 7.0-7.3 s cold, 4.3-4.8 s with a warm pip cache.
(d) **Unquoted versions**: YAML reads `3.10` as the number 3.1. Fix: quote, `["3.10", "3.11"]`.

`@v7` follows the maintainers' moving major tag (fixes arrive; you trust them); a 40-character SHA pins one
commit forever (reproducible, immune to a moved tag; you update it, e.g. via Dependabot); `@main` is a branch
and pins nothing. Forks: GitHub does not give repository secrets to workflows triggered by pull requests from
forks, because the fork's author controls the code that would run; a gate that needs secrets cannot check them.

| Common wrong answer | Why it fails |
|---|---|
| "Secrets are masked in logs, so it is safe" | Masking is string matching; base64 or split output is printed in clear |
| "actionlint passed, so the workflow is fine" | It finds syntax and type errors; the lab's flawed starter passes it |

### 7. Coordinated omission; percentiles (w6d4, 2.2-2.3; worked example)

A **closed-loop** generator (fixed users, each waits for its response) stops sending while the server stalls,
so the requests real clients would have sent never exist and their delays are never measured: **coordinated
omission**. An **open-loop** generator schedules request *i* at *t₀ + i/λ* regardless of responses and measures
latency from the **intended** start.

*(SYNTHETIC)* One 10 ms server, one 1 s stall, about 50 requests/s for 60 s: closed loop **p99 = 10.0 ms**
(one 1,010 ms sample, 0.03 % over 100 ms); open loop **p99 = 710.1 ms**, p99.9 980 ms (3.07 % over 100 ms).

Percentile with linear interpolation: *h = (n − 1)p/100*, *P = x⌊h⌋ + (h − ⌊h⌋)(x⌈h⌉ − x⌊h⌋)*. Care: a p99
from 200 requests is decided by 2 of them (collect thousands); percentiles **do not average** (aggregate raw
latencies or histograms, not per-host p95s). Report p50/p95/p99 at a stated rate, not a mean.

| Common wrong answer | Why it fails |
|---|---|
| "Measure from when the request was actually sent" | That is the measurement coordinated omission corrupts; measure from the intended time |
| "More virtual users fixes a closed loop" | They all stall together; the schedule, not the user count, is the issue |

### 8. Little's law, saturation, workers, a load-independent delay (w6d4, 2.4-2.7, tasks 6-8; section 8)

*L = λW*: requests in the system = arrival rate × time in system, for any stable system. A single-request
worker with service time *S* is busy *ρ = λS*; *n* workers need *n = ⌈λS/ρ*⌉* for a target utilisation *ρ**.
Target 0.6-0.75 because queueing delay grows like *ρ/(1 − ρ)*: about 1 service time at 0.5, 2.3 at 0.7, 9 at 0.9.

One worker served about **83 requests/s** at most. At 90/s p50 was 1,219 ms and the queue grew for the whole
run; at 120/s about 95-97 % of requests timed out at 10 s, served throughput fell to 1.8/s, and RSS went from
90 MB to **2.1-2.8 GB** (2,494 MB in the run quoted).

CPU-bound Python holds the GIL, so more **threads** give more requests in progress, not more completed;
more **worker processes** give more throughput at the cost of a copy of the libraries and model each
(90 MB idle with 1 worker, 220 MB with 2, about 395 MB with 4).

p50 50 ms at both 5 and 100 requests/s with 10 ms server-side: a delay that does not grow with load is not
queueing. Hypotheses: (1) a fixed network-level delay (Nagle meeting delayed ACKs, about 40 ms; the w6d4
finding with `--workers 2`); (2) per-request overhead outside the measured span (new connection, TLS or DNS per
request in the client, a synchronous call to another service, a sleep); (3) the load generator itself (late
starts, its own event loop). Separating measurements: compare client-side latency with the server-side span
for the same requests; look at the **histogram** (a bimodal 10 ms / 50 ms split points to a discrete fixed
delay); change one thing (set `TCP_NODELAY`; reuse connections; check the generator's late-start count). In the
lab, forcing `TCP_NODELAY` cut p50 at 60/s from 52 ms to 9.5 ms.

| Common wrong answer | Why it fails |
|---|---|
| "Add workers until latency drops" | No mechanism; here more workers *introduced* the delay |
| "It's the GIL" | Each worker is a separate process; and the delay did not depend on load |
| "Run at 95 % utilisation to save money" | Queueing delay explodes near 1; one burst and the service collapses |

### 9. Credentials, roles, tags (w6d5, 2.2 and 2.4)

Credentials live only in the AWS CLI's SSO cache on your machine, as **temporary role credentials** from IAM
Identity Center (`aws configure sso` once, `aws sso login` per session). Never: committed to the repository
(including `deploy/config.toml`), baked into an image (anyone who can pull it reads every layer), as plain
environment variables in a task definition (visible to anyone who can describe it; ECS has a separate
`secrets` field), or the root user. `aws sso login` gives credentials that **expire on their own**, behind
browser sign-in and MFA; an access key works until someone deletes it, wherever it was copied.

The **task execution role** lets ECS itself pull the image from ECR and write logs to CloudWatch
(`AmazonECSTaskExecutionRolePolicy`). A **task role** would give the application code AWS permissions; this
service calls no AWS API, so it has none (least privilege).

The tag is the **git SHA** in an **immutable** ECR repository, so "release 1a2b3c4d5e6f" names exactly one
build forever, the deployment record is exact, and rollback has something to point at.

| Common wrong answer | Why it fails |
|---|---|
| "A private repository makes committed keys acceptable" | Repositories get forked, cloned and printed in CI logs; treat a committed key as leaked |
| "Give the task role admin to be safe" | The application needs no AWS access; any permission is attack surface |
| "Tag `latest` and overwrite it" | Mutable tags make "what is running?" unanswerable and rollback impossible |

### 10. Cost, budget, exposure, health check, dry run (w6d5, 2.3, 2.5, 2.8; figures 1-2)

cost ≈ *T*<sub>hours</sub> · *n*<sub>tasks</sub> · (*r*<sub>vCPU</sub>·vCPU + *r*<sub>GB</sub>·GB + *r*<sub>IPv4</sub>)
\+ *r*<sub>ECR</sub>·GB<sub>images</sub> + *r*<sub>logs</sub>·GB<sub>logs</sub>. **Time dominates.** Billed vCPU-hours
of a 0.25 vCPU task: **0.5** (same-day lab), **16** (a weekend), **182.5** (a forgotten month), **365** (two
forgotten tasks). No prices are quoted: they vary by region and date, and the pricing pages were unreachable
when the lesson was written.

The budget alert comes first because the dangerous failure is the forgotten resource, and an alert set up
afterwards does not cover the window in which you forget.

"Not public": the security group has **no inbound rule** by default (the task's public IP exists only to pull
from ECR without a NAT gateway). With `network.allowed_cidr`, only your own address as a `/32`; anything wider
needs `allow_public = true` *and* the public sign-off, otherwise the planner refuses.

The platform health check should probe **`/readyz`** (model loaded), not `/healthz` (process answers);
otherwise a task that cannot serve predictions counts as healthy and is never replaced. The lesson's local runs
answered `/readyz` after 2.9-3.3 s, hence a `startPeriod`.

A dry run proves the plan is what you intend and complete (the live mode runs the same printed text). It does
not prove permissions, quotas, regional availability, or the unresolved `assignPublicIp` question; those are
only tested live, and none of them says whether predictions are correct.

| Common wrong answer | Why it fails |
|---|---|
| "Small task, small bill" | Size multiplies; hours dominate |
| "A public IP means it is reachable" | Reachability is the security group's inbound rules; none by default |
| "Healthy task, working service" | Health checks see readiness, not correctness (week 7) |

### 11. Digests, promotion, rollback versus revert (w6d6, 2.1-2.2, 2.7; incidents 1 and 2)

A **tag** is a name a registry can move (unless the repository is immutable); a **digest** is the hash of the
image manifest and cannot point at different content. Promotion deploys the digest that staging ran
successfully; it **never rebuilds**, because a rebuild is a different artifact: three builds of the same
unchanged source tree gave **three different digests**.

**Rollback** (redeploy the most recent earlier good digest) is right when **the image changed**: incident 1,
a hand-promoted "threshold hotfix" whose `model.json` no longer matched `checksums.json`, so the loader refused
it; rollback to the previous good release restored readiness. It is **wrong when the image did not change**:
incident 2, `FLOWGUARD_MODEL_DIR` changed to `/models/flowguard-z/1.0.1`, a version no image contains. The fix is
to **revert the configuration and redeploy the same digest**; rollback would have picked the older release
`a1b2c3d4e5f6`, which fails with the same environment file and also removes a good release. Rollback is also
unsafe across schema or API changes (expand-then-contract migrations).

| Common wrong answer | Why it fails |
|---|---|
| "Rollback is always the safe first move" | It does nothing for configuration incidents and can undo good releases |
| "Rebuild the same commit for production" | Different bytes; "tested in staging" no longer applies |

### 12. Two validation layers; the memory incident; when a deployment is good (w6d6, 2.3, 2.7; incident 3)

**Startup** validation checks names and formats of `FLOWGUARD_*` variables once and exits (status 2, one JSON
error naming the variable) on a bug that can never fix itself: `FLOWGUARD_MODEL_DlR` (lower-case L) is an
**unknown variable, almost always a typo**, so the container stops at once. **Readiness** handles state: a
missing model directory passes format validation (an absolute path), the process stays up and logs
`model not loaded`, `/readyz` answers 503 and `/healthz` 200, so the platform sends it no traffic.

Memory incident: after a "right-size memory" change (a 64 MiB limit), `/readyz` answered **200 for about 3 s**,
then nothing; the **logs ended on normal startup lines** ("Application startup complete", "Uvicorn running on
http://0.0.0.0:8000"), with no ERROR and no traceback, because the kernel killed the process before it could log.
The service uses about 64 MiB at idle, so the limit left no room (the reference log also notes the second Python
process the health check starts). The cause was visible only in container state:
`docker inspect` showed `exited oom=true exit=137`. Fix: revert the configuration and redeploy the same digest.

A deployment is `good` only when the new version is ready, healthy and **stays** so for a soak period of at
least a few health-check intervals (and ideally through first real traffic), long enough for its likely failure
modes to appear; one successful probe is not enough. Time not ready per incident in the scripted replay:
20, 20 and 13 s.

| Common wrong answer | Why it fails |
|---|---|
| "Validate everything, including file existence, at startup and exit" | A missing model is state; exiting turns it into a crash loop with less evidence than a not-ready service with a clear log |
| "No ERROR line, so the logs are fine" | The OOM kill leaves no log line; container state is evidence logs cannot provide |
| "Ready once, so good" | Incident 3 was ready for 3 s before being killed |

---

# Notebook 37 — Structured logging and service metrics

✍️ Written answers: compare yours against the rubric; wording will differ.


### Reasoning questions

**1. 500s never counted.** In Starlette, a handler registered for `Exception` lives in
`ServerErrorMiddleware`, the outermost layer. When the endpoint raises, the exception propagates *out of*
`call_next` in your middleware; no response object comes back, so code placed after `call_next` never
runs. The fix is `try/finally` with `status = 500` set before the `try`; the bookkeeping in `finally` runs
on both paths and the exception continues outward to be turned into a 500. 422 and 404 are different:
their handlers live in the inner `ExceptionMiddleware`, so `call_next` returns a response for them.
*Common wrong answers:* "add `@app.exception_handler(Exception)` that increments the counter" (it works
for the counter but duplicates bookkeeping and still leaves in-flight and latency wrong unless repeated
there); "catch the exception and return a 500 yourself" (works, but swallows it before the outer handler
and its logging unless you re-raise).

**2. In-flight = 1.** The `/metrics` request is itself in flight while `render()` runs; the gauge was
incremented for it. Requiring 0 would make the check depend on whether the scrape counts itself (a
legitimate design choice either way); requiring <= 1 still catches a leak, because three crashed requests
leave it at >= 3. *Wrong answer:* "a background task is running" (there is none).

**3. Averaging p99s.** Instance A: 9,000 requests, p99 50 ms. Instance B: 1,000 requests, p99 1,008 ms.
Average 529 ms; true p99 588 ms (worked example). With a 250 ms SLO stated as "99 % under 250 ms", the
truth is that 6.7 % of all requests are slower than 250 ms, an SLO breach, while each instance's p99 and
any average of them cannot express that share. Correct: sum bucket counts across instances, then compute
the fraction above 250 ms (exact if 250 ms is a bucket edge) or estimate the quantile.
*Wrong answer:* "weight the p99s by traffic" (still not a percentile of the combined distribution).

**4. Validity.** Latency of failures measures nothing useful for the user and is often very short (fast
500s), so including them would improve the latency SLI during an outage. A 422 is the service correctly
rejecting a bad request: the client's fault, not evidence about availability; counting it as bad lets
one broken client burn your budget. A 503 means the service could not serve: the service's fault.

**5. Samples counter.** No. The client re-sends the run so far every 60 samples, so each sample is scored
up to ~19 times; the counter counts sample-scorings, not distinct seconds. To count distinct anomalous
time you would need the stateful streaming endpoint (each sample once), or an event-level count of alarm
episodes per machine computed downstream, or a log field with the timestamp range of the newly added
samples. Know what a counter counts before charting it.

**6. Not logged.** The sensor values (payload): data exposure, size, unreadability; summaries suffice to
debug. Request headers wholesale: they may contain credentials (Authorization, cookies). Also acceptable:
full tracebacks in responses (never), client IPs without a retention policy.

### Design-choice explanation (what a strong answer contains)

* A `machine_id` label creates up to 120,000 x routes x statuses series for the counter, and x 10 more
  for histogram buckets: millions of series, which the monitoring system will reject or charge for, and
  most of them empty most of the time.
* Instead: keep metrics at service level (route, status, model version) for alerting; put `machine_id` in
  the access/prediction log events and answer per-machine questions with a log query (top-N machines by
  5xx count in the last hour), or a periodic batch job that aggregates logs into a per-machine table.
* If a small fixed grouping matters operationally (site, product line, fleet segment with < ~20 values),
  that can be a label.
* Cost: log queries are slower and logs may be sampled; per-machine error accounting therefore needs
  errors to be logged unsampled.

### Rubric notes for the challenge (`SLO.md`)

"Meets" on every row requires: valid/good definitions that exclude 4xx and count 503; targets with a
window and a reason tied to the client's behaviour (re-sends every minute) and to measured latency; a
budget computed from a stated traffic assumption; a paging rule with two windows per rule; a ticket rule
for slow burns; and an explicit statement that model quality and input drift are outside these SLOs.
The reference `SLO.md` is in `challenge/`.

*Common weak answers:* 99.99 % "because it sounds professional" (4.3 minutes per 30 days, unachievable
for a single-container prototype); latency SLO on the mean; one paging threshold on a 5-minute window;
no traffic assumption, so the budget has no units.

### Interview rep: rubric and worked answer

| Area | Strong answer includes |
|---|---|
| Per-request log | request id (propagated end to end), model version, decision, score, latency, rule outcome; NO raw card data or PII; sampled INFO for successes, all errors; a separate access-controlled capture for later labelling, joined by transaction id |
| Metrics | request counter by route/status/model_version; latency histogram with a bucket edge at 80 ms; in-flight / queue depth; score histogram and decision rate (block share) per model version |
| Paging | multi-window burn-rate on availability and on the 80 ms latency SLI; a page on a sudden change of the block rate (a broken model or feature can block everyone with no 5xx at all) |
| Not knowable on day one | precision and recall (chargebacks 30-90 days late); use proxy metrics (block rate, score distribution, manual review outcomes) and plan delayed evaluation |
| Cardinality and cost | no merchant or card id labels; per-merchant views from logs |

*Worked answer, condensed.* "Each request carries an id from the payment gateway; I log one access event
and one decision event with id, model version, score, decision, latency and the rule that fired, no card
number. Metrics: requests by status and model version, an 80 ms-edged latency histogram, in-flight, and
a score histogram plus decision counter per model version. I page on SLO burn for availability and
latency with two windows, and separately on the block rate leaving a band derived from last week,
because the most damaging failure (blocking all payments) returns 200. What I cannot know for 30-90
days is whether decisions are right, so I track proxies and schedule a delayed evaluation job joined on
transaction id."

---

# Notebook 38 — Input monitoring and drift statistics

✍️ Written answers: compare yours against the rubric; wording will differ.


### Reasoning questions

**1. Mean of sorted differences.** Equal to W1 only when both samples have the same size (then the
optimal transport pairs the i-th smallest values). With 60 against 9,000 it either fails or, if truncated
to the shorter length, compares the window with the 60 *smallest* reference values: a large, meaningless
distance. Use the CDF integral (or `scipy.stats.wasserstein_distance`). *Wrong answer:* "it is fine
because both are sorted".

**2. Sentinels out of the statistics.** A sentinel is not a measurement; it is a broken input with a
different cause (a producer bug) and owner. Included, it dominates the window: W1 moves by roughly
(share of sentinels) x 10,000 L/min, so the dashboard shows a huge "drift" on flow rate while the actual
flow distribution may be unchanged, and the real issue (a producer sending sentinels) is reported under
the wrong name. Count violations separately and exclude them.

**3. KS on 1 Hz data.** The test assumes independent observations; consecutive seconds are strongly
correlated, so the effective sample size is far smaller than 60 and the null distribution used for the
p-value is too narrow: false positives in most windows (worked example: 75 % at phi = 0.9). Use the KS
*statistic* (or W1) with a threshold calibrated on stable windows of the same sensor, which includes the
autocorrelation in the calibration.

**4. PSI and window size.** Under no drift, the expected PSI is approximately (k - 1)(1/n + 1/m): sampling
noise in the bin shares. Smaller windows have noisier shares and larger PSI; a fixed 0.1 is therefore
exceeded by most 60-sample windows and by almost no 480-sample windows (98 % at n = 30, 0 % at n = 480
in Figure 2).

**5. Replay, reference A.** The calibration windows were the development runs' normal operation, so the
thresholds absorbed the variation between those runs. A closing valve changes the one-minute
distributions of most sensors by less than that variation: no alert. The two `other` test runs operate at
a slightly different temperature / vibration level than any development burn-in, so every normal minute
exceeds the threshold: the monitor detects "new operating conditions", not faults.

**6. Price alert after a planned change.** Not necessarily. Drift says the input distribution moved;
accuracy depends on whether the model's learned relation still holds at the new prices and whether the
decision boundary is crossed more often. You need labels (delayed), or proxies such as the prediction
distribution and downstream business metrics; and you need to know whether the price range after the
change was represented in training. Annotate the change and re-baseline; evaluate when labels arrive (w7d3).

### Design-choice explanation (what a strong answer contains)

Per-machine reference (each run's first 5 minutes after start-up, or a rolling "last stable hour"),
one-minute windows (the detector's alarm granularity), W1 in sensor units with per-sensor thresholds
calibrated on stable data across many machines with a Bonferroni split over the 8 sensors, target about
1 alert per machine-day measured on held-out stable data. Separate schema and missingness counters with
their own alerts to the data owner. An alert means "this machine's inputs changed: check sensor or
process"; it does not mean "fault" (the detector decides that) and does not mean "the model is wrong"
(that needs labels). Optionally a daily fleet-level report against the development data for "outside the
validated domain".

### Interview rep: worked answer and rubric

1. $D = \sup_x |F_1(x) - F_2(x)|$. Under the null (same continuous distribution, independent samples) its
   distribution depends only on the sample sizes (distribution-free), which gives the p-value. Fails with
   autocorrelation (effective sample size), and with ties or discrete data the exact null changes.
2. Report an effect size in meaningful units: W1 or difference in means/quantiles in the feature's units,
   share of values outside the historical range, compared with a materiality threshold agreed with the
   product team. With 10 million rows every difference is significant.
3. Label reference rows 0 and current rows 1, train a classifier with cross-validation, measure AUC on
   held-out rows. 0.5: the classifier cannot tell them apart (no detectable change in the joint
   distribution it can model). 0.65: the samples differ; the model's feature importances point to where.
   Group-aware CV if rows are dependent.
4. A change in the relation between features (joint distribution) can leave every marginal unchanged,
   e.g. current and flow both normal but no longer correlated; and many small marginal changes can matter
   together while each stays under its threshold.

| Score | Criteria |
|---|---|
| Strong | all four correct, mentions independence and effect sizes, gives a concrete joint-shift example |
| Adequate | definitions right, misses why p-values fail or the classifier-test interpretation |
| Weak | equates significance with importance; cannot define the statistic |

### Challenge: common weak submissions

* Ignore the calendar: the price feature alerts for weeks after the planned change (alert fatigue).
* Suppress the feature forever: the unplanned price drop on day 50 is missed.
* PSI > 0.25 rule: misses the 10 % price drop (PSI about 0.1) and even the planned 12 % change.
* Monitor only the values present: a 30 % outage of `basket_size` is invisible.

---

# Notebook 39 — Drift is not degradation: delayed labels and measured performance

✍️ Written answers: compare yours against the rubric; wording will differ.


### 1. Shift types

* **Covariate shift**: $P(x)$ changes, $P(y \mid x)$ fixed. SKAB: the flow sensor is recalibrated, or the
  pump runs at a different set point.
* **Prior shift**: $P(y)$ changes, $P(x \mid y)$ fixed. SKAB: valves start failing more often (older
  parts), each failure looking as before.
* **Concept shift**: $P(y \mid x)$ changes. SKAB: a new fault mechanism (e.g. rotor imbalance) that leaves
  the flow rate untouched, or the plant redefines a fault to include short transients.

*Common wrong answer:* "concept drift = the data looks different". That is covariate shift; concept
shift can leave every input statistic unchanged.

### 2. Period B

The score is $\max_j |x_j - \mu_j| / \sigma_j$ with $\mu, \sigma$ estimated on each run's own burn-in.
Under $x' = a x + b$ with $a > 0$, $\mu' = a\mu + b$ and $\sigma' = a\sigma$, so every score is unchanged
(up to $10^{-14}$ rounding, which flipped 198 samples that sat exactly on the threshold but not which
faults were caught). A detector with *fixed* reference statistics (e.g. the w2d6 z-score against
development data, or a gradient-boosted model on raw levels) would see every sample shifted by
$(0.08\bar x + 2.5)/\sigma \approx (0.08 \cdot 32 + 2.5)/0.45 \approx 11$ standard deviations and alarm continuously: precision collapses.

*Common wrong answer:* "PSI was high so the model degraded but we got lucky." There was nothing lucky:
invariance to affine changes is a design property of per-run normalisation.

### 3. Period C's three numbers

* **Day 65, unknown.** Four alarms confirmed (four caught faults) and no missed-fault report had arrived
  yet (reports take 14-60 days). Four events is below `min_events = 5`.
* **Day 90, 0.67 [0.30, 0.90].** Two reports had arrived: 4 / (4 + 2).
* **Day 150, 0.36 [0.15, 0.65].** All 7 reports that will ever arrive: 4 / 11. The truth is 4 / 20; the
  9 missed faults that inspections never found are invisible. The estimate is an upper bound.

*Common wrong answer:* "the estimate converged, so it equals recall." It converged to $C / (C + \rho M)$
with $\rho \approx 0.6$, not to $C / (C + M)$.

### 4. Verification bias

Upward: the investigated alarms are those most likely to be true. Unbiased options: investigate a
**random** sample of the uninvestigated alarms as well (even 10 %), then weight each labelled alarm by
the inverse of its investigation probability (Horvitz-Thompson). Or investigate a random fraction of
all alarms instead of the top fraction. Report both the weighted estimate and the counts.

### 5. Window sizing

±0.10 needs about 90 faults of known outcome near recall 0.6 (Wilson). At 2 faults a week that is
about 45 weeks per window, and each answer is available 60 days after the window closes. Conclusion:
recall cannot be monitored on a useful cadence; use a fast proxy (alert rate, precision under a fixed
alert budget, operator feedback) for detection and recall for quarterly confirmation, and say so.

*Common wrong answer:* "a weekly window". It holds two faults.

### 6. Event time versus label time

* Window by event time, existence by label time (correct): each period is judged on its own events,
  with only the evidence available on that day.
* Window by **label** time: a fault from January confirmed in March counts in March. Degradation appears
  in the wrong period and is smeared over the delay distribution.
* Existence ignored (all labels used): a back-test sees labels that had not arrived; the monitor looks
  faster and more certain than it can be in production (the `ignores_as_of` mutant).

### 7. Inconclusive instead of a point comparison (design choice)

A point comparison turns noise into decisions: with 20 faults per period, the same model's recall
estimate moves by ±0.2 between periods. Comparing it with `baseline - 0.1` would raise false
"degraded" alarms and miss real drops at random. "Inconclusive" says what the evidence supports. To the
manager: green means the evidence shows the model is not worse by more than the margin; red means it
shows it is; amber means not enough evidence yet, with the date by which there will be. The cost: slower
and rarer red lights, and more ambers when events are rare; the remedy is longer windows or a faster
proxy, not a looser rule.

### Interview rep: churn dashboard (rubric and worked answer)

**Worked answer (outline).** The label (cancelled within 90 days) arrives 90 days after each
prediction, so "is the model still accurate this week" is not answerable this week. Show four panels.
(1) **Input validity**: share of requests rejected or imputed. (2) **Input and score drift**: calibrated
PSI on the top features and on the score distribution, plus the share of customers above the action
threshold, labelled as "inputs changed", not "model broken". (3) **Delayed performance**: AUC, precision
at the retention team's capacity, and calibration for the cohort predicted 90-120 days ago, with
intervals and the cohort size; earlier cohorts shown as "pending". (4) **Selection effects**: customers
who received a retention offer were treated, so their outcomes are not the model's untreated outcomes;
keep a random holdout without offers to measure the model honestly. Actions: drift → investigate;
measured drop → escalate; pending → wait. Mention seasonality (prior shift in churn) and that precision
moves with prevalence.

**Scoring.** 0-3 with the rubric in `assessment.md`. A 3 must mention the 90-day delay and pending
cohorts, intervals with counts, the treatment/holdout problem and one fast proxy with its failure mode.

---

# Notebook 40 — Model updates: retraining triggers, shadow and canary, rollback

✍️ Written answers: compare yours against the rubric; wording will differ.


### 1. Triggers and when they mislead

* **Scheduled** (e.g. quarterly): fires when nothing changed; a retrain on fresh data may only add
  variance. Gate it like any other candidate.
* **Measured degradation** (labelled metric below baseline, w7d3): may be a pipeline bug or a label change,
  not a model that needs new data; retraining on corrupted inputs bakes the bug in.
* **Drift**: the w7d3 recalibrated sensor moved PSI 9-13x past its threshold while the detector caught the
  same faults; retraining would have fitted the model to a calibration offset for nothing.
* **New data or features available**: fires on opportunity, not need; the new feature may not be
  available at serving time (2.0.0's accelerometers).

### 2. A lower end of exactly zero

1.1.0 catches valve1/8 in addition to everything 1.0.0 catches and misses nothing that 1.0.0 catches.
Per experiment the difference is +1 on one experiment and 0 on six. A paired resample can omit valve1/8
(difference 0) but can never produce a negative difference, so the 2.5th percentile is 0.000.
Superiority needs $L > 0$: reject. Non-inferiority with margin 0.05 needs $L > -0.05$: promote.
The data cannot show a one-fault improvement on 7 experiments; the choice is a policy decision, and
non-inferiority is justified only because the stakeholder explicitly accepted the higher alert budget.

*Common wrong answer:* "the bootstrap is broken because 0 is suspicious". It is the correct consequence
of a one-sided pattern of differences.

### 3. 2.0.0 dev versus test

(a) **Overfitting the operating point**: the threshold and post-processing were chosen on 27 development
experiments, with `merge_gap = 0` selected; with three sensors the grid has more ways to fit noise.
(b) **Shift between development and test experiments**: the accelerometers behave differently in the
test recordings (sensor-specific variation across runs), so the max over sensors fires late or not at all.
Distinguish them with grouped cross-validation inside development data (w3d2): if 2.0.0 also collapses
on held-out development folds, it is (a); if it holds on development folds but not on test, look at the
accelerometer distributions of the test runs (b).

### 4. Shadow coverage

The shadow traffic was 20 valve recordings, and 16 of them are development data 1.1.0 was tuned on. All
5 of 1.1.0's development false alarms happened in the `other` family, which the shadow never saw. And the
shadow labels were added afterwards from the dataset; in production, shadow outputs have no labels for
weeks. Shadow shows that the candidate runs and where it disagrees; the budget is checked on the traffic
that contains the risky slices, with the canary's alert-rate bound.

### 5. Canary and rare events

About 0.2 faults per week reach the canary machines (10 % of 2): almost surely zero or one. The canary
says nothing about recall. Its stopping rule watches what happens often: serving errors, latency
percentiles, alert rate per machine-hour (against the budget, with exact Poisson bounds), input
validation failures. Recall was decided by the offline gate and will be confirmed later by delayed labels.

### 6. Order and atomicity

* **Audit after the move**: if the pointer move fails (disk full, permissions) and the audit was written
  first, the log claims a promotion that never happened; the next rollback then "restores" a version
  based on a false history.
* **Atomic move**: writing the pointer in place truncates it first; a crash between truncation and write
  leaves an empty or partial pointer, and the service cannot start or loads a nonexistent version.
  `os.replace` of a fully written temporary file means readers see either the old pointer or the new one.

### 7. Rollback as a stack (design choice)

Sequence: promote 1.0.0, promote 1.1.0, rollback, rollback. With "go to the `from` of the last entry",
the first rollback goes 1.1.0 → 1.0.0 (correct) and writes `from 1.1.0, to 1.0.0`; the second rollback
then reads `from 1.1.0` and **re-deploys 1.1.0**, the version that was just removed, perhaps at night by
an on-call engineer who expected to go further back. With the stack, the second rollback finds that the
only remaining promotion has `from None` and refuses, which is the honest answer: there is nothing older
to return to. The stack also makes the meaning of "rollback" independent of how many rollbacks happened.

### Interview rep: fraud model rollout (worked outline)

1. **Contract and artifact.** Bundle model + threshold + feature schema + preprocessing as one immutable
   version; check the serving contract (features available within 50 ms) before anything else.
2. **Offline gate.** Paired comparison on the same held-out, time-ordered transactions (later than
   training), predeclared policy; guardrails: false-positive rate at the operating point (customer
   friction), p99 latency measured on the serving path; slices: merchant category, card-not-present,
   new customers.
3. **Shadow** for one to two weeks on full traffic: disagreement analysis, latency and error budget of the
   candidate, feature-availability errors. Outputs unlabelled; chargebacks arrive in 30-90 days.
4. **Canary** at 1-5 % with automatic stop on latency, errors, alert/decline rate bounds, with the
   repeated-looks problem handled (alpha spending or a minimum exposure).
5. **Promote** by pointer move with audit; keep the previous version warm.
6. **Rollback**: one command or an automatic guardrail breach, audited, compatible with today's schema;
   practised before it is needed.
7. **After**: delayed-label evaluation of the new model against the old one's history; a review date.

Score with the rubric in `assessment.md`; a 3 mentions label delay, what the canary cannot measure, and
versioning the threshold and features with the model.

---

# Notebook 41 — Reliability and failure handling

✍️ Written answers: compare yours against the rubric; wording will differ.


### 1. The units bug the model cannot see

The score is `|x − mean(b)| / sd(b)` where `b` is the experiment's burn-in. Multiplying every value by
`c > 0` multiplies the numerator and the denominator by `c`, so every score is unchanged:
`|c·x − c·mean(b)| / (c·sd(b)) = |x − mean(b)| / sd(b)`. Same scores means the same 313 alarms. Only the
training-support guard (`out_of_support`, 1,140 of 1,140 values flagged, counter
`flowguard_out_of_support_total 1140`) sees it, because it compares raw values with the 0.56 to 133.69 L/min
range of development data. A model on raw values (a fixed threshold, a tree on absolute features) would
*not* be blind. It would fire everywhere, which is loud but just as wrong, and support checks are still the
cleaner signal.

*Common wrong answers.* "The model is robust to units, so no problem": the plant's decision may be fine
today, but every downstream consumer of the raw values (dashboards, the fallback rule, drift monitors) is
wrong, and the next model may not be scale invariant. "Validation would catch it": the values are
finite, in schema and plausible-looking numbers. Only knowledge of the training distribution catches them.

### 2. Liveness vs readiness with a bad bundle

Restarting reloads the same bad bundle, so a failing liveness probe cannot fix it. If `/healthz` failed
on the bundle, the orchestrator would restart all 3 instances in a loop: a crash loop with no answers at
all, not even the fallback. If `/readyz` returned 200 without a model, the load balancer would keep
routing to instances that can only give fallback answers, and the rollout gate (w6d6) would never stop the
bad release. With the lesson's choice, all 3 instances report not-ready, so the rollout halts or
rolls back. Callers that still reach an instance get explicit `degraded` answers. The alert on readiness
is the signal to roll back.

*Common wrong answer.* "Both should fail, the service is broken". This loses the fallback and creates the
crash loop.

### 3. Deadlines and the bulkhead

Yes. Python threads cannot be killed, so the model call keeps running after the deadline answer.
The slot must be released when the *work* ends (the future's done-callback), not when the response is
sent. Otherwise, during a slow-dependency incident each request gets a fast deadline answer and frees
its slot while its model call keeps running. In-flight work grows without bound, CPU contention makes
every call slower, and the bulkhead protects nothing (mutant `slot_released_on_response`).

### 4. Delays

* After the `429` with `Retry-After: 1`: exactly 1.0 s (below the 5 s cap).
* After the `503` without the header (retry index 1): uniform in [0, min(5, 0.2·2¹)] = [0, 0.4] s.
* After the read timeout (retry index 2): uniform in [0, 0.8] s.

*Common wrong answer.* Using the Retry-After value for later retries, or starting the exponential at
index 1 for the first retry. The contract counts the first retry as index 0.

### 5. What to retry

Retry: 429, 502, 503, connection refused (and 504). Do not retry: 400, 409, 413, 422, 500.

* **409 Conflict**: it means the request conflicts with the current state (for example the same
  idempotency key with a different body). The same request will conflict again.
* **500**: for this service a 500 means a bug. The known failure modes are answered with explicit
  degradation, so a 500 is deterministic for that input, and retrying multiplies the damage. Some
  systems retry 500 once. If you do, make it part of a bounded, jittered policy and only for idempotent
  calls.

### 6. "Just use the fallback"

The fallback is a safety net with a measured cost. On the 7 frozen test experiments it detected 2 faults
against the model's 5, so it would have missed 3 of the 5 faults the model caught. Point recall drops from
0.270 to 0.234. Zero false alarms for both means it is not noisier, only blinder. Nobody would notice,
which is the problem: a quiet stretch would be read as "healthy". So the answer is to keep the fallback,
always flag it, alert when the degraded rate exceeds a small threshold, and fix the slow model
(w6d4: threads, deadlines), not the flag.

### Design-choice explanation: model answer (about 200 words)

A model failure in flowguard is a *known* state with a defined answer: the envelope rule. Returning `200`
with `degraded: true` and a reason gives the caller something to act on (show "monitoring degraded" on
the plant dashboard, apply a stricter manual check) instead of an error page. It keeps the caller's own
error handling for real errors, and it does not provoke retries: clients retry 503s, and retrying a
failing model only adds load. The degraded counter and log event keep it visible to operators, and
readiness 503 handles routing.

The strongest argument for `503`: a 200 can be consumed by a caller that ignores the new field. That
caller treats the fallback's silence as health, which is exactly the silent wrong answer we wanted to
avoid. A status code is much harder to ignore than a JSON field.

I would switch to `503` (or a dedicated status) when callers cannot be relied on to read `degraded`:
third-party integrations, or a consumer that automatically acts on `above_threshold`. Then failure must be
loud. The same applies if the fallback's cost becomes unacceptable for the decision. A fallback catching 2
of 7 faults may be too weak for a safety function.

### Interview rep: worked answer and rubric

**Likely story.** Something made the feature store slightly slower at 14:02, perhaps a heavy query or a
noisy neighbour. "Nothing changed" is common and not evidence. The scoring service had no deadline on
the feature call, so its threads blocked and p99 rose to 9 s. Checkout timed out and retried, probably
immediately and several times, so traffic to scoring multiplied, and so did traffic to the feature store,
which reached 100 % CPU: a positive feedback loop. The 14:30 restart dropped the in-flight work, but every
instance came back cold at the same moment, all clients retried in lock-step, and the cold caches added
load. That explains "worse for 10 minutes". It recovered once retry budgets ran out and the feature
store caught up.

**Changes, by priority.**
1. Deadline on the feature call, with a bulkhead around it, and explicit degraded answers.
2. Clients: bounded retries with full jitter, honouring `Retry-After`; retry only 429/503/transport errors.
3. Load shedding with 429 so overload is visible and cheap.
4. A circuit breaker around the feature store.
5. Rolling restarts, not all at once, with readiness gating.
6. Alerts on shed rate, degraded rate and dependency latency, and a runbook entry.

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Identifies the feedback loop (timeouts → retries → more load) | missing | mentions retries | explains amplification with the timeline |
| Explains why the restart made it worse | missing | "restarts are risky" | synchronised retries plus cold start |
| Deadlines and bulkheads | missing | one of them | both, and why a deadline alone is not enough |
| Retry discipline | missing | "add backoff" | bounded, jittered, honours Retry-After, idempotency |
| Prioritises and verifies | list only | some order | ordered, with how to test each (fault injection) |

8-10: strong; 5-7: adequate, review 2.4-2.5; below 5: redo the lab's task 2 and the worked example.

---

# Notebook 42 — Project milestone 4: monitoring demonstration and runbook

✍️ Written answers: compare yours against the rubric; wording will differ.


### 1. False alarms implied by the threshold

If the 27 development windows and a new healthy window are exchangeable (drawn from the same population
of healthy experiments), each of the 28 is equally likely to be the largest. A new healthy window therefore
exceeds the maximum of the other 27 with probability 1/28, about 3.6 % per window. If that is too many:
use a higher quantile with more calibration windows (split experiments into shorter windows, accepting
their autocorrelation); require persistence (two consecutive windows above); or, better here, change what
is monitored so that healthy machines are not far from the reference (per-machine references, normalised
values). Raising the threshold by hand without data is not calibration.

*Common wrong answer.* "Max means no false alarms." It means no false alarms *on the calibration set*.
Figure 2 shows a healthy test experiment at 7.38 against 7.53.

### 2. Units bug: which alert

`out_of_support` names the cause (values outside the physical range seen in development: 560 of 560) and
is specific: drift fires for any distribution change, including legitimate ones (E3). The alarm rate does
not change because the burn-in z-score is scale invariant: multiplying values and burn-in by 60 leaves every
score unchanged (w7d5).

### 3. The missed fault

Only labels reveal it: the inspection of `valve1/8` weeks later (E6 counts it as a missed fault). No
proxy fired because, to the detector, the fault looks like normal operation (alarm share 0.0009, PSI 4.04,
in support). The report lists it as "not detected" because the purpose of the demo is to show what the
monitoring can and cannot see; dropping it would turn a known limitation into a hidden one.

### 4. "Rollback = edit CURRENT"

* The running process still serves the bad model → restart, then `GET /version`.
* The old process may still be running beside the new one → stop it; check `pgrep`/the pid list.
* The new process may not be ready (bundle missing, checksum) → wait for `/readyz` 200 before routing traffic.
* Other instances may not have been restarted → check `/version` on each.
* The rollback target may be wrong (rolled back twice, or to a version that was never good) → read
  `HISTORY.jsonl` and state the target explicitly.

### 5. Recall from 2 faults

1 of 2 detected: a 95 % Wilson interval is roughly 0.09 to 0.91 (w3d5), so it is almost uninformative.
"Labelled traffic only" warns of verification bias: inspections are not random. Machines with alarms are
more likely to be inspected, so detected faults get labels faster than missed ones, and recall measured on
labelled traffic is biased upward (w7d3).

### Interview rep: model answer (5 minutes) and follow-ups

**Structure.** Separate what I can see *now* from what I can see *when labels arrive*.

*Now, without labels:*
1. Service health: readiness, error and degraded rates, latency, shed rate. A broken model often shows up
   here first.
2. Inputs: schema violations (rejected at the edge), values outside the training support (counted), drift
   against a reference calibrated on healthy data. These say the model is being asked about
   something new, not that it is wrong.
3. Outputs: alarm rate per machine against the budget the business accepted. A jump right after a release
   points to the release. On a single machine it is more likely a real fault or a sensor.

*When labels arrive:* event recall, false alarm events per hour and detection delay on inspected
machines, with intervals. Account for verification bias: inspected machines are not a random sample.

*Process:* every signal has an alert with a runbook entry, a scripted replay proves each alert fires,
and releases are reversible: rollback by restart, confirmed with `/version`.

*Honest limits:* some failures look like normal operation to every proxy (our E5). Only labels catch those,
weeks later. In this project the drift monitor has a thin margin (a healthy experiment at 7.38 against a
threshold of 7.53).

**Follow-ups an interviewer may ask**
1. Your drift alert fires; what do you do? (Check for an intended operating change; look at alarms on that
   machine; do not retrain on reflex.)
2. How did you choose the alarm-rate budget? (From the alert budget the stakeholder accepted, 1 false alarm
   per 8 h, measured on development data.)
3. Why not monitor accuracy directly with a sample of labelled data? (Cost and delay. Do it, but randomise
   which machines are inspected to avoid verification bias.)
4. What if drift and alarm rate both fire after a release? (Roll back first, then investigate.)
5. How do you avoid alert fatigue? (Calibrate on healthy data, require persistence, route by severity, delete
   alerts nobody acts on.)

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Separates proxies from labelled performance | no | implicitly | explicitly, with the delay |
| Concrete signals with thresholds and their origin | none | named only | named with how they are calibrated |
| Drift vs degradation | conflated | mentioned | explained with an example |
| Labels: coverage and bias | ignored | coverage mentioned | verification bias explained |
| Operability (alerts, runbook, rollback verified) | absent | partial | complete and tested |

8-10 strong; 5-7 adequate; below 5: reread section 2 and the runbook.

---

# Week 7 review day — Review and catch-up (light)

✍️ Written answers: compare yours against the rubric; wording will differ.


Open only after all twelve answers have an attempt. Score each answer **solid** (the core point and the
mechanism, numbers approximately right), **shaky** (the core point without the mechanism, or a wrong
number that changes a conclusion) or **missing**. Each answer lists the common wrong answers and why they
fail. Numbers come from the Week 7 lessons' authoring runs (2026-11-22); real SKAB results use the frozen
v2 manifest (7 test, 27 development experiments).

---

### 1. Metrics, logs, traces; request ids; the crash path (w7d1)

* **Metrics** answer "is the service healthy, is it getting worse?": pre-aggregated counts, sums,
  buckets, current values; cost grows with the number of label combinations (series), not with traffic.
  Alerts are written on them. **Logs** answer "what happened to this request / machine / version?": one
  structured event per thing that happened; cost grows with traffic. **Traces** follow one request across
  several services; `flowguard` is one process, so it stops at a correlation id (`X-Request-ID`).
* **Never count log lines for an error rate**: access logs are often sampled at high traffic (say 1 in 100
  for 2xx), a refactor can change a log level or message, and counting is slow. Counters are exact.
* **Never a request id as a label**: each distinct value is a new time series stored forever (cardinality).
  Labels must come from small fixed sets (route template, status, method, model version). Unknown paths
  are labelled `unmatched`, so a scanner hitting random URLs does not create a series per path.
* **Crash path**: in Starlette the `Exception` handler lives in `ServerErrorMiddleware`, *outside* your
  middleware, so when the handler raises, `call_next` raises instead of returning a 500 response.
  Bookkeeping written only after `call_next` gives three symptoms: no access-log line for the crashed
  request, no 500 in the request counter, and an in-flight gauge that leaks one unit per crash. Fix: one
  `try/finally` around `call_next` (count, observe latency, decrement in-flight, write the access line),
  then let the exception propagate. 422 and 404 do come back as responses, because their handlers are in
  the inner `ExceptionMiddleware`.

Common wrong answers. "Logs and metrics are interchangeable" (they answer different questions at different
cost). "Add the request id as a label so you can drill down" (that is what logs are for). "Wrap `call_next`
in `try/except` and return a 500 yourself" (works, but duplicates the outer handler and is not what the lab
asks; the essential point is that bookkeeping must run on the exception path).

### 2. Buckets, percentiles, error budgets, the replay (w7d1)

* `x_bucket{le="0.05"} 38`: 38 observations were **less than or equal to** 0.05 s. Buckets are
  cumulative, so the series never decreases; the mandatory `le="+Inf"` bucket equals `_count`.
* Worked example (SYNTHETIC; instance A 9,000 requests around 20 ms, B 1,000 around 300 ms): mean of the
  two p99s **528.9 ms** (not a percentile of anything), true p99 of all 10,000 **587.9 ms**, estimate from
  summed buckets **721.9 ms** (in the right 500-1,000 ms bucket, interpolated high because interpolation
  assumes a uniform spread inside the bucket). The share slower than 250 ms (6.7 %) was exact because
  250 ms is a bucket edge: put edges at SLO thresholds. Percentiles cannot be averaged; bucket counts can be
  summed.
* Error budget: `(1 - 0.995) x 1,728,000 = 8,640` bad requests per 30 days. Burn rate = observed bad
  fraction / (1 - target); 1 spends exactly the budget over the window; 14.4 for one hour spends 2 % of a
  30-day budget (14.4 / 720). Multi-window: page only when a long window (enough evidence) **and** a short
  window (still happening) both burn fast. On the synthetic month, a 3-hour partial outage paged for 168
  minutes, a 4-minute total outage did not page, and the month ended with 42 % of the budget spent.
* Replay: `in_flight` was 1 because the scrape itself is a request in flight while the registry renders.
  `flowguard_predicted_samples_total` counts samples **processed**, and the plant client re-sent the run so
  far every 60 samples, so the same seconds were scored repeatedly: 2,624 "exceeding" are not 2,624
  distinct anomalous seconds.

Common wrong answers. "Each bucket counts observations in its interval" (that is the per-bucket view, not
what `/metrics` serves). "Average the instances' p99s" (meaningless). "Page when the 5-minute error rate
exceeds the SLO" (pages on every blip). "`in_flight` should be 0, so something leaks" (not here: the scrape).

### 3. Three questions; KS, W1, PSI (w7d2)

* **Schema violation** (a `-9999` sentinel, an infinity, a physically impossible value): a broken input;
  owner the data producer; counted, rejected or quarantined, and **kept out** of the statistics, because one
  sentinel moves a Wasserstein distance by hundreds of units and hides what the other rows do.
  **Missingness** (NaN): a sensor or pipeline failure; reported as a share per sensor, not as drift.
  **Distribution shift** of values that pass both checks: evidence that something changed, not that the
  model got worse.
* **KS**: `D = sup |F_R(x) - F_C(x)|`, unitless, invariant to monotone transforms, most sensitive to
  location shifts near the middle. **Wasserstein-1**: `∫ |F_R - F_C| dx`, in the sensor's own units; a
  pure shift by δ gives exactly `|δ|`, which makes thresholds explainable. **PSI**: bins at the
  reference's deciles, shares p and q floored at ε = 1e-4, `Σ (q - p) ln(q / p)`, the symmetric
  (Jeffreys) divergence `KL(q||p) + KL(p||q)`.
* Floor: a window whose values all lie above the reference maximum leaves nine empty bins, where `ln(0)`
  is `-inf`. Dropping those terms with `nansum` removes exactly the bins that carry the evidence of drift
  (the lab's `psi_without_floor` mutant).

Common wrong answers. "Treat NaN as drift" or "include violations and let the statistic catch them"
(mixes owners and hides real shifts). "KS is in the sensor's units" (W1 is). "PSI is a test with a known
false-alarm rate" (it is a description; the rate comes from calibration).

### 4. Why p-values and PSI folklore fail; calibration; the real replay (w7d2)

* KS with no drift, share of windows with p < 0.05 (reference 2,000, windows of 240, AR(1) data):
  **5.5 %** at φ = 0, **21.8 %** at 0.5, **75.0 %** at 0.9, **98.5 %** at 0.98. The test assumes
  independent observations; autocorrelated windows hold far fewer independent pieces of information, so
  the test is overconfident. Large samples have the opposite problem: **p = 3.1e-8** for a W1 of
  0.011 °C between two 200,000-sample sets, a difference below any thermometer's resolution.
* PSI under no drift grows like `(k - 1)(1/n + 1/m)`, so its false-alarm rate depends on window size: with
  i.i.d. data and a 5,000-sample reference, **98.2 %** of 30-sample windows exceed 0.1 and **0.0 %** of
  1,440-sample windows.
* Calibration: replay windows you consider stable, set each sensor's threshold at the quantile giving the
  false-alarm rate you can afford, and report the rate measured on held-out stable windows. With m sensors
  alerting on "any", split α across them (Bonferroni, α/m each): on the lab's 4-sensor synthetic data,
  **2.75 %** of held-out stable windows alerted with the correction and **13 %** without.
* Real SKAB, one-minute windows of the 7 test runs: reference **A** (pooled development burn-ins) alerted
  on **21 %** of normal windows (8 of 8 in the two `other` runs, whose temperature or vibration lies slightly
  outside anything in development) and **14 %** of fully anomalous windows (5 of 35); reference **B** (each
  run's own burn-in) on **3 %** of normal (1 of 38) and **20 %** of anomalous (7 of 35). The w4d5 detector
  catches 5 of 7 test faults. A calibrated drift monitor tolerates the variation between experiments, and a
  closing valve is smaller than that variation in most sensors' one-minute windows: drift monitoring does
  not replace fault detection. Counts are small (38 and 35 windows from 7 runs); the conclusion does not
  depend on the second decimal.

Common wrong answers. "Use a smaller α" (does not fix dependence). "0.25 is the industry standard" (a
convention whose meaning depends on n and m). "Calibrated to 5 % means 5 % in production" (the in-sample
rate was 0 % and the test runs gave 21 % under A; report held-out rates).

### 5. Kinds of shift; drift without degradation and the reverse (w7d3)

* **Covariate shift**: P(x) changes, P(y | x) does not (a recalibrated sensor). **Prior shift**: P(y)
  changes, P(x | y) does not (more faults this season; precision at a fixed threshold moves). **Concept
  shift**: P(y | x) changes (a new fault mechanism, a new definition of "fault"); input statistics may not
  move at all.
* Period B (flow sensor 1.08x + 2.5): PSI of **6.1-8.9** in every window, 9-13 times its threshold of
  **0.660**, and the detector caught **the same 11 of 20** faults as in period A. Reason: the burn-in
  z-score `|x - mean| / sd` is invariant to `a x + b` with a > 0. Drift without degradation.
* Period C (a release that doubled the threshold, 14.49 instead of 7.24): recall fell from **11/20 to
  4/20**, inputs identical to period A, so the drift monitor said exactly what it said for A. Degradation
  without drift.
* 198 samples scored **exactly** at the threshold (the flow sensor is quantised and the w4d5 operating
  point was chosen from score quantiles), so a 1e-14 rounding from the recalibration flipped their flags
  and changed one alarm's extent, not which faults were caught. Put thresholds between distinct score
  values.

Common wrong answers. "A large drift means the model is broken" (period B). "No drift means the model is
fine" (period C). "Covariate shift never harms a model" (it harms one that extrapolates badly; this
detector is invariant by construction).

### 6. Biased labels, as-of evaluation, power (w7d3)

* **Precision from investigated alarms** estimates P(y = 1 | investigated), not P(y = 1 | alarm). When
  investigation follows the score and P(fault | score) rises with the score, it is biased upward. With a
  random or known investigation probability the bias vanishes or can be corrected (inverse-probability
  weighting).
* **Recall from reported misses**: `C / (C + M_reported)` with `E[M_reported] = ρ M`; for ρ < 1 it
  overestimates recall, so it is an upper bound, and early in the label delay it is more optimistic still.
* **As-of rule**: a metric "as of day d" uses only labels with `label_time <= d`. Without it, a back-test
  sees the future.
* Power: Wilson 95 % half-width about `1.96 sqrt(r (1 - r) / n)`; at r = 0.6, about **±0.20 at 20 faults**
  and **±0.10 only at about 89**. A window needs enough labelled events, not enough samples.
* Period C (truth 4/20 = 0.20): **unknown** on day 65 (no missed-fault report yet), **0.67** on day 90,
  **0.36 [0.15, 0.65]** on day 150, so the rule said "inconclusive", because the interval overlaps the
  baseline 0.61. Period B showed the opposite failure: an early, optimistic "yes" (0.85 on day 65).
* Fraud worked example (SYNTHETIC): when half the fraud started scoring like legitimate traffic, recall
  halved (0.55 → 0.27), the PSI of the score distribution stayed at 0.001, recall estimated a week later
  said 1.00, and **precision of the reviewed alerts** (0.29 → 0.13) moved within a week. It worked because
  the number of alerts was fixed by design (a top-40 budget). With a fixed **threshold**, the same shift
  shows up as fewer alerts, not lower precision.

Common wrong answers. "Reviewer confirm rate is the model's accuracy." "Wait for enough samples" (events
are the unit). "Inconclusive means no degradation" (it means the data cannot tell yet).

### 7. The gate (w7d4)

* Superiority: promote if `L > 0`. Non-inferiority with margin δ: promote if `L > -δ`. Otherwise reject.
* Pairing: `Var(ā - b̄) = Var(ā) + Var(b̄) - 2 Cov(ā, b̄)`; when difficulty is shared across models the
  covariance is large and the interval shrinks. Worked example (SYNTHETIC, 40 stores): paired
  **[+0.046, +0.133]**, unpaired **[-0.029, +0.208]** for the same difference.
* Real gate on the 7 test experiments: 1.1.0 (re-tuned to 1 false alarm per hour) recall 0.714 → 0.857,
  difference **+0.143 [+0.000, +0.429]**: **promote** under non-inferiority, **reject** under superiority.
  The lower end is exactly 0 because 1.1.0 catches one more fault (valve1/8) and misses none, so no
  resample can be negative; with 7 experiments a one-fault improvement cannot be demonstrated. Promoting is
  a decision to accept the stakeholder's new alert budget, and the audit log says so.
* 2.0.0: (1) **worse**: recall 0.714 → 0.143, difference -0.571 [-0.857, -0.143], and slice regressions
  (other 0.00 against 1.00, valve1 0.25 against 0.75), although on development data it looked marginally
  better (12/27 against 11/27); (2) **incompatible**: it needs `accelerometer1_rms` and
  `accelerometer2_rms`, which the serving contract does not carry, so `promote` refused it before anything
  moved.
* Versioned together: model parameters, threshold and post-processing, input schema, preprocessing. A
  threshold changed outside the bundle is an unversioned model.

Common wrong answers. "The gate passed, so it is better" (non-inferior is not better). "Compare the two
models' separate intervals" (unpaired, much wider). "Promote 2.0.0, it was better on development data."

### 8. Shadow, canary, rollback (w7d4)

* **Shadow**: the candidate scores real inputs, its outputs are logged, never served. It measures
  operational behaviour (errors, latency, alert volume, disagreements) on real traffic without risk. It
  does not measure performance: without labels, disagreement is not error.
* Real shadow run (20 valve recordings): 1.1.0 differed in 15 of 20 runs and raised 4 alarms 1.0.0 did
  not (afterwards all 4 were on real faults; 15 of 20 faults caught against 11), served responses
  identical to current. Two coverage problems: all 5 of 1.1.0's development false alarms occurred in the
  `other` family, which this shadow traffic never contained; and 16 of the 20 recordings were development
  data that 1.1.0 was tuned on. A shadow period must cover the slices where the candidate behaves
  differently.
* **Canary**: a fraction f of traffic for time T at event rate λ sees about `f λ T` events; for a fault
  detector that may be zero faults, so a canary bounds frequent guardrails (errors, latency, alert rate) far
  better than recall. Each look at accumulating data is another test.
* Guardrail evidence: 0 false alarms in **1.22** normal test hours gives an exact Poisson 95 % upper bound
  of about **2.5 per hour**, above the budget of 1 per hour; on development data 1.1.0 raised 5 in 5.0 h,
  exactly the budget it was tuned to. The test set cannot confirm the guardrail.
* Reload endpoint: token from `FLOWGUARD_ADMIN_TOKEN` read at request time from the environment (never a
  file in the repository), compared with `hmac.compare_digest`; unset → 403, wrong token → 401.
  Rollback = registry pointer to the previous version + reload; the API's response for valve1/8 after
  promote → reload → rollback → reload was identical to the original, and the audit log reads
  `promote None→1.0.0`, `promote 1.0.0→1.1.0`, `rollback 1.1.0→1.0.0`.

Common wrong answers. "Shadow proves the candidate is better." "A one-week canary at 10 % will measure
recall." "Rollback means retraining the old model."

### 9. Three failure kinds; units bug; liveness versus readiness; fallback (w7d5)

| Kind | flowguard example | Caller should see |
|---|---|---|
| Down | bundle missing, checksum mismatch | `/readyz` 503, `/healthz` 200, fallback answers flagged `degraded` |
| Slow | model call stuck behind a starved CPU | a deadline answer flagged `degraded`; `429` + `Retry-After` when too much work is in flight |
| Silently wrong | NaN scores; flow sent in L/h instead of L/min | `degraded` (NaN) or the values listed in `out_of_support` (units) |

* Units bug: the burn-in z-score is invariant to scaling the input, so ×60 gives **exactly the same 313
  alarms** on valve1/13; only the support guard, comparing raw values with the range seen in development
  data, noticed it (**1,140 of 1,140** values out of support).
* Corrupt bundle: `/healthz` 200 (the process can answer; a restart would reload the same bad bundle, and a
  liveness probe that checks the model turns one bad artifact into a crash loop), `/readyz` 503 (do not send
  traffic; a rollout gate stops).
* Test set: model **5 of 7** faults, fallback envelope rule **2 of 7**, neither with false alarm events. The
  fallback is a safety net with a known cost; a consumer who knows an answer is degraded can treat a quiet
  stretch as "unknown" rather than "healthy".

Common wrong answers. "Return 500 on any model problem" (hides the difference between a bug and a known
degraded mode; clients retry 500s). "Clip out-of-range values" (turns an extrapolation into a confident
answer about a different input). "Liveness should check the model."

### 10. Retries, jitter, deadlines, bulkheads (w7d5)

* Retry: connection refused, read timeout, `429` and `503` (after `Retry-After`), `502`, `504`. Never:
  `400`, `404`, `409`, `413`, `422` (the same request fails the same way). `500`: not here (may be a
  deterministic bug).
* Full jitter: delay before retry k uniform in `[0, min(cap, base · 2^k)]`. `Retry-After` from the server
  wins, capped at the client's maximum delay. Attempts are bounded; extra load is at most
  `max_attempts - 1` times the original, and only while failures last. Side-effecting requests need an
  idempotency key reused across attempts.
* Retry storm (SYNTHETIC; 200 clients, 2 s outage, capacity 20 per 100 ms, 10 attempts, base 0.1 s, cap
  6.4 s): immediate retries **2,000 requests, 0 served**, all 200 gave up; exponential without jitter
  **1,800 requests, 100 served, 100 gave up**, with all 200 clients arriving in the same 100 ms bucket (10
  times capacity) at each step; full jitter **1,385 requests, all 200 served by 8.05 s**, never more than
  **17** per bucket after recovery.
* A deadline frees the **caller**; the model call keeps running in its worker thread (Python cannot kill a
  thread). So the bulkhead slot is released in the future's **completion callback**, not when the answer is
  sent; the check: with `max_inflight = 1`, a 0.8 s model and a 0.1 s deadline, the second request is shed
  with 429 until the first call ends.
* Little's law `L = λ W`: at 20 requests/s, 50 ms gives L = 1; 1 s gives **L = 20**. A bulkhead of 4 sheds
  beyond 4 concurrent calls, and the shed rate becomes an alertable signal of the slowdown.

Common wrong answers. "Retry everything, three times" (multiplies a persistent failure). "Exponential
backoff is enough" (deterministic schedules re-synchronise clients). "The deadline cancels the work."

### 11. The eight events (w7d6)

| Event | Problem | Expected signal |
|---|---|---|
| E1-normal | none | none (an alarm is a false alarm) |
| E2-units-bug | client sends L/h (×60) | `out_of_support` |
| E3-input-drift | pump at 80 % flow | `drift` |
| E4-fault | real valve fault (valve1/13) | `detector` |
| E5-fault | real valve fault the model is known to miss (valve1/8) | `detector` |
| E6-labels | inspection results arrive | `delayed_eval` |
| E7-bad-promotion | threshold typed as 1.5 | `alarm_rate` |
| E8-rollback | recovery | `version_restored` |

* E2: the z-score is scale invariant (w7d5), so the detector cannot see the bug; only raw values against
  the development support can (560 out-of-support values, all from E2; drift also fired). E3: 80 % flow is in
  range (no support alert) and the burn-in adapts (no alarms); only the raw-value distribution moves.
* E5: no signal fired; the report lists it as **not detected (expected detector)**. 7 of 8 events went as
  expected. Hiding a miss is worse than having one: the report is evidence only if it shows failures too.
* Event recall 0.5 from 2 labelled faults (1 detected) says almost nothing about the true rate: with n = 2
  any interval is nearly [0, 1].

Common wrong answers. "The demo should be all green." "Drift should catch the units bug, so the support
guard is redundant" (here both fired, but a units bug inside the drift threshold would only be caught by
support). "E5 is a bug in the demo."

### 12. Calibration margin; the planted problems; rollback is a process event (w7d6)

* Drift threshold = the **largest** PSI among the normal rows of the **27 development experiments**,
  **7.5253** (calibration values 3.26 to 7.53). With 27 exchangeable healthy windows, a new healthy window
  exceeds the maximum with probability about **1/28**. The healthy part of test experiment `other/1`
  reached **7.38**, within 2 % of alerting; the 80 % flow replay reached 9.62. The margin is thin because
  SKAB experiments run at different, nearly constant flow levels; per-machine references or monitoring
  normalised values would be better, and the runbook's limitations must say so.
* Three planted problems and the reviewer's question that finds each: (1) **rollback without restart**:
  "does the version column follow the registry history?" (the rollback row showed the wrong version,
  because the old process kept serving); (2) **a hand-typed number in the report**: "is every number in the
  report in `results.json`?" (a module constant instead of `results["summary"]`); (3) **a server left
  running**: "did every process the demo started stop?" (`pgrep -af flowguard.api` should print nothing).
* A running process loaded its bundle at startup. Changing the pointer changes nothing until the process is
  replaced: stop the old service, start a new one from the registry path, wait for `/readyz`, and confirm
  `GET /version` returns the restored version. Only then is it a rollback.

Common wrong answers. "Set the threshold at the 95th percentile of 27 values" (that is essentially the
second-largest value; say what false-alarm rate it implies). "The pointer file is the source of truth for
what is serving" (`/version` is). "The report can be edited after the run to fix a typo" (then it is no
longer generated evidence).

---

# Notebook 43 — Project completion audit: reproduce from a clean clone

✍️ Written answers: compare yours against the rubric; wording will differ.


### Reasoning questions

1. **Not necessarily.** Deterministic code on a different platform can legitimately differ by floating-point
   reordering, but that is of order 1e-12 for these metrics, not 1e-4. A fourth-decimal difference means a
   different computation. Check, in order: the resolved package versions in both venvs (`pip freeze` diff; the
   lock may not be honoured on macOS wheels), thread counts in BLAS/OpenMP (set `OMP_NUM_THREADS=1` and rerun),
   then the data hashes and the tidy-table hash in the provenance block. Only after the cause is known do you set
   a tolerance, sized to the explained effect (for example 1e-9 for reordering), and write the reason next to it.
   *Common wrong answer:* "set abs_tol = 1e-3 and move on": it hides real differences such as a changed split.
2. A copy includes untracked and ignored files (data, caches, `results/`, a local config); a clean working tree
   only means no *modified tracked* files. Only a clone shows what the commit contains. *Wrong answer:* "copying
   is the same if `git status` is clean": ignored files do not appear in `git status`.
3. An unpinned transitive dependency is resolved to whatever is newest at install time; a new `threadpoolctl` or
   `joblib` can change parallel behaviour or break imports. `pip freeze` in a fresh venv holding only your direct
   dependencies lists exactly what your project pulls in, at the versions that worked; in your everyday
   environment it lists unrelated packages too (and possibly versions your project never needed).
4. **Design choice.** Headline values are the claims; declaring them makes the audit's promise explicit and the
   log readable, and lets you set a tolerance per value where needed. Comparing the whole file would fail on
   fields that legitimately differ (provenance: commit hash, timestamps, auditor paths). The risk: a bug that
   changes an undeclared number goes unnoticed. Cover it by declaring every number quoted in the report (the
   w8d2 number-trace check makes that list), by a `repeat = 2` run for determinism, and by unit tests for the
   rest. *Weak answer:* "the file is too big": size is not the reason; meaning is.
5. The hash detects any change to a downloaded file (silent upstream edits, truncated downloads, a different
   commit). It does not guarantee availability, and it does not say the data are correct. If the upstream
   disappeared: use an archived copy where the licence allows (GPL-3.0 allows redistribution under its terms,
   which you would check), and record in the README that the data must be obtained from the archive.

### Interview rep rubric (score 0-2 each)

| Element | 2 points if the answer... |
|---|---|
| Mechanism | describes the clean-clone audit concretely: clone, fresh venv, pinned lock, data by hash, one command, comparison with tolerances |
| Evidence | points to a committed log, its date and verdict, and how long it takes |
| Honesty | names the number they trust least (for flowguard: test recall from 7 events) and why |
| Failure story | describes a real finding from their first audit and the fix |
| Limits | separates "reproducible" from "correct" and from "generalises" |

A strong 3-minute answer for the reference project: "Every number in the report is generated by `make evaluate`
from data downloaded by hash and a frozen split. I audit that from a clean clone: a tool clones the commit into
an empty directory, builds a venv from a fully pinned lock, downloads and verifies the data, runs the pipeline
and compares 18 headline numbers with the committed results; the last run passed with zero difference in 75
seconds. That shows the numbers are what the code produces, not that they are right: the test set has only 7
recordings, so I report intervals, and recall of 5 of 7 could be anywhere from about a third to nine tenths."

---

# Notebook 44 — Technical report and model limitations

✍️ Written answers: compare yours against the rubric; wording will differ.


### Reasoning questions

1. **No.** Overlapping separate intervals do not show equivalence, and each test interval is wide because only 7
   recordings are resampled. Compute the paired difference with a cluster bootstrap over the same recordings,
   and compare it with a minimum practically important difference fixed in advance. Do it on development data,
   where the decision is made (27 recordings): +0.069 [0.022, 0.128] for logistic minus flow-rate z-score,
   "inconclusive" because the interval includes values below 0.05. The test look is reported, not used to choose.
   *Common wrong answer:* "overlap means no significant difference": it confuses two marginal intervals with the
   interval of the difference, and it ignores the pairing.
2. Zero events in about 1.2 hours is consistent with the budget and also with rates far above it: with a Poisson
   rate of one per 8 hours, the chance of no false alarm in 1.2 hours is about $e^{-0.15} \approx 0.86$. Sentence:
   "No false alarm occurred in about 1.2 hours of normal operation in the test recordings; this is too little to
   confirm the budget of one per 8 hours, which is monitored in operation." *Wrong answer:* "the model has zero
   false alarms".
3. Value-anywhere tracing proves a number *exists* in the results, not that it is the right one. Stricter options:
   tag numbers with the key they come from (a template that renders `{monitoring.drift_share_a:.0%}`), trace per
   section to a sub-tree of the results, or generate the prose (worked example). The checker is a floor.
4. The sentence protects the decision: without it, a reader may deploy on a real plant expecting benchmark
   performance. Removing it would make every number misleading, and if a reviewer finds the omission the project's
   credibility suffers more than from the caveat. Wording: "Evaluated on a laboratory testbed; a pilot on the
   plant's own data, with the same protocol, is the next step before relying on it."
5. A defensible choice: (a) 7 test recordings and 34 faults (bounds every claim); (b) laboratory testbed, unseen
   fault families (bounds where it applies); (c) drift is not degradation, labels arrive late (bounds how failure
   would be noticed). Other choices are fine if justified by the stakeholder's decision.

### Interview rep rubric (score 0-2 each)

| Element | 2 points if the answer... |
|---|---|
| Plain language | uses counts ("5 of the 7 faults we tested") and a range ("between about a third and nine in ten") |
| Cause | explains that 7 test faults is too few to pin the rate down, with an everyday analogy |
| Usefulness | says what the system is good for now (an early warning that supplements inspection) |
| Path forward | proposes how to get a reliable number (a pilot with logged faults; how many) |
| No jargon | avoids "confidence interval", "bootstrap", "PR-AUC" |

Strong answer: "We tested it on 7 recorded faults and it caught 5. With only 7, that is like judging a goalkeeper
on 7 penalties: the true rate could be anywhere from about one in three to nine in ten. So I cannot promise 70 %.
What I can say is that it caught most faults within about two minutes and raised no false alarms in our tests. If
you run it alongside your inspections for a few months and we log every confirmed fault, a few dozen faults would
narrow that range enough to plan on."

---

# Notebook 45 — ML system design

✍️ Written answers: compare yours against the rubric; wording will differ.


**Q1.** 40,000,000 / 86,400 s ≈ 463 transactions/s on average; × 6 ≈ 2,778/s at peak. Busy cores =
2,778/s × 0.008 s ≈ 22.2 (Little's law). Usable cores per replica = 4 × 0.5 = 2. Replicas = ceil(22.2 / 2)
= **12**, then add capacity for a zone failure (e.g. 3 zones × 6 = 18) because 12 is the minimum with
everything healthy. *Common wrong answers:* dividing by 3,600 (per hour) gives 24x too much; forgetting the
utilisation target gives 6; rounding 11.1 to 11.

**Q2.** Predictions in the last 90 days are labelled only if at least 60 days old: (90 − 60)/90 = **one
third**. With a 100-day delay, **none** are: the evaluation window must grow past 100 days or monitoring
has to rely on proxies and input checks until labels arrive. *Wrong:* "two thirds" (counts the wrong end
of the window); "all of them, just later" (true eventually, but not in today's window).

**Q3.** (a) **Batch**: computed once a week, no latency constraint, cheapest. (b) **Online**: the decision
blocks the authorisation and depends on this transaction's details. (c) **Streaming**: features are windows
over a continuous signal and the reaction time (a minute) is shorter than any batch cadence. (d) **Batch**:
produced daily for a planning process; online adds cost and nothing else. *Wrong:* "online for everything
to be safe" — online multiplies cost and failure modes when the consumer does not need fresh answers.

**Q4.** With linear costs `c_late` per minute late and `c_early` per minute over-estimated, the expected
cost of quoting `q` is minimised where `P(T ≤ q) = c_late / (c_late + c_early)` (the newsvendor result).
With `c_late = 3 c_early` that is the 0.75 quantile. Mean + margin assumes a symmetric, constant-width
error distribution; delivery times are right-skewed and their spread varies with load, so a fixed margin
is too wide at quiet times and too narrow at peak. *Assumption:* the costs really are linear and in the
stated ratio; if lateness costs grow faster (anger at 20 min late, not 2), the right quantile moves up.

**Q5.** (1) Different window boundaries (SQL `>= now - 15 min` on event time vs the stream's processing
time); (2) late or out-of-order events counted in training but missed online; (3) different filters or
definitions (cancelled orders included in one place); also time zones, null handling. Prevention: one
feature definition executed by one engine for both (a feature store or shared library), with training rows
produced by **replaying** the online computation point-in-time, plus a parity test that compares logged
online values with recomputed offline values on a sample every day.

**Q6.** Optimising and evaluating the same quantity invites Goodhart effects and blind spots. A metric not
trained on checks that the improvement means what you think. D2: trained on pinball loss, launched on
**late-order rate and conversion**; D1: trained on click-derived preferences, launched on **success rate**
(no quick re-search) and per-department guardrails.

**Q7.** Jumping to a model before requirements; no metric or the wrong metric (accuracy, MAE) for the
decision; no discussion of where labels come from and when they arrive; no numbers (QPS, latency, data
size), so no basis for architecture choices; ignoring failure modes and cost. Instead: three minutes of
requirements, an explicit target and label, one estimation table, then the architecture.

---

# Notebook 46 — Coding and SQL interviews, timed

✍️ Written answers: compare yours against the rubric; wording will differ.


### Assessment questions

**Q1.** O(n · m) where m is the number of kept events scanned; worst case O(n²) when most events are kept
and keys repeat rarely (e.g. many keys, large gaps, or a small window). The check `test_p3_is_linear` uses
200,000 events with a small window so nearly all are kept. *Common wrong answer:* "O(n) because we break
early" — the break happens only when the key is found; for keys not seen recently the scan runs the full
list.

**Q2.** `RANK()` gives equal values the same rank, so three drivers tied at the top all get rank 1 and the
city returns three rows; `ROW_NUMBER()` numbers rows uniquely and the `driver_id` tie-breaker makes the
choice deterministic. `DENSE_RANK()` is right when the question asks for "all drivers with the top two
*counts*" (ties included by design). *Wrong:* `ROW_NUMBER()` without a tie-breaker — correct row count,
non-deterministic answer.

**Q3.** Storing values: O(n) memory, two passes, exact enough with `pvariance` (it uses exact arithmetic on
the input floats). Welford: O(s) memory for s sensors, one pass, streaming-friendly, numerically stable.
Both are O(n) time. In an interview, Welford if the input could be a stream or huge; storing is acceptable
if you say the memory cost. The one to avoid is `E[x²] − E[x]²`, which fails for large offsets (the check
uses values near 1e8-1e10 with spreads below 1).

**Q4.** Feasibility must be **monotone**: if a maximum batch cost X is achievable, every X' > X is too.
Then the smallest feasible X is found by binary search between max(costs) (a batch must hold the largest
item) and sum(costs) (one batch). The greedy check is correct because packing each batch as full as
possible never increases the number of batches needed.

**Q5.** `march_completed`: one row per completed March trip; `paid`: one row per trip with a succeeded
payment; the join `cities ⟕ march_completed ⟕ paid` has one row per (city, trip) or one per city with no
trips. Invariants: `SUM(completed_trips)` equals `SELECT COUNT(*) FROM trips WHERE status='completed' AND
March`; revenue equals the sum of succeeded payments of those trips computed separately; the city count is 5.

**Q6.** CPython's default recursion limit is about 1,000 frames; a recursive DFS on a 30,000-step chain
raises `RecursionError` (raising the limit risks a crash of the interpreter). Kahn's algorithm only emits a
step when all its predecessors are done; steps on a cycle never reach in-degree 0, so if fewer than V steps
are emitted, a cycle exists among the remaining ones.

**Q7.** Say it: "I have an O(n²) solution; let me write it so we have something correct, then optimise."
Write the brute force quickly with a test, then name the bottleneck (the repeated scan, the repeated sort)
and the data structure that removes it. Interviewers score progress and reasoning, not only the final
complexity.

### Notes on the timed set (read after your attempt)

| # | Pattern | Key insight | Most common mistake (and the mutant that encodes it) |
|---|---|---|---|
| P1 | hash maps | nested dict: latest label per annotator | collecting all labels per sample (`p1_counts_changed_minds`) |
| P2 | two pointers | the alarm pointer only moves forward | not consuming the alarm (`p2_alarm_reused`); nested loops (`p2_nested_loops`) |
| P3 | sliding window + hash map | only the last *kept* time per key matters | updating on every event (`p3_window_from_last_seen`) |
| P4 | aggregation + top-k | Welford or two-pass; population variance; explicit tie rule | n − 1 (`p4_sample_variance`); `E[x²] − E[x]²` (`p4_naive_sum_of_squares`) |
| P5 | binary search on the answer | monotone feasibility check | walking up one unit at a time (`p5_greedy_average`) |
| P6 | graphs (topological sort) | Kahn's algorithm with a min-heap | recursive DFS (`p6_recursive_dfs`); no cycle check (`p6_no_cycle_check`) |
| Q1 | grain, joins, fan-out | pre-aggregate payments per trip; LEFT JOIN from cities | joining attempts (`q1_fanout_count`); inner join drops a city (`q1_inner_join_drops_city`) |
| Q2 | top-n per group | `ROW_NUMBER` with a tie-breaker | `RANK` (`q2_rank_keeps_ties`); counting cancelled trips (`q2_all_statuses`) |
| Q3 | gaps and islands | `day - row_number` on DISTINCT days | one row per trip (`q3_trips_not_days`); latest tie (`q3_latest_tie`) |
| C1 | sliding window, monotonic deques | max and min of a window in amortised O(1) | adjacent differences only (`c1_adjacent_differences`); O(n²) (`c1_quadratic`) |
| C2 | cohorts, relative windows | first completed trip + `DATETIME(first, '+30 days')` | calendar month (`c2_calendar_month`); first trip of any status (`c2_first_trip_any_status`); integer division (`c2_integer_division`) |

Reference solutions: `lab/python/*.py`, `lab/sql/*.sql`, `challenge/python/c1_longest_stable_run.py`,
`challenge/sql/c2_driver_cohorts.sql`. Each mutant's `MUTANT.md` names the checks that reject it.

---

# Notebook 47 — Explaining the project and defending tradeoffs

✍️ Written answers: compare yours against the rubric; wording will differ.


1. The listener remembers the last thing said. Limitation before Next step lets the talk end on what
   you will do about the weakness; a talk that ends on Evidence leaves the obvious objection to the
   interviewer, who will raise it with less charity.
2. Yes, with its protocol-B result next to it: hiding the best test number invites "didn't you try
   boosting?"; showing it with 0.636 on the unseen family turns it into your strongest argument.
   *Common wrong answer:* leaving it off "to keep the slide clean" - the omission is noticed.
3. Compared with a baseline (clock, chance, the incumbent rule) and with its uncertainty (interval or
   number of independent units). Without both, "good" is undefined.
4. It demonstrates judgement and honesty, shows you analysed errors, and pre-empts the question an
   interviewer would ask anyway. A second success adds little information.
5. Restate the question, concede what is true in it, and say what you would check - "I haven't
   measured that; the way I would find out is ...". Do not improvise a number.
6. Learner-specific. A strong answer names the question and turns the gap into a next step.

---

# Diagnostic (notebooks 01-02)

Scoring guidance: [diagnostic/SCORING.md](diagnostic/SCORING.md). Per-section notes, model answers and common wrong answers:

- [a1_python](diagnostic/a1_python/NOTES.md)
- [a2_sql](diagnostic/a2_sql/NOTES.md)
- [a3_cleaning](diagnostic/a3_cleaning/NOTES.md)
- [b1_baseline](diagnostic/b1_baseline/NOTES.md)
- [b2_leakage](diagnostic/b2_leakage/NOTES.md)
- [b3_testing_api](diagnostic/b3_testing_api/NOTES.md)
- [b4_explain](diagnostic/b4_explain/NOTES.md)
