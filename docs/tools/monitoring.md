---
title: "Logging and monitoring"
parent: Tool guides
nav_order: 16
---

# Logging and monitoring

**Logging** is a program writing down what it does. **Monitoring** is turning those records into a few numbers,
watching them, and calling a person when one goes wrong. For a model service there is a third layer: watching
the **data** and the **model's quality**, which can change while the service itself looks perfectly healthy.
This guide covers what Week 11 uses (notebooks 42-44).

## What it is, and why teams use it

A deployed model answers requests all day with nobody watching. Without logs, the first sign of trouble is a
complaint, and then nobody can say what happened. With them you can answer: how many requests, how many failed,
how slow, which model version answered, and what the inputs looked like. Monitoring then makes sure that the
important questions are asked automatically, every few minutes.

## Python's logging module

Everything below works in Colab and locally; `logging` is part of Python.

```python
import logging, sys

log = logging.getLogger("churn_api")             # one logger per module or service
handler = logging.StreamHandler(sys.stdout)      # where records go (console here)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
log.addHandler(handler)
log.setLevel(logging.INFO)                       # keep INFO and above

log.info("model loaded: %s", "churn_v3")         # pass arguments, do not build the string yourself
log.warning("slow request: %d ms", 812)
log.debug("dropped: below INFO")
```

**Levels**, least to most serious: `DEBUG` (developer details), `INFO` (normal events), `WARNING` (odd but
handled), `ERROR` (an operation failed), `CRITICAL` (the service cannot work). The level set on a logger is a
filter: `INFO` keeps INFO, WARNING, ERROR, CRITICAL.

The parts: a **logger** creates records; **handlers** send them somewhere (`StreamHandler` to the console,
`FileHandler` to a file); a **formatter** turns a record into text. In a container, log to standard output: the
platform (Docker, ECS) collects it and sends it to the log service.

`log.exception("scoring failed")` inside an `except` block logs at ERROR level with the traceback: use it
instead of `print(e)`.

## Structured logs: JSON Lines

Plain sentences are for people. Logs are read by machines first, so write **one JSON object per line**:

```json
{"time": "2026-03-03T07:14:09+00:00", "level": "INFO", "request_id": "r-1842", "model_version": "churn_v3", "latency_ms": 41.3, "prediction": 1, "inputs": {"recency_days": 40, "segment": "consumer"}}
```

A minimal JSON formatter (notebook 42 builds it):

```python
import json

class JsonFormatter(logging.Formatter):
    def format(self, record):
        out = {"time": self.formatTime(record), "level": record.levelname,
               "logger": record.name, "message": record.getMessage()}
        out.update(getattr(record, "fields", {}) or {})
        return json.dumps(out, default=str)

handler.setFormatter(JsonFormatter())
log.info("prediction served", extra={"fields": {"request_id": "r-9", "latency_ms": 31.2}})
```

Reading such a log with pandas: `pd.read_json(path, lines=True)` for clean files; a small loop with
`json.loads` and `try/except json.JSONDecodeError` when some lines may be broken.

## What to log for a model service

| Field | Why |
|---|---|
| `time` in UTC, ISO 8601 (`datetime.now(timezone.utc).isoformat()`) | ordering, joining systems; time zones cause bugs |
| `request_id` | follow one request through several services |
| `model_version` | which model answered; essential after an update |
| `latency_ms` | speed |
| `status` | 200, 422 (bad input), 500 (our failure), 503 (not ready) |
| `prediction` (and score) | compare with labels later; watch the prediction distribution |
| `inputs`: the model's features only | debugging and drift checks |

What **not** to log: personal data the model does not need (names, emails, phone numbers, addresses), secrets
and tokens, full request bodies. Build the `inputs` field from an **allow-list** of feature names, so a new field
added by a client never reaches the logs by accident. Logs are kept long and read widely; data protection rules
apply to them.

## Metrics

A **metric** is a number computed per time window. Start with these:

