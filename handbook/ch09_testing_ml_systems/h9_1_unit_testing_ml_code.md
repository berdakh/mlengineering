# H9.1 — Unit testing ML code

**Chapter 9: Testing ML systems** · Section id `H9.1` · **Content status:** Reviewed
(claims about pytest/NumPy behaviour checked against the sources in §H9.1.10; code fragments
executed as part of lesson [w1d5](../../lessons/w1d5_testing_ml_code/README.md)).

Used by: [w1d5 — Testing ML code with pytest](../../lessons/w1d5_testing_ml_code/README.md).
Later sections of this chapter (planned): H9.2 data-validation tests, H9.3 API and
integration tests, H9.4 statistical performance checks and model promotion gates.

---

## H9.1.1 Overview

Software tests answer one question: *does this code do what its contract says?* ML projects
add a second question that sounds similar and is entirely different: *is this model good
enough?* The first has a yes/no answer that is the same on every run. The second is an
estimate with a sampling distribution. Most testing trouble in ML projects comes from using
the instrument designed for one question on the other — asserting a metric in a unit test,
or trusting a good metric as proof that the code is right.

This section covers the first question for the code that surrounds a model: feature
computation, data loading, splitting, metric computation, post-processing. It gives

- a taxonomy of where expected values come from when outputs are numbers (§H9.1.2),
- the arithmetic of floating-point tolerances (§H9.1.3),
- the pytest mechanisms you need and no more (§H9.1.4),
- the layering of test kinds in an ML system and what each is entitled to claim (§H9.1.5),
- how to measure whether a suite is any good (§H9.1.6),
- failure modes and a quick reference.

The running claim: **a test is a detector of defects and should be judged by its
sensitivity and its false-alarm rate, like any detector.**

---

## H9.1.2 Oracles for numerical code

An *oracle* is the source of the expected value in a test. The *oracle problem* is that for
most scientific code you cannot produce the expected output for an arbitrary input without
running the code. The way out is to stop testing arbitrary inputs and to choose inputs for
which something is known.

### Known answers

Construct inputs with a closed-form output.

*Root mean square.* For `x_n = A·sin(2πf n/fs + φ)` sampled over a whole number of periods,

`rms(x) = sqrt( (1/N) Σ x_n² ) = A/√2`.

*Line length.* For a ramp `x_n = n`, `Σ |x_{n+1} − x_n| = N − 1`. For the zigzag
`0,1,0,1,0` it is 4, while the signed sum is 0.

*Band power.* Let `X_k = Σ_n (x_n − x̄) e^{−2πi kn/N}` and define the one-sided periodogram

`P_k = c_k · |X_k|² / (fs · N)`, with `c_k = 2` for `0 < k < N/2` and `c_k = 1` for `k = 0` and `k = N/2`,

on frequencies `f_k = k·fs/N`, spacing `Δf = fs/N`. Parseval's theorem for the DFT,
`Σ_n |y_n|² = (1/N) Σ_k |Y_k|²`, gives

`Σ_{k=0}^{N/2} P_k · Δf = (1/N) Σ_n (x_n − x̄)² = Var(x)` (population variance, `ddof=0`).

Two consequences are directly testable. Total power equals variance — this pins the
normalisation and the factor 2. And a tone of amplitude `A` at a bin frequency has all its
power, `A²/2`, in one bin — this pins which bins a band selects.

A known-answer input must be **discriminating**: the plausible wrong implementations must
give a different number on it. `A = 1` cannot tell `A` from `A²`; a monotone ramp cannot
tell `Σ|Δx|` from `ΣΔx`; a zero-mean signal cannot tell whether the mean is removed. When
you write the test, write down the wrong formula you are excluding.

It must also be **exact for the reason you think**. A 25 Hz tone in a 0.5 s window at 256 Hz
is not on a bin (bins are 2 Hz apart); its power in 10–40 Hz is 0.491, not 0.5, because of
spectral leakage. Tests built on such inputs need tolerances that have nothing to do with
floating point, and those tolerances then hide real defects. Choose `fs`, `N`, `f` so the
closed form holds exactly.

### Invariances (metamorphic relations)

When `f(x)` is unknown but the effect of transforming `x` is known, test the relation:

