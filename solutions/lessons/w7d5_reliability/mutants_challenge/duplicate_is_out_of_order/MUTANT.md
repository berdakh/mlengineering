# Mutant: duplicate_is_out_of_order

A replayed sample is reported as out of order. The two need different handling: a duplicate is harmless to drop, an out-of-order sample may signal a clock or transport fault worth alerting on.
