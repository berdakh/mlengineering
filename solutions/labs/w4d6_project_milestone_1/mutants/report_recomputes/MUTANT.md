# Mutant: the report step recomputes

`render` reruns `evaluate` from the file paths remembered in the results instead of formatting the
numbers it was given. The report can then disagree with results.json, and rendering takes as long as
evaluating. Caught by `test_report_renders_from_results_only`.
