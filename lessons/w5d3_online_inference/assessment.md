# Assessment - w5d3 online inference

Answer in writing (or aloud, recorded) before opening
`solutions/lessons/w5d3_online_inference/assessment_answers.md`. 20-25 minutes in total.

## Reasoning questions

1. A sensor reports pressure in pascals around 1.0e5 Pa with an SD of 3 Pa. Your colleague keeps
   `n`, `Σx`, `Σx²` per machine. Estimate the relative error of the variance in float64, and say
   whether it matters for a z-score detector with threshold 7.
2. Your streaming scorer returns `0.0` during the warm-up "so the dashboard has no gaps". Give two
   concrete downstream harms.
3. Why must a rejected sample leave the state unchanged? Describe a failure that happens if an
   out-of-order sample is rejected *after* the Welford update ran.
4. With `gap_policy="flag"`, streaming and batch scores agree. With `gap_policy="reset"` they do not
   agree with `score_batch(run)`. Is the reset policy therefore wrong? What does parity mean for it?
5. Parity of scores holds within 1e-9. Does that guarantee identical alarms? When could it fail, and
   how would you test for it?
6. A process restarts while machine `P07` is at sample 60 of its 100-sample burn-in. Without a
   snapshot, what happens to `P07`'s scores for the rest of the run? With a snapshot that stores only
   `mu` and `sigma`?

## Explain a design choice (written, 150-250 words)

Defend the duplicate policy of this lesson: identical retry -> previous answer, same timestamp with a
different value -> error. Compare with two alternatives ("last write wins" and "always error") in
terms of correctness under at-least-once delivery, and what each tells the client.

## Rubric for the open-ended answers

| Criterion | Strong | Adequate | Weak |
|---|---|---|---|
| Numerical reasoning (Q1) | estimates `ε(μ/σ)²`, gets the order of magnitude, relates it to the threshold | knows cancellation happens, no estimate | "float64 is precise enough" |
| Contract thinking (Q2-Q4) | names the consumer that is misled and the invariant that protects it | describes the bug | restates the rule |
| Scores vs decisions (Q5) | distinguishes score parity from decision parity, proposes a margin test | mentions thresholds | "1e-9 is negligible" |
| State and restarts (Q6) | traces both cases to concrete wrong scores | one case | no mechanism |
| Design choice | argues from delivery semantics and from what the client can do next | lists the options | asserts a preference |

## Interview rep (12 minutes, Python, reduced assistance)

> Implement `SlidingMedian(w)` with `push(x) -> float | None`: the median of the last `w` values of
> a stream, `None` until `w` values have arrived. State the time per `push` and the memory. Then write
> two tests you would run before trusting it.

Time yourself. No hints for this one; compare afterwards with
`solutions/lessons/w5d3_online_inference/interview_rep/` (reference with tests) and the rubric in the
answers file.
