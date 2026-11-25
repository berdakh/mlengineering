# Assessment answers - w5d3 online inference

## 1. Pressure in pascals, `n`, `Σx`, `Σx²`

`μ/σ ≈ 1e5 / 3 ≈ 3.3e4`, so `(μ/σ)² ≈ 1.1e9` and the lower bound `ε(μ/σ)² ≈ 1.2e-7`. Summing 10,000
values adds accumulated rounding: a simulation (20 draws of 10,000 SYNTHETIC samples, mean 1e5, SD 3,
run while authoring this answer) gave a median relative error of 3.0e-6 and a maximum of 1.3e-5. The SD
is off by about half of that, so z-scores are off by ~1e-6 relative: for threshold 7 an alarm decision
changes only if a score lies within ~1e-5 of 7. **For detection it does not matter; for a parity test
with tolerance 1e-9 it fails**, and the fix (Welford, or shift by the first sample) costs nothing.

*Common wrong answers.* "float64 has 16 digits, so no problem" (ignores cancellation). "The error is
1e-16" (confuses machine epsilon with the error of a difference of large numbers).

## 2. Returning 0.0 during warm-up

* Every consumer reads it as "measured and perfectly normal": a monthly mean of scores, an SLO such as
  "fraction of samples with score < 3", or a model-monitoring drift statistic (week 7) is biased toward
  normal by every restart.
* An alert rule `score < 0.5 for 10 min -> sensor stuck` fires on every warm-up. More generally,
  downstream code cannot tell "no information" from "good news", so no consumer can handle warm-up
  correctly even if it wants to.

The honest representation is `null` plus a status, so a dashboard can draw a gap and label it.

## 3. Rejections must not change the state

If the Welford update ran before the out-of-order check, the late value would be inside `mean` and
`M2` although the caller was told it was rejected. The client then (correctly) re-sends it later in the
right order, and it is counted twice; or the client gives up and the state contains a value no record
says was accepted. Either way the scores no longer equal `score_batch` of any sequence of accepted
samples, and nobody can reproduce them. The general rule: validate everything, then mutate.

## 4. Gap reset and parity

The reset policy is not wrong; it implements a different batch function: "split the run at gaps longer
than `max_gap_s` and score each segment with `score_batch`". Parity must be stated against *that*
function (the checks test exactly this). The point is that every streaming policy has a batch
definition, and that definition is what you evaluate offline. If offline evaluation used
`score_batch(run)` and production uses reset, the offline numbers describe a different system.

## 5. Score parity vs decision parity

No. A score within the tolerance of the threshold can fall on different sides in the two paths. Test
it directly: compare the boolean exceedances as well as the scores, and report the smallest distance of
any score to the threshold (0.036 on the real replay, so no decision can differ there). If decisions
must match exactly, use the same arithmetic in both paths (one code path, as `hysteresis_batch` does in
the challenge) rather than two implementations.

## 6. Restart during the burn-in

* **No snapshot**: the new process starts a fresh burn-in at sample 61. Its `mu`/`sigma` come from
  samples 61-160, scores start at 161, and they differ from batch for the whole run. If a fault starts
  around sample 120, it is absorbed into the calibration and may never be detected.
* **Snapshot with only `mu`/`sigma`**: both are `None` at sample 60, so the restored scorer has no
  accumulators and restarts the burn-in from zero: the same failure as no snapshot, but with the false
  confidence of "we checkpoint". (This is the `restore_restarts_burn_in` mutant.)

## Design choice: duplicate policy (model answer)

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

## Rubric for the interview rep

| Level | Evidence |
|---|---|
| Strong | ring buffer for eviction + sorted structure (bisect) or two heaps with lazy deletion; correct even-`w` median; `None` before `w` values; states O(w) memory and O(w) (bisect/list) or O(log w) (heaps) time per push; tests compare with `numpy.median` on random data **with ties** and check the first `w-1` outputs |
| Adequate | correct but recomputes `sorted(window)` on every push (O(w log w)), says so, tests only a hand-made example |
| Weak | upper median for even `w`; removes the wrong element when values repeat; no tests |

Reference: `solutions/labs/w5d3_online_inference/interview_rep/sliding_median.py` and its tests
(`python -m pytest solutions/labs/w5d3_online_inference/interview_rep -q`: 11 passed). An
upper-median version fails 2 of them.
