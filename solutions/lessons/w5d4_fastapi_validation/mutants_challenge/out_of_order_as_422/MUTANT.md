# Mutant: out_of_order_as_422

Reports a late sample as 422 (validation error). The body is valid; it conflicts with the
server's current state. A client that treats 422 as 'fix your payload' will never understand why its
perfectly formed sample is rejected.
