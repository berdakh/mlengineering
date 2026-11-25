# f6 reference answers

1. **4xx (422 with FastAPI/pydantic).** The client sent an invalid body and must fix it; the request
   is rejected at the boundary and never reaches the model. The error body names the field.
2. **503 (or 504 if the service is a gateway) with a clear error, not a 500 stack trace and never a
   score made up from missing features.** Readiness reports "not ready" while the dependency is down
   so the load balancer stops sending traffic; liveness stays OK (restarting would not help). For the
   operator: a 4xx is the client's problem and needs no page; a 5xx/503 is ours and may page someone.
3. **Not safe as designed:** the side effect (a CRM task) happens twice. Make it idempotent: the
   client sends an idempotency key (or a request id), the service records keys and returns the first
   result for a repeated key without creating a second task. Alternatively separate scoring (safe to
   retry) from task creation.
4. **A model problem (out of support), not a validation error:** the value is legal. The service may
   still score but must flag it (e.g. `out_of_support: true`, metric increment, log event) and must
   not silently return a confident score as if the input were typical, nor reject a legal request
   with a 4xx. Monitoring counts these.
5. **Not a good unit test.** It tests a property of one trained artifact on two hand-picked accounts,
   so it breaks on every retrain for reasons that are not bugs, and passes while the code is wrong in
   ways the two accounts do not reveal. Unit tests check code contracts (shapes, invariants, schema,
   determinism); model quality belongs to an evaluation step with a held-out set and a threshold
   chosen before looking - outside the unit-test suite.
