# Mutant: auto_register

POSTing a sample to an unknown machine silently creates its stream. A typo in a machine id
(`pump-O7` for `pump-07`) then starts a second burn-in instead of being reported, and the real
machine's stream stops receiving data without anyone noticing.
