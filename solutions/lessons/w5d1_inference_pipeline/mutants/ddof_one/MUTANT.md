# Mutant: sample standard deviation in serving

`calibrate` uses `pandas.Series.std()`, whose default is ddof=1, while the evaluated path used NumPy's
ddof=0. Every score is off by a factor sqrt(100/99), about 0.5 %: invisible on a dashboard, a real
training/serving skew. Caught by `test_scores_match_the_evaluated_path` and the planted-shift test.
