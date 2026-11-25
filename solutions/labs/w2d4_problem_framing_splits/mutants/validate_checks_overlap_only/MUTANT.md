# Mutant: validate_checks_overlap_only

**The mistake.** The validator checks the one failure everyone thinks of (test/dev overlap) and
nothing else: an experiment in two dev folds, an id that does not exist, a labelled experiment left
out, the fault-free recording in test, or a manifest of row indices all pass.

**Why a learner writes it.** "No overlap" is the stated goal; the other ways a hand-edited or stale
manifest goes wrong only appear after the dataset changes.

**Caught by.** `test_rejects_broken_manifests` (seven of its eight cases).
