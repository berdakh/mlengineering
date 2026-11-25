# Mutant: impl_still_drops_final_event

**The mistake.** The tests are the reference tests, but the submitted
implementation still loses an event that is open when the array ends (two of the
three planted defects were fixed, then work stopped because "the tests I ran were green").

**Why it is plausible.** The learner ran an earlier, weaker version of their tests
against their fix and did not re-run the final suite.

**Expected outcome.** Rejected by the implementation checks (random comparison against the spec).
