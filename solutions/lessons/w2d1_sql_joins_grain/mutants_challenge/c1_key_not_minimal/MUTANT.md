# Mutant: c1_key_not_minimal

The result is correct but the declared key includes a measure (`n_orders`). Any superset of a key is unique,
so "it is unique" was taken as proof. A key that contains a measure does not describe the grain and would
not protect a later join against fan-out.

Changed file: `queries/c1_site_type_costs.sql`
