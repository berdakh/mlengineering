# Status-code decisions (w5d4 challenge, reference)

A late sample is **409 Conflict**, not 400 or 422: its body is valid against the schema (so not 422)
and it is not malformed as a request on its own (so not 400); it is refused because it conflicts with
the current state of the resource, the stream's last accepted timestamp. 409 tells the client exactly
that: re-reading the resource (`GET /streams/{id}` returns `last_timestamp`) explains the refusal, and
resending the same sample will keep failing. A conflicting duplicate is 409 for the same reason, with a
different `code` so clients can tell the two apart.

`POST` to an unknown machine is **404** instead of creating the stream, because creation has
consequences (a new burn-in) that must be intended. With auto-creation, a typo in a machine id would
silently start a second stream and starve the real one; with 404, the typo surfaces on the first
request. Creation is a separate, idempotent `PUT`, so a client that wants "create if missing" can
always send `PUT` first at no risk.

Locking: one global lock around registry operations. An update costs microseconds (w5d3), so the lock
is held for microseconds and serialising streaming requests costs little at this scale; a lock per
machine would allow parallel updates of different machines and is the next step if profiling shows
contention.
