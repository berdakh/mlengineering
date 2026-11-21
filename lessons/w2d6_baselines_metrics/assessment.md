# w2d6 assessment

Write answers before opening `solutions/lessons/w2d6_baselines_metrics/assessment_answers.md`.
Short answers: 3-6 sentences, with a number or formula where one exists.

## Reasoning questions

1. A detector has recall 0.90 and false-positive rate 0.02. Compute its precision at prevalence 0.30
   and at prevalence 0.001. State which of ROC AUC and average precision changes between the two
   settings and why.
2. In the lab table the constant scorer has test F1 = 0.544. Derive that number from the test
   prevalence (0.373), and explain what it implies for anyone quoting "F1 = 0.6" on this benchmark.
3. The clock baseline (score = elapsed time `t`) has test F1 0.835 but PR-AUC only 0.513. Explain
   both numbers from how the experiments are constructed. Name two kinds of model input that could
   let a learned model exploit the same regularity without being given `t`.
4. "Mahalanobis, global reference" has dev PR-AUC 0.664, yet on test its threshold flags everything
   (precision 0.374, recall 1.000). What does that say about the scores, and what is the general
   lesson about threshold transfer?
5. A colleague trains with `class_weight="balanced"`, reports the same PR-AUC as your unweighted
   model, and proposes to apply the rule "act if p >= 0.08". What happens, and what are two correct
   ways forward?
6. Your Brier score improved from 0.081 to 0.078 after adding features. Can you conclude that
   calibration improved? What would you look at?

## Design-choice explanation (about 150 words)

For `flowguard` you must pick between fitting "normal" on the global fault-free recording and
calibrating on the first 100 rows of each experiment. Choose one for the baseline every later model
must beat. Justify the choice with the table, state the operational assumption it makes, describe a
realistic situation in which the assumption fails, and say what you would monitor to notice.

## Rubric

| Criterion | Not yet | Adequate | Strong |
|---|---|---|---|
| Quantitative correctness (Q1, Q2) | formula missing or misapplied | correct numbers | correct numbers and the within-class / across-class reason |
| Reading evidence (Q3, Q4) | restates the table | explains each number from data structure | also names what would falsify the explanation and how to test it |
| Probability versus ranking (Q5, Q6) | treats scores and probabilities alike | identifies the miscalibration and one remedy | two remedies, and knows Brier mixes calibration with discrimination |
| Design choice | preference without evidence | choice tied to table and an assumption | assumption, failure scenario, monitoring signal, and what remains unknown (no intervals yet) |
| Honesty about uncertainty | claims ordering between close rows | notes small test set | states the unit of independence (experiment) and defers claims to w3d5 |

## Interview rep (ML fundamentals, 10-15 minutes, spoken or written, no notes)

> "You have fitted an L2-regularised logistic regression to predict a rare event (1 % positive).
> (a) Write the loss you are minimising. (b) A stakeholder asks why you did not 'balance the classes'.
> Explain what downsampling the negatives by a factor of 10 does to the fitted model, precisely, and
> how you would correct for it. (c) They then ask whether to evaluate with accuracy, ROC AUC or
> PR-AUC. Give a recommendation and its limits."

Assistance level for Week 2: attempt untimed first, then read the rubric and worked answer in
`assessment_answers.md`, then redo part (b) from memory.
