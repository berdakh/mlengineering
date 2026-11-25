# Milestone 4 submission: flowguard monitoring demonstration

<!-- Fill every field. Replace every TODO. Graded by structure checks and by a reviewer with the
     rubric in labs/w7d6_project_milestone_4/assessment.md. -->

Repository: TODO (URL of your flowguard repository)
Commit: TODO (hash of the commit the demo was run from)
Tag: TODO (e.g. v0.9.0-m4)
Demo command: TODO (the exact command, e.g. `make monitor-demo RAW=data/raw/skab`)
Report: TODO (path of the generated monitoring_demo.md inside the repository)
Runbook: TODO (path of RUNBOOK.md)
Time spent: TODO (hours)

## Demo results (copied from results.json, summary)

Events: TODO
Events as expected: TODO
Drift threshold: TODO
Faults labelled: TODO
Faults detected: TODO
Not as expected: TODO (event ids and one sentence each, or "none")

## Checklist

Tick each item (`- [x]`) or mark it `- [n/a]` with a one-line reason. No unticked boxes.

- [ ] One command regenerates the whole demo from raw data, the frozen manifest and the scenario file.
- [ ] Every number in the report comes from results.json; nothing in the report is typed by hand.
- [ ] Normal operation produced no alert in the demo, and the report shows it.
- [ ] A bad input (units) was caught by validation or the support guard, not by the model.
- [ ] Input drift was flagged by a monitor whose threshold was calibrated on development data only.
- [ ] A real fault was detected as an alarm event; any missed fault is listed as not detected.
- [ ] The delayed-label report states how much traffic it covers.
- [ ] A bad promotion was caught by a monitored signal and rolled back; /version confirmed the rollback.
- [ ] Every service process the demo started was stopped (pids recorded in results.json).
- [ ] Running the demo twice gives identical numbers.
- [ ] Every alert in configs/alerts.toml has a runbook entry with meaning, first actions and escalation.
- [ ] The runbook's known limitations include the measured weaknesses (fallback, drift monitor, small label set).

## Self-review

Score each row 1 (below expectations), 2 (meets) or 3 (exceeds), using the rubric in `assessment.md`.
Evidence: at least one concrete sentence pointing at a file, a number or a command.

| Criterion | Score | Evidence |
|---|---|---|
| Reproducible demo | TODO | TODO |
| Coverage of failure scenarios | TODO | TODO |
| Report integrity | TODO | TODO |
| Service lifecycle and rollback | TODO | TODO |
| Runbook usefulness | TODO | TODO |
| Honesty about limitations | TODO | TODO |

## Questions for the reviewer

- TODO (at least one specific question you want feedback on)
