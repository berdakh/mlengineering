# w1d3 assessment — model answers

Open only after writing your own answers. For each question: a model answer, then the
common incorrect answers and why they fail.

## Q1 — tests pass after `pip uninstall`

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

## Q2 — "command not found" after adding an entry point

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

## Q3 — 140 exact pins in `dependencies`

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

## Q4 (design choice) — port the bug first, fix it second

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

## Q5 — identical metrics after the fix

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

## Q6 — `main()` returns an exit code

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

## Interview rep — rubric and reference

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
