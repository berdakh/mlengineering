# Mutant: one burn-in for every experiment

Batch inference calibrates on the first rows of the whole table instead of each experiment's own
first rows. Evaluation shares the function, so evaluation and batch agree with each other; the API,
which receives a per-experiment burn-in, does not. Three-way parity catches what two-way would miss.
