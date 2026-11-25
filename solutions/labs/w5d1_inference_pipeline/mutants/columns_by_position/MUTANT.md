# Mutant: columns matched by position

When the input has the right NUMBER of columns, `validate_input` renames them to the expected names by
position. A producer that swaps two columns then silently swaps two sensors. Caught by
`test_misordered_columns_are_refused_not_matched_by_position`.
