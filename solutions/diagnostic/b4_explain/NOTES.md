# b4_explain - reviewer notes (rubric only; no automated check)

## What a strong memo contains

**Recommendation:** do not replace the alarm yet; run the candidate in shadow next to the existing
alarm after a corrected offline evaluation (about a week of work).

**Reasons specific to this scenario (the top two or three, not all):**

1. **The 0.97 is very likely optimistic because of how rows were split.** The label is "failure
   within 7 days", so each failure creates up to 168 consecutive positive hourly rows from one
   compressor that are nearly identical. Shuffled 5-fold CV puts neighbours of the same pre-failure
   episode in train and test: the model can recognise the *episode*, not learn a precursor. The
   evaluation must hold out whole failure episodes - by time (train on earlier months, test on later)
   and ideally by compressor or site as well.
2. **The effective sample size is 31 failures, not ~500,000 rows.** Any estimate has wide
   uncertainty; with a grouped/temporal split some folds will hold only a handful of failures.
   Differences such as 0.97 vs 0.90 cannot be judged without intervals.
3. **ROC AUC at 0.8% prevalence does not describe the operational experience.** Technicians feel
   alarms per week and missed failures. The decision needs event-level numbers at a chosen operating
   point: how many of the failures are flagged, with how much lead time, at how many false alarms per
   compressor-month.
4. **The comparison is against the wrong baseline.** The proposal is to replace the threshold alarm,
   so the threshold alarm must be scored on the same held-out failures with the same event-level metric.
   Logistic regression is a modelling baseline, not the incumbent.

Also acceptable as secondary points: label quality of maintenance logs; whether features use
information recorded after the failure (e.g. post-repair values, rolling windows centred on the row);
cost asymmetry between a missed failure and a false alarm; site shift for new customers; a fallback
if the model service is down.

**Smallest decisive evidence:** re-evaluate both the boosted model and the current threshold alarm
with a forward-in-time split that holds out entire failure episodes, report failures caught / lead
time / false alarms per compressor-month with an interval. One to three days if the pipeline exists.

**Deliberate tradeoff:** e.g. delaying a possibly better alarm by a few weeks in exchange for not
replacing a known system with one of unknown false-alarm rate; or keeping the old alarm in parallel
(more noise for a while) to bound the risk of missed failures.

## Common weak answers and why they fall short

* **"AUC 0.97 is great, ship it"** / **"boosting beats logistic regression, so ship"** - accepts the
  evaluation at face value.
* **A list of fifteen generic caveats** ("check for bias, drift, explainability, more data...") with
  no priority and no tie to 7-day windows, 31 failures or the incumbent alarm.
* **"Use cross-subject validation"** with no mention of time or of overlapping label windows - the
  right instinct transferred incompletely: here the leaking unit is the failure *episode*.
* **"Imbalanced, so use SMOTE / accuracy is bad"** - addresses training, not whether the evidence
  supports the decision.
* **"Never ship until perfect"** - no actionable path; ignores that the current alarm also fails.
* **Correct content, unusable form:** recommendation buried in the last paragraph, jargon without
  translation, over the word limit.

## Rubric

| Aspect | Demonstrated independently | Partial | Not yet demonstrated |
|---|---|---|---|
| Technical reasoning | Identifies the overlapping-window/episode leakage and at least one of: effective sample size, metric vs operations, wrong baseline - each with the mechanism | Names "leakage" or "imbalance" without the mechanism in this data | Accepts the result |
| Prioritisation | Two or three reasons, most important first | Correct points diluted among generic ones | Unranked list or single minor point |
| Actionability | Clear recommendation up front, concrete next experiment with effort estimate | Recommendation present but no path to a decision | No recommendation |
| Communication | Readable by the product manager; within the limit; tradeoff stated | Accurate but written for ML specialists | Unclear |

This section also feeds the interview-preparation thread: it is the same skill as answering "tell me
about a time you pushed back on a result".
