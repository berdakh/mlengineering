# Mutant: no_range_limits

Types only, no `ge`/`le`: a value in the wrong unit (flow in m3/s, pressure in Pa) or a sentinel
such as -9999 is scored as if it were a reading.