| Metric | How | Note |
|---|---|---|
| traffic | requests per window | a sudden drop is as alarming as a spike |
| error rate | share of status ≥ 500 | count 422 (client's bad input) separately |
| latency p50 / p95 / p99 | `np.percentile(latencies, [50, 95, 99])` | percentiles, not the mean: latency is skewed |
| saturation | CPU, memory | measured by the platform |
| prediction rate | share of positive predictions (or the score's mean) | a jump often means the inputs changed |

With pandas:

```python
df["window"] = pd.to_datetime(df["time"]).dt.floor("1h")
metrics = df.groupby("window").agg(requests=("status", "size"),
                                   error_rate=("status", lambda s: (s >= 500).mean()),
                                   p95_latency_ms=("latency_ms", lambda s: s.quantile(0.95)))
```

(`Series.quantile` skips NaN; `np.percentile` does not, so drop NaN first when you use it.)

## Dashboards

A dashboard is for **looking**: a few panels, stacked, sharing the time axis so events line up.

```python
fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
for ax, col in zip(axes, ["requests", "error_rate", "p95_latency_ms"]):
    ax.plot(metrics.index, metrics[col]); ax.set_title(col)
fig.tight_layout()
```

In production the same panels live in a tool such as CloudWatch dashboards or Grafana, fed by the log service or
by a metrics system such as Prometheus. Keep the number of panels small; a forty-panel dashboard is not read.

## Alerts

An alert is for **acting**: it notifies a person when a rule is broken. Each rule has

1. a metric and a direction (`>` for errors and latency, `<` for traffic);
2. a threshold: an agreed target (a **service level objective**, SLO, e.g. "error rate below 2 %"), or the
   metric's normal range (e.g. mean + 3 standard deviations over a quiet period). A baseline with no variation
   (zero errors all day) gives a threshold of zero: use an SLO there;
3. a duration: how many windows in a row the rule must be broken (filters one-off blips, alerts a bit later);
4. an owner and a short runbook: who is notified and what they check first.

The test of a good alert: when it fires, a person must do something now. Alerts that fire for nothing teach people
to ignore all alerts.

## Monitoring the data and the model

The service can be healthy while the model quietly gets worse. Two different things to watch:

* **Input drift**: the distribution of a feature changed compared with the training data. Measurable at once,
  without labels.
* **Degradation**: the model's quality (recall, precision, error) got worse. Needs **labels**, which usually
  arrive late (a week, a quarter).

They can happen independently: a recalibrated sensor can shift an input without hurting the model; a new kind of
fault can hurt the model without moving any input much (notebook 43 shows both).

**PSI** (population stability index), per feature:

```python
def psi(reference, current, bins=10, eps=1e-4):
    inner = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)[1:-1]))
    edges = np.concatenate([[-np.inf], inner, [np.inf]])
    share = lambda v: np.bincount(np.searchsorted(edges[1:-1], v, side="right"),
                                  minlength=len(edges) - 1) / len(v)
    p, q = np.maximum(share(reference), eps), np.maximum(share(current), eps)
    return float(np.sum((q - p) * np.log(q / p)))
```

**KS statistic**: the largest gap between the two empirical CDFs; `scipy.stats.ks_2samp(a, b).statistic`.

Practical rules:

* Choose the **reference** carefully: data from the same setup the model was trained and validated on. A
  reference recorded under different conditions makes everything look drifted (notebook 44 shows it on SKAB).
* PSI and KS on **small windows** are large even with no drift. Calibrate thresholds by computing the statistic
  on windows of the same size from quiet, reference-like data. The "0.1 / 0.25" rule of thumb comes from credit
  scoring with large samples.
* Use p-values with care: with thousands of rows, harmless differences are "significant".
* When drift fires, find the **cause** before acting: a pipeline bug, a changed unit, a new data source, a real
  change in the world. Then check whatever labels exist.
* When labels arrive, compute quality on the **labelled rows only** (with their delay), per window and per
  segment, and compare with the validation results.

## Safe model updates

* **Shadow**: the new model scores copies of live requests; its answers are only logged. Compare agreement,
  latency, errors.
* **Canary**: a small, stable share of users (route by a hash of the id) gets the new model; guardrail metrics
  must hold before the share grows.
* **Rollback**: switch back to the previous version, which you kept. Log `model_version` in every record so you
  can tell the versions apart in every metric.

## Common errors and how to read them

| Symptom | Likely cause | Fix |
|---|---|---|
| every line printed twice | the logger has two handlers, or propagates to the root logger which also prints | `log.propagate = False`, or add the handler once |
| no log output at all | level too high, or no handler | `log.setLevel(logging.INFO)`; add a handler |
| `--- Logging error ---` with a traceback | your formatter raised, or `%` arguments do not match the message | fix the formatter; count `%s` against the arguments |
| `TypeError: Object of type int64 is not JSON serializable` | NumPy numbers in the record | convert with `int(...)`/`float(...)`, or `json.dumps(..., default=str)` |
| `JSONDecodeError` reading a log | a broken line (process killed mid-write) | skip and count bad lines |
| times off by hours between systems | local time without a time zone | always log UTC with the offset |
| PSI is `inf` or `nan` | an empty bin and no floor | floor the shares at a small `eps` |
| drift alert fires every day | threshold not calibrated for the window size, or wrong reference | calibrate on quiet data; revisit the reference |

## Cheat sheet

```python
log = logging.getLogger("svc"); log.setLevel(logging.INFO)
log.info("msg %s", value, extra={"fields": {...}})        # with a JSON formatter
log.exception("failed")                                    # inside except: includes the traceback

record = {"time": datetime.now(timezone.utc).isoformat(), "request_id": rid,
          "model_version": v, "latency_ms": round(ms, 1), "prediction": y,
          "inputs": {k: x[k] for k in ALLOWED if k in x}}
open(path, "a").write(json.dumps(record) + "\n")

df = pd.read_json(path, lines=True)
df["window"] = pd.to_datetime(df["time"]).dt.floor("1h")
np.percentile(latencies, [50, 95, 99])

alert if metric > threshold for n windows in a row        # threshold: SLO or mean + k*std of a quiet period
psi(reference, current) per feature; ks_2samp(a, b).statistic
recall on labelled rows with day <= today - label_delay
```

## Where to go next

* Course: [42 · Logging and monitoring](../notebooks/42_logging_monitoring.html),
  [43 · Drift, degradation and model updates](../notebooks/43_drift_and_updates.html),
  [44 · Project milestone 3](../notebooks/44_project_m3_monitoring.html).
* Handbook: [15. Logging, monitoring and updates](../handbook/ch15_logging_monitoring_updates/index.md), with
  sections on service logs and metrics, input drift, drift vs degradation with delayed labels, and updates.
* Python documentation: the *Logging HOWTO* and *Logging Cookbook*.
* For production tools: the documentation of CloudWatch (AWS), Prometheus and Grafana, and the Google SRE book's
  chapter on monitoring distributed systems (free online).
