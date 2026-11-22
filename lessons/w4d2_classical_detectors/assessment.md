# W4D2 assessment

Write answers before opening `solutions/lessons/w4d2_classical_detectors/assessment_answers.md`.
Two to five sentences each unless stated.

## Reasoning questions

**Q1.** A PCA detector monitors 30 sensors. A pump bearing starts to fail and one vibration channel
slowly decouples from motor current, which it normally tracks. Which statistic alarms first, T² or Q,
and why? What happens to that statistic if `k` is raised until 99.9% of the variance is retained?

**Q2.** A colleague sets `IsolationForest(contamination=0.02)` "because about 2% of our data is fraud"
and reports precision and recall from `predict`. What decision did that parameter make, and what should
they do instead?

**Q3.** In the lab, the GBT had the best test PR-AUC on protocol A and the worst point estimate on
protocol B. Give two different reasons a supervised model can lose its advantage on an unseen fault
family, and one way to tell them apart with the data you have.

**Q4.** A team compares a tuned GBT (200 random-search trials) with an isolation forest run with
defaults and reports that the GBT wins by 0.05 PR-AUC. List the things you would need to know before
accepting the conclusion.

**Q5.** Permutation importance on the training rows of the challenge GBT puts half of the importance on
`card_age_days`. A product manager reads this as "card age is the strongest fraud signal". Explain what
the number does show.

**Q6.** HistGradientBoosting's early stopping holds out a random 10% of rows. Why is that a problem for
the SKAB data, and what is the cheapest correct alternative?

## Design-choice explanation

**Q7.** (8-10 sentences.) The lab gives every detector the same 40 features, the same three-config
budget, and the same best-F1 threshold rule. Defend this design against a colleague who says "each model
should be shown at its best: give the GBT more features and a bigger search, and give the isolation forest
raw sensors because that is what it is good at". Say what question each design answers.

## Rubric (Q7 and open answers)

| Level | Description |
|---|---|
| Strong | Separates the two questions (which *model* is better on equal footing vs which *system* — model plus features plus budget — is best); explains that unequal budgets confound selection optimism with model quality (w3d3); proposes running the "each at its best" variant as a separate, labelled experiment with its own nested estimate. |
| Adequate | Defends equal footing with one clear argument but does not address the legitimate part of the colleague's point. |
| Not yet | Argues only that equal is "fairer" without saying what is being estimated, or accepts unequal budgets without comment. |

## Interview rep (10-15 minutes, ML fundamentals: trees and ensembles)

1. (Explain, 4 minutes, aloud.) Bagging versus boosting: what each reduces (bias or variance), why
   random forests decorrelate trees, and why boosting needs a learning rate.
2. (Code, 10 minutes.) Write `best_split(x, y)` for one numeric feature and binary labels: return the
   threshold (midpoint between consecutive distinct sorted values) that minimises the weighted Gini
   impurity of the two children, and that impurity. Target O(n log n). Write two tests, one with a
   perfectly separable feature.

A reference implementation with tests is in `solutions/lessons/w4d2_classical_detectors/interview_rep/`.
