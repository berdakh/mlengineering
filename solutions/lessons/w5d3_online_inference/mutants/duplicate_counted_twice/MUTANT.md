# Mutant: duplicate_counted_twice

Treats a retried sample (same timestamp, same value) as new data: it is added to the burn-in
accumulators again and n_seen increases. Client retries after timeouts are normal; this makes the
score depend on network behaviour.
