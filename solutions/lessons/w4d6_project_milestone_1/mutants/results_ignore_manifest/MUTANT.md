# Mutant: results do not depend on the split manifest

The results rule lists the tidy table and the code but not $(SPLITS). Editing the manifest leaves a
stale report that make calls up to date. Caught by `test_changed_manifest_makes_results_stale`.
