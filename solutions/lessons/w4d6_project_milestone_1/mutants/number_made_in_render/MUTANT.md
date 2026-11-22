# Mutant: a number computed in the report step

`render` adds a 'mean PR-AUC across candidates' column that is computed while rendering and never
stored in results.json. Harmless-looking, but now the report contains a number no one can trace or
reproduce from the results file. Caught by `test_every_table_number_comes_from_results_json`.
