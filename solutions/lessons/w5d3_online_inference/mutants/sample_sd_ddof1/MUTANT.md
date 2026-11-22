# Mutant: sample_sd_ddof1

Calibrates with the sample standard deviation (divides M2 by n-1). It is the textbook default in many
statistics courses and `pandas.Series.std`, but the detector was calibrated with the population SD
(`np.std`, ddof=0). Every score is off by sqrt(99/100) for n_burn=100: small, systematic, and exactly
the kind of training/serving skew parity tests exist to catch.
