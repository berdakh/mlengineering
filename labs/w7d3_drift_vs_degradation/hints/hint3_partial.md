# Hint 3 (partial implementation)

```python
def join_verdicts(alarms, verdicts, as_of=None):
    known = verdicts if as_of is None else verdicts[pd.to_datetime(verdicts["label_time"]) <= pd.Timestamp(as_of)]
    orphan = ~known["alarm_id"].isin(alarms["alarm_id"])
    latest = (known[~orphan].sort_values("label_time", kind="stable")
              .drop_duplicates("alarm_id", keep="last")[["alarm_id", "verdict", "fault_id", "label_time"]])
    joined = alarms.merge(latest, on="alarm_id", how="left")
    joined["verdict"] = joined["verdict"].astype("boolean")
    report = {...}   # five counts; see the docstring
    return joined, report


def _proportion(k, n, min_n, level):
    if n < min_n or n == 0:
        return {"status": INSUFFICIENT, "estimate": math.nan, "low": math.nan, "high": math.nan, "k": k, "n": n}
    low, high = wilson_interval(k, n, level)
    return {"status": OK, "estimate": k / n, "low": low, "high": high, "k": k, "n": n}


def _judge(estimate, low, high, status, baseline, margin):
    if baseline is None:
        return "not_monitored"
    if status != OK:
        return "unknown"
    # TODO: "no" when clearly worse, "yes" when clearly not worse, otherwise "inconclusive"
```

`window_metrics` and the action table of `monitor_report` are left to you.
