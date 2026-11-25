# Selection report (your deliverable for w3d3)

Fill this in from **your own** run of `selection_report.py`. Keep it to one page.

## 1. Protocol

| Item | Your value |
|---|---|
| Split manifest version and seed | |
| Unit of the folds | |
| Search space (families, hyperparameters, ranges, scales) | |
| Number of candidates, seed of the sampler | |
| Metric used for selection, and why this one | |
| Selection rule (max or one-SE) and the complexity ordering | |
| Threshold rule(s), and the data they were chosen on | |
| Number of times the test experiments were evaluated | |

## 2. Numbers

| Quantity | Value |
|---|---|
| Best dev CV score of any trial (mean, SE over folds) | |
| Dev CV score of the selected trial | |
| Nested estimate of the whole procedure (mean, SE over outer folds) | |
| Test PR-AUC of the selected, refitted model | |
| Test precision / recall / F1 at the frozen best-F1 threshold | |
| Test precision / recall / false-alarm rate at the frozen alert-budget threshold | |

## 3. Reading (5-8 sentences)

* Which of the three dev-side numbers would you put in a report as "expected performance", and why?
* The outer folds chose different candidates. What does that say about the search?
* Is the gap between the nested estimate and the test score evidence of anything? State the number of
  independent units on each side before answering.
* What would you have been tempted to change after seeing the test number, and why must you not?

## 4. What this does not establish

(At least two limitations. One must concern the size of the test set.)