| Relation | Detects |
|---|---|
| `rms(a·x) = |a|·rms(x)`; `power(a·x) = a²·power(x)` | wrong exponent, missing `abs` |
| `power(x + c) = power(x)` for bands including 0 Hz | missing mean removal |
| `P[a,c) = P[a,b) + P[b,c)` | inclusive/exclusive edge errors |
| output unchanged under row permutation | hidden dependence on input order |
| `z(a·x + b) = z(x)`, `a > 0` (z-scores, correlations) | normalisation errors |
| changing `x[t+1:]` leaves `out[:t+1]` unchanged | non-causal feature (future leakage) |
| time-shifting the input shifts detected events by the same amount | index arithmetic errors |

Invariances are cheap, apply to random (seeded) inputs, and cover wide input ranges. Their
blind spot is any defect that respects the symmetry: mean-absolute-value scales exactly like
RMS, and a z-score whose baseline wrongly includes the current sample is still affine
invariant and causal (the worked example in w1d5 shows exactly this). **Use invariances for
breadth and at least one known answer per function to anchor the value.**

### Contracts

Assertions about structure need no numerical oracle at all, and in ML code they guard the
most expensive mistakes:

- a split partitions the rows, and no group id appears on both sides;
- a feature table has exactly one row per entity key and no NaN;
- a loader raises a specific exception on a missing column instead of failing later;
- a function does not modify its input;
- a parameter that is accepted is actually used (vary it, require an effect).

### Differential tests

Compare with an independent implementation: a library routine
(`scipy.signal.periodogram`), a slow obviously-correct loop, or the previous release. Good
for complex algorithms; weaker than the above because both sides can share a misreading of
the specification, and comparing with "what the code printed last time" is not independent
at all. That last form — a *characterisation* (golden-master) test — has one legitimate
job: pinning behaviour while you restructure code. Replace it with a real oracle afterwards.

---

## H9.1.3 Floating-point tolerances

Definitions (verified against the installed libraries, §H9.1.10):

- **pytest:** `actual == pytest.approx(expected, rel=r, abs=a)` holds when
  `|actual − expected| ≤ max(r·|expected|, a)`. Defaults: `r = 1e-6`, `a = 1e-12`. If only
  `abs` is given, the relative tolerance is not applied. Infinity equals only itself; NaN
  equals nothing unless `nan_ok=True`.
- **NumPy:** `numpy.testing.assert_allclose(actual, desired, rtol, atol)` passes when
  `|actual − desired| ≤ atol + rtol·|desired|` elementwise. Defaults: `rtol = 1e-7`,
  `atol = 0`, and NaNs in matching positions compare equal (`equal_nan=True`).

Note the asymmetry: both scale the relative part by the *expected* value, so put the
trusted number on the expected side.

**Choosing the number.** Double precision has machine epsilon `ε ≈ 2.2·10⁻¹⁶`. A sum of `N`
terms accumulates a relative error of order `N·ε` in the worst case when terms have the
same sign — about `3·10⁻¹⁴` for `N = 128`. Subtraction of nearly equal quantities
(*cancellation*) amplifies relative error by `|a| / |a − b|`. So:

1. Estimate the numerical noise `η` of the computation (`N·ε`, times any cancellation factor).
2. Estimate the smallest defect `δ` you intend to detect, as a relative change in output.
3. Pick a tolerance near the geometric middle: `η ≪ tol ≪ δ`.

For window features, `η ~ 10⁻¹⁴` and the subtle defects are `δ ~ 10⁻¹` (mean-abs vs RMS is
10 %), so anything from `10⁻¹²` to `10⁻⁶` is defensible and `10⁻⁹` is a comfortable choice.
What is not defensible is a tolerance arrived at by increasing it until the test passed.

**Expected value zero.** Relative tolerance vanishes at 0. "No power outside the band" needs
an absolute tolerance, chosen relative to the scale of the *other* quantities in the test
(for unit-amplitude tones, `abs=1e-12`).

**Exact equality is sometimes right.** Integer results, set membership, and two runs of the
*same* arithmetic (determinism, causality) should be compared exactly
(`assert_array_equal`). A tolerance there would hide nondeterminism.

