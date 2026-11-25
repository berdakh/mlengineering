# w3d1 assessment - model answers

## 1. `hours_since_last_maintenance`

It is a temporal-aggregate leak if "last maintenance" is looked up in today's log for historical rows:
for a row at time *t* it may pick a maintenance event that happened *after t* (often *because* of the
fault being predicted, so it is target-correlated). It is legitimate if it is computed as of the row's
timestamp, using only maintenance events dated before *t* and recorded (entered into the log) before *t*.
Check: recompute it point-in-time for a sample of rows and compare; any difference is leakage. The
second condition (recorded before *t*) matters because logs are often back-filled.

*Common incorrect answers.* "It is a normal feature, maintenance is in the past" (ignores how the export
was computed). "Drop it" (it is probably one of the most useful legitimate features once computed
correctly).

## 2. Scaling versus selection

Scaling estimates a mean and a standard deviation per column. Including test rows shifts those slightly;
the label is not involved, and for a scale-equivariant downstream model the effect is only through the
slightly different transform, so it is numerically tiny when *n* is moderate. Selection uses the
**labels**: it picks the columns whose correlation with the label is largest in a sample that includes
the validation rows, so the chosen columns are correlated with the validation labels by construction.
That is why it grows with *p*/*n*. The rule is applied to both because (i) you cannot know in advance
which regime you are in (small *n*, heavy-tailed columns, target encoding sit in between), (ii) a served
model never has the test period's statistics, so fitting on them makes training and serving inconsistent,
and (iii) the correct version costs nothing with a `Pipeline`.

*Common incorrect answer.* "Scaling leakage does not matter." The worked example shows it did not matter
*here*; that is a measurement on one dataset, not a rule.

## 3. "Removing the leak improved the model by 0.07"

* The test set changed: v1 has 9 test experiments, v2 has 7 (`other/11` and `other/12` moved to
  development). PR-AUC over a different set of experiments is a different quantity; with seven to nine
  experiments, swapping two can move it by this much on its own.
* On the 7 experiments that are test under both manifests, training with v1 or v2 gives 0.899 versus
  0.900: no measurable difference attributable to the leak for this model.
* Also: the duplicate leak, if anything, should *inflate* v1 (test rows seen in training). That v1 is
  lower is explained by the 178 contradictory labels on shared rows and by composition, which shows the
  difference is not a leak effect.
* And: "improved the model" is wrong in kind. The model was not changed; the estimate was.

## 4. Clock probe near prevalence

No. It shows that *elapsed time alone* does not predict the label at point level. Protocol leaks can be
carried by other variables: position relative to a recording event (start of a test step), time of day,
operator, batch or session id, file order. Check: single-feature probes on all metadata; per-group onset
distributions; whether labels cluster by acquisition session; `time_monotone_columns` on engineered
features (a cumulative feature can be a clock even if `t` is excluded); and ask how the labels were
produced.

## 5. Components, not pairs

A shares rows with B, B shares rows with C, A and C share nothing. With pairs, a splitter that keeps each
listed pair together may put {A, B} in fold 1 and then treat {B, C} as "B is already placed, C can go
anywhere", or process pairs independently and end with A in test, B in development and C in test. B
carries information about both. Only the component {A, B, C} as one unit guarantees no shared rows across
sides. SKAB has this case: `other/2`-`other/3`-`other/4`.

## 6. Deleting duplicated rows instead of grouping

*Advantage:* keeps more experiments available for the test set (more independent units for the estimate).

*Problems:* (i) The rows are not just duplicates, 235 have **contradictory labels**; deleting one copy
picks a label arbitrarily and hides a labelling problem that should be reported to the data owner.
(ii) A copied segment is evidence that the two files are not independent recordings (shared
acquisition, the same run exported twice, or concatenation); experiments that share 37 % of their rows
likely share more than the exact copies (operating point, adjacent unexported samples), so deleting
exact matches does not make them independent. (iii) It changes the experiments' time series (gaps),
which interacts with rolling features.

## 7. Design choice (model answer)

The test set exists to give one estimate that no decision has touched. Every development experiment has
been seen while choosing features, baselines, thresholds and (from w3d3) hyperparameters; its test
result would be optimistic by an amount we cannot measure, because the selection happened informally
across several sessions. Moving it into test would trade an unknown bias for a smaller variance, and the
bias does not shrink with more data. Cost on the real data: the test set falls from 9 to 7 experiments
(4 `valve1`, 1 `valve2`, 2 `other`), so `other` is represented by two experiments and every interval in
w3d5 will be wider. Report: the manifest version, the reason for the change, the new composition, and a
sentence that conclusions about the `other` family rest on two experiments.

## Interview rep rubric (self-score, 0-2 each, 10+ is strong)

| Point | 2 | 1 | 0 |
|---|---|---|---|
| Prediction moment | States "at ticket creation" and judges every feature against it | Mentions timing for some features | Not mentioned |
| Target leakage | Names number of agent replies and satisfaction score as post-creation (satisfaction is usually collected after resolution: near-proxy of the outcome) | Names one | None |
| Assigned team | Asks whether assignment happens at creation or after triage, possibly after escalation | Treats it as fine or as leaky without asking | Not mentioned |
| Grouping | Customers with many tickets; split by customer or check performance on new customers | Mentions grouping vaguely | Not mentioned |
| Time | Train on earlier months, test on later; text and products drift | Mentions time | Not mentioned |
| First action and expected number | Single-feature probes, refit with creation-time features and a time split; expects a large drop, e.g. "0.94 is not credible for routing at creation; I would expect something like 0.7-0.8 and would not be surprised by less" | Proposes a fix without measuring | Accepts 0.94 |

*Common weak answers.* Arguing about the model class (BERT versus logistic regression) before the
features; proposing cross-validation "to be more robust" (does not address any of the leaks).
