# Mutant: self_consistency_only

**The mistake.** The "expected" values are produced by the code under test: a
function is compared with itself on a copy, `window_features` is compared with the
individual feature functions it calls, the ratio is recomputed from the returned
band powers. The oracle and the implementation share every bug, so the tests are
tautologies.

**Why it is plausible.** It looks rigorous (many asserts, exact equality) and is
what you get when expected values are copied from the function's own output
without an independent derivation.

**Expected outcome.** Passes on the correct package; almost every numerical bug survives.
