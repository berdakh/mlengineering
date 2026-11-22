# Mutant `no_embargo`

**Mistake.** `purged_time_split` drops rows before each test block but ignores `embargo`: training resumes at the row right after the block.

**Why plausible.** "Do not train on the past of the test block that overlaps it" is the intuitive half. The rows *after* the block have feature windows that reach back into it, which is easy to overlook when thinking in forecasting terms.

**Caught by.** `test_purged_split_blocks_and_buffers` (cases with `embargo > 0`) and the shared-sample property test.
