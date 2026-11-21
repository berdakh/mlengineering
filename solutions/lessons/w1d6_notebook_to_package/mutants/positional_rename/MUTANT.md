# Mutant: positional_rename

`df.columns = NEW_NAMES` from the notebook: names are assigned by position. It works on today's files
and silently swaps sensors (and `anomaly` with `changepoint`) the day an export changes column order.
The fix is to rename by name and fail on anything unexpected.

Rejected by `test_reordered_columns_are_not_silently_mislabelled`.
