# Mutant: depends_on_repo_data

**The mistake.** The reference suite plus one test that reads the course dataset
through a path relative to the repository root. The suite passes only when run
from one particular working directory on one particular checkout.

**Why it is plausible.** The data file is right there, and tests "pass on my machine".

**Expected outcome.** Fails on the *correct* package, because the checks run the
suite from a temporary directory: unit tests must construct their own data.
