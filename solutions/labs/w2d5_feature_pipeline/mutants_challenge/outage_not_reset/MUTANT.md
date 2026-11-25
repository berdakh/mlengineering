# Mutant: outage_not_reset

Outages are ignored: there is one segment per series. Time-based windows hide this bug better than row-count windows because old rows fall out of the window on their own; what goes wrong is the 'full window' rule, which now treats the first seconds after a long outage as fully observed. Caught by the outage test and the reference comparison.

Changed file: `timefeatures.py`
