# p4_naive_sum_of_squares
E[x^2] - E[x]^2 in floating point: fine for small values, wrong when values are around 1e9 with a small
spread (catastrophic cancellation). Caught by: test_p4_large_offset_is_stable.
