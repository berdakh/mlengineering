# balanced_class_weight

The model is fitted with `class_weight="balanced"` because the classes are imbalanced (about 7% churn).

Why it is plausible: it is the reflex remedy for imbalance, and it leaves ROC AUC and PR-AUC essentially unchanged, so ranking metrics give no warning.

Why it is wrong here: reweighting changes the prior the model believes in. Its outputs average far above the churn rate, so comparing them with a break-even probability sends the offer to a large share of customers at a loss. Either fit unweighted, or recalibrate on validation data before applying a cost threshold.

Caught by: `test_probabilities_are_calibrated_in_the_large_on_the_fitting_data`.
