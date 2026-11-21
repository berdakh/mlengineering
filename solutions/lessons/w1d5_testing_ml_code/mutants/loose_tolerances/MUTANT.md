# Mutant: loose_tolerances

**The mistake.** The right known-answer tests, but every comparison uses
`rel=0.15` "to be safe against floating point". The mean-absolute-value bug
(`2A/pi = 0.637A` instead of `A/sqrt(2) = 0.707A`, a 10 % error) fits inside the tolerance.

**Why it is plausible.** Tolerances are often widened until a flaky test goes
green, without asking how large a real defect would be.

**Expected outcome.** Passes on the correct package; `rms_is_mean_abs` survives.
Only `tests/test_features.py` is replaced; the other reference test files are kept.
