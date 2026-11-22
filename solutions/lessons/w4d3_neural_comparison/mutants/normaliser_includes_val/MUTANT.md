# Mutant: normalisation statistics include the validation frame

"More data gives better statistics." But the validation frame exists to estimate how the model
behaves on data it was not fitted to; letting it shape the normaliser is a small leak of the same
kind as fitting a scaler before cross-validation. Caught by: the normaliser check.
