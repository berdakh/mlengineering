# Mutant: never_half_opens

The call path never moves from open to half-open, so once the dependency recovers the breaker stays open forever: the mitigation becomes a permanent outage.
