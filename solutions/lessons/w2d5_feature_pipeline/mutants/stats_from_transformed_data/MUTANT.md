# Mutant: stats_from_transformed_data

`transform` standardises each column with the mean and standard deviation of the frame it is given, ignoring what `fit` stored. Every frame then looks 'normal on average', test rows influence their own scaling, and a single row cannot be scored at all. This is the feature-pipeline version of fitting a scaler on all rows before splitting. Caught by the ReferenceStats checks.

Changed file: `src/flowguard/features.py`
