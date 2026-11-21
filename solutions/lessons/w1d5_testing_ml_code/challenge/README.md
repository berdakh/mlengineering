# Reference solution — w1d5 challenge

* `eventkit/events.py` — repaired implementation (identical to the specification-following
  reference used by the checks).
* `tests/test_events.py` — tests derived from the specification; kills all 8 defective variants.

Defects planted in the shipped starter, and the reference test that exposes each:

| Defect | Exposed by |
|---|---|
| event still open at the end of the array is never emitted | `test_runs` case `[0, 0, 5, 5]` |
| `>=` instead of `>` | `test_threshold_is_strict` |
| duration filter applied before merging | `test_merge_happens_before_duration_filter` |

Run: `cd solutions/lessons/w1d5_testing_ml_code/challenge && python -m pytest tests -q`
