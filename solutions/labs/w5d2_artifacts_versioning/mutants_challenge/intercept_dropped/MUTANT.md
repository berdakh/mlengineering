# Mutant: the intercept is not saved

Only the coefficients are stored ("the weights are the model"). Every score is shifted by the
intercept: rankings are unchanged, so PR-AUC is too, but every thresholded decision moves. Caught by
`test_loaded_model_scores_like_the_trained_one`.
