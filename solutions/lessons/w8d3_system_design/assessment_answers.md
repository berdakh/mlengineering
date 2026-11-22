# w8d3 assessment — model answers

**Q1.** 40,000,000 / 86,400 s ≈ 463 transactions/s on average; × 6 ≈ 2,778/s at peak. Busy cores =
2,778/s × 0.008 s ≈ 22.2 (Little's law). Usable cores per replica = 4 × 0.5 = 2. Replicas = ceil(22.2 / 2)
= **12**, then add capacity for a zone failure (e.g. 3 zones × 6 = 18) because 12 is the minimum with
everything healthy. *Common wrong answers:* dividing by 3,600 (per hour) gives 24x too much; forgetting the
utilisation target gives 6; rounding 11.1 to 11.

**Q2.** Predictions in the last 90 days are labelled only if at least 60 days old: (90 − 60)/90 = **one
third**. With a 100-day delay, **none** are: the evaluation window must grow past 100 days or monitoring
has to rely on proxies and input checks until labels arrive. *Wrong:* "two thirds" (counts the wrong end
of the window); "all of them, just later" (true eventually, but not in today's window).

**Q3.** (a) **Batch**: computed once a week, no latency constraint, cheapest. (b) **Online**: the decision
blocks the authorisation and depends on this transaction's details. (c) **Streaming**: features are windows
over a continuous signal and the reaction time (a minute) is shorter than any batch cadence. (d) **Batch**:
produced daily for a planning process; online adds cost and nothing else. *Wrong:* "online for everything
to be safe" — online multiplies cost and failure modes when the consumer does not need fresh answers.

**Q4.** With linear costs `c_late` per minute late and `c_early` per minute over-estimated, the expected
cost of quoting `q` is minimised where `P(T ≤ q) = c_late / (c_late + c_early)` (the newsvendor result).
With `c_late = 3 c_early` that is the 0.75 quantile. Mean + margin assumes a symmetric, constant-width
error distribution; delivery times are right-skewed and their spread varies with load, so a fixed margin
is too wide at quiet times and too narrow at peak. *Assumption:* the costs really are linear and in the
stated ratio; if lateness costs grow faster (anger at 20 min late, not 2), the right quantile moves up.

**Q5.** (1) Different window boundaries (SQL `>= now - 15 min` on event time vs the stream's processing
time); (2) late or out-of-order events counted in training but missed online; (3) different filters or
definitions (cancelled orders included in one place); also time zones, null handling. Prevention: one
feature definition executed by one engine for both (a feature store or shared library), with training rows
produced by **replaying** the online computation point-in-time, plus a parity test that compares logged
online values with recomputed offline values on a sample every day.

**Q6.** Optimising and evaluating the same quantity invites Goodhart effects and blind spots. A metric not
trained on checks that the improvement means what you think. D2: trained on pinball loss, launched on
**late-order rate and conversion**; D1: trained on click-derived preferences, launched on **success rate**
(no quick re-search) and per-department guardrails.

**Q7.** Jumping to a model before requirements; no metric or the wrong metric (accuracy, MAE) for the
decision; no discussion of where labels come from and when they arrive; no numbers (QPS, latency, data
size), so no basis for architecture choices; ignoring failure modes and cost. Instead: three minutes of
requirements, an explicit target and label, one estimation table, then the architecture.
