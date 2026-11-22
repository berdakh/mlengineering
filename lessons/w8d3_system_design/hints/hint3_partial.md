# w8d3 hint 3 — partial implementation

```python
import math

def _positive(**values):
    for name, v in values.items():
        if not (isinstance(v, (int, float)) and math.isfinite(v) and v > 0):
            raise ValueError(f"{name} must be a finite number > 0, got {v!r}")

def peak_qps(requests_per_day, peak_to_mean):
    _positive(requests_per_day=requests_per_day, peak_to_mean=peak_to_mean)
    if peak_to_mean < 1:
        raise ValueError("peak_to_mean must be >= 1")
    return requests_per_day / 86_400 * peak_to_mean

def replicas_needed(peak_qps_value, service_ms, cores_per_replica, target_utilisation):
    ...  # validate
    busy = peak_qps_value * service_ms / 1000
    return max(1, math.ceil(busy / (cores_per_replica * target_utilisation) - 1e-12))
```

The remaining three follow the same pattern. `labels_available` is
`predictions_per_day * label_rate * max(0, window_days - label_delay_days)`.

**Design review, the two blockers in outline.** §4 lists two fields that are written *after* the ticket is
routed. §5 splits tickets at random although the system will route *future* tickets and the same customers
and outages produce near-duplicate tickets. Write the fix for each as a protocol, not as "be careful".
