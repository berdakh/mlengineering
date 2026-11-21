# H2.2 Configuration, logging and reproducible runs

**Chapter 2 — Maintainable Python for ML** · **Section id:** `H2.2` · **Content status:** Reviewed
(code fragments executed; sources as listed in [H2.2.9](#h229-sources-and-verification-status))
**Used by:** lesson [w1d4](../../lessons/w1d4_config_logging/README.md) ·
**Builds on:** H2.1 (project structure and environments) · **Leads to:** Chapter 9 (testing), Chapter 8 (reproducible experiments)

---

## H2.2.1 Overview

A research script answers "what happens if I run this?". Software that other people depend on must
also answer, long after the fact, "what exactly was run?" and "what happened while it ran?". Three
small mechanisms provide those answers:

1. **Configuration as data** — every value that may differ between runs is declared in one typed,
   validated, immutable object, assembled from layers with a fixed precedence.
2. **Logging** — code emits structured records; the application alone decides where they go.
3. **Run records** — each run writes a directory with its resolved configuration, results, log and
   provenance (code, environment and data identity).

None of this is specific to machine learning, but ML makes it urgent: results depend on dozens of
settings, on data that changes underneath you, and on randomness — and a wrong setting usually
produces a plausible number instead of a crash.

## H2.2.2 Configuration

### What counts as configuration

Sort every literal in a training script into one of four bins:

| Bin | Example | Where it lives |
|---|---|---|
| **Method constant** | the formula for RMS; a band edge you never vary | code (a named constant) |
| **Experiment configuration** | learning rate, `C`, seed, feature set, data path | versioned config file, overridable per run |
| **Deploy configuration** | service port, bucket name, database URL, log level | environment of the deployment |
| **Secret** | API keys, passwords, tokens | secret store / environment; never in the repo, never in logs or snapshots |

The boundary between the first two moves over time: a constant becomes configuration the day you
vary it. Resist promoting early — every key is a dimension that must be validated, documented,
defaulted and kept backward compatible. A config with two hundred keys is a second, untyped program.

The *Twelve-Factor App* methodology defines config as "everything that is likely to vary between
deploys", demands strict separation of config from code, and offers a litmus test: could the
codebase be made open source at any moment without compromising any credentials? It recommends
environment variables because they are language- and OS-agnostic and hard to commit by accident, and
it explicitly excludes "internal application config" that does not vary between deploys, which is
"best done in the code". That advice is about *deploy* configuration. Experiment configuration has
the opposite need — it must be reviewed, versioned and diffed — so it belongs in files in the
repository. Hold both ideas: hyperparameters in versioned files, deployment details and secrets in
the environment.

### Layers and precedence

Real programs take values from several places. Fix one order and document it:

```
built-in defaults  <  config file  <  environment variables  <  command-line flags
(least specific, most durable)                    (most specific, most ephemeral)
```

The rule of thumb is that the source closest to the single invocation wins. Implement layering as
*merge raw values first, validate once at the end*:

```python
merged = {}                       # nested dict
merged = deep_merge(merged, read_toml(path))
merged = deep_merge(merged, from_environment(os.environ))
merged = deep_merge(merged, from_cli(overrides))
config = build_and_validate(merged)       # defaults filled in by the dataclasses
```

Validating each layer separately duplicates rules and lets a later layer introduce an invalid value
unchecked. Validating once, last, guarantees that what you validated is what runs.

### Strictness

A loader has three jobs and should fail loudly at each:

- **Unknown keys are errors.** Lenient lookup (`cfg.get("seed", 7)`) converts typos into silently
  different experiments. Compare `set(given)` with the declared fields.
- **Types are checked.** TOML gives you typed values, but nothing stops `seed = "7"`. Python
  dataclasses record annotations and do not enforce them: `SplitConfig(seed="7")` constructs happily
  (executed: it does). Check explicitly, and mind `bool`, which is a subclass of `int` in Python.
- **Ranges and cross-field constraints are checked** (`0 < test_fraction < 1`, `low_hz < high_hz`,
  `high_hz <= fs / 2`). The last one is a cross-field rule; the Nyquist bound is exactly the sort of
  domain constraint worth encoding once.

Error messages should name the offending key in the user's vocabulary (`split.test_fraction`), give
the received value and state the constraint. Config errors are user errors: exit non-zero with one
line, not a traceback.

### Immutability and the dependency direction

Build the config once at start-up and freeze it (`@dataclass(frozen=True)`; assigning to a field
raises `FrozenInstanceError`, a subclass of `AttributeError`). A mutable config that functions
"adjust" on the way down is a global variable with extra steps; the snapshot written at the start no
longer describes the end.

Only the entry point should know the config *object*. Core functions take plain values:

```python
# entry point
metrics = train_and_evaluate(features, cfg.split.test_fraction, cfg.split.seed, cfg.model.C)

# library - knows nothing about files, TOML, or Config
def train_and_evaluate(features, test_fraction=0.3, seed=7, C=1.0): ...
```

This keeps the library usable from a notebook, a test, a batch job and an API without dragging a
file format along. When a function needs more than five or six settings, pass the relevant
*sub*-config (`cfg.model`), never the whole tree.

### Format and tooling decisions

| Choice | For | Against | Use when |
|---|---|---|---|
| **TOML** (`tomllib`, stdlib ≥ 3.11) | typed scalars, no implicit conversion, comments, same format as `pyproject.toml`, no dependency | read-only in the stdlib (no writer), deep nesting is clumsy | small-to-medium configs; this course's default |
| **YAML** | ubiquitous in ML/infra tooling, compact nesting, anchors | needs a third-party parser; implicit typing surprises (in YAML 1.1 parsers unquoted `no`, `on`, `off` may load as booleans and some numeric-looking strings as numbers); `yaml.load` without a safe loader can construct arbitrary objects | you must interoperate with tools that require it (CI files, Kubernetes) |
| **JSON** | universal, has a stdlib writer | no comments, noisy to hand-edit | machine-written snapshots — which is how we use it |
| **Python file as config** | full expressiveness | config can execute anything, cannot be validated without running it, cannot be diffed as data | almost never for experiment settings |

| Choice | For | Against |
|---|---|---|
| **Frozen dataclasses + hand-written checks** | stdlib, explicit, you see every rule | you write the type/range checks yourself; nested construction is manual |
| **pydantic models** | type coercion and validation, good error paths, JSON schema, settings-from-environment support | a dependency with its own semantics to learn (e.g. coercion rules, handling of extra fields — check the current docs for defaults) |
| **Hydra / OmegaConf** | config composition from groups, command-line overrides, sweep launching | considerable machinery; changes working directory and output layout conventions; hides merging logic you should understand first |

The course starts with dataclasses because the whole loader is forty lines you can read, moves to
pydantic in Week 5 where request validation requires it anyway, and treats composition frameworks as
optional. The decision is cheap to revisit *because* the rest of the package depends only on the
`Config` object's attributes.

### Overrides on the command line

A generic `--set section.key=value` flag scales better than one flag per key and keeps a single
schema. The design question is how the text after `=` acquires a type. A consistent answer is "it is
a TOML value": `tomllib.loads(f"v = {raw}")["v"]` turns `11` into an int, `0.5` into a float and
`"ERROR"` into a string by the same rules as the file. Decide explicitly what to do with bare words
(`data.path=a/b.csv` is not valid TOML): rejecting is strict; falling back to a string is friendlier
and still type-checked afterwards because the override passes through the same validation.

## H2.2.3 Logging

### The model

The standard library's `logging` separates four roles:

- **Logger** — a named object code calls (`logger.info(...)`). Names are dotted and hierarchical;
  `logging.getLogger(__name__)` gives each module a logger that mirrors the package structure.
- **Handler** — delivers records to a destination (stream, file, socket).
- **Formatter** — turns a record into text.
- **Level** — an integer severity on each record (`DEBUG` 10, `INFO` 20, `WARNING` 30, `ERROR` 40,
  `CRITICAL` 50) with thresholds on both loggers and handlers.

A record emitted on `pkg.mod` is first tested against the *effective level* of that logger (its own
level, or the nearest ancestor's if unset; the root defaults to `WARNING`). If it passes, it is
handed to the handlers of `pkg.mod`, then of `pkg`, then of the root — **propagation** — until a
logger with `propagate = False` is reached. Each handler applies its own level. Two consequences:

- Ancestor *logger* levels do not filter propagated records; only ancestor *handlers'* levels do.
- Attaching the same destination at two levels of the hierarchy prints every line twice.

With no configuration, a record that passes the level test but finds no handler anywhere goes to the
"handler of last resort": stderr, `WARNING` and above, message only. That is why un-configured
scripts show warnings but never `info`.

### Library versus application

The single most useful rule: **libraries emit, applications configure.**

*Library module:*

```python
import logging
logger = logging.getLogger(__name__)      # nothing else at import time

def load_windows(path):
    ...
    logger.info("loaded data path=%s rows=%d", path, len(df))
```

*Application entry point:*

```python
def main(argv=None):
    cfg = load_config(...)
    setup_logging(cfg.logging.level, run_dir / "train.log")   # exactly once
    ...
```

The logging HOWTO states it strongly: do not log to the root logger from a library, and do not add
handlers other than `NullHandler` to a library's loggers, because handler configuration is the
prerogative of the application developer. `logging.basicConfig()` is an application call; it
configures the *root* logger and does nothing if the root already has handlers unless `force=True` —
so calling it from a library at import is both intrusive and unreliable.

A subtlety when a module is both: run as `python -m pkg.cli`, the module's `__name__` is
`"__main__"`, so `getLogger(__name__)` is *not* a child of `pkg`. Either give that one logger an
explicit name (`getLogger("pkg.cli")`) or configure the root logger.

### Where to attach handlers

| Attach to | Effect | Choose when |
|---|---|---|
| root logger | every library's records flow to your destinations | services and scripts where you want one complete log; set noisy third-party loggers to `WARNING` |
| your package's top-level logger, `propagate=False` | only your package's records are handled | command-line tools where third-party chatter is unwanted; costs you third-party warnings in the file |

### What to log, and how

- **stdout is for results, stderr for diagnostics.** `StreamHandler()` defaults to `sys.stderr`;
  keep it. A tool whose stdout is parseable composes with other tools.
- **Event plus context.** `"split seed=%d n_train=%d n_test=%d"` — a stable event phrase followed by
  `key=value` pairs. Stable phrases can be grepped and counted; values can be extracted. JSON
  logging (Chapter 15) is the same idea with a machine-readable formatter.
- **Pass arguments, do not pre-format.** `logger.debug("coef=%s", coef)` defers string formatting
  until a handler actually emits the record; an f-string pays the cost even when DEBUG is off.
- **Levels by audience.** DEBUG for the developer diagnosing; INFO for the operator confirming a
  healthy run (counts, sizes, durations, final metrics); WARNING for "continued, but look at this"
  (fallbacks taken, rows dropped, values clipped); ERROR for "could not produce the result".
  Use `logger.exception(...)` inside an `except` block to include the traceback.
- **Log counts at boundaries.** Rows in, rows out, rows dropped and why, class balance, number of
  groups. In data work most incidents are diagnosed from a count that changed.
- **Never log secrets or raw personal data.** Logs are copied, shipped and retained more widely than
  the data they describe.

### Logging, print, and experiment trackers

| Mechanism | Is for | Is not for |
|---|---|---|
| `print` | the program's *result* on stdout; throwaway exploration | diagnostics in reusable code (cannot be filtered, routed or silenced) |
| `logging` | the narrative of one process: what happened, in order, with context | comparing runs; storing metrics you will query |
| run directory / experiment tracker | durable, structured facts *about* a run: config, metrics, artefacts, provenance | step-by-step narrative |
| `warnings.warn` | telling the *caller* their usage should change (deprecations) | reporting runtime events |

They complement each other: the log explains one run; the run record makes many runs comparable.

## H2.2.4 Randomness and what a seed buys

### Thread the seed; do not set it globally

```python
# avoid: hidden global state, order-dependent, invisible in signatures
np.random.seed(0)

# prefer: randomness is an argument
def simulate(n, rng: np.random.Generator): ...
rng = np.random.default_rng(cfg.seed)
```

With scikit-learn, pass an integer `random_state` wherever randomness exists. Its glossary is
precise: an integer gives the same results across different calls; `None` uses NumPy's global state
and gives different results on each call; a `RandomState` *instance* is consumed, so repeated calls
differ. The glossary also suggests checking stability across several seeds.

When one seed must drive several independent components (split, initialisation, augmentation),
derive child streams instead of reusing the integer or adding offsets:
`np.random.SeedSequence(seed).spawn(3)` returns three child seed sequences (call executed on NumPy
2.5.3; the independence property is from memory of the NumPy docs, not re-read this session).

### What is and is not guaranteed

- **NumPy.** The compatibility policy guarantees the same stream for the same `Generator`,
  `BitGenerator`, seed and call sequence "on the same build of numpy, in the same environment, on
  the same machine", and warns that these conditions are strict: floating-point differences between
  CPUs and different LAPACK builds can change results. Stream changes in `Generator` are permitted
  in feature (`X.Y`) releases; the legacy `RandomState` is frozen. Even `rng.random()` five times is
  not guaranteed to equal `rng.random(5)`. Hence: record the NumPy version with every run, and
  commit generated datasets instead of relying on regeneration.
- **PyTorch.** Its reproducibility notes open with the statement that completely reproducible
  results are not guaranteed across releases, individual commits or platforms, and may differ
  between CPU and GPU with identical seeds. Controls that narrow nondeterminism on one platform:
  `torch.manual_seed`; `torch.backends.cudnn.benchmark = False` (the benchmark picks convolution
  algorithms by timing, which can differ per run); `torch.use_deterministic_algorithms(True)`
  (raises on operations lacking a deterministic implementation); and, for multi-worker data loading,
  a `worker_init_fn` that seeds NumPy/`random` per worker together with an explicit `generator`.
  Each trades speed or coverage for repeatability, so treat them as configuration.
- **Everything else.** Thread scheduling in BLAS, non-associativity of floating-point addition under
  parallel reduction, iteration over sets, file-system listing order (`os.listdir` is unordered —
  sort it), data loaded "latest version" from a mutable location.

### A seed fixes a draw, not the distribution

For a metric $M$ evaluated on a random split $S$ with training randomness $R$:

$$\operatorname{Var}(M)=\operatorname{Var}_S\big(\mathbb{E}[M\mid S]\big)+\mathbb{E}_S\big[\operatorname{Var}_R(M\mid S)\big].$$

Seeding makes $M$ repeatable; it says nothing about either term. Estimating them needs several
seeds. With $k$ seeds the sample mean $\bar M$ and sample standard deviation $s$ give a spread to
report (mean ± s.d., and the range); note that results from overlapping resamples of one dataset are
not independent, so $s/\sqrt{k}$ understates the uncertainty of $\bar M$ (Chapter 6 returns to
this). To compare two variants, use the *same* seeds for both and examine the paired differences
$d_i = M^{B}_i - M^{A}_i$: pairing cancels the split term, which is usually the larger one when
groups are few.

*Worked numbers (synthetic pump data, lesson w1d4, executed):* seeds 0–9, logistic regression,
3 of 10 units held out: F1 ranges 0.778–0.930, mean 0.879, sample s.d. 0.044. A single-seed
"improvement" of 0.02 is therefore uninterpretable on its own.

Never select the seed by the test metric; that is tuning on the test set with one extra
hyperparameter.

## H2.2.5 Run records and provenance

### Vocabulary

Terminology in this area is inconsistent between communities. The US National Academies report
(2019) uses *reproducibility* for obtaining consistent results with the same data and code and
*replicability* for consistent results across studies with new data; the ACM's badging terminology
originally used the two words the other way round and was later revised to align (*both recalled
from memory; not re-verified this session*). This handbook uses:

- **repeatable** — same code, config, data and environment give the same numbers, for you, now;
- **reproducible** — another person can regenerate the result from recorded artefacts;
- **replicable** — the finding holds on new data.

Engineering practice delivers the first two. The third is a scientific property that no amount of
tooling confers — but you cannot investigate a failure to replicate without the first two.

### The run directory

One directory per run, never reused, written by the program:

```
runs/20261121T200855Z-fd801fc3/
  config.json        resolved configuration (after all layers)
  metrics.json       results
  environment.json   interpreter, platform, package versions, git commit(+dirty), data path and sha256, argv
  train.log          DEBUG-level narrative
```

Design points:

- **Identifier.** Timestamp (sortable) plus a short fingerprint of the resolved config (same
  settings → same suffix, which makes repeats visible), created with `mkdir(exist_ok=False)` and a
  retry suffix so that two runs can never share a directory. Use UTC.
- **Write the config snapshot before the work starts.** A crashed run should still be explained.
- **Hash the data, do not just name it.** A path identifies a location; a content hash identifies
  the bytes. Hash in chunks for large files; for very large or partitioned datasets hash a manifest
  (file names, sizes, per-file hashes) instead.
- **Record the dirty flag.** A commit hash for a working tree with uncommitted changes is
  misleading; record `-dirty` (or refuse to run for results you intend to report).
- **Provenance collection must not fail the run.** No git, no installed-package metadata, a
  read-only directory: degrade to `null` and log a warning.
- **Record ≠ recreate.** `environment.json` lets you *detect* that the environment changed. Lock
  files (H2.1) and container images (Chapter 12) let you *rebuild* it.

A run directory is the smallest thing that works. Experiment trackers (Chapter 8) add a database,
comparison UI and artefact storage on top of the same four records; adopt one when you can name
which manual step it removes.

## H2.2.6 Common failure modes

| Failure | Symptom | Prevention |
|---|---|---|
| Lenient config lookup | typo'd key silently ignored; experiment differs from intent | reject unknown keys |
| Overrides applied after validation, or to a copy | flag accepted, no effect | merge raw layers, validate once, last |
| Snapshot of the file instead of the resolved object | record contradicts what ran | serialise the object the computation received |
| Config mutated during the run | snapshot stale | frozen objects; derive, do not mutate |
| Secrets in config files or logs | credential in git history / log aggregator | environment or secret store; never log config values that may hold secrets |
| `basicConfig` / handlers in library modules | duplicate lines, hijacked formats, noisy tests | libraries only call `getLogger(__name__)` |
| Logs on stdout | downstream parsing breaks at higher verbosity | diagnostics to stderr |
| `__main__` logger outside the package hierarchy | entry-point INFO lines vanish | explicit logger name or root configuration |
| Global seeding | results depend on call order and imports | pass seeds / generators as arguments |
| Seed recorded but not threaded | "different seeds" give identical splits | test that changing the seed changes the split |
| Reporting one seed | noise mistaken for improvement | several seeds, paired comparisons |
| Run directory reused | results of two runs interleaved | unique id, `exist_ok=False` |
| Data identified by path only | "same" data silently changed | content hash |
| Believing the record recreates the environment | cannot rebuild old model | lock files, images |

## H2.2.7 Quick reference

```python
# --- read TOML (Python >= 3.11) -------------------------------------------------
import tomllib
with open("configs/base.toml", "rb") as fh:      # binary mode is required
    raw = tomllib.load(fh)                         # dict; raises tomllib.TOMLDecodeError
value = tomllib.loads("v = 0.5")["v"]             # parse one typed value

# --- typed, immutable config ----------------------------------------------------
from dataclasses import dataclass, field, fields, asdict
@dataclass(frozen=True)
class SplitConfig:
    test_fraction: float = 0.3
    seed: int = 7
    def __post_init__(self):                       # range checks; types are NOT enforced for you
        if not 0 < self.test_fraction < 1:
            raise ValueError(f"split.test_fraction must be in (0, 1), got {self.test_fraction}")
unknown = set(raw.get("split", {})) - {f.name for f in fields(SplitConfig)}
snapshot = asdict(SplitConfig())                   # recurses into nested dataclasses

# --- logging: library ------------------------------------------------------------
import logging
logger = logging.getLogger(__name__)
logger.info("loaded data path=%s rows=%d", path, n)

# --- logging: application (once) -------------------------------------------------
import sys
pkg = logging.getLogger("pumpwatch")
pkg.setLevel(logging.DEBUG); pkg.propagate = False
fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s")
console = logging.StreamHandler(sys.stderr); console.setLevel("INFO"); console.setFormatter(fmt)
logfile = logging.FileHandler(run_dir / "train.log"); logfile.setLevel(logging.DEBUG); logfile.setFormatter(fmt)
pkg.addHandler(console); pkg.addHandler(logfile)

# --- seeds -------------------------------------------------------------------------
import numpy as np
rng = np.random.default_rng(seed)                  # local generator, passed as an argument
GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=seed)   # int -> repeatable across calls

# --- provenance --------------------------------------------------------------------
import hashlib, platform, subprocess
from importlib import metadata
metadata.version("scikit-learn"); platform.python_version()
subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout  # non-empty -> dirty
h = hashlib.sha256()
with open(path, "rb") as fh:
    while chunk := fh.read(1 << 20):
        h.update(chunk)
```

**Checklist for a run you intend to report**

- [ ] resolved config snapshot written before work starts
- [ ] unknown keys / bad types / bad ranges rejected with the key named
- [ ] seed in the config and demonstrably reaches every random component
- [ ] code commit recorded, working tree clean
- [ ] library versions, Python version, platform recorded
- [ ] data content hash recorded
- [ ] log file kept with row/group counts at each boundary
- [ ] results over more than one seed; comparisons paired
- [ ] a sentence stating what nondeterminism remains

## H2.2.8 Practice pointers

- Lab and challenge: [lessons/w1d4_config_logging](../../lessons/w1d4_config_logging/README.md).
- Reference implementation (open after attempting): `solutions/lessons/w1d4_config_logging/lab/src/pumpwatch/{config,logging_setup,runs,cli}.py`.
- Plausible mistakes, as runnable overlays: `solutions/lessons/w1d4_config_logging/mutants/`.

## H2.2.9 Sources and verification status

The usual documentation sites were not reachable from the authoring environment
(docs.python.org, numpy.org, scikit-learn.org, pytorch.org and 12factor.net are outside its network
allow-list). The documents below were therefore read **as documentation source files from the
projects' official GitHub repositories** on 2026-11-21, which is the text the websites are built
from; rendered pages were not opened and their URLs were not link-checked.

| Claim(s) | Source consulted (repository path, branch) | Status |
|---|---|---|
| Root default level WARNING; `getLogger(__name__)`; propagation to ancestor handlers; handler of last resort; "do not add handlers other than NullHandler" to library loggers; do not log to the root logger from a library | `python/cpython` `Doc/howto/logging.rst` (3.13) — Logging HOWTO | Read; claims match |
| `basicConfig` does nothing if the root logger already has handlers unless `force=True` | `python/cpython` `Doc/library/logging.rst` (3.13); also executed | Read + executed |
| `tomllib` added in 3.11; parses TOML 1.0.0; no writing support; file must be opened in binary mode; type conversion table | `python/cpython` `Doc/library/tomllib.rst` (3.13) | Read; claims match |
| `frozen=True` → `FrozenInstanceError`; `__post_init__`; dataclasses do not validate types | `python/cpython` `Doc/library/dataclasses.rst` (3.13) for the first two; non-validation and `FrozenInstanceError ⊂ AttributeError` executed on Python 3.13.18 | Read + executed |
| Twelve-Factor definition of config, litmus test, environment variables, exclusion of internal application config | `heroku/12factor` `content/en/config.md` (master) | Read; quotations match |
| NumPy stream-compatibility policy (same build/environment/machine; Generator may change in feature releases; `RandomState` frozen; `random()`×5 vs `random(5)`) | `numpy/numpy` `doc/source/reference/random/compatibility.rst` (main) | Read; claims match |
| scikit-learn `random_state` semantics for `None`, int, `RandomState` instance | `scikit-learn/scikit-learn` `doc/glossary.rst` (main) | Read; claims match |
| PyTorch reproducibility caveats; `manual_seed`; `cudnn.benchmark`; `use_deterministic_algorithms`; DataLoader `worker_init_fn` + `generator` | `pytorch/pytorch` `docs/source/notes/randomness.md` (main) | Read; claims match. No PyTorch code executed |
| Effective-level and handler-level filtering details; `StreamHandler` default stream is stderr | Python `logging` behaviour as exercised by the lesson's reference solution and checks | Executed (behavioural), library reference text for these points not separately quoted |
| YAML 1.1 implicit typing pitfalls; unsafe `yaml.load` | — | **Not re-verified this session** (from memory) |
| pydantic and Hydra/OmegaConf characteristics | — | **Not re-verified this session** (from memory); check current docs before relying on defaults |
| `SeedSequence.spawn` exists and returns child sequences | executed on NumPy 2.5.3 | Executed; statistical-independence claim **not re-verified this session** |
| NASEM (2019) vs ACM terminology for reproducibility/replicability | — | **Not re-verified this session** (from memory) |
| Seed-spread figures for the synthetic pump data | computed in the authoring session with the w1d4 reference solution (Python 3.13.18, NumPy 2.5.3, pandas 3.0.5, scikit-learn 1.9.1) | Executed; SYNTHETIC data — illustrates the phenomenon, not its size on real data |

Further reading (optional, not required to complete the lesson): the Python *Logging Cookbook*; the
scikit-learn user-guide page on controlling randomness; NEP 19 (NumPy random number generator
policy).
