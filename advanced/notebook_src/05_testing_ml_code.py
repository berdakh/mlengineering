# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/advanced/notebooks/05_testing_ml_code.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 05 · Testing ML code with pytest: what a unit test can and cannot tell you
#
# **Week 1 · day 5 · 2 h essential path + up to 1 h optional** · lab files: [`labs/w1d5_testing_ml_code/`](../../labs/w1d5_testing_ml_code/)
#
# **Objective.** Write a pytest suite that catches realistic defects in signal-feature and splitting code, and separate deterministic unit tests from statistical performance checks.

# %%
# --- Setup: works on your laptop AND in Google Colab ----------------------------
# In Colab this clones the course repository and installs the requirements (about a
# minute, first run only). On your own machine it just finds the repository. Every
# command in this notebook runs from the repository root. Safe to re-run.
import os
import subprocess
import sys
from pathlib import Path

if "google.colab" in sys.modules:
    if not Path("/content/mlengineering").exists():
        subprocess.run(["git", "clone", "--depth", "1",
                        "https://github.com/berdakh/mlengineering.git",
                        "/content/mlengineering"], check=True)
    os.chdir("/content/mlengineering")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "-r", "requirements.txt"], check=True)

REPO_ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents]
                 if (p / "src" / "mlcourse").is_dir())
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "src"))
print("repo root:", REPO_ROOT)

# %% [markdown]
# **Content status:** Execution verified (see Verification record) ·
# **Handbook:** [H9.1 Unit testing ML code](../../docs/handbook/ch09_testing_ml_systems/h9_1_unit_testing_ml_code.md) ·
# **Solutions (open only after an attempt):** `solutions/labs/w1d5_testing_ml_code/`
#
# > Data note. The lab's tests build their own signals. One script
# > (`example/metric_variability.py`) uses `data/synthetic/pump_vibration.csv`, which is
# > **SYNTHETIC**; its numbers illustrate metric variance and say nothing about real pumps.
#
# ---

# %% [markdown]
# ## 1. Purpose
#
# **Primary objective.** Write a pytest suite for signal-feature and data-splitting code
# that *demonstrably* detects realistic defects — and be able to say which kinds of defect
# no unit test will ever detect.
#
# **What you will learn**
#
# - Where expected values ("oracles") come from when the code computes numbers nobody can
#   check by eye: closed-form answers, conservation laws, invariances, and contracts.
# - How to choose a floating-point tolerance by reasoning instead of by loosening until green.
# - pytest mechanics that matter in practice: fixtures and factories, `tmp_path`,
#   `parametrize`, `approx`, `raises`.
# - The difference between a **unit test** (deterministic statement about code) and a
#   **statistical performance check** (noisy statement about a model on data), and where each belongs.
#
# **Why an applied ML engineer needs it.** ML code fails silently. A feature with a missing
# square root, a band edge counted twice, or a split that leaks a unit still produces a
# plausible AUC. In research the reviewer of last resort is you, staring at a plot; in a team,
# it is a test suite that runs on every change, written so that a colleague who breaks
# `band_power` finds out in ten seconds and not from a degraded model three weeks later.
# Interviewers probe exactly this: "how do you know your preprocessing is correct?"
#
# **Prerequisites.** [w1d3](03_package_structure.ipynb) (the `pumpwatch` package;
# its public API is the code under test). [w1d4](04_config_logging.ipynb) is helpful
# but not required. You know what a periodogram and a grouped split are.
#
# **Time**
#
# | Activity | Essential (2 h) | Optional (≤ 1 h) |
# |---|---|---|
# | Concepts (§2) | 25 min | H9.1 in full: +20 min |
# | Worked example (§3) | 20 min | |
# | Guided lab (§4) | 60 min | |
# | Assessment questions (§7) | 15 min | |
# | Independent challenge (§5) | | 40 min |
# | Interview rep (§7) | | 15 min |
#
# If you already test numerical code this way, skip to §4 step 0, run the checks, and let the
# survivor list tell you what to read.
#
# ---

