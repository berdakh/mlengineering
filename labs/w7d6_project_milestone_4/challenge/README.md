# Challenge: submit milestone 4 (independent)

Run the demo on the **real** data in your own flowguard repository, read the report as a reviewer would,
and fill in [SUBMISSION.md](SUBMISSION.md). Tick only what is true; mark anything you did not do as `n/a`
with a reason. Score yourself against the rubric in [../assessment.md](../assessment.md) with evidence a
reviewer can check (a file, a number, a command). Commit the generated report and your runbook, tag the
commit (`git tag v0.9.0-m4`), push, and push the submission.

The "Demo results" fields are copied from your generated `results.json` (summary). If an event was not as
expected (in the reference run, `E5-fault`: the model misses the fault in `valve1/8`), say so: a demo
that shows a known miss honestly is stronger than one that hides it.

**Acceptance criteria.** `python wb.py check w7d6 --challenge` passes (structure only: no TODO left, header
and result fields well formed, every checklist item ticked or justified, every self-review row scored
with evidence, at least one specific question). Quality is judged by the reviewer, not by the checks.
