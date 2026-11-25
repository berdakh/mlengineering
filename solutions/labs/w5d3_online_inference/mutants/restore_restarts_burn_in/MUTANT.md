# Mutant: restore_restarts_burn_in

The snapshot keeps the frozen mu/sigma but not the Welford accumulators, so a scorer restored in the
middle of the burn-in starts calibrating from zero. Restarts during start-up are exactly when this
happens in production.
