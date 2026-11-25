# Mutant: the feature layout is recorded but not checked

`model.json` lists the features by name, but the loader always builds `[z, |z|]`. A bundle written by
a future version with another layout (same shape) loads and scores silently wrong: training/serving
skew moved into the artifact. Caught by `test_an_unimplemented_feature_layout_is_refused`.
