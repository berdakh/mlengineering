# f6_testing_api - reviewer notes (parallel form of b3)

## Part 1: tests graded by what they catch

| Broken implementation | Clause violated | A test that catches it |
|---|---|---|
| `bug_row_level` | all rows of a group share a fold | `folds.groupby(group).nunique() == 1` |
| `bug_no_error_few_groups` | ValueError when groups < folds | `pytest.raises(ValueError)` with 9 folds for 8 groups |
| `bug_mutates_input` | input not modified | compare a copy before/after with `assert_frame_equal` |
| `bug_seed_ignored` | same input and seed -> same folds | call twice with the same seed and compare (probability of a false pass with 8 groups and 4 folds is about 4 in 10,000) |

The reference suite (`lab/test_folds.py`) has one test per clause and passes on the correct version.
Note the spec's "whatever the row order" clause: the reference also checks it, although no broken
version targets it - a strong suite tests the specification, not the known bugs.

## Part 2 and 3

Reference schema and answers in `lab/`. Common wrong answers: `extra="ignore"` (default) lets a
misspelt optional field vanish; ranges missing; for question 2 returning 500 or a default score; for
question 3 "retries are always safe for POST"; for question 4 rejecting a legal request with 422 or
silently clipping it; for question 5 calling a single-artifact ranking assertion a unit test.

## Rubric (assign per aspect)

| Aspect | Demonstrated independently | Partial | Not yet demonstrated |
|---|---|---|---|
| Test design | all four broken versions caught, tests named by clause, without opening `impls/` | three caught, or caught only after reading `impls/` | two or fewer |
| Validation | schema passes all checks first time or with one fix | passes after several check-driven iterations | fails |
| API concepts | answers 1-3: correct status classes, readiness vs liveness, idempotency key | partly correct | confuses client and server errors |
| Validation vs evaluation | answers 4-5 separate out-of-support handling and model evaluation from unit tests | one of the two | neither |
