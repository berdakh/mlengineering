# w5d7 - retrieval answers

Open only after all twelve questions have a written attempt. Each answer states what a "solid"
answer must contain, then common wrong answers and why they fail.

Written against the final Week 5 lessons on 2026-11-22. Every real-data number is copied from those
lessons' authoring runs on the frozen manifest v2 (7 test, 27 development experiments). Numbers marked
*(SYNTHETIC)* come from the lessons' synthetic illustrations. Section references are to the lesson
named in each heading.

## 1. Training/serving skew versus numerical noise (w5d1, 2.2)

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

## 2. Fit-time configuration versus per-run state (w5d1, 2.3; Figure 5)

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

## 3. Batch command design; more alarms without skew (w5d1, 2.5 and section 8)

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

## 4. Bundle anatomy and refusals (w5d2, 2.1 and 2.3)

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

## 5. Pickle and the alternatives (w5d2, 2.2 and 3.2)

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

## 6. Four versions; the registry (w5d2, 2.4 and 2.5)

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

## 7. Welford; O(1) state (w5d3, 2.1 and 2.3; worked example)

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

## 8. Five streaming decisions; 0.5 % lower (w5d3, 2.4 and section 8)

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

## 9. Three gates, decision order, liveness versus readiness (w5d4, 2.1-2.3; section 8)

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

## 10. NaN, sync handlers, lifespan (w5d4, 2.2, 2.4 and 2.7)

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

## 11. Test layers, kill matrix, concurrency, contracts (w5d5, 2.1-2.7)

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

## 12. Three-way parity; 1.0541; round-trip CSV (w5d6, 2.1 and 2.2; section 8)

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
