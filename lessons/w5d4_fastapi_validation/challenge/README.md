# w5d4 challenge: a stateful streaming endpoint

**Independent work. No step-by-step guidance; hints are in `../hints/` (level 1 first).**

`/predict` is stateless: every request carries a whole run from the start of monitoring. A gateway on
the plant floor would rather send each reading as it arrives. That needs per-machine state on the
server: exactly the `StreamRegistry` of w5d3. Your job is to expose it over HTTP so that every outcome
of the streaming contract becomes the right status code.

## Setup

```bash
cp -r lessons/w5d4_fastapi_validation/lab/. lessons/w5d4_fastapi_validation/challenge/
cp lessons/w5d4_fastapi_validation/challenge/given/streaming.py \
   lessons/w5d4_fastapi_validation/challenge/src/flowguard/streaming.py   # or your own from w5d3
python wb.py check w5d4 --challenge
```

`given/streaming.py` is a snapshot of the w5d3 reference solution (as every lab in this course ships
snapshots of earlier units). If you finished w5d3, use your own: the checks only rely on its contract.

## The contract to implement

Stream ids are path segments, so they match `^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$` (no `/`); anything
else is 422. Every error uses the lab's error body. The streams use `max_gap_s = 5` and
`gap_policy = "flag"`.

| Request | Success | Errors |
|---|---|---|
| `PUT /streams/{id}` | 201 `{"machine_id", "created": true}` if new; 200 `{"created": false}` if it already existed (state kept) | 422 bad id; 503 `not_ready` |
| `POST /streams/{id}/samples`, body = one `Sample` | 200 `{"machine_id", "timestamp", "score", "status", "exceeds_threshold", "n_seen", "after_gap", "duplicate"}` | 404 `unknown_machine`; 409 `out_of_order`; 409 `conflicting_duplicate`; 422 invalid sample; 503 `not_ready` |
| `GET /streams/{id}` | 200 `{"machine_id", "n_seen", "status": "new" / "warming_up" / "ok", "last_timestamp"}` | 404 `unknown_machine` |
| `DELETE /streams/{id}` | 204, empty body | 404 `unknown_machine` |

A retried sample (same timestamp, same values) returns the previous answer with `"duplicate": true`.

## Acceptance criteria

1. `python wb.py check w5d4 --challenge` passes (11 checks), and the lab checks still pass on your
   challenge copy (`WB_TARGET_DIR=lessons/w5d4_fastapi_validation/challenge python -m pytest
   lessons/w5d4_fastapi_validation/checks -q`).
2. Streaming the samples of a run one by one gives the same scores as `POST /predict` with the whole run.
3. Concurrent requests cannot corrupt a machine's state: guard registry access with a lock, and write
   two sentences in a comment explaining your choice (one global lock or one per machine).
4. In a short `challenge/NOTES.md` (5-8 sentences), defend two status-code decisions: why a late
   sample is 409 and not 400 or 422, and why `POST` to an unknown machine is 404 instead of creating it.

The reference solution and the wrong submissions the checks reject are in
`solutions/lessons/w5d4_fastapi_validation/challenge/` and `mutants_challenge/`; open them after submitting.