**Approximate claims.** Some true statements are approximate by nature ("linear
interpolation of three missing samples changes RMS by less than 5 %"). Give them their
own test, a justified bound, and a comment; do not let them set the tolerance for exact claims.

---

## H9.1.4 pytest mechanics that carry the weight

**Discovery and imports.** pytest collects `test_*.py` files and `test_*` functions. For a
`src/` layout, either install the package (`pip install -e .`) or tell pytest where it is
with the `pythonpath` configuration value (`[tool.pytest.ini_options] pythonpath = ["src"]`).
Tests should import the package by name and never edit `sys.path`; that keeps "which copy
of the code am I testing?" answerable. (pytest's default `prepend` import mode puts each
test file's base directory on `sys.path`, which is why a helper module next to the tests is
importable; the pytest documentation recommends `importlib` mode for new projects, under
which helpers should live in a proper package or in fixtures.)

**Assertions.** Plain `assert`; pytest rewrites it to show operand values on failure.

**Fixtures.** A fixture is a function, decorated with `@pytest.fixture`, whose return value
is injected into any test that names it as a parameter. The default scope is `function`:
the fixture is built anew for every test, so tests cannot contaminate each other through
it. Wider scopes (`class`, `module`, `package`, `session`) share one instance and are for
expensive, read-only resources. Fixtures placed in `conftest.py` are available to all tests
in that directory without import.

```python
@pytest.fixture
def rng():
    return np.random.default_rng(12345)      # seeded: failures are reproducible
```

**Factory fixtures.** When tests need variations of the same data, return a function:

```python
@pytest.fixture
def make_frame():
    def _make(n_units=6, n_windows=8, n_samples=64, seed=0): ...
    return _make
```

**`tmp_path`.** A built-in fixture that provides a `pathlib.Path` to a temporary directory
unique to each test. Use it for every test that touches the filesystem; nothing is written
into the repository and tests cannot see each other's files.

**Parametrisation.** One test body, several inputs; each case is reported separately.

```python
@pytest.mark.parametrize("amplitude", [0.5, 1.0, 3.0])
def test_rms_of_sine(amplitude): ...
```

Use it for boundary tables (`score, expected` pairs) — the table *is* the specification by example.

**Exceptions.** `with pytest.raises(ValueError, match="label"):` asserts the type and that
the regular expression is found (`re.search`) in the message. Match on the informative
fragment (the column name), not the whole sentence, so rewording the message does not break the test.

**Selecting.** `pytest -k "band_power and not slow"`, `pytest path/to/test_file.py::test_name`,
`-x` to stop at the first failure, `-q` for compact output.

---

## H9.1.5 Layers of testing in an ML system

| Layer | Question | Input chosen by | Outcome | When it runs | On failure |
|---|---|---|---|---|---|
| Unit test | Does this function obey its contract? | test author | deterministic | every change | fix the code; block merge |
| Integration / smoke test | Do the parts work together at all? | test author (tiny, synthetic) | deterministic | every change | fix the wiring; block merge |
| Data validation | Does *this batch* satisfy the schema and ranges? | the world | deterministic per batch | every load | stop that pipeline run; investigate data |
| Statistical performance check | Is *this model* good enough? | held-out sample | random variable | per trained model | do not promote; investigate with error analysis |

The dividing line runs between the third and fourth rows. Above it, a failure has a single
meaning. Below it, the measured metric `m̂` is an estimate of an unknown `m`; with few
independent test groups its standard error is large. On the synthetic pump data of Week 1,
identical code gives held-out AUC between 0.946 and 1.000 depending only on which three of
ten units are held out (`lessons/w1d5_testing_ml_code/example/metric_variability.py`). A
threshold placed inside that range fails by chance; a threshold placed safely below it
passes with most code defects present — an end-to-end metric test survived 13 of the 14
defects injected in w1d5.

Consequences for practice:

- **Do not gate code merges on model metrics.** Gate *model promotion* on them, in the
  evaluation stage, with an interval or a comparison to the incumbent on the same split.
- **A "minimal performance" smoke test is acceptable in the unit suite only when it is
  deterministic by construction**: fixed seeds, tiny synthetic data, and classes separated by
  a margin so large that only a wiring error (wrong probability column, labels misaligned,
  features all zero) can fail it. State this in its docstring.
