# b3 - Testing and API concepts

**Time box: 25 minutes.** Session B, section 3 of 4. No hints; pytest and pydantic docs are fine.

## Part 1 - write tests (about 12 minutes)

`lab/split_impl.py` contains `train_test_split_by_date`, with its specification in the docstring.
Write tests for it in `lab/test_split.py`.

Your tests are graded by what they *catch*: the checks run your test file against the correct
implementation (all tests must pass) and against four implementations that each violate one clause
of the specification (at least one of your tests must fail on each). The broken versions live in
`checks/impls/`; do not open that directory until you have finished - derive your tests from the
specification. (If you do look, say so in `SUBMISSION.md`; the result then counts as guided, not independent.)

```bash
python -m pytest diagnostic/b3_testing_api/lab/test_split.py -q    # your tests, correct implementation
```

## Part 2 - request validation (about 6 minutes)

In `lab/schemas.py` define a pydantic (v2) model `PredictRequest` for the body of `POST /predict`:

| Field | Rule |
|---|---|
| `customer_id` | string, `C` followed by exactly five digits |
| `plan` | one of `basic`, `standard`, `premium` |
| `tenure_days` | integer, >= 0 |
| `sessions_30d` | integer, >= 0 |
| `monthly_price` | number, > 0 and <= 500 |
| `avg_session_min` | optional number >= 0; defaults to `None` |

Fields not listed here must be rejected, not ignored.

## Part 3 - short written answers (about 7 minutes)

Answer the five questions in `lab/ANSWERS.md`. No FastAPI code is needed; these probe concepts.

## Check your work

```bash
python wb.py check diagnostic/b3_testing_api     # or:
python -m pytest diagnostic/b3_testing_api/checks -q
```

The starter fails the checks. The checks take a few seconds because they start pytest subprocesses.

## Acceptance criteria

* Your tests pass on the correct implementation and detect all four broken ones.
* The schema accepts the valid payloads and rejects each invalid one.
* Written answers distinguish client errors from server errors, and validation from model evaluation.

## Submit

`lab/test_split.py`, `lab/schemas.py`, `lab/ANSWERS.md`, time used.
