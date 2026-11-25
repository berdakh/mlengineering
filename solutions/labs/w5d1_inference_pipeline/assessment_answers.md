# W5D1 assessment: model answers

## Reasoning questions

**1. 1.4e-14 on scores near 8.** Not skew. A relative difference of about 2e-15 is one or two units in
the last place of a double. It came from reading the CSV with pandas' default float parser, which is
not round-trip exact: 2,017 of 6,659 scores changed in the last digit, the largest by a relative
5.9e-16. With `float_precision="round_trip"` the difference is exactly 0. It would become skew if
any alarm decision changed (a score within 1e-14 of the threshold, which is possible but has to be
checked), or if the difference grew with the score in a way that pointed to a different formula, for
example a constant factor of sqrt(100/99) from ddof=1.
*Common incorrect answers.* "Any difference is skew" turns floating-point order of operations into
false alarms in CI. "It is tiny, so ignore it" with no tolerance and no decision check is how a
0.5 % ddof skew also gets ignored.

**2. Per-batch standardisation.** The detector measures distance from the run's own start-up level.
Standardising by the batch puts the fault inside the reference: the mean moves towards the faulty
level and the standard deviation grows. In the lesson's synthetic run, a 6-SD step gives a median score of
5.67 calibrated on burn-in, against 0.93 calibrated on the whole run. Maximally wrong: a batch made
entirely of faulty rows (a late chunk of a long fault). Its own z-scores are noise around 0, so the
detector reports health during the fault.
*Common incorrect answer.* "It only removes drift." It removes the signal the detector exists to see.

**3. Column order.** For selecting by name: every column is named, and name-based selection is immune
to order. For refusing: a producer that changed the order changed its export code, so other
assumptions may have changed too (units, sensor mapping). A loud refusal is cheaper than a quiet
assumption. Selecting by name is safe only if every consumer downstream also works by name. Ship
the strict version with a versioned schema, and relax it only when the producer is under the same
team's control and has its own contract tests. The real danger is matching by *position*, which is
what the mutant did.

**4. Per-run errors.** A short run is a property of one run's data, not of the file's format, and the
other runs' predictions are still correct and needed. Stopping the batch would let one truncated
upload silence every machine. Stop everything when the failure means the input cannot be trusted as
a whole: a schema error, a file from the wrong plant, or more than a set fraction of runs failing,
which suggests an upstream outage rather than bad runs.

**5. Refusing to overwrite.** It prevents silently replacing yesterday's predictions (which may
already have been acted on or audited) with predictions for a different input, for example a
scheduler retry that points at the wrong date. Cost: a re-run with a corrected input needs
`--force` or a new output directory. That is a deliberate step, and the manifest records what
replaced what.

## Design-choice explanation: model answer

The operating point is the one decision made with labels. It is only valid for the exact function
that produced the scores it was chosen on. If it were chosen with the evaluation code and served with
another implementation, the two would agree today and could diverge after any refactor of either. The
threshold would then be applied to a different score than the one it was tuned on. Choosing it with
`Detector.score_batch` makes the served object the evaluated object. The parity test keeps the w4d5
code honest: it scores the same synthetic runs through `flowguard.detectors` and through `Detector`
and requires agreement within 1e-12 and identical alarms. That test runs in CI, so neither path can
change alone.

## Interview rep rubric (debugging: fewer alerts than offline)

| Level | What the answer contains |
|---|---|
| Strong | Starts from "the served function or the served data differs from the evaluated one", not from "the model is bad". In order: (1) replay a sample of logged production inputs through the offline pipeline and compare scores row by row (parity; finds skew); (2) compare the input distributions and the score distribution in production against the evaluation set (finds population shift or a broken feature: constant, all-null, unit change); (3) check what threshold and model version are actually loaded (config skew). Notes that "alerts are good" means precision is fine, so the score is probably shrunk or shifted, not random. Mentions feature order, defaults for missing values, per-batch normalisation and stale reference statistics as usual causes. |
| Adequate | Proposes comparing offline and online scores and checking feature distributions, without an order of checks or a hypothesis about what "fewer but good alerts" implies. |
| Weak | Retrains the model, lowers the threshold, or blames concept drift before checking that the served function is the evaluated one. |

Worked answer, abridged. "Fewer alerts with good precision means production scores are shrunk relative
to offline ones. I'd take yesterday's logged inputs and score them with the offline pipeline. If the
scores differ row by row, it's skew. Then I'd diff the feature vectors and find the first feature
that differs: usually a default for missing values, a re-implemented scaler, or a feature computed
over the request batch instead of the user's history. If the scores agree, the inputs moved, and I
compare feature distributions against the evaluation period. Last, I'd confirm the threshold and
model version the service actually loaded. Whatever it is, the fix includes a parity test in CI."
