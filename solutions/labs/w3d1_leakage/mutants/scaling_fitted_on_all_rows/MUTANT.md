# Mutant: scaling_fitted_on_all_rows

Standardises numeric columns in `prepare`, using the mean and standard deviation of all rows, before the split. The statistics include the test period, and a served model would receive unscaled rows. On this data the reported number barely moves, which is why the check looks at behaviour (test rows must not influence anything fitted), not at the number.
