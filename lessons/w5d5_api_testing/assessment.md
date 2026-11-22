# Assessment — w5d5 API testing

Answer in writing before opening `solutions/lessons/w5d5_api_testing/assessment_answers.md`.

## Reasoning questions

1. Your suite has 95 % line coverage of `api.py` and kills 7 of 12 defects. Explain how both can be
   true, and which two kinds of assertion close the gap.
2. Why does `TestClient(app)` without `with` see a service that is "not ready", and why is that useful
   rather than only a pitfall?
3. A defect makes `/predict` return 500 for a request containing `NaN`. The contract says 422. Give
   one reason this matters to a client and one reason it matters to the team operating the service.
4. The concurrency test passes on the defective service in one CI run out of fifty. Is the test wrong?
   What would you change, and what would you change in the code review checklist instead?
5. Why is `std(ddof=1)` in the service a defect even though it is "the unbiased estimator"? Which
   test caught it, and why did it need a burn-in of exactly two unequal values to be sensitive?
6. Classify each change from v1 to v2 in the challenge as breaking or compatible, from the client's
   side, and say why the same change (`T` -> `T | None`) is compatible in a request and breaking in a
   response.

## Design choice (explain in 6-10 sentences)

The service starts *degraded* when the bundle cannot be loaded (alive, not ready) instead of crashing
at startup. Argue for this choice, then give the strongest argument for crashing instead, and say
which deployment setting (orchestrator, health checks, alerting) makes each choice the better one.

## Interview rep (debugging, 10-15 min, no notes)

`interview_rep/test_flaky.py` passes when one test is selected and fails when the whole file runs.

```bash
PYTHONPATH=lessons/w5d5_api_testing/lab/service python -m pytest lessons/w5d5_api_testing/interview_rep/test_flaky.py -q
PYTHONPATH=lessons/w5d5_api_testing/lab/service python -m pytest lessons/w5d5_api_testing/interview_rep/test_flaky.py -q -k scores
```

Out loud or in writing: (a) state your first two hypotheses and how you would test each in under a
minute; (b) find the cause; (c) fix the tests, not the service; (d) name the general rule this
violates and one tool-level safeguard (for example a pytest plugin or option) that would have exposed
it earlier.

## Rubric (for the open answers)

| Criterion | 1 - not yet | 2 - partial | 3 - solid |
|---|---|---|---|
| Status vs content | names one kind of assertion | both kinds, no example | both kinds with a defect each catches |
| Lifecycle | "with is needed" | explains lifespan | uses the no-startup state as a deliberate test |
| Concurrency | "add retries" | explains shared state | separates detection (test) from prevention (no shared mutable state) |
| Contract asymmetry | lists changes | classifies most | justifies each from what a client sends or reads |
| Debugging narrative | jumps to the fix | finds the cause | hypotheses ordered by cost, cause, fix, general rule, safeguard |
