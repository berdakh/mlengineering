# Mutant: happy path only

The suite checks that a valid request returns 200 with the right number of scores, and that
`/healthz` answers. It never sends a bad request, never starts the app without a model, never checks
values. Most realistic defects (422 vs 500, readiness, checksum, extra fields) survive. Rejected
because it lets defects through.
