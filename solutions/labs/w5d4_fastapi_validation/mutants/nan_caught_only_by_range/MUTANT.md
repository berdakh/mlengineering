# Mutant: nan_caught_only_by_range

Relies on the range limits to reject NaN. They do (NaN fails every comparison), but the error says
'less than or equal to 500' for a NaN, which sends the client looking for an out-of-range value that
does not exist. And a field without limits would accept NaN.
