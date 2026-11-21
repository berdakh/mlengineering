# W2D3 — model answers

## Q1

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

## Q2

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

## Q3

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

## Q4

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

## Q5 — reference report

See `challenge/QUALITY_REPORT.md` in this solutions folder.

## Interview rep — rubric and a model answer outline

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
