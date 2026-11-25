# Mutant: a parity test that compares shapes, not values

The serving path is fixed, but the test asserts only equal length and finite values. It catches the
original's burn-in bug (different length) and nothing else. Caught by
`test_parity_test_fails_on_each_planted_bug[bug_clip.py / bug_order.py / bug_burnin.py]`.
