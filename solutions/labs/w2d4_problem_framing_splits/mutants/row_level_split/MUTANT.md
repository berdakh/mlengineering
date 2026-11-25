# Mutant: row_level_split

**The mistake.** Rows are assigned to test/dev folds independently and the manifest lists the
experiment ids that those rows came from. Every experiment has rows on both sides, so nearly every
id appears in test *and* in several folds. This is the classic "random split of windows" error from
subject-wise biosignal and sensor work, written down as a manifest that looks structurally fine.

**Why a learner writes it.** `train_test_split(df)` is muscle memory; converting the result to ids
afterwards feels like it restores the grouping.

**Caught by.** `test_every_labelled_experiment_is_assigned_exactly_once`.
