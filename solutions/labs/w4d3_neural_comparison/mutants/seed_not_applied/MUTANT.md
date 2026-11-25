# Mutant: the seed is not applied to weight initialisation

The shuffling generator is seeded, but the model is built from the global RNG state, so two runs
with the same `seed` start from different weights. Results cannot be reproduced and "seed 3" in
a table means nothing. Caught by: the same-seed determinism check.
