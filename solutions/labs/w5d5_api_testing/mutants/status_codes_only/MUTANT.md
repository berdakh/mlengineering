# Mutant: status codes only

A thorough-looking suite that asserts every status code in the contract (200, 413, 422, 503) but
never inspects a response body. Defects in the *content* survive: signed scores, a strict threshold,
the sample instead of the population std, a missing model version, and the concurrency race (each
corrupted response still has status 200). Rejected because a correct status is not a correct answer.
