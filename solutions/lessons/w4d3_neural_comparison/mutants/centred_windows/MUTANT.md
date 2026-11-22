# Mutant: centred windows

The window for row t is centred on t, as in offline analysis (and zero-phase filtering).
It looks `window/2` rows into the future, which a deployed detector cannot do. Offline scores look
better and earlier than they will be live. Caught by: the window and score causality checks.