# %% [markdown]
# ## 2. Conceptual explanation
#
# ### 2.1 Intuition: a test is a detector, so evaluate it like one
#
# A detector (for faults, fraud or seizures) is validated by injecting events with known ground
# truth and counting what it finds. A test suite is the same kind of object: a detector whose targets
# are *defects*. Its sensitivity is measured by injecting known defects into correct code and
# counting how many make at least one test fail. That procedure is **mutation testing**; an
# injected defect is a **mutant**, a mutant the suite fails on is **killed**, one it passes on
# has **survived**. Today's checks grade your suite this way: 14 realistic defects, each must be killed.
#
# The same analogy gives the two error types. A suite that fails on correct code (false
# alarm) is **flaky** or **over-specified**; a suite that passes on defective code (miss) is
# **weak**. "All tests pass" tells you nothing until you know the suite's sensitivity.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/labs/w1d5_testing_ml_code/figures/kill_matrix.svg" alt="Real harness runs: six test suites against 14 injected defects; starter, runs-without-error and self-comparison detect 0, the end-to-end metric suite 1, loose tolerances 13, the reference suite 14" width="100%">
#
# *Real runs of this lesson's grading harness. All six suites pass on the correct package; a suite is only as good as the defects it notices. Defects are numbered rather than named so the figure does not give the lab away. Regenerate with `python labs/w1d5_testing_ml_code/figures/make_figures.py` (about a minute).*
#
# ### 2.2 The oracle problem
#
# A test needs an expected value that does **not** come from the code under test. For numerical
# ML code there are four dependable sources, in decreasing order of strength:
#
# 1. **Known answers from mathematics.** Construct an input whose output you can derive.
#    - RMS of `A·sin` over whole periods: `A/√2`.
#    - A pure tone of amplitude `A` carries power `A²/2`, all of it at its own frequency.
#    - Parseval: total power in the spectrum equals the variance of the signal.
#      With the one-sided periodogram `P_k` used in `band_power` and `Δf = fs/N`:
#
#      `Σ_k P_k · Δf = (1/N) Σ_n (x_n − x̄)²`
# 2. **Invariances (metamorphic relations).** You may not know `f(x)`, but you know how `f`
#    must change when `x` changes: `rms(a·x) = |a|·rms(x)`, `band_power(a·x) = a²·band_power(x)`,
#    band power over `[a,c)` = `[a,b)` + `[b,c)`, features do not depend on row order,
#    a constant offset adds no band power.
# 3. **Structural contracts.** Statements about shape and set membership that need no numbers:
#    one row per `(unit, window)`, no unit on both sides of a split, train ∪ test = all rows,
#    a missing column raises `ValueError`.
# 4. **Differential testing.** Compare against an independent implementation
#    (`scipy.signal.periodogram`, a slow loop). Useful, but two implementations can share a
#    misreading of the spec, so it ranks below 1–3.
#
# What is *not* an oracle: the function's own output on a copy of the input, or an "expected"
# number pasted from its last run. The second is a **characterisation test** — legitimate for
# pinning behaviour during a refactor (w1d3), worthless as evidence of correctness.
#
# Two properties of a good known-answer input, both visible in the lab:
#
# - **It discriminates.** A monotone ramp gives the same line length with or without `abs`.
#   Amplitude `A = 1` cannot distinguish `A` from `A²`. Pick inputs on which the plausible
#   wrong formula gives a *different* number.
# - **It sits on the boundary.** Bugs in comparisons (`<` vs `<=`) are invisible unless a
#   sample lies exactly on the edge: a tone at exactly 40 Hz for bands `[10,40)` and `[40,70)`.
#
# ### 2.3 Tolerances are a design decision
#
# Floating-point results are compared with a tolerance. The two definitions you will use:
#
# - `pytest.approx(expected, rel=r, abs=a)`: equal if `|actual − expected| ≤ max(r·|expected|, a)`.
#   Defaults `rel=1e-6`, `abs=1e-12`. If you pass only `abs`, the relative tolerance is not applied.
# - `numpy.testing.assert_allclose(actual, desired, rtol, atol)`: passes if
#   `|actual − desired| ≤ atol + rtol·|desired|`. Defaults `rtol=1e-7`, `atol=0`.
#
# Choose the tolerance to sit in the gap between two magnitudes:
#
# `numerical noise  ≪  tolerance  ≪  smallest defect you must detect`
#
# *Numerical noise* for a sum of `N` double-precision terms is of order `N·ε` relative, with
# `ε ≈ 2.2e-16`: about `3e-14` for a 128-sample window. *Smallest defect*: mean-absolute-value
# instead of RMS gives `2A/π = 0.637A` instead of `0.707A`, a 10 % error. So `rel=1e-9` is five
# orders above the noise and eight below the defect; `rel=0.15` "to be safe" lets the defect through.
#
# A relative tolerance is meaningless when the expected value is 0 (`r·0 = 0`); that is the
# case for "a 92 Hz tone has no power in 10–40 Hz", which needs `abs=`.
#
# If a test needs a loose tolerance, something in the *input* is uncontrolled — typically a
# tone that does not fall on an FFT bin (spectral leakage) or a non-integer number of periods.
# Fix the input (`fs=256`, `N=128` → 2 Hz bins; use 24, 40, 92 Hz), not the tolerance. Reserve
# loose tolerances for tests whose claim is itself approximate ("interpolating three missing
# samples changes RMS by < 5 %"), and say so in a comment.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/labs/w1d5_testing_ml_code/figures/tolerance_regions.svg" alt="Largest error that passes as a function of the expected value, for an absolute tolerance of 1e-9, a relative tolerance of 1e-6 and their combination; the two cross at an expected value of 1e-3" width="100%">
#
# *Arithmetic, not data. Below `|b| = abs / rel` the absolute term decides; above it the relative term does. An expected value of exactly zero needs an absolute tolerance.*
#
# ### 2.4 The test pyramid for ML, and the line that matters
#
# | Layer | Claim | Deterministic? | Runs | Example |
# |---|---|---|---|---|
# | Unit tests | this function obeys its contract | yes | every change, seconds | `rms(sine) = A/√2` |
# | Integration / smoke | the pieces are wired together | yes (fixed seeds, tiny data) | every change | pipeline reaches AUC ≥ 0.9 on a trivially separable frame |
# | Data validation | *this dataset* satisfies the schema | yes | every data load | columns present, ranges (Week 2) |
# | Statistical performance checks | *this model* is good enough on held-out data | **no** — an estimate with variance | per trained model, in evaluation | grouped-CV AUC with interval vs. baseline (Week 3) |
#
# The first three are about **code and data contracts**; a failure means something is broken.
# The fourth is about **a model's quality**; its outcome is a random variable and a "failure"
# may be bad luck in which units were held out.
#
# Concrete evidence, produced by `example/metric_variability.py` on the synthetic pump data:
# the same correct code with 20 different split seeds gives held-out AUC from 0.946 to 1.000
# and F1 from 0.78 to 0.95. A unit test `assert auc > 0.95` fails for seed 4 with no defect
# present — and, as you will measure in the lab, a suite consisting only of such a test
# *passes* with 13 of the 14 injected defects present. It is both flaky and weak.
#
# A **defensible minimal-performance smoke check** inside a unit suite has three properties:
# (1) data constructed so the task is trivially separable, with a margin so wide that only a
# wiring error can fail it; (2) all seeds fixed, so it is deterministic; (3) a docstring
# stating that it checks wiring, not quality. `auc >= 0.9` on such a frame catches "used the
# probability of the wrong class" (AUC ≈ 0) and "labels misaligned with features" (AUC ≈ 0.5).
# Real performance thresholds belong in the evaluation stage, with uncertainty attached.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-05-01.svg" alt="Diagram 1 of notebook 05" style="max-width:100%">
#
# *The line that matters runs between the two boxes: above it a red result is a defect, below it a red result may be an unlucky split.*
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/labs/w1d5_testing_ml_code/figures/auc_over_seeds.svg" alt="SYNTHETIC pump data: test ROC AUC of the correct code for 20 split seeds ranges from 0.9464 to 1.0; one seed falls below the 0.95 assertion threshold" width="100%">
#
# *SYNTHETIC data. The same correct code under 20 split seeds: `assert auc > 0.95` fails once (seed 4) with no defect present.*
#
# ### 2.5 What coverage means
#
# Line coverage is the fraction of lines *executed* by the suite. It is a good detector of
# untested code (0 % is informative) and a poor measure of tested code: the "runs without
# error" suite in today's mutants executes nearly every line of `features.py` and kills none
# of the feature defects, because executing a line is not the same as checking its result.
# Use coverage to find gaps; use mutation (even by hand: break the code, see if a test fails)
# to judge strength.
#
# ### 2.6 Connection to other domains
#
# - Scientists validate detectors on synthetic signals with known ground truth; known-answer
#   tests are that practice made permanent and automatic.
# - A leak-free grouped split (by subject, machine or customer) is a *structural* property. It is
#   usually checked by inspection; `train_units.isdisjoint(test_units)` checks it on every commit.
# - Reviewer question "is the improvement within noise?" is the statistical-check layer.
#   Keeping it out of the unit suite is the software form of not confusing a bug with variance.
#
# ### 2.7 Industry example
#
# A payments team computes "transactions in the last 24 h" as a fraud feature. The training
# pipeline (batch SQL) uses a half-open window `[t−24h, t)`; the online service's
# reimplementation uses `<=` at one end. Offline metrics are unaffected; online, every
# transaction counts itself, the feature is shifted by one, and precision at the operating
# threshold drops. No AUC assertion catches this, because each implementation is
# self-consistent. A boundary unit test on each side — an event exactly at `t` and exactly at
# `t−24h` — does. The same defect class is in today's lab (`band_power` edge) and in the
# challenge (`>` vs `>=`).
#
# ### 2.8 Limitations and common misconceptions
#
# - *"The tests pass, so the code is correct."* They pass, so none of the defects *your tests
#   can detect* is present.
# - *"Unit tests cannot be written for ML because outputs are stochastic."* Feature code,
#   splitting, loading and metric computation are deterministic. Only model quality is statistical.
# - *"A metric threshold is the most relevant test."* It is the least sensitive to code defects (§2.4).
# - *"100 % coverage."* See §2.5.
# - *"Random test data is more thorough."* Unseeded random data makes failures unreproducible;
#   seeded random data is fine for invariances but gives no known answer.
# - **What unit tests cannot detect:** a correct implementation of the wrong idea (features
#   that do not generalise), leakage that lives in the *experimental design* rather than in a
#   function (scaler fitted before the split — fixed in w1d3 by construction with a `Pipeline`,
#   because it is hard to assert from outside), and data that violates assumptions at runtime.
#
# ---

