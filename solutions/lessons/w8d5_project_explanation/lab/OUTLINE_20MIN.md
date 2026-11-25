# 20-minute walkthrough: outline (reference)

- [2 min] Problem and stakeholder: what the reliability engineer needs; show the event timeline figure of one experiment
- [3 min] Data and its traps: 34 experiments, duplicated rows with contradictory labels, the clock baseline; show the onset-row figure
- [3 min] Evaluation protocol: split by experiment with overlap groups, development versus one test look, event metrics, cluster bootstrap
- [3 min] Model comparison and decision: the decision table with intervals, protocol B collapse of boosted trees, neural seeds, the rule for choosing
- [3 min] From model to service: one inference object, artifact without pickle, API contract, container, CI; show the architecture diagram
- [2 min] Operating it: latency finding (Nagle), monitoring separation of validity, drift and degradation, fallback, rollback
- [2 min] Failure example: the missed fault valve1/8 and what the logs and scores show
- [2 min] Limitations and next steps; then questions
