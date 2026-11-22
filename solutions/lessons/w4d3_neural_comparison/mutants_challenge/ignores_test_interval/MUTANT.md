# Mutant: only seed variance enters the verdict

Two deterministic detectors have seed_se = 0, so any difference, however small, becomes a
verdict. Seed repeats do not measure test-set sampling uncertainty. Caught by: the verdict checks.
