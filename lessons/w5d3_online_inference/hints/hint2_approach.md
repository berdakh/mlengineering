# Hint 2 - approach (w5d3)

**Lab: shape of `update`.**

```text
ts, value = parse(row)                    # may raise InvalidSampleError
if there is a last timestamp:
    earlier  -> raise OutOfOrderError
    equal    -> same value: return last result with duplicate=True; else raise ConflictingDuplicateError
    gap      -> after_gap = True; if policy is "reset": reset the calibration accumulators only
if still calibrating:  Welford update; if count == n_burn: freeze mu, sigma; result = no score
else:                  score = |value - mu| / sigma
update n_seen, last_ts, last_value, last_result; return result
```

`dataclasses.replace(result, duplicate=True)` (or `ScoreResult(**{**asdict(r), "duplicate": True})`)
builds the duplicate answer without mutating the frozen original.

`snapshot()` must survive `json.loads(json.dumps(...))`: store timestamps as ISO strings and the last
result as a dict; rebuild both in `restore`.

**Challenge.** Keep `alarm`, `run_hi`, `run_lo`. For the dev evaluation: compute batch scores per
development experiment with `detector.score_batch`, turn them into `exceeds` with NaN for the warm-up,
run `hysteresis_batch` per experiment (never across experiment boundaries), and pass the 0/1 states to
`evaluate_experiments(dev, flagged, burn_in=detector.n_burn)` with the default `min_duration=1`.
For the batch rule, pass the raw exceedances with the bundle's `min_duration` and `merge_gap`.
