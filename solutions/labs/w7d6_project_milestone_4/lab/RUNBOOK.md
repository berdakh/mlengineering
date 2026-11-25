# flowguard runbook

Owner: the flowguard maintainer (this repository). Audience: whoever is on call for the plant monitoring
stack. Educational prototype: no real plant depends on it.

## Service overview

* **What it does.** Scores the flow-rate sensor of each pump in windows sent by the plant gateway and
  returns per-sample alarms. An alarm *event* (at least 30 consecutive alarming samples) is a suspected
  fault for the reliability engineer, not an automatic action.
* **Model.** Burn-in z-score of `flow_rate`, threshold 7.2441 (alert budget 1 false alarm per 8 h on
  development data). On the 7 frozen test experiments it detected 5 faults; it misses some valve faults
  (for example `valve1/8`).
* **Fallback.** When the model cannot answer, an envelope rule (27.94 to 128.69 L/min) answers with
  `degraded: true`. It detected 2 of 7 test faults: treat degraded periods as *unknown*, not healthy.
* **Endpoints.** `/predict`, `/healthz` (liveness), `/readyz` (readiness: 503 without a model), `/version`,
  `/metrics`.
* **Artifacts.** Registry at `reports/registry/` in the demo (`CURRENT` + immutable versions +
  `HISTORY.jsonl`). The service serves `<registry>/<CURRENT>`, read at startup only.

## Dashboards and queries

| Question | Query |
|---|---|
| Is it up and which model? | `curl -s 127.0.0.1:8000/readyz; curl -s 127.0.0.1:8000/version` |
| Counters | `curl -s 127.0.0.1:8000/metrics` (`flowguard_degraded_total`, `flowguard_out_of_support_total`, `flowguard_shed_total`, `flowguard_alarm_values_total`, `flowguard_values_scored_total`) |
| What happened to request X? | `grep '"request_id": "X"' reports/service.log` |
| Degraded answers by reason | `grep '"event": "degraded"' reports/service.log \| grep -o '"reason": "[a-z_]*"' \| sort \| uniq -c` |
| Alarm share per machine | `grep '"event": "predict"' reports/service.log` (fields `machine_id`, `values`, `alarms`) |
| Registry state | `PYTHONPATH=src python -m flowguard registry show --root reports/registry` |

## Alerts

### ServiceNotReady

**Meaning:** no model is loaded on this instance; it answers only with the fallback and the load balancer
should not route to it. Usually a missing or modified bundle after a promotion.
**First actions:** 1) `curl /readyz` and read `reason`; 2) check `HISTORY.jsonl` for a promotion in the
last hour; if there is one, roll back (see Rollback) and restart; 3) if no promotion, verify the bundle
checksums (`python -c "from flowguard.bundle import load_bundle; load_bundle('<dir>')"`).
**Escalate:** if not ready after a rollback and restart, page the maintainer (SEV1).

### ModelDegraded

**Meaning:** the model failed for some requests (`model_error`, `invalid_scores`, `deadline`) and the
fallback answered. Detection quality is reduced (2 of 7 instead of 5 of 7 test faults).
**First actions:** 1) count reasons with the query above; 2) `deadline` → check CPU and threads (w6d4:
thread oversubscription) and the shed counter; 3) `model_error`/`invalid_scores` → find the first
`model_error` log event, note the error type, roll back if it started with a promotion.
**Escalate:** if degraded share stays above 1 % for 30 min, page the maintainer (SEV2) and tell the
reliability engineer that monitoring is degraded.

### InputOutOfSupport

**Meaning:** values outside the range seen in development data (0.56 to 133.69 L/min). Scores for them are
extrapolation. The z-score is scale invariant, so a units error does **not** change alarms. This alert
is the only signal for it.
**First actions:** 1) find the machine in `predict` log events with `out_of_support > 0`; 2) compare raw
values with the expected L/min range (×60 suggests L/h, ÷60 suggests L/s); 3) contact the gateway owner;
do not retrain on these values.
**Escalate:** gateway team the same day (SEV2); the maintainer if a whole site is affected.

### InputDrift

**Meaning:** a machine's flow-rate distribution differs from the development reference more than any
development experiment did. It is a change in inputs, not a measured loss of performance. The
threshold is the largest PSI on 27 development experiments, so expect occasional alerts on genuinely
new but healthy regimes.
**First actions:** 1) check whether the machine's operating point changed on purpose (maintenance log);
2) check alarms on that machine: the burn-in normalisation adapts to level changes, so drift alone
does not mean wrong alarms; 3) record it for the next labelled evaluation (w7d3).
**Escalate:** ticket for the maintainer (SEV3); review at the weekly model meeting.

### AlarmRateHigh

**Meaning:** more alarming samples than the budget allows on a machine without an open maintenance
ticket. Either a real fault, or a model or configuration error. After a promotion, assume the latter.
**First actions:** 1) check `HISTORY.jsonl`: a promotion in the last day makes a bad model the prime
suspect: roll back, restart, confirm `/version` and the alarm share; 2) if no promotion, inform the
reliability engineer (it may be a real fault) and check `FaultDetected` events on the same machine.
**Escalate:** maintainer (SEV2) when a rollback was needed; include the version pair in the incident note.

### FaultDetected

**Meaning:** the product working as intended: an alarm event on a machine. Not an operational problem
with the service.
**First actions:** 1) forward machine id, event start and duration to the reliability engineer; 2) do not
silence it from the service side; 3) record the outcome when the inspection result arrives (these are the
delayed labels).
**Escalate:** to the plant, not to engineering, unless many machines alarm at once (then suspect
`AlarmRateHigh`).

## Common incidents

| Symptom | Likely cause | Fix |
|---|---|---|
| Alarms everywhere right after a release | bad threshold or wrong model promoted | roll back, restart, verify `/version` |
| Degraded `deadline` answers, shed counter rising | CPU starvation or thread oversubscription | limit BLAS/OpenMP threads to 1 per worker (w6d4), restart |
| Out-of-support on one machine only | gateway unit conversion | fix at the gateway; keep the guard |
| Not ready after deploy | bundle missing or checksum mismatch | roll back to the previous version |

## Rollback

```bash
PYTHONPATH=src python -m flowguard registry show --root reports/registry
PYTHONPATH=src python -m flowguard registry rollback --root reports/registry --reason "<why>"
# restart the service (the running process still serves the old version), then:
curl -s 127.0.0.1:8000/version            # model_version must be the previous one
curl -s 127.0.0.1:8000/readyz             # 200
```

The demo performs exactly this at event `E8-rollback`. A rollback is complete only after the restart and
the `/version` check.

## Escalation

1. On call (first responder): follows the alert sections above.
2. Maintainer: model, bundle and service changes; owns rollbacks after the first one.
3. Reliability engineer: decides what an alarm means for the plant; supplies delayed labels.

## Known limitations

* One process, one machine: no failover; a crash means no answers until restart.
* Drift monitoring compares whole-replay distributions with a pooled reference; SKAB experiments differ
  so much from one another that single healthy experiments already reach PSI 3.3 to 7.5. It is a coarse
  signal.
* The delayed-label estimate covers only labelled traffic (3 replays, 2 faults in the demo): an event
  recall of 0.5 from 2 faults says almost nothing about the true rate.
* The fallback is much weaker than the model (2 of 7 test faults against 5 of 7).
* No authentication; bind to 127.0.0.1 only.