# %% [markdown]
# ## 3. Worked example — testing a rolling z-score from its specification
#
# Different code from the lab, same method. Files: [`example/`](../../labs/w1d5_testing_ml_code/example).
#
# **Function under test.** `rolling_zscore(x, window)` scores each sample against the
# `window` samples *before* it (a trailing baseline, as used in equipment monitoring and in
# causal EEG artefact detection): `z[t] = (x[t] − mean(B_t)) / std(B_t)`, `B_t = x[t−window : t]`,
# sample std (`ddof=1`), NaN during warm-up and where the baseline is flat.
# No dataset: inputs are hand-written arrays and `default_rng(0)` noise (200 samples).
#
# **Run it** (from the repository root):
#
# ```bash
# python -m pytest labs/w1d5_testing_ml_code/example -q                    # corrected version
# ZSCORE_IMPL=buggy python -m pytest labs/w1d5_testing_ml_code/example -q  # first version
# ```
#
# **Expected output.** Corrected version: `9 passed`. First version: `3 failed, 6 passed`, with
#
# ```
# FAILED ...::test_known_answer_computed_by_hand        (obtained 1.4608, expected 5.8095)
# FAILED ...::test_flat_baseline_gives_nan_not_infinity (obtained 1.5, expected NaN)
# FAILED ...::test_spike_does_not_dilute_its_own_score  (obtained 4.23, expected 32.24)
# ```
#
# **Important decisions in the test code**
#
# 1. *Known answer by hand.* `[1,2,3,4,10]`, window 4: baseline mean 2.5, sample variance 5/3,
#    so `z = 7.5/√(5/3) = 5.8095`. The expected value is written as the formula, not as a
#    pasted number, so the reader can audit it. Tolerance `1e-12`: five numbers, no cancellation.
# 2. *Invariances.* A z-score is unitless, so `z(a·x + b) = z(x)` for `a > 0`
#    (parametrised over three gain/offset pairs), and it is causal: altering samples from
#    index 120 on must leave `z[:120]` bit-identical (`assert_array_equal`, no tolerance,
#    because the same arithmetic is performed).
# 3. *A property taken from a sentence of the spec.* "An anomaly must not dilute its own
#    score" becomes: a 10× larger spike has a 10× larger z.
# 4. *Fixture.* `noise` is a function-scoped fixture, so each test receives a fresh array and
#    a test that mutated it could not affect another.
#
# **Interpretation.** The defect is one slice: `x[t-window+1 : t+1]` includes the current
# sample in its own baseline. Look at *which* tests fail. The affine-invariance and causality
# tests pass on the defective version — the bug respects both symmetries. The hand-computed
# answer and the spec-derived property catch it. That is the general pattern: invariances are
# cheap and broad but blind to anything that preserves the symmetry; at least one known answer
# per function anchors the absolute value. In a detector this defect is consequential: the
# largest anomalies suppress their own scores (5.8 → 1.5 here) while offline AUC, which only
# ranks, may barely move.
#
# **Second script — metric variance** (uses the SYNTHETIC pump data):

# %%
!python labs/w1d5_testing_ml_code/example/metric_variability.py