- **Training for many epochs is not a unit test.** If a learning check is wanted for a
  neural model, the standard cheap forms are: loss decreases over a few steps on one fixed
  batch; the model can overfit a handful of examples; output shapes and dtypes are right;
  with dropout off, output for sample *i* does not depend on other samples in the batch.
  (These are stated here as common practice and are developed in Week 4; not executed in this section.)

**What unit tests cannot establish.** That the features are the right features; that
validation mirrors deployment; that preprocessing statistics were fitted on training data
only when that is an experimental-design property rather than a function contract. For such
risks prefer controls that make the error impossible to express (a scikit-learn `Pipeline`
that owns its scaler; a split function that is the only way to obtain indices) over tests
that try to observe it afterwards.

---

## H9.1.6 Measuring a suite: coverage and mutation

**Coverage** is the fraction of statements (or branches) executed during the test run.
Unexecuted code is certainly untested, so low coverage is actionable. Executed code is not
thereby verified: a test that calls every function and asserts only that the result is a
float achieves full line coverage and detects nothing. Treat coverage as a gap finder.

**Mutation analysis** measures sensitivity directly. Take the correct code, introduce one
small defect (a *mutant*), run the suite. The mutant is *killed* if some test fails and
*survives* otherwise:

`mutation score = killed mutants / (total mutants − equivalent mutants)`

where an *equivalent* mutant changes the text but not the behaviour and cannot be killed.
Tools automate mutant generation; you do not need one to benefit. The manual habit is
enough: after writing a test, break the code in the way you fear and watch the test fail.
A test you have never seen fail has not been tested.

This is the same logic as validating a detector on signals with planted events, and it has
the same caveat: the score is relative to the mutants you chose. Fourteen hand-picked
defects (w1d5) are realistic but not exhaustive.

---

## H9.1.7 Practical decisions and tradeoffs

- **How many tests?** Per public function: one known answer, one or two invariances, each
  documented error. Per boundary in the spec: a case on it. Stop there; more tests of the
  same kind add maintenance, not sensitivity.
- **Public behaviour vs internals.** Test through the public API. Tests that assert private
  helper names or call order break on every refactor and discourage improving the code.
- **Random inputs.** Fine for invariances, always seeded. For broad randomised property
  testing a dedicated library (Hypothesis) generates and shrinks cases; it is optional here
  and not part of the course stack.
- **Speed budget.** A unit suite that takes more than tens of seconds stops being run.
  Keep frames tiny (tens of windows); mark anything slow and run it separately.
- **Fixtures vs inline data.** Inline the three numbers a reader needs to audit the
  expected value; put bulky construction in a factory fixture.
- **When a test is flaky.** Find the uncontrolled input (unseeded RNG, time, ordering of a
  set or of a `groupby`, thread count, a tolerance at the noise floor). Do not add retries.
