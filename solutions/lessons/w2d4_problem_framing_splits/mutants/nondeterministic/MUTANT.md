# Mutant: nondeterministic

**The mistake.** The generator is created without the seed. The manifest still records `"seed": 0`,
which is worse than recording nothing: it claims a reproducibility that does not exist.

**Why a learner writes it.** A refactor drops the argument; one run looks fine.

**Caught by.** `test_same_seed_gives_same_manifest`, `test_result_does_not_depend_on_row_order`.
