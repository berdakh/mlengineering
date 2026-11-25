# f6 - Testing and API concepts (parallel form of b3)

**Time box: 25 minutes.** Sitting B, section 3 of 4. No hints; pytest and pydantic docs are fine.

## Part 1 - write tests (about 12 minutes)

`lab/fold_impl.py` contains `assign_folds_by_group`, with its specification in the docstring.
Write tests for it in `lab/test_folds.py`.

Your tests are graded by what they *catch*: the checks run your test file against the correct
implementation (all tests must pass) and against four implementations that each violate one clause
of the specification (at least one of your tests must fail on each). The broken versions live in
`checks/impls/`; do not open that directory until you have finished - derive your tests from the
specification. (If you do look, say so in `../SUBMISSION.md`; the result then counts as guided.)

```bash
python -m pytest lessons/w8d6_final_assessment/f6_testing_api/lab/test_folds.py -q
```

## Part 2 - request validation (about 6 minutes)

In `lab/schemas.py` define a pydantic (v2) model `ScoreRequest` for the body of `POST /score`:

| Field | Rule |
|---|---|
| `account_id` | string, `A` followed by exactly five digits |
| `tier` | one of `starter`, `business`, `enterprise` |
| `tenure_days` | integer, >= 0 |
| `shipments_30d` | integer, >= 0 |
| `monthly_fee` | number, > 0 and <= 1000 |
| `avg_parcel_kg` | optional number, > 0 and <= 70; defaults to `None` |

Fields not listed here must be rejected, not ignored.

## Part 3 - short written answers (about 7 minutes)

Answer the five questions in `lab/ANSWERS.md`. No FastAPI code is needed; these probe concepts.

## Check your work

```bash
python wb.py check lessons/w8d6_final_assessment/f6_testing_api     # or:
python -m pytest lessons/w8d6_final_assessment/f6_testing_api/checks -q
```

The starter fails the checks. They take a few seconds because they start pytest subprocesses.

## Acceptance criteria

* Your tests pass on the correct implementation and detect all four broken ones.
* The schema accepts the valid payloads and rejects each invalid one.
* Written answers distinguish client errors from server errors, side effects from pure computation,
  and validation from model evaluation.

## Submit

`lab/test_folds.py`, `lab/schemas.py`, `lab/ANSWERS.md`, time used.