- **When expected values are genuinely unknown** (a complex model's output): fall back to
  contracts (shape, range, determinism, invariances) plus a small differential test against
  a saved, *reviewed* output — and label it as a regression test.

---

## H9.1.8 Common failure modes

| Failure mode | Symptom | Remedy |
|---|---|---|
| Tautological oracle | expected value computed by the code under test | derive from mathematics or the spec |
| Non-discriminating input | test passes with the defect inserted | choose input where wrong formula differs; try the mutation by hand |
| Tolerance creep | `rel=0.1` everywhere | fix the input so the answer is exact; reason `η ≪ tol ≪ δ` |
| Relative tolerance at zero | test can never pass, or `abs` set huge | absolute tolerance scaled to the problem |
| Metric as unit test | intermittent CI failures; defects pass | move to evaluation; keep only a deterministic wiring check |
| Environment coupling | passes locally, fails in CI | no cwd-relative paths, no network, `tmp_path`, seeded RNG |
| Shared mutable fixture | tests pass alone, fail together (or reverse) | function scope, or return copies |
| Testing the mock | all collaborators replaced; real integration never runs | at least one smoke test through the real path |
| Characterisation tests kept forever | bugs are enforced by the suite | replace with oracles once contracts exist |
| Coverage as goal | 100 % with assertion-free tests | review by mutation |

---

## H9.1.9 Quick reference

```python
import numpy as np, pytest

# known answer, tight tolerance
assert rms(tone(24.0, 3.0)) == pytest.approx(3.0 / np.sqrt(2), rel=1e-9)

# expected zero -> absolute tolerance
assert band_power(tone(92.0), FS, 10, 40) == pytest.approx(0.0, abs=1e-12)

# arrays
np.testing.assert_allclose(actual, desired, rtol=1e-9, atol=0)
np.testing.assert_array_equal(run_a, run_b)            # determinism: exact

# invariance, parametrised
@pytest.mark.parametrize("a", [-2.0, 0.1, 7.0])
def test_scaling(rng, a):
    x = rng.standard_normal(128)
    assert rms(a * x) == pytest.approx(abs(a) * rms(x), rel=1e-9)

# error contract + temporary files
def test_missing_column(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("unit_id,window_id\nP01,0\n")
    with pytest.raises(ValueError, match="label"):
        load_windows(path)

# structural contract
assert set(train_units).isdisjoint(test_units)
```

Checklist before trusting a test:

1. Where does the expected value come from, and could a reviewer verify it without running code?
2. Which wrong implementation does this test fail on? Did I see it fail?
3. Is the tolerance between the numerical noise and the smallest defect of interest?
4. Does it run from any directory, offline, in any order, in milliseconds?
5. Which layer is it — and is it in the right place?

Commands: `python -m pytest -q` · `-x` stop at first failure · `-k EXPR` select by name ·
`path::test_name` run one test · `--durations=5` slowest tests.

---

## H9.1.10 Sources and verification status

Network note: `docs.pytest.org` and `numpy.org` were **not reachable** from the authoring
environment (2026-11-21). The claims below were verified against the documentation
*sources* in the pytest repository and against the docstrings of the installed libraries
(pytest 9.1.1, NumPy 2.5.3), which are the same texts the websites render.

| Claim | Source consulted | Status |
|---|---|---|
| `approx` defaults `rel=1e-6`, `abs=1e-12`; equal if either tolerance met; `abs`-only disables `rel`; inf/NaN handling, `nan_ok` | `pytest.approx.__doc__` (pytest 9.1.1) | verified |
| `assert_allclose` criterion `atol + rtol·|desired|`; defaults `rtol=1e-7`, `atol=0`, `equal_nan=True` | `numpy.testing.assert_allclose` docstring and signature (NumPy 2.5.3) | verified |
| `raises(match=...)` uses `re.search` on the exception text | `pytest.raises.__doc__` (pytest 9.1.1) | verified |
| Fixture scopes and default `function` scope; factory-as-fixture pattern | `doc/en/how-to/fixtures.rst`, pytest `main` branch (raw.githubusercontent.com) | verified |
| `tmp_path` is a `pathlib.Path` unique to each test function | `doc/en/how-to/tmp_path.rst`, same | verified |
| `parametrize` runs the test once per argument tuple | `doc/en/how-to/parametrize.rst`, same | verified |
| `pythonpath` setting; default `prepend` import mode; `importlib` recommended for new projects | `doc/en/explanation/goodpractices.rst`, same | verified |
| Parseval identity and one-sided periodogram normalisation | derived in §H9.1.2; confirmed numerically by the lab's reference test (`rel=1e-9`) | verified by execution |
| RMS of a sine `A/√2`; mean-abs `2A/π`; 25 Hz leakage value 0.491 | computed in the authoring environment | verified by execution |
| AUC spread 0.946–1.000 over 20 split seeds (SYNTHETIC data) | `example/metric_variability.py` | verified by execution; not a statement about real data |
| Summation error bound of order `N·ε` | standard result (e.g. Higham, *Accuracy and Stability of Numerical Algorithms*, ch. 4) | **cited from memory, not re-verified this session** |
| Mutation testing terminology (killed/survived/equivalent, mutation score) | standard usage (e.g. Jia & Harman, "An Analysis and Survey of the Development of Mutation Testing", IEEE TSE 2011) | **cited from memory, not re-verified this session** |
| Neural-network test patterns in §H9.1.5 | common practice | **not verified or executed here; revisit in Week 4** |
| Coverage tooling (`pytest-cov`) | — | not installed, not used; no coverage figures are quoted |

Optional further reading (not required to complete the lesson): the pytest "How-to" guides
on fixtures and parametrisation; Higham ch. 1–4 for floating-point error analysis.
