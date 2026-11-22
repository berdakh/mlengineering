# Mutant: incoming request id ignored

The service always generates its own id, so the client's id (the one the caller will quote in a ticket) cannot be found in our logs. Caught by `test_incoming_request_id_is_propagated_and_bad_ones_replaced`.
