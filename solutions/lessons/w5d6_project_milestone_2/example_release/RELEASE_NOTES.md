# flowguard 0.6.0 — release candidate (milestone 2)

**What it is.** The detector chosen in milestone 1 (burn-in flow-rate |z|, threshold 7.244 chosen on
development experiments for one false alarm per 8 h), packaged once and used by three paths: the
evaluation report, batch inference (`flowguard predict-batch`) and an HTTP API (`flowguard-api/1`).
Educational prototype; no claim about any real plant.

**Artifact.** `models/current/` built by `make model` from `configs/model.toml` and the frozen manifest
`splits/v2.json` (sha256 `a9f4e243...5314`, the same manifest as the milestone-1 report). The bundle
records the config, its hash, the manifest hash and a hash of the 27 development experiments' data.

**Evidence.**
* Three-way parity on every row of all 35 experiments (46,806 rows): maximum absolute difference 0.0
  between evaluation and batch, and between evaluation and the API ([parity.json](parity.json)).
* Version agreement: package, bundle and `/version` all report 0.6.0; model `flowrate-z-2026.11`.
* Test split, point level after the 100 burn-in rows (`flowguard evaluate --split test`): 686 rows
  flagged, 671 of them anomalous (precision 0.98); 671 of 2,487 anomalous rows flagged (recall 0.27).
  Event level, unchanged from milestone 1: 5 of 7 faults detected, 0 false alarms, median delay 100 s.
* `make test`: 10 tests (unit, bundle integration, API, parity) pass.

**Changes since 0.5.0.** Fixed a training/serving skew: the API computed the burn-in standard
deviation with ddof=1, evaluation with ddof=0 (about 0.5 % smaller API scores at 100 burn-in rows;
see the lesson's parity figure). Version single-sourced. Long recordings are scored through the API in
chunks of at most 3,600 values, each chunk with the same burn-in.

**Known limitations.** Seven independent test experiments; one laboratory testbed; point-level recall
is low by design of the alert budget; the API scores whatever burn-in it is given and cannot check that
the burn-in really was normal operation. Latency under load is not measured yet (w6d4).
