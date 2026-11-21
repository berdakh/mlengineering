# b3_testing_api - reviewer notes

Reference: `lab/test_split.py`, `lab/schemas.py`. Verified with
`python tools/verify_checks.py diagnostic/b3_testing_api`.

## Part 1 - tests

The four broken implementations (`diagnostic/b3_testing_api/checks/impls/`) each violate one clause:

| Variant | Violated clause | A test that catches it |
|---|---|---|
| `bug_boundary` | cutoff rows belong to test | data with a row exactly at the cutoff; assert it is in test |
| `bug_drops_rows` | every row in exactly one output | `len(train) + len(test) == len(df)` with a row at the cutoff |
| `bug_no_empty_error` | `ValueError` on an empty side | `pytest.raises(ValueError)` with a cutoff outside the data |
| `bug_mutates_input` | input not modified | deep copy before, `assert_frame_equal` after, with **unsorted string dates** as input |

Common weak submissions:

* **Happy path only** (mutant `happy_path_only`): cutoff between dates, sorted input, asserts on
  lengths. Passes on every broken variant.
* **No row exactly at the boundary** - the single most informative test case for any split or
  windowing function, and the one that prevents off-by-one leakage between train and test.
* **Mutation test with already-sorted, already-datetime input** - the in-place conversion and sort
  are then invisible. Tests must use inputs on which the bug would show.
* **Tests that re-implement the function** (`expected = df[df.date < cutoff]`) - they share its bugs.
  Prefer hand-written expected values on tiny frames.
* **Wrong expectation** (mutant `wrong_expectation`) - fails on the correct implementation.

## Part 2 - schema

Reference uses `Field` constraints, `Literal`, and `extra="forbid"`. Equivalent alternatives:
`Annotated[int, Field(ge=0)]`, `constr`/`StringConstraints(pattern=...)`, an `Enum` for `plan`.
Weak submissions: types without bounds (mutant `no_bounds_schema`); unknown fields silently ignored
(mutant `extra_fields_allowed`); a hand-written `validate()` method that duplicates what the library does.

## Part 3 - model answers

1. **4xx** - the request is invalid (FastAPI returns 422 Unprocessable Entity for a body that fails
   validation; 400 is also defensible). The *client* must fix it; retrying unchanged cannot succeed.
   It must not reach the model: a negative tenure would produce a confident, meaningless score.
2. **5xx** - typically 503 Service Unavailable (the server cannot serve now), not 4xx. Readiness
   should report "not ready" so the platform does not route traffic to this instance (or the process
   should fail to start); liveness may still be true. The distinction tells the operator whose
   problem it is and whether a retry can help: 4xx = caller's bug, 5xx = ours, pages on-call.
3. Safe if scoring is a pure function of the request: the same input gives the same output and
   nothing else changes, so a retry is harmless (POST is not idempotent *by definition*, but this
   handler can be in practice). Unsafe once the handler has side effects - logging a prediction that
   is later joined to outcomes, billing per call, triggering an action. Remedy: a client-supplied
   request/idempotency key, de-duplicated server-side.
4. Not a schema-validation problem (the value is legal) and not something the model will flag by
   itself - models extrapolate silently. The service should detect inputs outside the training range
   (range checks from training statistics), then log, flag in the response, or fall back to a
   default policy. It must not fail the request with a 4xx as if the client had erred, and must not
   return the score as if it were as trustworthy as any other.
5. Not a unit test: it depends on data, a training run and randomness; it can fail without any code
   defect and pass with one. It belongs in a model-evaluation / release gate that runs on new model
   candidates with a justified threshold and tolerance. In the unit-test suite it makes CI slow and
   flaky, and teaches people to ignore red builds.

Common incorrect answers: "500 for bad input"; "200 with an error message in the body"; "POST is
never safe to retry" or "always safe"; "out-of-distribution inputs are caught by pydantic"; treating
a metric threshold as a unit test.

## Rubric

| Aspect | Demonstrated independently | Partial | Not yet demonstrated |
|---|---|---|---|
| Test design | Correct impl passes, all 4 variants caught, tests derived from the spec with boundary cases | 2-3 variants caught | Happy path only, or tests fail on the correct impl |
| Validation | Schema passes all checks | Bounds present, extras not forbidden (or vice versa) | Types only |
| API concepts | Q1-Q3 correct with reasons | Status classes right, reasoning thin | 4xx/5xx confused |
| Validation vs evaluation | Q4 and Q5 distinguish the layers clearly | One of the two | Conflated |

No FastAPI experience is required for this section; "Not yet demonstrated" on API concepts simply
keeps Week 5 at full length.
