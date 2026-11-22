# Mutant: the estimator is saved with joblib

The obvious artifact: `joblib.dump(model.model_)`. It round-trips and is checksummed, but joblib files
are pickle streams. Loading one runs code, and scikit-learn only guarantees loading in the version that
wrote it. Caught by `test_nothing_is_pickled`.
