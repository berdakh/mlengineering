# Hint 1 - concept (w5d4)

**Lab.** Separate the three gates: pydantic decides "does this body match the schema" (422, for free
once the constraints are right); your endpoint decides "is it meaningful" (400) and "can I serve it"
(503); exception handlers decide "what does the client see when anything goes wrong". If one handler
turns every expected error into the same body, the endpoint code stays short: raise, do not build
responses by hand in every branch.

The model is state of the *application*, not of a request: it belongs in `app.state`, filled once by
the lifespan. If anything in `/predict` reads from disk, it is in the wrong place.

**Challenge.** The streaming module already raises a distinct exception for each situation. Your
endpoint is a translation table from those exceptions to status codes, plus a lock. 409 Conflict is
for requests that are well-formed but conflict with the current state of the resource; the stream's
last timestamp is that state.