# %% [markdown]
# Expected last line: `AUC min 0.9464  max 1.0000  -> runs below 0.95: 1 of 20`. This is the
# evidence behind §2.4. It cannot tell you how variable metrics are on real equipment data;
# it shows only that *identical code* produces a spread, which is all the argument needs.
#
# **Reproducibility.** Deterministic; versions in the verification record below.
#
# ---

# %% [markdown]
# ## 4. Guided lab — make the suite kill 14 defects
#
# **Result to produce:** `lab/tests/` — a suite that passes on the correct package, runs in
# under 20 s, and fails on every injected defect; plus `lab/TESTING_NOTES.md` (step 8).
#
# **Code under test:** `lab/src/pumpwatch/` (v0.1.0, identical to the w1d3 reference). You may
# test your own package from w1d3/w1d4 instead if it keeps the same public API — the checks
# always grade your *tests* against the reference copy in `checks/reference_pkg/`.
#
# **Rules of the game**
#
# - Tests import `pumpwatch` normally (`from pumpwatch.features import rms`). Do not touch `sys.path`.
# - Tests build their own data. The checks run your suite from a temporary directory with
#   networking blocked; a test that reads `data/synthetic/...` will fail there.
# - `checks/bugs.py` lists the defects. Reading it first turns this lab into guided
#   practice — your call, but record it honestly in the workbench.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-05-02.svg" alt="Diagram 2 of notebook 05" style="max-width:100%">
#
# *How the lab grades you: your tests are the detector, the injected defects are the ground truth.*
#
# ### Step 0 — baseline (5 min)
#
# ```bash
# cd labs/w1d5_testing_ml_code/lab
# python -m pytest -q                      # the starter suite: 2 passed
# cd ../../..
# python -m pytest labs/w1d5_testing_ml_code/checks -q
# ```
#
# *Checkpoint:* `14 failed, 2 passed`. All 14 defects survive the starter tests. Read
# `lab/tests/test_starter.py` and decide why before continuing.
#
# ### Step 1 — deterministic signals and a frame factory (10 min)
#
# Create `lab/tests/signals.py` (a plain module; test files in the same folder can
# `from signals import ...`) and `lab/tests/conftest.py`:
#
# ```python
# # signals.py
# import numpy as np
#
# FS = 256.0
# N = 128          # TODO: what is the frequency resolution? Which tone frequencies are "safe"?
#
# def tone(freq_hz, amplitude=1.0, n=N, fs=FS, phase=0.3):
#     ...          # amplitude * sin(2*pi*f*t + phase)
# ```
#
# ```python
# # conftest.py
# import numpy as np, pandas as pd, pytest
# from signals import tone
#
# @pytest.fixture
# def rng():
#     return np.random.default_rng(12345)
#
# @pytest.fixture
# def make_frame():
#     """Factory fixture: returns a function that builds a long-format frame."""
#     def _make(n_units=6, n_windows=8, n_samples=64, seed=0):
#         ...      # columns: unit_id, window_id, sample, vibration, temperature_c, label
#                  # make label-1 windows differ by a LARGE 92 Hz component; give every unit both labels
#     return _make
# ```
#
# *Checkpoint:* `python -c "import sys; sys.path.insert(0,'labs/w1d5_testing_ml_code/lab/tests'); from signals import tone; print(tone(24).std())"` prints `0.7071...`.
#
# ### Step 2 — scalar features (10 min) → kills 4
#
# Write `tests/test_features.py`. For `rms`, `line_length`, `peak_to_peak`: one known answer
# each **that discriminates** (§2.2), plus the scaling law, parametrised over a few `a`
# including a negative one.
#
# *Checkpoint:* `python -m pytest labs/w1d5_testing_ml_code/checks -q -k "rms or line_length or p2p"` → `4 passed`.
# *If `line_length_missing_abs` survives:* what is `sum(diff(x))` for your input?
#
# ### Step 3 — band power (15 min) → kills 3
#
# Tests for: Parseval (total power = variance — read the docstring about the upper edge),
# pure tone power `A²/2`, a tone outside the band (expected 0 → which tolerance?), a tone
# exactly on a band edge, additivity over adjacent bands, a constant offset.
#
# *Checkpoint:* `-k band_power` → `3 passed`.
# *If Parseval fails on the correct package:* is the Nyquist bin inside `[low, high)`? Are you
# comparing against `np.var(x)` (ddof=0) or `ddof=1`?
# *If the edge bug survives:* is any spectral power exactly on your edge frequency?
#
# ### Step 4 — gaps and the feature dictionary (5 min) → kills 2
#
# `fill_gaps` on a hand-written array with an interior NaN and NaNs at both ends;
# `window_features` on a two-tone signal with known `bp_low`, `bp_high` and `ratio`.
#
# ### Step 5 — feature table and loader (10 min) → kills 2
#
# `build_feature_table`: row count and uniqueness of `(unit_id, window_id)`; invariance to
# row order (`df.sample(frac=1, random_state=0)`). `load_windows`: write CSVs into `tmp_path`;
# a good file loads, a file missing a column raises `ValueError` (use
# `pytest.raises(..., match=...)` and `parametrize` over the dropped column), a missing path
# raises `FileNotFoundError`.
#
# *If the row-order bug survives:* which features are order-dependent? Compare those.
#
# ### Step 6 — split (5 min) → kills 2
#
# On a small features frame with ~10 units: no unit on both sides; indices form a partition;
# same seed → same split; and a test that fails if the `seed` argument is ignored. Think about
# why "same seed, same result" cannot be that test.
#
# ### Step 7 — smoke test of training (5 min) → kills 1
#
# `train_and_evaluate` on `build_feature_table(make_frame(), FS)`: contract of the returned
# dict and a wiring check as defined in §2.4, with a docstring that says what it is.
#
# ### Step 8 — verify and write notes (5 min)

# %%
!python -m pytest labs/w1d5_testing_ml_code/checks -q

