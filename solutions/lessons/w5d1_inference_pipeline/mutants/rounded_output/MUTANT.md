# Mutant: rounded predictions

`predictions.csv` is written with `float_format="%.4f"` to make the file smaller and easier to read.
Scores near the threshold now compare differently downstream from how they were computed, and the
file no longer reproduces the object's output. Caught by `test_cli_scores_the_file_like_the_object`.
