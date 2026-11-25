# Peer review of FLAWED_REPORT.md

Reviewer: reference answer (course solutions) · Date: 2026-11-25

## Summary for the author

The report claims a late-payment model that is "highly reliable", better than the baseline, causally
informative, and ready for all customers and a new market. The evaluation cannot support any of these: the
split lets each customer's invoices appear on both sides, the threshold was tuned on the test set, the
headline metric is accuracy on a 6 % positive class, and the top feature is probably only known after the
invoice is late. The one change that matters most is to re-run the evaluation with a split by customer and
by time, with every choice made on validation data, and to drop the leaking feature.

## Issues

Line numbers refer to `FLAWED_REPORT.md`. Severity: `major` (changes a conclusion) or `minor`.

| # | Line | Problem | Why it matters | Requested change | Severity |
|---|---|---|---|---|---|
| 6 | 35 | Text says recall 0.62, table says 0.58 | The reader cannot tell which number is real; numbers were typed by hand | Generate every number in the text and table from one results file | minor |
| 7 | 37 | Feature importance reported without caution | Importance of a leaking feature confirms the leak, not a mechanism; impurity importances are also biased to high-cardinality features | Remove the leaking feature first; if importances stay, use permutation importance on held-out data and describe them as associations | minor |
| 10 | 43 | Recommends deploying to all customers next month | No baseline comparison at the decision level, no monitoring, no rollback plan | Propose a pilot with a holdout of uncalled customers, monitoring of recall once labels arrive, and a stop rule | minor |
| 12 | 22 | Default hyperparameters, no tuning or validation set described | The comparison with the baseline may reflect tuning effort rather than model class | Describe the validation procedure and give both models the same tuning budget | minor |
| 13 | 3 | The author is not named | Accountability | Add the author's name and the date at the top | minor |
| 14 | 30 | Table has no units | Readability | Add a caption that says what each column means | minor |

## Recommendation

Revise before any deployment decision. The revised report must show results on a customer- and time-based
split with the leaking feature removed, metrics that match the call budget with intervals, a threshold chosen
on validation data, a limitations section, and no causal or new-market claims.
