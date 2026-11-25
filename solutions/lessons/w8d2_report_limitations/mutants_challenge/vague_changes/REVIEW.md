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
| 1 | 17 | `days_since_last_reminder` is computed from reminders sent after the due date | Target leakage: at issue time no reminder exists, so the model is scored with information it will not have; it is also the top feature (line 37) | fix this | major |
| 2 | 21 | Random split of invoices although each customer has about 15 invoices | Customer identity leaks across the split, and later invoices train the model that predicts earlier ones; the estimate is optimistic for new customers and new months | fix this | major |
| 3 | 23 | Threshold chosen to maximise F1 on the test set | The test set has been used for fitting, so recall and precision at the threshold are optimistic | fix this | major |
| 4 | 27 | 94.1 % accuracy presented as evidence of reliability | With 6 % late invoices, predicting "on time" for everything scores 94 %; accuracy says nothing here | fix this | major |
| 5 | 34 | "Significantly better" from 0.71 versus 0.69 AUC with no test or interval | A 0.02 AUC difference can easily be noise on one test split; the claim is unsupported | fix this | major |
| 6 | 35 | Text says recall 0.62, table says 0.58 | The reader cannot tell which number is real; numbers were typed by hand | fix this | minor |
| 7 | 37 | Feature importance reported without caution | Importance of a leaking feature confirms the leak, not a mechanism; impurity importances are also biased to high-cardinality features | fix this | minor |
| 8 | 41 | Causal recommendation (split large invoices) from a predictive model | Amount is associated with lateness through customer size and contract type; splitting invoices may change nothing or annoy customers | fix this | major |
| 9 | 42 | Claims equal performance in a new market with no data from it | Different payment law, terms and customers; nothing in the evaluation covers this | fix this | major |
| 10 | 43 | Recommends deploying to all customers next month | No baseline comparison at the decision level, no monitoring, no rollback plan | fix this | minor |
| 11 | 47 | "None identified" under Limitations | Every evaluation has limits; this one has several above; an empty section signals they were not considered | fix this | major |
| 12 | 22 | Default hyperparameters, no tuning or validation set described | The comparison with the baseline may reflect tuning effort rather than model class | fix this | minor |

## Recommendation

Revise before any deployment decision. The revised report must show results on a customer- and time-based
split with the leaking feature removed, metrics that match the call budget with intervals, a threshold chosen
on validation data, a limitations section, and no causal or new-market claims.
