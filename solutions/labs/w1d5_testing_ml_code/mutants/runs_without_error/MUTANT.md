# Mutant: runs_without_error

**The mistake.** Every function is called and the result is checked only for type,
finiteness or sign ("smoke coverage"). Line coverage of this suite is high; its
ability to detect wrong numbers is close to zero.

**Why it is plausible.** It is the natural first draft when converting notebook
cells ("it ran and printed a number") into tests.

**Expected outcome.** Passes on the correct package; almost every injected bug survives.
