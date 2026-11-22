# w1d7 - retrieval answers

Open only after all twelve questions have a written attempt. Each answer gives the mechanism a
"solid" answer must contain, then the common wrong answers and why they fail. Wording will differ;
score the mechanism.

## 1. Tests pass locally, the wheel is missing a subpackage

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

## 2. What an editable install does

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

## 3. Declared dependencies versus a lock

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

## 4. Seed 3 versus seed 7, +0.04 F1

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

## 5. Precedence and strictness

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

## 6. Libraries and logging configuration

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

## 7. Tests for `rms`

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

## 8. `assert auc > 0.95` as a unit test

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

## 9. Tolerances

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

## 10. `NOT IN` with NULLs

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

## 11. Scaling before the split

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

## 12. Characterisation tests; what stays out of Git

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
