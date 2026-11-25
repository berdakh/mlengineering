# w6d6 model answers, common wrong answers, rubrics

## 1. Rebuilds

Staging tested one artifact; a rebuild is another artifact with the same source. Differences can be
harmless metadata (timestamps, which is what changed the digests here) or not: a dependency resolved to a
newer version, a base image tag that moved, a build argument. "Passed in staging" is evidence about a
digest. Promotion redeploys that digest, so the evidence carries over exactly.

*Common wrong answer:* "the code is the same, so the image is the same." The authoring run's three digests
for one tree are the counterexample.

## 2. Rollback scope

* **Bad promotion (checksum mismatch):** fixed: the image changed, and the previous good digest has a valid
  bundle.
* **Wrong `FLOWGUARD_MODEL_DIR`:** not fixed. The current digest was good before, so the tool skips it and
  picks the release before it, which fails with the same environment file *and* undoes a good release.
* **Memory 64m:** not fixed, for the same reason: the older image needs the same memory.

## 3. Two validation layers

An unknown variable name or a malformed value is a bug in the deployment's configuration that cannot
become right by waiting; exiting with status 2 and the variable's name stops a bad deployment at once and
tells the reader exactly what to fix. A missing directory is a fact about the filesystem: the process can
run, log, answer `/healthz` and report through `/readyz` that it must not get traffic. Keeping it alive
keeps the evidence (logs, `/version`) accessible, and the platform's readiness logic does the rest.

*Common wrong answer:* "check that the directory exists at startup and exit." Defensible for this service,
but you lose the running process's diagnostics and conflate "configured wrong" with "model unavailable",
which for a model fetched at startup can be transient.

## 4. Exit 137

From the container runtime: `docker inspect` shows `OOMKilled=true` and exit code 137 (128 + 9, SIGKILL).
The kernel's out-of-memory killer sends SIGKILL, which a process cannot catch; it has no chance to log.
Platform events (Docker events, ECS stopped-task reasons, Kubernetes `OOMKilled` status) carry the cause.

## 5. "Good" too early

Mark a deployment good only after the container has stayed healthy for a soak period longer than the
slowest failure mode (here, at least two health-check intervals; in practice minutes, or until a number of
real requests succeed). The cost is slower deployments and slower rollbacks, and a soak period that is too
short still misses failures that need load (memory growing with traffic).

## 6. Sorting by time

The history is written by several tools (deploy, promote, rollback marking entries), may be merged from
two machines or edited by hand to annotate an incident, and could be appended to concurrently. Any of these
breaks "last element = current". Time is the order that means something; list position is an accident.

## 7. Design choice: environment in the image (model answer)

Against, for this service. The point of one image per release is that the artifact tested in staging is the
artifact that runs in production. A separate production image built with production configuration is, by
construction, never tested before production: staging tested a different digest. It also multiplies images
(one per environment per release), and turns every configuration change, including emergency ones, into a
rebuild and push. Keeping configuration in version-controlled env files outside the image, validated at
startup, gives one artifact and a reviewed, diffable configuration (`git diff -- ops/env` solved incident 1).

The strongest point of the other side: with configuration outside the image, "what is running" is the pair
(digest, configuration), and the deployment record must capture both. Here it captures only the digest,
which is why incidents 1 and 3 needed `git diff` rather than the history. The right answer to that is to
record a hash of the configuration in each history entry, not to bake configuration into images.

*Rubric:* 2 points for a position with a reason specific to promotion or testing; 2 for stating the
opposing side's real strength (traceability of configuration) and answering it.

## Challenge rubric (postmortem)

The checks cover structure, facts and language. Score the analysis (2 points each, 12 total; 9+ passes):

1. **Root cause is about the system:** a unit mismatch between a new client and training data, with no
   unit contract at the boundary; not "someone made a mistake".
2. **Explains why every check passed:** fixture written with the same wrong assumption; smoke test checks
   status codes; dashboards show service health, not prediction quality.
3. **Impact is measured from the right start:** 14:02, when production served the release, not 14:09 when
   someone noticed; business impact in orders (212, 37).
4. **Action items cover detect and prevent**, and at least one targets prediction quality (distribution
   alert, shadow or replay comparison before promotion), not only process.
5. **Mitigation thinking:** something that limits damage when detection is slow (delay automatic orders
   after a model release).
6. **Tone:** describes conditions, not people; "what went well" is real (prediction log by release,
   digest rollback in four minutes, the analyst's report taken seriously).

Common weak postmortems: "root cause: the test was wrong" (stops one step early); action items that are
all "be more careful" or "add more tests"; impact counted from detection; no action that would detect
wrong predictions in a service that is otherwise healthy.

## Interview rep rubric (debugging narrative)

| Element | Strong answer contains | Points |
|---|---|---|
| Symptom | what was observed, by what signal, and when | 1 |
| First hypothesis | stated honestly, including if it was wrong | 1 |
| Discriminating test | the one check that separated hypotheses, and its result | 2 |
| Cause | mechanism, not just component ("the kernel killed it at 64 MiB", not "memory issue") | 2 |
| Fix | and why that fix (rollback versus revert) | 1 |
| Prevention | a change that removes the class of failure or detects it earlier | 2 |
| Delivery | under 5 minutes, chronological, no unexplained jargon | 1 |

8+ of 10: interview-ready for this question. The most common gap is the discriminating test: candidates
describe what they tried, not what told them which hypothesis was right.
