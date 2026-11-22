# Hint 3 — partial implementation

```python
# guards.py
def out_of_support(values, low, high):
    return [i for i, v in enumerate(values) if v < low or v > high]
```

```python
# api.py, inside predict()
def degraded(reason: str) -> dict:
    metrics.inc("flowguard_degraded_total", reason=reason)
    log_event("degraded", request_id=rid, reason=reason)
    return {"model_version": model.model_version if model is not None else None,
            "degraded": True, "reason": reason, "fallback": FALLBACK, "scores": None,
            "above_threshold": fallback_alarms(body.values, settings.envelope_low, settings.envelope_high),
            "out_of_support": oos, "request_id": rid}
```

```python
# client.py
def backoff(self, retry_index):
    return self.rng.uniform(0.0, min(self.policy.max_delay, self.policy.base_delay * 2 ** retry_index))
```

```python
# tests/test_faults.py: the shape of one drill
def test_model_error_degrades(make_client):
    client = make_client({"model_error": None})
    data = client.post("/predict", json=BODY).json()
    assert data["degraded"] is True and data["reason"] == "model_error" and data["scores"] is None
```

The remaining pieces (the bulkhead, readiness, the rest of the client loop and the other drills) follow
the contract and hint 2.
