# Hint 1 (concept)

Training/serving skew is any difference between the function that was evaluated and the function that
runs. It enters wherever the same computation exists twice. List every step the training path takes
between raw rows and a number (which rows calibrate, which statistic, what happens to extreme values,
in what order the features are stacked) and ask of each: where does the serving path get this from?
A value that the serving code supplies itself, rather than reading from the model, is a candidate.

For the lab: the threshold, the burn-in length and the post-processing are decisions made on
development data. Nothing about the batch being scored may change them. And the calibration of a run
uses its first `n_burn` rows only; a fault later in the run must not be able to move it.
