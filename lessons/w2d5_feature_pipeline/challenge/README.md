# W2D5 independent challenge — causal features on irregularly sampled data

**Time:** about 40 minutes. **Help allowed:** library documentation. **Not allowed for the
independent flag:** hint 3, the reference solution, or an assistant writing the function.

## Scenario

A cold-chain operator monitors walk-in freezers. Each freezer's sensor reports its temperature
*on change* plus an occasional heartbeat, so the interval between readings varies from under a
second to several seconds, and the uplink sometimes drops for minutes. An alerting rule needs
"mean and spread of the temperature over the last 30 s and the last 2 min" for every reading,
computed exactly as the edge device would compute it: from past readings only.

The lab's features counted *rows*. Here a row count is meaningless: thirty rows may be twenty
seconds or four minutes. Windows must be measured in *time*.

## Task

Implement, in `challenge/timefeatures.py`:

```python
def time_window_features(df, windows_s=(30.0, 120.0), max_gap_s=20.0) -> pd.DataFrame
```

**Input.** A DataFrame with columns `series_id` (str), `timestamp` (datetime64), `value`
(float). Rows may arrive in any order. Timestamps are unique within a series.

**Output.** One row per input row, **same index and same order as the input**, with columns:

| Column | Definition |
|---|---|
| `series_id`, `timestamp` | copied from the input |
| `dt_prev_s` | seconds since the previous reading of the same series (NaN for the first) |
| `segment` | 0-based counter per series, incremented when `dt_prev_s > max_gap_s` |
| `count_<w>s` | number of readings of the same series **and segment** with timestamp in `(τ − w, τ]`, where τ is the row's timestamp |
| `mean_<w>s` | mean of `value` over those readings, **NaN unless the segment is at least `w` seconds old** (`τ − segment_start ≥ w`) |
| `std_<w>s` | sample standard deviation (ddof = 1) over those readings, NaN under the same rule and when fewer than two readings |

`<w>` is the window as an integer number of seconds: `mean_30s`, `count_120s`.
A missing required column raises `ValueError`.

## Acceptance criteria

1. `python wb.py check w2d5 --challenge` passes.
2. No feature of a reading changes if any later reading is altered **or removed**.
3. Readings of one series never influence another series' features.
4. The window is half-open exactly as specified: a reading exactly `w` seconds old is outside.
5. After an outage longer than `max_gap_s` the windowed features restart from NaN.
6. In two or three sentences (in `challenge/NOTES.md`): why is criterion 2's *removal* test a
   stronger statement than the *alteration* test for irregular data, and which mistake would
   pass every look-ahead test here and still be wrong?

## What transfers from the lab, and what does not

The grouping, segment and perturbation ideas transfer directly. The window mechanics do not:
you need a time-indexed rolling window and you must decide how "a full window" is defined when
rows are not evenly spaced. Check the endpoint convention of whatever you use; do not assume it.
