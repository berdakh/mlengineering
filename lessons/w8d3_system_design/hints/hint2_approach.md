# w8d3 hint 2 — approach

**Worksheet.**
1. Validate first: a helper that raises `ValueError` unless a value is finite and positive, and another for
   fractions in (0, 1]. Call them at the top of each function; the checks pass `nan`, 0 and negatives.
2. `replicas_needed`: busy cores = qps × ms / 1000. Divide by usable cores per replica (cores × target
   utilisation), round **up**, and never return fewer than one. Watch floating point at exact boundaries
   (2.0000000001 must not become 3): subtract a tiny epsilon before `ceil`.
3. `labels_for_precision`: invert the half-width of a normal-approximation interval,
   `h = z·sqrt(p(1-p)/n)`, for `n`, then round up.
4. `latency_remaining_ms` may return a negative number; that is the useful answer when a design is over
   budget.

**Design review.** Walk the doc in the order of the lesson's structure (requirements → data and labels →
evaluation → serving → monitoring → iteration). For each section write one line "what would go wrong in
production if built exactly like this?" Then rank: anything that makes the reported metric meaningless is
a blocker; anything that breaks the service or the users at launch is major.
