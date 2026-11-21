# Mutant: tests_encode_inclusive_threshold

**The mistake.** One expected value was obtained by running the shipped (defective)
implementation and pasting its output: the test asserts that a score *equal* to the
threshold opens an event. The spec says strictly greater.

**Why it is plausible.** "Characterisation" of existing behaviour is a legitimate
technique for refactoring, and is exactly wrong when the existing behaviour is the bug.

**Expected outcome.** Fails on the correct implementation, so the suite is rejected.
