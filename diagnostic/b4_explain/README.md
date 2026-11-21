# b4 - Explain and defend an ML decision

**Time box: 20 minutes.** Session B, section 4 of 4. Written only; no code, no automated check.

## Scenario

You join a team that maintains monitoring for industrial air compressors: 40 compressors at 6
customer sites, hourly sensor aggregates (pressures, temperatures, vibration RMS, motor current) for
18 months. Maintenance logs give 31 recorded failures. Today an alarm fires when discharge temperature
exceeds a fixed threshold; technicians complain about false alarms and two failures were missed last year.

A teammate presents this result and the product manager wants a decision this week:

> "Each hourly row is labelled 1 if that compressor failed within the next 7 days (0.8% of rows are
> positive). A gradient-boosted model reaches **ROC AUC 0.97** in 5-fold cross-validation with
> shuffled rows; logistic regression gets 0.90. I propose we replace the threshold alarm with the
> boosted model next sprint."

## Task

Write a memo to the product manager and the teammate in `lab/MEMO.md`, **at most 350 words**:

1. Your recommendation (ship / do not ship yet / ship in a limited form) in the first two sentences.
2. The two or three most important reasons, each tied to a specific property of this data or this
   evaluation - not generic caveats.
3. The smallest additional piece of evidence that would change or confirm your recommendation, and
   how long you estimate it takes to produce.
4. One tradeoff you are making deliberately.

Write for a reader who is technically literate but not an ML specialist. No bullet-point dump of
every possible concern: prioritise.

## Acceptance criteria

Graded by rubric after you submit (see `SUBMISSION.md`). The rubric looks at: correctness of the
technical reasoning, prioritisation, whether the recommendation is actionable, and clarity.

## Submit

`lab/MEMO.md`, time used.
