# Question bank: what a strong answer contains (reviewer side)

Each row: the points a strong answer makes, the artifact that backs them, and the common weak answer.
Numbers are from the cited lessons (real SKAB unless marked). The reference answers in `lab/ANSWERS.md`
are one way to say them.

| # | A strong answer contains | Backed by | Weak answer |
|---|---|---|---|
| Q01 | how it was found (data skeleton / overlap check); 1,290 duplicated rows, 235 with contradictory labels; overlap groups kept on one side; test set repaired, not redrawn | `docs/guides/project.md`, `notebooks/13_leakage.ipynb` | "we removed duplicates" (they span files; removal hides the label conflict) |
| Q02 | protocol leak (onset near row 550-600 in 31/34 experiments); clock F1 0.835; time-monotone features forbidden; clock kept as a sanity row | `notebooks/12_baselines_metrics.ipynb` | "the clock baseline is a curiosity" |
| Q03 | concedes; event recall 5/7 with interval about 0.36-0.92; decisions on 27 dev experiments; one test look; relative not precise claims | `labs/w4d5_model_choice/figures/test_look.csv` | "we have thousands of samples" |
| Q04 | protocol A 0.920 vs leave-family-out 0.636; labels support supervision for seen families only; isolation forest / PCA held up | `notebooks/20_classical_detectors.ipynb` | "trees overfit" without the protocol-B evidence |
| Q05 | tried under equal budget; 5 seeds, mean 0.754 sd 0.068 vs 0.884 for flow-rate z; data size argument; would revisit with more data | `notebooks/21_neural_comparison.ipynb` | "deep learning is overkill" (opinion, no evidence) |
| Q06 | decision rule set in advance (MPID 0.05); logistic +0.069 [0.022, 0.128] inconclusive; cost columns (370 B, NumPy only, sub-ms); explainability | `labs/w4d5_model_choice/figures/decision_table.csv` | apologising for simplicity |
| Q07 | alert budget first; threshold 7.24 and post-processing on dev; one test look; nested-validation optimism | `notebooks/15_hyperparameter_selection.ipynb` | "tuned it on the test set to be safe" |
| Q08 | event-level as decision metric (recall, delay, false alarms/h); point metrics' bias; point-adjust inflation; events don't fix leakage (clock 3/7) | `notebooks/16_point_vs_event_evaluation.ipynb` | "F1" with no level stated |
| Q09 | drift answers "did inputs change", not "is there a fault"; 14-20 % of fault windows flagged; three monitors for three questions | `notebooks/38_input_monitoring_drift.ipynb` | "drift detects faults" |
| Q10 | 422 at the boundary; out-of-support flagged; readiness false on model failure; fallback with `degraded: true`; fallback 2/7 vs model 5/7 | `notebooks/41_reliability.ipynb` | "it returns 500" or "it uses a default score" |
| Q11 | Nagle + delayed ACK with multi-worker uvicorn; ~40 ms floor; p50 52 -> 9.5 ms with TCP_NODELAY; measured, then fixed | `notebooks/34_latency_resources.ipynb` | "Python is slow; we added workers" |
| Q12 | one inference object; three-way parity exactly 0 over 46,806 rows; streaming within 1e-12; CSV round-trip finding | `notebooks/30_project_milestone_2.ipynb` | "we used the same code" (untested claim) |
| Q13 | 198 samples exactly at the threshold; 1e-14 differences flip flags; same faults caught; deterministic tie rule and documented comparison | `notebooks/39_drift_vs_degradation.ipynb` | "floating point doesn't matter" |
| Q14 | delayed labels joined to logged predictions; threshold regression 11/20 -> 4/20 with no drift flag; estimate unknown then inconclusive; proxies as early warning | `notebooks/39_drift_vs_degradation.ipynb` | "the drift monitor would tell us" |
| Q15 | offline gate with paired comparison and margin (+0.143 [0.000, 0.429]); shadow; coverage gap (no "other" family in shadow traffic); rollback as pointer move, byte-identical | `notebooks/40_model_updates_rollback.ipynb` | "A/B test it" with no guardrails |
| Q16 | more independent experiments first; label review of the 235 rows; per-family supervision with leave-family-out; live monitoring calibration | `docs/guides/project.md` | "try transformers" |
| Q17 | lab testbed, induced faults, ~35 % anomalous samples, 34 experiments; experimenter labels; false alarms/lead times don't transfer; pilot needed | `docs/guides/project.md` | overclaiming plant readiness |
| Q18 | experiment = independent unit (like patient); row-level ROC-AUC 0.986 vs experiment-level 0.849 on dev; cost: fewer, noisier folds | `notebooks/10_problem_framing_splits.ipynb` | "to avoid overfitting" |
| Q19 | dependence within experiments; row bootstrap 3-7x too narrow; cluster bootstrap; exact binomial for 7 events | `notebooks/17_uncertainty.ipynb` | "the bootstrap is standard" |
| Q20 | what transfers (units, events, artefacts, drift); what is new (package, tests, CI, artifact, API, container, deployment, monitoring, rollback) | `docs/handbook/index.md` | "it is the same" or "nothing transfers" |

## Scoring a full set

Count answers meeting all three rows of the answers rubric (honesty, grounding, brevity). Do not turn
the count into a grade; use it to pick the five answers to rewrite and re-record.
