# Mutant: sequential only

The full reference suite without the concurrency test. Every request is sent one after another, so
the shared-state race cannot happen during the tests and survives. Rejected: services run requests
concurrently, and only a concurrent test can see this class of defect.
