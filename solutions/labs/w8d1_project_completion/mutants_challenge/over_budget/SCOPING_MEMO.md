# Gap list and scoping memo

Project: reference flowguard (course solutions) · Time available before submission: 5 h · Date: 2026-11-22

## Gap list

| # | Gap | Evidence | Impact if left | Effort (h) | Decision | Reason |
|---|---|---|---|---|---|---|
| 1 | Clean-clone audit ran on Python 3.13 only | `real_audit/REPRODUCTION_LOG.md` (Auditor Python 3.13.18) | requires-python says >= 3.11; a 3.11 user may not reproduce the numbers | 1 | fix now | add the audit to the CI matrix so 3.11 and 3.12 run it on every tag |
| 2 | Drift threshold has a thin margin | w7d6 report: threshold 7.53, a healthy test experiment reached 7.38 | roughly one false drift alert per 28 healthy windows by construction | 1.5 | fix now | recalibrate per family and state the implied false-alarm rate in the runbook |
| 3 | No live cloud deployment | `DELIVERABLES.md` row "One deployment": partial (dry run only) | cannot show a public endpoint; latency numbers are local only | 3 | scope out | live AWS use was never authorised and costs money for no learning gain here |
| 4 | Only 7 test experiments, 34 events in total | w4d6 report: test recall 5 of 7, Wilson interval [0.36, 0.92] | no claim about recall better than "roughly a third to nine tenths" | 0 | scope out | the dataset is fixed; more data would need a new benchmark version |
| 5 | Duplicated rows with contradictory labels in five file pairs | `project/README.md`: 1,290 shared rows, 235 with conflicting labels | some labels are wrong; scores near segment boundaries are uncertain | 4 | defer | adjudicating labels needs the testbed authors; keep the overlap groups together meanwhile |
| 6 | Fallback rule detects 2 of 7 test faults | w7d5 drill: fallback 2/7 versus model 5/7 | degraded mode is much weaker than the model it replaces | 2 | fix now | improve after the report; the degraded flag already makes the weakness visible to users |
| 7 | Runbook not tested by someone else | w7d6 rubric row "tested by someone else" not met | an on-call engineer may not be able to follow it | 1 | fix now | ask a colleague to run the rollback section once and record the gaps |

## Scoping decisions

Fix now, in this order, 3.5 of the 5 hours: the CI audit on 3.11 and 3.12 (gap 1) because every other
claim depends on reproducibility; the drift recalibration (gap 2) because the runbook currently promises a
false-alarm rate the threshold does not deliver; the runbook dry run (gap 7). The remaining 1.5 hours go
to the technical report in w8d2. Deferred: label adjudication and a better fallback, both after the report.
Scoped out: a live deployment and any attempt to enlarge the test set.

## What I will say about scoped-out items

The deployment exists as a reviewed runbook and a dry run, and the same container runs locally with the
production configuration; I chose not to spend money on a public endpoint that would prove nothing new.
The small test set is a property of the benchmark: I report intervals instead of point estimates, and I say
the recall could be anywhere from about a third to nine tenths. With more time I would collect or
simulate more fault events before claiming anything about rare fault types.
