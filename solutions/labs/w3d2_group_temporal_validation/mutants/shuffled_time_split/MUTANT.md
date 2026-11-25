# Mutant `shuffled_time_split`

**Mistake.** `purged_time_split` delegates to `KFold(shuffle=True)`; test "blocks" are random rows and no buffer is applied.

**Why plausible.** `shuffle=True` is muscle memory, and a buffer cannot even be defined once the test rows are scattered through time.

**Caught by.** `test_purged_split_blocks_and_buffers` (blocks must be contiguous and in time order).
