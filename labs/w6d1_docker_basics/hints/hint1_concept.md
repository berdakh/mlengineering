# Hint 1 - concept (w6d1)

**Lab.** Think of each Dockerfile instruction as a cached function of its inputs and of everything
above it. Ask of every line: "how often does its input change?" and sort accordingly. Then ask of the
running container three questions, each answered by one instruction: *who* runs the server (`USER`),
*what* is PID 1 (`CMD` form), and *where* does it listen (`--host`). Finally, the image must find two
things at run time: the code (`PYTHONPATH` or an installed package) and the model
(`FLOWGUARD_MODEL_DIR`). Both are paths *inside the image*, produced by your `WORKDIR` and `COPY`.

`.dockerignore` patterns behave like paths from the context root, not like `.gitignore` patterns.

**Challenge.** Each broken build has one mechanism behind its complaint. A: the cache. B: who
receives SIGTERM (and a missing `USER`). C: what `docker build .` sends, and what `COPY . .` then
writes into a layer. Diagnose the mechanism before editing anything.
