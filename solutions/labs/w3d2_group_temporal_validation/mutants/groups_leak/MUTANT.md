# Mutant `groups_leak`

**Mistake.** `group_kfold_indices` shuffles and folds *rows*; the `groups` argument is only used for the argument check.

**Why plausible.** It is what `KFold(shuffle=True)` does, and it is the habit this lesson exists to break: the function runs, returns the right shapes, and reports a better number.

**Caught by.** `test_group_kfold_never_splits_a_group_and_validates_each_once`, and the planted-effect check: on the synthetic machines the estimate is about 0.89 against a truth of 0.63.
