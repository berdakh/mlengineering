# Mutant: a late detection is called a miss

An event first flagged more than `late_after` rows after onset is recorded as `miss`. This is the
convention of benchmarks with a fixed detection window, carried over without thought. It merges two
failures with different remedies: a miss needs a different signal, a late detection needs a faster
statistic or a lower threshold.

Rejected by `test_late_detection_is_late_not_a_miss` and `test_short_onset_latency_is_a_boundary_error`.
