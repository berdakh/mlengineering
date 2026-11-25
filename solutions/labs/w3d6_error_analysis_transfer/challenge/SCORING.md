# Transfer exercise part 2: scoring guidance

No numeric score. Three evidence levels per criterion, as in the diagnostic. The checks cover the
first four rows mechanically; the rest are read from `REPORT.md`.

| Criterion | Not yet demonstrated | Partial | Demonstrated independently |
|---|---|---|---|
| Leak audit | a post-issue column is used, or columns are dropped without reasons | named leaks excluded, export-time aggregates (`customer_late_rate`, `account_status`) missed or excluded without the "when is it computed" argument | every column classified with the time it becomes known; notices evidence in the data (constant within customer) |
| Split | random rows, or customer-grouped only | temporal by issue date, label delay ignored | temporal, labels restricted to those decided before the cut-off, and the grouping question answered from the deployment |
| Metric | AUC / accuracy / F1 reported as the answer | precision at k over the whole period | k per week, as the team works; states that calibration is not needed |
| Plausibility | does not react to an impossible score | notices and removes the cause | compares with a ceiling or a sanity bound unprompted |
| Baseline | none, or "random" only | a rule, without comparing it honestly | a rule a team could run without a model, same split and metric, and the conclusion follows the comparison even when the model loses |
| Uncertainty | none | row bootstrap or a normal interval on 209 calls | resampling unit justified (customer or week); states what the interval omits |
| Error slice | none, or several without sizes | one slice with size | slice chosen for a stated reason, size given, next check named, no slice hunting |
| Limitations | boilerplate | names the synthetic data and the single quarter | also separates prediction from the causal question (does a call change payment?) |
| Time management | no report at the bell | report incomplete, evaluation complete | both complete, or the gaps are listed precisely |

## Reading the outcome

* **All "Demonstrated", sitting unassisted and within time:** record under "Demonstrated in this
  course" in `progress/SKILLS_LEDGER.md` (leak-free evaluation on unfamiliar tabular data), with the
  conditions. Week 3 topics need no repetition.
* **Split or leak audit "Partial":** redo the w3d1/w3d2 challenges cold before Week 4.
* **Metric or baseline "Partial":** re-read H5.2 and redo this exercise's sections 1 and 4 only.
* **Assisted or over time:** mark `review`; repeat on a re-seeded table in Week 4 (the generator
  takes a seed: `simulate(seed=...)`), where the leaks are the same and the numbers are not.

## Common outcomes and what they indicate

| Observation | Usual cause |
|---|---|
| Test AUC above 0.83 | a post-issue column, most often `customer_late_rate` kept as "customer history" |
| Checks pass but report claims the model "improves on the rule" | reading 0.722 vs 0.727 (or the reverse on another seed) as a difference |
| Train set of 9,244 rows | temporal split without the label delay |
| Metric near 0.9 with honest features | global top-k taken from the last weeks, or ranking on the label |
| Interval of width 0.02 | bootstrap over all test rows instead of the called invoices |