# %% [markdown]
# Then create `lab/TESTING_NOTES.md` (≤ 15 lines): which defect survived longest and why;
# one tolerance you chose and its justification in the form of §2.3; two defects in this
# package that *no* test in your suite could catch.
#
# **Debugging guidance**
#
# | Symptom | Likely cause |
# |---|---|
# | `ModuleNotFoundError: pumpwatch` when running your tests | run from `lab/` (its `pyproject.toml` sets `pythonpath = ["src"]`) |
# | `ModuleNotFoundError: signals` | `signals.py` must sit in `tests/`, and `tests/` must not contain `__init__.py` |
# | check "passes on correct package" fails but local run passes | test depends on cwd, repo data, or network |
# | test passes locally with a bug you inserted by hand | your input does not discriminate, or tolerance too wide |
# | suite > 20 s | you are building large frames or looping in Python; 6 units × 8 windows × 64 samples is enough |
#
# Stuck for more than 10 minutes on one defect → hints.
#
# ---

# %%
# Run the automated checks on your guided lab.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w1d5")

# %% [markdown]
# ## 5. Independent challenge — test and repair an event extractor *(optional extension, 40 min)*
#
# Task and acceptance criteria: [`challenge/README.md`](../../labs/w1d5_testing_ml_code/challenge/README.md).
#
# In short: `challenge/eventkit/events.py` converts a per-sample anomaly score into events
# (threshold → merge close runs → drop short ones) — the step between a detector's output and
# event-level evaluation, which the portfolio project needs in Week 3. It was "written quickly
# and never tested" and contains an undisclosed number of defects. You write tests **from the
# specification**, use them to find and fix the defects, and are graded on both the repaired
# function and the strength of your tests. No starter tests beyond one happy-path case, no
# step list. This is the unit's evidence of *independent* skill.

# %%
!python -m pytest labs/w1d5_testing_ml_code/checks_challenge -q

# %% [markdown]
# ---
#
#
# ### The challenge brief
#
#
# **Kind:** independent demonstration (transfer). **Time:** about 40 minutes.
# **No solution here.** Reference: `solutions/labs/w1d5_testing_ml_code/challenge/` — open it only after your attempt.
#
# #### Context
#
# A detector emits one anomaly score per sample. Operations do not page an engineer per
# sample; they page per *event*. `eventkit.events.detect_events` performs that conversion.
# It is the same post-processing used in many event detectors, from seismic to clinical (threshold,
# join fragments, enforce a minimum duration), and the portfolio project will use it for
# event-level evaluation in Week 3.
#
# The file `eventkit/events.py` was written quickly and never tested. It contains defects.
# How many is not disclosed.
#
# #### Specification
#
# ```
# detect_events(score, threshold, min_samples=1, merge_gap=0) -> list[tuple[int, int]]
# ```
#
# 1. `score` is a one-dimensional sequence of floats (list or NumPy array). It is not modified.
# 2. A sample is *above* when `score[i] > threshold` (strictly). A NaN score is never above.
# 3. A *run* is a maximal block of consecutive above samples.
# 4. Two neighbouring runs are **merged** into one event when the number of non-above samples
#    between them is `<= merge_gap`. Merging chains: A–B–C can become one event.
#    With `merge_gap=0` nothing is merged.
# 5. **After** merging, an event is kept only if its length `stop - start >= min_samples`.
# 6. Events are returned in increasing order as half-open index pairs `(start, stop)`:
#    `start` is the first sample of the event, `stop` is one past its last sample.
#    An event may begin at index 0 and may end at `len(score)`.
# 7. Empty input returns `[]`.
# 8. `ValueError` is raised if `score` is not one-dimensional, if `min_samples < 1`, or if `merge_gap < 0`.
#
# #### Your task
#
# 1. Write tests in `tests/test_events.py` **from the specification above**, not from what the
#    code currently does.
# 2. Use them to find the defects; repair `eventkit/events.py`. Keep the signature.
# 3. Add to the top of your test file a comment block (5–10 lines): the defects you found,
#    and for each one the test that exposed it.
#
# Run your tests:
#
# ```bash
# cd labs/w1d5_testing_ml_code/challenge
# python -m pytest -q
# ```
#
# #### Acceptance criteria
#
# Automated (`python -m pytest labs/w1d5_testing_ml_code/checks_challenge -q` from the repo root):
#
# - [ ] Your repaired `detect_events` agrees with the specification on 400 random score
#       arrays (with ties at the threshold and NaNs) and on the error contracts.
# - [ ] Your tests pass against a correct implementation — i.e. they assert nothing the spec does not promise.
# - [ ] Your tests fail against each of 8 defective implementations (the defects you were
#       given are among them; the others are mistakes of the same kind).
# - [ ] Your tests run in under 10 seconds, from any directory, without network access.
#
# Not automated — judge yourself against the rubric in `../assessment.md`:
#
# - [ ] Each test name states the clause of the spec it checks.
# - [ ] The defect log (task 3) is accurate.
# - [ ] You did not open `checks_challenge/` (it contains implementations) or hints 3–4 before
#       passing. If you did, mark the challenge as guided practice rather than independent skill.
#
# #### What you may use
#
# The lesson, handbook H9.1, pytest and NumPy documentation, hints 1–2.

# %%
# Run the automated checks on your independent challenge.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w1d5", challenge=True)

