# Mutant: anomaly_free_in_test

**The mistake.** The fault-free recording is treated as one more family. It lands in a dev fold (a
single-member family is never sent to test here, but the check also covers folds), where it
contributes 9,405 negative samples and zero events: point-level metrics shift, event recall is
undefined for it, and detectors that need normal reference data no longer have a designated source.

**Why a learner writes it.** "Split all the files" is the obvious loop.

**Caught by.** `test_fault_free_recording_is_reference_only`, `test_every_labelled_experiment_is_assigned_exactly_once`.
