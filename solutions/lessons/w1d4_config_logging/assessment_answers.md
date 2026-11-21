# W1D4 assessment — model answers

Open only after writing your own. Model answers are one good answer, not the only one; score with
the rubric in `lessons/w1d4_config_logging/assessment.md`.

## A1

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

## A2

(1) A command-line override (`--set model.C=0.1`): the file says 1.0, the snapshot 0.1.
(2) The file was edited without committing (the `-dirty` suffix on the recorded commit tells you),
or the file was changed in a later commit and you are reading the wrong revision. Also acceptable:
a key omitted from the file, where the snapshot shows the default in force *at that code version*.
Trust `config.json`: it was serialised by the run itself from the single object that the computation
received. The file is an *input* to that object, one of several.

*Common incorrect answer.* "Trust git, it is the source of truth." Git is the source of truth for
what was *committed*; the run may not have used exactly that.

## A3

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

## A4

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

## A5

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

## A6

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

## B1 — one defensible answer

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

## C — reference

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

## Lab reproducibility note — what a good one contains

*Fixed by the config:* data path, sampling rate, split fraction and seed, `C`; given those and the
same environment, the pipeline (interpolation, features, group split, scaler + logistic regression
with the lbfgs solver) is deterministic, verified by two identical runs. *Recorded but not fixed:*
Python and library versions, platform, git commit and dirty flag, data file hash — a mismatch can be
detected but the environment cannot be recreated from the record alone. *Neither:* BLAS threading
and numerical differences across machines/builds (could change low-order digits), anything read
from the process environment, and the fact that the result is one draw over splits. A 3-point note
also says what would change the picture (a neural model, a GPU).

## Challenge note (criterion 6) — what a good one contains

A metric delta can be attributed to a modelling change only when `same_data` is true and
`config_diff` contains nothing but the intended modelling keys — in particular not `split.seed` or
`data.*` — *and* the code commits are the ones intended. Even then it is one split: you would still
want the delta's distribution over seeds (paired), the environment diff, and whether the comparison
was planned before looking at the numbers.