# %% [markdown]
# ## 6. Progressive hints
#
# Open in order, and only as far as you need. Note in your progress which level you used.
#
# 1. [Conceptual hint](../../labs/w1d5_testing_ml_code/hints/hint1_concept.md) — how to think about each family of defect.
# 2. [Suggested approach](../../labs/w1d5_testing_ml_code/hints/hint2_approach.md) — which test design kills what, without code.
# 3. [Partial implementation](../../labs/w1d5_testing_ml_code/hints/hint3_partial.md) — fixture and several complete tests; skeleton for the challenge.
# 4. Full reference solutions (separate tree): `solutions/labs/w1d5_testing_ml_code/lab/` and `.../challenge/`.
#
# ---
#
#
# Open one hint at a time, only after a real attempt.
#
# <details>
# <summary><b>Hint 1 concept</b></summary>
#
#
# **For every function, ask three questions before writing a test.**
#
# 1. *Is there an input for which I can derive the output on paper?* (known answer)
# 2. *What transformation of the input has a predictable effect on the output?* (invariance)
# 3. *What does the function promise about shape, membership or errors?* (contract)
#
# **For every test, ask one question after writing it:** *what is the most plausible wrong
# implementation, and would this test fail on it?* If you cannot name a wrong implementation
# that fails, the test is decoration.
#
# Families of defect and what detects them:
#
# | Defect family | Detected by |
# |---|---|
# | wrong formula with the right "shape" (mean square vs root mean square, mean-abs vs RMS) | a known answer with a tight tolerance, on an input where the formulas differ |
# | missing `abs`, missing sign handling | an input that goes **up and down**, or a negative scale factor |
# | wrong normalisation constant in a spectrum | a conservation law (total power = variance), or a tone of known power |
# | `<` vs `<=`, off-by-one | an input placed **exactly on the boundary** |
# | hidden dependence on row order | permute the input, expect the same output |
# | missing validation | `pytest.raises` on the invalid input |
# | leaking split | set arithmetic on group ids — no numbers needed |
# | ignored parameter | vary the parameter and require the output to change |
# | mis-wired training/evaluation | a problem so easy that only a wiring error can fail |
#
# **For the challenge:** each numbered clause of the specification contains at least one
# comparison or one boundary. Count them. Each needs a case on the boundary and one on either side.
#
# </details>
#
# <details>
# <summary><b>Hint 2 approach</b></summary>
#
#
# ##### Lab
#
# **Test signals.** With `fs = 256` and `N = 128` the FFT bins are 2 Hz apart. A tone at an even
# frequency with any phase occupies exactly one bin, so its band power is exactly `A²/2` and
# its RMS exactly `A/√2`. That is what lets you use `rel=1e-9`.
#
# **rms.** Sine of amplitude ≠ 1 (try 0.5 and 3). Add the scaling law with a negative factor.
# Both rms defects fail the sine test; only one of them fails the scaling law — work out which.
#
# **line_length.** `[0, 1, 0, 1, 0]` has line length 4. What does a signed sum give?
#
# **peak_to_peak.** Any all-positive array, e.g. `[3, 5, 4]`.
#
# **band_power.**
# - Parseval: noise plus a constant offset; integrate from 0 to *beyond* Nyquist because the
#   upper edge is exclusive; compare with `np.var(x)` (population variance).
# - One tone inside a band → `A²/2`; a tone outside → 0 with an **absolute** tolerance.
# - Edge: a 40 Hz tone has zero power in `[10, 40)` and all of it in `[40, 70)`.
#   Additivity (`[10,40) + [40,70) = [10,70)`) fails for the same defect on white noise.
# - Offset: `band_power(x + 100, fs, 0, 40) == band_power(x, fs, 0, 40)` — the band must start
#   at 0 Hz for a DC defect to be visible.
#
# **fill_gaps.** `[0, 1, nan, 3, 4] → [0, 1, 2, 3, 4]`. Zero-filling gives a different array.
#
# **ratio.** Two tones, amplitudes 1.0 (24 Hz) and 0.5 (92 Hz): `bp_low = 0.5`, `bp_high = 0.125`,
# `ratio = 0.25`. An inverted ratio gives 4.
#
# **build_feature_table.** Shuffle rows with a fixed `random_state`; compare `line_length`
# (order-dependent) after sorting both tables by `(unit_id, window_id)`.
#
# **load_windows.** Write a CSV without one required column into `tmp_path`; expect `ValueError`.
#
# **split.** Ten units. (a) `set(train units).isdisjoint(set(test units))`. (b) Collect the
# test-unit sets for seeds 0–9; require more than one distinct set.
#
# **model.** In your frame, give label-1 windows a 92 Hz tone of amplitude 2 on top of a
# 24 Hz tone of amplitude 1, and let every unit have both labels. AUC is 1.0 on correct code;
# with the wrong probability column it is 0.0. Assert `>= 0.9` and document why.
#
# ##### Challenge
#
# Build a table before writing tests: rows = spec clauses, columns = "on the boundary",
# "just inside", "just outside". Then:
#
# - clause 2: a score equal to the threshold; a NaN between two above samples;
# - clause 4: a gap of exactly `merge_gap`, and of `merge_gap + 1`;
# - clause 5: an event of exactly `min_samples`; and the *order* of 4 and 5 — fragments that
#   are each too short but long enough once merged;
# - clause 6: an event touching index 0; an event still open at the last sample; check `stop`;
# - clause 8: each invalid parameter.
#
# Finally add one randomised structural test (seeded): every returned event has
# `stop - start >= min_samples`, starts and ends on an above sample, and consecutive events
# are more than `merge_gap` apart.
#
# </details>
#
# <details>
# <summary><b>Hint 3 partial</b></summary>
#
#
# Using this file means the lab counts as guided practice.
#
# ##### Lab: fixture and a few complete tests
#
# ```python
# # tests/signals.py
# import numpy as np
#
# FS = 256.0
# N = 128
#
# def tone(freq_hz, amplitude=1.0, n=N, fs=FS, phase=0.3):
#     return amplitude * np.sin(2 * np.pi * freq_hz * np.arange(n) / fs + phase)
# ```
#
# ```python
# # tests/conftest.py
# import numpy as np
# import pandas as pd
# import pytest
# from signals import tone
#
# @pytest.fixture
# def rng():
#     return np.random.default_rng(12345)
#
# @pytest.fixture
# def make_frame():
#     def _make(n_units=6, n_windows=8, n_samples=64, seed=0):
#         rng = np.random.default_rng(seed)
#         frames = []
#         for u in range(n_units):
#             for w in range(n_windows):
#                 label = int(w >= n_windows // 2)
#                 x = tone(24.0, 1.0, n_samples) + 0.05 * rng.standard_normal(n_samples)
#                 if label:
#                     x = x + tone(92.0, 2.0, n_samples)
#                 frames.append(pd.DataFrame({
#                     "unit_id": f"U{u:02d}", "window_id": w, "sample": np.arange(n_samples),
#                     "vibration": x, "temperature_c": 40.0 + label, "label": label,
#                 }))
#         return pd.concat(frames, ignore_index=True)
#     return _make
# ```
#
# ```python
# # tests/test_features.py (excerpt)
# import numpy as np
# import pytest
# from signals import FS, N, tone
# from pumpwatch.features import band_power, line_length, rms
#
# @pytest.mark.parametrize("amplitude", [0.5, 1.0, 3.0])
# def test_rms_of_sine(amplitude):
#     assert rms(tone(24.0, amplitude)) == pytest.approx(amplitude / np.sqrt(2), rel=1e-9)
#
# def test_line_length_zigzag():
#     assert line_length(np.array([0.0, 1.0, 0.0, 1.0, 0.0])) == pytest.approx(4.0)
#
# def test_parseval(rng):
#     x = rng.standard_normal(N) + 5.0
#     total = band_power(x, FS, 0.0, FS / 2 + FS / N)
#     assert total == pytest.approx(np.var(x), rel=1e-9)
#
# def test_band_edges_are_half_open():
#     x = tone(40.0)
#     assert band_power(x, FS, 10.0, 40.0) == pytest.approx(0.0, abs=1e-12)
#     assert band_power(x, FS, 40.0, 70.0) == pytest.approx(0.5, rel=1e-9)
# ```
#
# Still yours to write: peak-to-peak, scaling laws, offset invariance, `fill_gaps`, the
# two-tone `ratio`, the feature-table tests, the loader tests, all split tests, the model smoke test.
#
# ##### Challenge: skeleton only
#
# ```python
# import numpy as np
# import pytest
# from eventkit.events import detect_events
#
# @pytest.mark.parametrize("score, expected", [
#     ([0, 0, 5, 5, 5, 0, 0], [(2, 5)]),
#     # TODO: event touching index 0
#     # TODO: event still open at the end of the array
#     # TODO: empty input
# ])
# def test_runs(score, expected):
#     assert detect_events(score, threshold=1) == expected
#
# def test_threshold_is_strict():
#     ...   # a score exactly equal to the threshold
#
# def test_merge_gap_boundary():
#     ...   # same score, merge_gap = gap - 1 and merge_gap = gap
#
# def test_merge_happens_before_duration_filter():
#     ...   # fragments each shorter than min_samples, long enough when merged
# ```
#
# </details>

