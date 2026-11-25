# W4D2 assessment — model answers

## Q1
Q alarms first: the fault breaks a relationship (vibration no longer tracks current), so the row leaves
the subspace spanned by normal co-variation while each sensor may stay in its normal range — T² measures
position inside the subspace and changes little. If `k` is raised until 99.9% of the variance is kept,
the retained subspace starts to include the small, noise-like directions, including the one along which
the fault moves; the fault is then "explained" by the model, Q shrinks towards noise, and T² (now divided
by tiny eigenvalues in those directions) becomes erratic. Choose `k` on detection performance, not on a
high variance share.

*Common incorrect answer.* "T², because the fault makes the vibration large." Early in a decoupling
fault the vibration is not large; it is inconsistent.

## Q2
`contamination` only set the threshold of `predict` so that 2% of the *training* rows are flagged. They
chose an operating point by assumption: the share of fraud is not the share of rows that should be
flagged (it depends on how the scores separate the classes and on the alarm budget). Instead: use the
continuous scores, report threshold-free metrics (average precision) on held-out labelled data, and pick
the threshold on development data from the business constraint (review capacity, cost of a miss).

## Q3
(a) The fault signature differs: the model learned what separates *those* faults (here, valve faults
move the flow rate directly) and a new mechanism moves other sensors. (b) The normal behaviour differs:
the new family's normal rows sit elsewhere (noisier flow in `other`), so the model's decision regions
cut through normal data. To tell them apart: look at false positives on the unseen family's *normal*
rows versus misses on its *fault* rows (a per-class error breakdown), or compare score distributions of
normal rows across families. On SKAB, both appear: `other` normal rows have higher |z| (1.25 vs 0.55
median for flow) and its faults move flow less (3.58 vs 5.22).

## Q4
* Were the budgets equal (trials, features, data)? If not, part of the 0.05 is selection optimism.
* Is 0.05 a nested or held-out estimate, or the best inner score (w3d3)?
* Same features and the same rows (did the forest get normal rows only, the GBT all rows)?
* Same threshold rule and evaluation unit; uncertainty on the difference, ideally paired by unit (w3d5);
  how many independent units.
* A second protocol (unseen family, later period) and the false-alarm rate at a usable operating point.

## Q5
It shows that the fitted model's average precision *on the training rows* depends heavily on that
feature — i.e. the model uses card age to recognise the five fraudulent accounts it was trained on. Card
age is constant per customer, so it acts as an account identifier. It says nothing about whether card
age predicts fraud for new customers; the grouped estimate (0.042, actual 0.159 on new customers)
suggests the model's knowledge is mostly account memory. Importance must be measured on held-out
*customers*, and even then it describes the model, not causation.

## Q6
A random 10% of rows puts rows from the same experiment (adjacent, autocorrelated, sharing a fault) in
both the training and the stopping set, so the stopping point is chosen on leaky validation data and
tends to over-fit. Cheapest correct alternative: turn early stopping off and treat `max_iter` (with the
learning rate) as a hyperparameter selected by the grouped out-of-fold procedure already in place; or
supply a validation set of whole held-out experiments.

## Q7 (key points for the rubric)
Equal footing answers "which *model family* is better for this data, other things equal": features,
budget, threshold rule and evaluation are held fixed so that differences can be attributed to the model.
The colleague's design answers a different, legitimate question: "which complete *system* is best?"
— but then the comparison confounds the model with the feature set and the search effort, and a larger
search inflates the winner's development score (optimism of the max, w3d3) unless the estimate is
nested. The right response is to run both as separate, labelled experiments: equal footing as the
controlled comparison, and "each at its best" with a nested estimate and with the budgets stated. If the
forest on raw sensors is genuinely better, that is a finding about features, and it should be tested by
giving the same raw sensors to the GBT as well.

## Interview rep — what a strong answer contains
1. Bagging averages models trained on bootstrap samples: it reduces variance, leaves bias. Random forests
   add feature subsampling at each split so that the trees' errors are less correlated; the variance of an
   average of correlated predictors is `ρσ² + (1−ρ)σ²/B`, so lowering `ρ` matters more than adding trees.
   Boosting fits each model to the residual errors (gradients) of the current ensemble: it reduces bias,
   and can over-fit; the learning rate shrinks each step so that many small steps generalise better
   (regularisation), at the cost of more iterations.
2. Code and tests: `solutions/labs/w4d2_classical_detectors/interview_rep/` (executed: 3 tests pass).
   Key points: sort once, cumulative positive counts give each split's child impurities in O(1), skip
   positions between equal values.
