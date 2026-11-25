# Hint 2 (approach)

**Lab.** Organise the suite by layer, one file each:

* `conftest.py`: `model`, `bundle_dir` (save into `tmp_path`), `client` (`with TestClient(...)`),
  `degraded_client` (empty directory), and a helper that builds a body with burn-in `[-1.0, 1.0]`
  (mean 0, population std 1, so score = |value|).
* `test_api_contract.py`: one content-rich happy path (scores, flags, version, threshold); a
  parametrised 422 test; raw-bytes `NaN`/`Infinity`; 3,600 vs 3,601 values; a value exactly at the
  threshold; burn-in `[0.0, 2.0]` where population std 1 and sample std 1.414 give different scores.
* `test_lifecycle.py`: ready after startup; not ready without `with`; empty directory degraded on
  every endpoint; bundle edited after saving refused.
* `test_concurrency.py`: `ThreadPoolExecutor(8)`, 48 requests, distinct values per request, compare
  each response with its own expectation.
* `test_integration.py`: round trip through `save_bundle`/`load_bundle`, then serve it.

**Challenge.** Write three helpers before `breaking_changes`: `resolve(schema, document)` that follows
`#/components/...` pointers; `types(schema, document)` that returns a frozenset type signature; and
`json_schema(container)` that digs out `content["application/json"]["schema"]`. Then compare request
bodies with "old types must be a subset of new types" and response fields with "new types must be a
subset of old types".