# %% [markdown]
# ## 7. Assessment
#
# - Questions, design-choice explanation, rubric and the interview rep: `assessment.md` (section 7 of this notebook).
# - Model answers and common incorrect answers: `solutions/labs/w1d5_testing_ml_code/assessment_answers.md`.
# - Automated checks: `checks/` (lab) and `checks_challenge/` (challenge). They grade
#   behaviour of your *suite* (passes on correct code, fails on defective code, fast,
#   self-contained), never its file names, test names or number of tests.
#
# What the automated checks do **not** establish: that your tests are readable, that your
# tolerances are justified, or that you could do this unaided on unfamiliar code. The written
# questions and the challenge address those.
#
# ---
#
#
# ### Assessment questions
#
#
# Answer in writing (`lab/ASSESSMENT.md` or your notes) **before** opening
# `solutions/labs/w1d5_testing_ml_code/assessment_answers.md`. Short answers: 2–5 sentences each.
# About 15 minutes for Part A + B. Part C is the optional interview rep.
#
# #### Part A — reasoning questions
#
# **A1.** A test computes `expected = np.sqrt(np.mean(x**2))` for random `x` and asserts
# `rms(x) == pytest.approx(expected)`. Is this a useful test? What does it detect and what can it not detect?
#
# **A2.** For each assertion, state the layer it belongs to (unit / integration-smoke / data
# validation / statistical performance check) and whether it should block a merge:
# (a) `set(train_units).isdisjoint(test_units)`
# (b) `df["temperature_c"].between(-20, 150).all()` on today's ingested file
# (c) `cv_auc_mean > 0.90` on the real training set
# (d) `train_and_evaluate(tiny_separable_frame)["auc"] >= 0.9`
#
# **A3.** `band_power(tone_25Hz, fs=256, low=10, high=40)` with `N=128` returns `0.4911`
# instead of the `0.5` you expected, so your test with `rel=1e-9` fails on the correct
# package. Explain the cause and give two ways to repair the *test* — one good, one bad — and say which is which.
#
# **A4.** Your suite has 100 % line coverage of `features.py`. A colleague concludes the
# feature code is correct. Give a concrete counter-example from today's lab.
#
# **A5.** The test "same seed → same split" passes. Which two defects in
# `group_train_test_split` can still be present? Which additional test detects each?
#
# **A6.** In w1d3 the scaler was moved inside a `Pipeline` to stop it from seeing test rows.
# Why is that leak hard to catch with a unit test of `train_and_evaluate`, and what does this
# tell you about the limits of testing as a control?
#
# #### Part B — explain a design choice (required)
#
# **B1.** The checks run your suite from a temporary directory, without network, and the lab
# forbids reading `data/synthetic/pump_vibration.csv` in unit tests. Argue for this constraint
# as if a teammate had asked "why can't my tests just use the real file — it's more realistic".
# Include what you would do instead to get the realism they want. (5–8 sentences.)
#
# #### Rubric for open-ended answers (A3, A6, B1)
#
# | Level | Description |
# |---|---|
# | 0 — missing | Restates the question, or the claim is wrong. |
# | 1 — partial | Correct conclusion, mechanism missing or vague ("floating point", "tests should be isolated"). |
# | 2 — sound | Correct mechanism stated precisely, with the specific quantity or failure involved (e.g. "25 Hz is between 2 Hz bins, so power leaks outside the band"). |
# | 3 — transferable | Level 2, plus a tradeoff or boundary of the rule (when you *would* use real data / a loose tolerance / a different control) and what you would do instead. |
#
# Target: level 2 on every item, level 3 on B1. Anything below 2 → set *review needed* and re-read the linked handbook section.
#
# Rubric for your **test code** (lab and challenge; self-assessed or reviewed):
#
# | Criterion | Meets | Does not meet |
# |---|---|---|
# | Independent oracle | expected values derived from math/spec and auditable in the test | values pasted from the function's output |
# | Discrimination | each test names (in title or comment) what wrong behaviour it rules out | "it works" tests |
# | Tolerance | tight where exact, loose only with a stated reason | uniform loose tolerance |
# | Isolation | no shared mutable state, no cwd/network/file dependence, seeded randomness | order-dependent or environment-dependent |
# | Readability | one behaviour per test, parametrised instead of copy-pasted | a single 80-line test |
#
# #### Part C — interview rep (optional, 15 minutes, timer on, no hints, no references)
#
# > **Prompt.** Implement `merge_intervals(intervals)`. Input: a list of half-open integer
# > intervals `(start, stop)` with `start < stop`, in any order. Output: the sorted list of
# > merged intervals, where intervals that overlap **or touch** (`a.stop == b.start`) are
# > merged. Then write the tests you would want before shipping it. Talk through (write down)
# > the boundary cases before you code.
#
# Deliverable: one file with the function and its tests. Afterwards compare with
# `solutions/labs/w1d5_testing_ml_code/interview_rep/` and score yourself:
#
# | Criterion | 0 | 1 | 2 |
# |---|---|---|---|
# | Clarified the contract first (touching? unsorted? empty? input mutated?) | no | some | all four |
# | Correctness | fails basic cases | fails a boundary | passes reference tests |
# | Tests | none / happy path | some boundaries | boundaries + a property (output sorted, disjoint, same covered set) |
# | Complexity stated | no | — | O(n log n) and why |
# | Time | > 25 min | 15–25 min | ≤ 15 min |
#
# Assistance for this rep is intentionally lower than in the lab: no starter code and no
# hints. Record the score in your progress notes; these reps recur and the trend is the evidence.

