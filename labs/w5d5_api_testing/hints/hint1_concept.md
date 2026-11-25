# Hint 1 (concept)

**Lab.** A test kills a defect only if the defect changes something the test asserts. For each row
of the contract table, ask two questions: *which status code* and *which body content* would differ
if this line were wrong? A suite that only asserts status codes cannot see a wrong number inside a
200 response, and a suite that sends one request at a time cannot see two requests interfering.
Look at the contract's boundaries (minimum, maximum, exactly at threshold, empty, non-finite,
unknown field, before startup, broken bundle): each is one test.

**Challenge.** Requests and responses are asymmetric. The server may start *accepting* more and
*returning* more; it may not start *requiring* more, *accepting* less, or *returning* less (or
something it never returned before, such as `null`). And FastAPI puts every pydantic body behind a
`$ref`, so comparing `paths` alone compares two identical pointers.
