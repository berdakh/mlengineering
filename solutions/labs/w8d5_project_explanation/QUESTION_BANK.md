# Question bank: what a strong answer contains (reviewer side)

Each row: the points a strong answer makes, the artifact that backs them, and the common weak answer.
Numbers are from the cited lessons (real SKAB unless marked). The reference answers in `lab/ANSWERS.md`
are one way to say them.

| # | A strong answer contains | Backed by | Weak answer |
|---|---|---|---|
| Q01 | how it was found (data skeleton / overlap check); 1,290 duplicated rows, 235 with contradictory labels; overlap groups kept on one side; test set repaired, not redrawn | `project/README.md`, `labs/w3d1_leakage/README.md` | "we removed duplicates" (they span files; removal hides the label conflict) |
| Q02 | protocol leak (onset near row 550-600 in 31/34 experiments); clock F1 0.835; time-monotone features forbidden; clock kept as a sanity row | `labs/w2d6_baselines_metrics/README.md` | "the clock baseline is a curiosity" |
| Q03 | concedes; event recall 5/7 with interval about 0.36-0.92; decisions on 27 dev experiments; one test look; relative not precise claims | `labs/w4d5_model_choice/figures/test_look.csv` | "we have thousands of samples" |
| Q04 | protocol A 0.920 vs leave-family-out 0.636; labels support supervision for seen families only; isolation forest / PCA held up | `labs/w4d2_classical_detectors/README.md` | "trees overfit" without the protocol-B evidence |
| Q05 | tried under equal budget; 5 seeds, mean 0.754 sd 0.068 vs 0.884 for flow-rate z; data size argument; would revisit with more data | `labs/w4d3_neural_comparison/README.md` | "deep learning is overkill" (opinion, no evidence) |
| Q06 | decision rule set in advance (MPID 0.05); logistic +0.069 [0.022, 0.128] inconclusive; cost columns (370 B, NumPy only, sub-ms); explainability | `labs/w4d5_model_choice/figures/decision_table.csv` | apologising for simplicity |
| Q07 | alert budget first; threshold 7.24 and post-processing on dev; one test look; nested-validation optimism | `labs/w3d3_hyperparameter_selection/README.md` | "tuned it on the test set to be safe" |
| Q08 | event-level as decision metric (recall, delay, false alarms/h); point metrics' bias; point-adjust inflation; events don't fix leakage (clock 3/7) | `labs/w3d4_point_vs_event_evaluation/README.md` | "F1" with no level stated |
| Q09 | drift answers "did inputs change", not "is there a fault"; 14-20 % of fault windows flagged; three monitors for three questions | `labs/w7d2_input_monitoring_drift/README.md` | "drift detects faults" |
| Q10 | 422 at the boundary; out-of-support flagged; readiness false on model failure; fallback with `degraded: true`; fallback 2/7 vs model 5/7 | `labs/w7d5_reliability/README.md` | "it returns 500" or "it uses a default score" |
| Q11 | Nagle + delayed ACK with multi-worker uvicorn; ~40 ms floor; p50 52 -> 9.5 ms with TCP_NODELAY; measured, then fixed | `labs/w6d4_latency_resources/README.md` | "Python is slow; we added workers" |
| Q12 | one inference object; three-way parity exactly 0 over 46,806 rows; streaming within 1e-12; CSV round-trip finding | `labs/w5d6_project_milestone_2/README.md` | "we used the same code" (untested claim) |
| Q13 | 198 samples exactly at the threshold; 1e-14 differences flip flags; same faults caught; deterministic tie rule and documented comparison | `labs/w7d3_drift_vs_degradation/README.md` | "floating point doesn't matter" |
| Q14 | delayed labels joined to logged predictions; threshold regression 11/20 -> 4/20 with no drift flag; estimate unknown then inconclusive; proxies as early warning | `labs/w7d3_drift_vs_degradation/README.md` | "the drift monitor would tell us" |
| Q15 | offline gate with paired comparison and margin (+0.143 [0.000, 0.429]); shadow; coverage gap (no "other" family in shadow traffic); rollback as pointer move, byte-identical | `labs/w7d4_model_updates_rollback/README.md` | "A/B test it" with no guardrails |
| Q16 | more independent experiments first; label review of the 235 rows; per-family supervision with leave-family-out; live monitoring calibration | `project/README.md` | "try transformers" |
| Q17 | lab testbed, induced faults, ~35 % anomalous samples, 34 experiments; experimenter labels; false alarms/lead times don't transfer; pilot needed | `project/README.md` | overclaiming plant readiness |
| Q18 | experiment = independent unit (like patient); row-level ROC-AUC 0.986 vs experiment-level 0.849 on dev; cost: fewer, noisier folds | `labs/w2d4_problem_framing_splits/README.md` | "to avoid overfitting" |
| Q19 | dependence within experiments; row bootstrap 3-7x too narrow; cluster bootstrap; exact binomial for 7 events | `labs/w3d5_uncertainty/README.md` | "the bootstrap is standard" |
| Q20 | what transfers (units, events, artefacts, drift); what is new (package, tests, CI, artifact, API, container, deployment, monitoring, rollback) | `handbook/README.md` | "it is the same" or "nothing transfers" |

## Scoring a full set

Count answers meeting all three rows of the answers rubric (honesty, grounding, brevity). Do not turn
the count into a grade; use it to pick the five answers to rewrite and re-record.
