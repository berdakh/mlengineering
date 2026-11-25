# Mutant: the API keeps its own copy of the formula

The endpoint computes the score inline with `std(ddof=1)` instead of calling `ZScoreModel.score`.
Unit tests of the model and of the API in isolation can both pass; only a parity test that compares
the API with the evaluation path on the same data sees the ~0.5 % skew (at 100 burn-in rows).
