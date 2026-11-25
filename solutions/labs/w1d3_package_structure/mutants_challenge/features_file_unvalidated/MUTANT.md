# Mutant: `load_features` trusts whatever file it is given

`train --features raw_windows.csv` reads the wrong kind of file and fails deep
inside pandas with a `KeyError` traceback (exit code 1) instead of a boundary
error. The raw-data loader validates its columns; the new loader copied the
`read_csv` call but not the validation.

Rejected by: `test_train_rejects_a_file_that_is_not_a_feature_table`.