# %% [markdown]
# ## 8. Reflection and review
#
# **You should now be able to, without notes:**
#
# - derive a known-answer test and an invariance test for a numerical function you did not write;
# - choose and defend a tolerance;
# - write fixtures/factories and file-based tests with `tmp_path`;
# - state which layer (unit / smoke / data validation / statistical check) a given assertion
#   belongs to, and why a metric threshold is a poor unit test;
# - estimate a suite's strength by injecting a defect.
#
# **Progress flags** (set them separately; see the workbench):
# *reading* — §2–3 read · *guided practice* — lab checks pass · *independent skill* —
# challenge checks pass **without** hints 3–4 and without reading `bugs.py` · *review needed* —
# any assessment answer you could not justify.
#
# **Reflection prompt (5 min, write it down).** Think of the feature-extraction code behind
# a result you have reported (a project, thesis, paper or assignment). Name one defect that could be present in it today without
# having changed the paper's headline metric. Which single test would detect it?
#
# **Retrieval practice (answer from memory in ~1 week, before w2d5; answer key is in the solutions file).**
# A colleague's test reads `assert band_power(x, fs, 8, 12) == pytest.approx(expected, rel=0.2)`
# where `expected` was copied from a notebook run. Name the two independent problems with
# this test and rewrite its *design* (not code) so that it can detect a factor-of-two error.
#
# **Next lesson.** [w1d6 — Notebook → package, independently](../../docs/guides/program-design.md): you refactor a
# different notebook with reduced assistance. The method is today's in reverse order: first
# pin current behaviour with characterisation tests, then restructure, then replace the pins
# with real oracles as each function gets a contract. In Week 2 the same contract thinking is
# applied to *data* (schema and quality checks); in Week 3 the statistical layer of §2.4 gets
# its own tools (grouped CV, intervals).
#
# ---

# %% [markdown]
# ## Verification record
#
# Executed in the authoring environment on 2026-11-21: Python 3.13.18, pytest 9.1.1,
# numpy 2.5.3, pandas 3.0.5, scikit-learn 1.9.1, scipy 1.18.1 (Linux).
#
# | What | Command | Result |
# |---|---|---|
# | Worked example, corrected | `python -m pytest labs/w1d5_testing_ml_code/example -q` | 9 passed |
# | Worked example, first version | `ZSCORE_IMPL=buggy python -m pytest labs/w1d5_testing_ml_code/example -q` | 3 failed, 6 passed |
# | Metric variance script | `python labs/w1d5_testing_ml_code/example/metric_variability.py` | AUC 0.9464–1.0000 over 20 seeds |
# | Starter suite on checks | `python -m pytest labs/w1d5_testing_ml_code/checks -q` | 14 failed, 2 passed (all 14 defects survive) |
# | Lab: solution + mutants | `python tools/verify_checks.py labs/w1d5_testing_ml_code --part lab` | solution passes; 5/5 weak suites rejected |
# | Challenge: solution + mutants | `python tools/verify_checks.py labs/w1d5_testing_ml_code --part challenge` | solution passes; 3/3 mutants rejected |
# | Challenge starter on checks | `python -m pytest labs/w1d5_testing_ml_code/checks_challenge -q` | 8 failed, 7 passed |
#
# Survivors measured for the weak suites: *runs_without_error* 14/14, *self_consistency_only*
# 14/14, *end_to_end_metric_only* 13/14, *loose_tolerances* 1/14 (`rms_is_mean_abs`).
# Check runtime: about 7 s for the lab checks and 2 s for the challenge checks on an idle
# machine (reference suite itself ≈ 2 s).
#
# Not verified here: behaviour on Python 3.11/3.12 and on other library versions; coverage
# tooling (`pytest-cov` is not installed and no coverage numbers are quoted).

# %% [markdown]
# ## Record your progress
#
# Tick only what is true. Passing the supplied checks is *guided practice*; mark *independent* only for work done without hints or solutions.

# %%
from mlcourse.progress import mark, note

# mark("w1d5", "reading")
# mark("w1d5", "guided")
# mark("w1d5", "independent")
# note("w1d5", "what tripped me up today")

