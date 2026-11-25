# Model card: flowguard flow-rate z-score detector (`flowrate-z-2026.11`)

Educational research prototype. Numbers are from `results.json` in this folder; see
[TECHNICAL_REPORT.md](TECHNICAL_REPORT.md) for methods and intervals.

| Field | Content |
|---|---|
| What it does | Scores each sample of a water-circulation testbed by the absolute z-score of the flow rate, normalised on the first 100 rows of the same run; alarms when the score stays above a threshold chosen for at most one false alarm per 8 hours of normal operation |
| Intended use | Teaching and research on fault-detection workflows; a starting point for a pilot that would be evaluated on its own data |
| Out of scope | Safety-critical shutdown decisions; any real plant without a new evaluation; fault types absent from SKAB; runs shorter than the normalisation window |
| Training data | SKAB `v0.9` development recordings (27), downloaded by hash; GPL-3.0, not redistributed |
| Evaluation data | 7 frozen test recordings, looked at once; plus a held-out fault family (protocol B) |
| Performance | Test PR-AUC 0.884 [0.811, 0.928] (cluster bootstrap over recordings); 5 of 7 faults detected, Wilson recall interval [0.36, 0.92]; median delay 100 s; no false alarm in about 1.2 hours of normal operation |
| Inputs | Flow rate in L/min at about one sample per second, validated against the data dictionary; out-of-support values are flagged, not silently scored |
| Outputs | Score, alarm flag, model version, `degraded` flag and reason |
| Known failure modes | Missed `valve1/8` and `valve2/0`; scale-invariant, so a units error does not change alarms and must be caught by the support check; degraded fallback detects 2 of 7 test faults |
| Monitoring | Out-of-support rate, alarm rate against the budget, input drift (PSI, threshold 7.53), degraded-mode time, delayed-label recall |
| Update policy | Offline gate on the frozen protocol (non-inferiority, paired cluster bootstrap), shadow run, promotion by registry pointer, rollback to the previous version |
| Ethical and practical considerations | Over-trust is the main risk: the alarm can miss faults, so it supplements and does not replace inspection |
