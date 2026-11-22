# w3d1 assessment

Answer in writing before opening `solutions/lessons/w3d1_leakage/assessment_answers.md`.
Questions 1-3 belong to the essential path (5 minutes); the rest to the optional extension.

## Reasoning questions

1. A predictive-maintenance model uses `hours_since_last_maintenance`. In the training export the column
   is computed from the maintenance log *as exported today*. Is it a leak? Under what condition is it
   legitimate, and what single check would tell you?
2. Standardising on all rows before cross-validation changed the AUC by 0.001 in the worked example.
   Selecting features on all rows changed it by up to 0.43. Both are preprocessing leakage. Explain the
   difference in mechanism, and why the rule "fit inside the pipeline" is applied to both anyway.
3. In `v1_vs_v2.py` the v2 test PR-AUC is 0.07 higher than v1. A colleague writes "removing the
   duplicate leak improved the model by 0.07". Give two reasons this is wrong, using numbers from the table.
4. Your clock probe on a new dataset gives PR-AUC 0.36 at prevalence 0.35. Does that prove there is no
   protocol leak? What else would you check?
5. Why must `find_overlap_groups` return connected components rather than the list of overlapping pairs?
   Construct a three-experiment example where using pairs produces a leaky split.
6. A teammate proposes to fix the duplicated SKAB rows by deleting the 1,290 duplicated rows from one of
   each pair of files instead of keeping experiments together. Give one advantage and two problems.

## Design-choice explanation (graded with the rubric)

7. `repair_splits` never moves a development experiment into the test set, even when that would keep the
   test set larger and better stratified. Defend this choice to a colleague who wants the larger test set.
   Then state what the choice costs on the real data and how you would report that cost.

## Rubric for question 7

| Level | Description |
|---|---|
| Strong | Argues from what the test set is for (an estimate untouched by any decision); identifies that development experiments have influenced choices (thresholds, features, models) during Weeks 2-3 so their test results would be optimistic in an unknown amount; quantifies the cost on the real data (test set 9 -> 7 experiments, `other/11` and `other/12` leave it); proposes reporting it (state the change, the new composition, and that intervals widen, w3d5) |
| Adequate | Correct principle and the cost, without the reporting plan or without the "unknown amount" argument |
| Weak | "Rules say test is untouched" without a reason, or accepts the colleague's proposal |

## Interview rep (validation and leakage, 15 minutes, spoken or written; no notes)

> "We built a model to predict which support tickets will escalate. We used all tickets from 2024,
> random 80/20 split, features include the ticket text, the customer's plan, the number of agent
> replies, the customer's satisfaction score, and the assigned team. Test AUC is 0.94. Product wants to
> use it to route tickets at creation time. Is the number trustworthy? What would you change?"

Aim to cover: the prediction moment, each feature against that moment, the unit of grouping, the split,
what you would run first, and what number you expect afterwards (a range, not a value). Self-score with
the rubric in the answers file.
