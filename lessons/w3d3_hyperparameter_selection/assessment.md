# Assessment - w3d3 hyperparameter and threshold selection

Answer in writing before opening `solutions/lessons/w3d3_hyperparameter_selection/assessment_answers.md`.
About 15 minutes for the questions; the interview rep is separate.

## Reasoning questions

1. You compare 24 configurations by 4-fold grouped CV; the best scores 0.891 ± 0.015 (SE over folds).
   Why is 0.891 a biased estimate of that configuration's performance on new experiments, and in which
   direction? Name two quantities that determine how large the bias is.
2. A colleague "does nested CV" like this: run the grid search with grouped 4-fold CV on all development
   experiments, take the best configuration, then run grouped 4-fold CV of that configuration and report
   the mean. What is wrong, and what number does this procedure actually estimate?
3. In the lab, the four outer folds of the nested estimate chose different model families. Is that a bug?
   What does it tell you about the search, and about the number you should report?
4. Your search space has five hyperparameters and a budget of 32 trials. Argue for random over grid search
   in two sentences, and say which hyperparameters you would sample on a log scale.
5. The decision threshold was chosen as the best-F1 threshold on the *in-sample* scores of the model
   refitted on all development experiments, then applied to test. What goes wrong, and how does the lab
   avoid it?
6. After seeing the test score, you notice a bug in feature scaling, fix it, rerun, and the test score
   rises by 0.03. You report the new number. What must the report say, and why?

## Design-choice explanation (6-10 sentences)

Explain your choice between the "max" and "one-standard-error" selection rules for the project's
supervised detector. Include: the SE of the top trials relative to the spread of the top means, your
complexity ordering and why it is the right ordering for a detector that will run online, and what the
rule does *not* fix about the number you report.

## Rubric

| Level | Description |
|---|---|
| Demonstrated | Separates the estimate of a configuration from the estimate of a procedure; locates every selection step (hyperparameters, family, threshold, post-processing, "best run") and the data it used; quantifies optimism with K, σ and correlation; treats test looks as a budget. |
| Partial | Correct mechanics of nested CV, but misses one selection step (usually the threshold or the "fix after seeing test") or justifies the one-SE rule only as "simpler is better". |
| Not yet | Reports the best CV score as expected performance, tunes thresholds on test, or treats nested CV as "CV twice". |

## Interview rep (ML fundamentals, 12 minutes, spoken)

Answer aloud, then write a 5-line summary:

1. "Why does L2 regularisation shrink the coefficients of two highly correlated features towards each
   other, while L1 tends to keep one and zero the other?" Use the geometry of the penalty or the
   optimality conditions.
2. "You increase the regularisation strength and the validation error first falls, then rises. Describe
   the bias and variance of the estimator along that path, and how you would choose the strength with
   only 25 independent groups."

Score yourself with the interview rubric in the answers file.
