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
| 1 | see report | `days_since_last_reminder` is computed from reminders sent after the due date | Target leakage: at issue time no reminder exists, so the model is scored with information it will not have; it is also the top feature (line 37) | Recompute every feature as of the issue date, drop or redefine this one, and report the effect on the metrics | major |
| 2 | see report | Random split of invoices although each customer has about 15 invoices | Customer identity leaks across the split, and later invoices train the model that predicts earlier ones; the estimate is optimistic for new customers and new months | Split by customer and by issue date (train on earlier months, test on later), matching how the model would be used | major |
| 3 | see report | Threshold chosen to maximise F1 on the test set | The test set has been used for fitting, so recall and precision at the threshold are optimistic | Choose the threshold on a validation period before touching the test set, then report the test once | major |
| 4 | see report | 94.1 % accuracy presented as evidence of reliability | With 6 % late invoices, predicting "on time" for everything scores 94 %; accuracy says nothing here | Report PR-AUC, and recall and precision at the call capacity of the team, against a trivial baseline | major |
| 5 | see report | "Significantly better" from 0.71 versus 0.69 AUC with no test or interval | A 0.02 AUC difference can easily be noise on one test split; the claim is unsupported | Give a paired bootstrap interval over customers for the difference, or drop the word significant | major |
| 6 | see report | Text says recall 0.62, table says 0.58 | The reader cannot tell which number is real; numbers were typed by hand | Generate every number in the text and table from one results file | minor |
| 7 | see report | Feature importance reported without caution | Importance of a leaking feature confirms the leak, not a mechanism; impurity importances are also biased to high-cardinality features | Remove the leaking feature first; if importances stay, use permutation importance on held-out data and describe them as associations | minor |
| 8 | see report | Causal recommendation (split large invoices) from a predictive model | Amount is associated with lateness through customer size and contract type; splitting invoices may change nothing or annoy customers | Remove the causal claim, or propose a controlled trial if the business wants to test it | major |
| 9 | see report | Claims equal performance in a new market with no data from it | Different payment law, terms and customers; nothing in the evaluation covers this | State that the German market is out of scope until data from it are evaluated; plan a shadow period | major |
| 10 | see report | Recommends deploying to all customers next month | No baseline comparison at the decision level, no monitoring, no rollback plan | Propose a pilot with a holdout of uncalled customers, monitoring of recall once labels arrive, and a stop rule | minor |
| 11 | see report | "None identified" under Limitations | Every evaluation has limits; this one has several above; an empty section signals they were not considered | Write the limitations with the impact and mitigation of each, starting with issues 1 to 4 | major |
| 12 | see report | Default hyperparameters, no tuning or validation set described | The comparison with the baseline may reflect tuning effort rather than model class | Describe the validation procedure and give both models the same tuning budget | minor |

## Recommendation

Revise before any deployment decision. The revised report must show results on a customer- and time-based
split with the leaking feature removed, metrics that match the call budget with intervals, a threshold chosen
on validation data, a limitations section, and no causal or new-market claims.
