# Milestone 4 submission: flowguard monitoring demonstration

Repository: https://github.com/example-user/flowguard (reference submission; replace with yours)
Commit: 3f9c2e1
Tag: v0.9.0-m4
Demo command: `make monitor-demo RAW=data/raw/skab OUT=reports`
Report: reports/monitoring_demo.md
Runbook: RUNBOOK.md
Time spent: TODO

## Demo results (copied from results.json, summary)

Events: 8
Events as expected: 7
Drift threshold: 7.5253
Faults labelled: 2
Faults detected: 1
Not as expected: E5-fault: the shipped model does not detect the fault in valve1/8 (alarm rate 0.0009, no alarm event), which matches the 5 of 7 test faults from milestone 1.

## Checklist

- [x] One command regenerates the whole demo from raw data, the frozen manifest and the scenario file.
- [x] Every number in the report comes from results.json; nothing in the report is typed by hand.
- [x] Normal operation produced no alert in the demo, and the report shows it.
- [x] A bad input (units) was caught by validation or the support guard, not by the model.
- [x] Input drift was flagged by a monitor whose threshold was calibrated on development data only.
- [x] A real fault was detected as an alarm event; any missed fault is listed as not detected.
- [x] The delayed-label report states how much traffic it covers.
- [x] A bad promotion was caught by a monitored signal and rolled back; /version confirmed the rollback.
- [x] Every service process the demo started was stopped (pids recorded in results.json).
- [x] Running the demo twice gives identical numbers.
- [x] Every alert in configs/alerts.toml has a runbook entry with meaning, first actions and escalation.
- [x] The runbook's known limitations include the measured weaknesses (fallback, drift monitor, small label set).

## Self-review

| Criterion | Score | Evidence |
|---|---|---|
| Reproducible demo | 2 | Two runs of `make monitor-demo` gave identical summaries; the checks rerun it on synthetic data. |
| Coverage of failure scenarios | 2 | Units bug, drift, two faults, bad promotion and rollback are scripted in scenarios/demo.toml; no injected model fault yet. |
| Report integrity | 3 | render_report reads only results.json; the planted hand-typed drift threshold of 0.25 was removed. |
| Service lifecycle and rollback | 2 | Three processes started and stopped (results.json server.pids); /version showed flowrate-z-2026.11 after E8. |
| Runbook usefulness | 2 | Six alerts with meaning, first actions and escalation; the rollback section has the exact commands. |
| Honesty about limitations | 3 | The report lists E5-fault as not detected and the runbook says 2 labelled faults say almost nothing about recall. |

## Questions for the reviewer

- The drift monitor's threshold is the maximum PSI over 27 development experiments, and a healthy test experiment already reaches 7.38 against 7.53: should I monitor normalised values instead of raw flow?
