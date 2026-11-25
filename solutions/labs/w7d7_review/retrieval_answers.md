# w7d7 retrieval sheet: model answers

Open only after all twelve answers have an attempt. Score each answer **solid** (the core point and the
mechanism, numbers approximately right), **shaky** (the core point without the mechanism, or a wrong
number that changes a conclusion) or **missing**. Each answer lists the common wrong answers and why they
fail. Numbers come from the Week 7 lessons' authoring runs (2026-11-22); real SKAB results use the frozen
v2 manifest (7 test, 27 development experiments).

---

## 1. Metrics, logs, traces; request ids; the crash path (w7d1)

* **Metrics** answer "is the service healthy, is it getting worse?": pre-aggregated counts, sums,
  buckets, current values; cost grows with the number of label combinations (series), not with traffic.
  Alerts are written on them. **Logs** answer "what happened to this request / machine / version?": one
  structured event per thing that happened; cost grows with traffic. **Traces** follow one request across
  several services; `flowguard` is one process, so it stops at a correlation id (`X-Request-ID`).
* **Never count log lines for an error rate**: access logs are often sampled at high traffic (say 1 in 100
  for 2xx), a refactor can change a log level or message, and counting is slow. Counters are exact.
* **Never a request id as a label**: each distinct value is a new time series stored forever (cardinality).
  Labels must come from small fixed sets (route template, status, method, model version). Unknown paths
  are labelled `unmatched`, so a scanner hitting random URLs does not create a series per path.
* **Crash path**: in Starlette the `Exception` handler lives in `ServerErrorMiddleware`, *outside* your
  middleware, so when the handler raises, `call_next` raises instead of returning a 500 response.
  Bookkeeping written only after `call_next` gives three symptoms: no access-log line for the crashed
  request, no 500 in the request counter, and an in-flight gauge that leaks one unit per crash. Fix: one
  `try/finally` around `call_next` (count, observe latency, decrement in-flight, write the access line),
  then let the exception propagate. 422 and 404 do come back as responses, because their handlers are in
  the inner `ExceptionMiddleware`.

Common wrong answers. "Logs and metrics are interchangeable" (they answer different questions at different
cost). "Add the request id as a label so you can drill down" (that is what logs are for). "Wrap `call_next`
in `try/except` and return a 500 yourself" (works, but duplicates the outer handler and is not what the lab
asks; the essential point is that bookkeeping must run on the exception path).

## 2. Buckets, percentiles, error budgets, the replay (w7d1)

* `x_bucket{le="0.05"} 38`: 38 observations were **less than or equal to** 0.05 s. Buckets are
  cumulative, so the series never decreases; the mandatory `le="+Inf"` bucket equals `_count`.
* Worked example (SYNTHETIC; instance A 9,000 requests around 20 ms, B 1,000 around 300 ms): mean of the
  two p99s **528.9 ms** (not a percentile of anything), true p99 of all 10,000 **587.9 ms**, estimate from
  summed buckets **721.9 ms** (in the right 500-1,000 ms bucket, interpolated high because interpolation
  assumes a uniform spread inside the bucket). The share slower than 250 ms (6.7 %) was exact because
  250 ms is a bucket edge: put edges at SLO thresholds. Percentiles cannot be averaged; bucket counts can be
  summed.
* Error budget: `(1 - 0.995) x 1,728,000 = 8,640` bad requests per 30 days. Burn rate = observed bad
  fraction / (1 - target); 1 spends exactly the budget over the window; 14.4 for one hour spends 2 % of a
  30-day budget (14.4 / 720). Multi-window: page only when a long window (enough evidence) **and** a short
  window (still happening) both burn fast. On the synthetic month, a 3-hour partial outage paged for 168
  minutes, a 4-minute total outage did not page, and the month ended with 42 % of the budget spent.
* Replay: `in_flight` was 1 because the scrape itself is a request in flight while the registry renders.
  `flowguard_predicted_samples_total` counts samples **processed**, and the plant client re-sent the run so
  far every 60 samples, so the same seconds were scored repeatedly: 2,624 "exceeding" are not 2,624
  distinct anomalous seconds.

Common wrong answers. "Each bucket counts observations in its interval" (that is the per-bucket view, not
what `/metrics` serves). "Average the instances' p99s" (meaningless). "Page when the 5-minute error rate
exceeds the SLO" (pages on every blip). "`in_flight` should be 0, so something leaks" (not here: the scrape).

## 3. Three questions; KS, W1, PSI (w7d2)

* **Schema violation** (a `-9999` sentinel, an infinity, a physically impossible value): a broken input;
  owner the data producer; counted, rejected or quarantined, and **kept out** of the statistics, because one
  sentinel moves a Wasserstein distance by hundreds of units and hides what the other rows do.
  **Missingness** (NaN): a sensor or pipeline failure; reported as a share per sensor, not as drift.
  **Distribution shift** of values that pass both checks: evidence that something changed, not that the
  model got worse.
* **KS**: `D = sup |F_R(x) - F_C(x)|`, unitless, invariant to monotone transforms, most sensitive to
  location shifts near the middle. **Wasserstein-1**: `∫ |F_R - F_C| dx`, in the sensor's own units; a
  pure shift by δ gives exactly `|δ|`, which makes thresholds explainable. **PSI**: bins at the
  reference's deciles, shares p and q floored at ε = 1e-4, `Σ (q - p) ln(q / p)`, the symmetric
  (Jeffreys) divergence `KL(q||p) + KL(p||q)`.
* Floor: a window whose values all lie above the reference maximum leaves nine empty bins, where `ln(0)`
  is `-inf`. Dropping those terms with `nansum` removes exactly the bins that carry the evidence of drift
  (the lab's `psi_without_floor` mutant).

Common wrong answers. "Treat NaN as drift" or "include violations and let the statistic catch them"
(mixes owners and hides real shifts). "KS is in the sensor's units" (W1 is). "PSI is a test with a known
false-alarm rate" (it is a description; the rate comes from calibration).

## 4. Why p-values and PSI folklore fail; calibration; the real replay (w7d2)

* KS with no drift, share of windows with p < 0.05 (reference 2,000, windows of 240, AR(1) data):
  **5.5 %** at φ = 0, **21.8 %** at 0.5, **75.0 %** at 0.9, **98.5 %** at 0.98. The test assumes
  independent observations; autocorrelated windows hold far fewer independent pieces of information, so
  the test is overconfident. Large samples have the opposite problem: **p = 3.1e-8** for a W1 of
  0.011 °C between two 200,000-sample sets, a difference below any thermometer's resolution.
* PSI under no drift grows like `(k - 1)(1/n + 1/m)`, so its false-alarm rate depends on window size: with
  i.i.d. data and a 5,000-sample reference, **98.2 %** of 30-sample windows exceed 0.1 and **0.0 %** of
  1,440-sample windows.
* Calibration: replay windows you consider stable, set each sensor's threshold at the quantile giving the
  false-alarm rate you can afford, and report the rate measured on held-out stable windows. With m sensors
  alerting on "any", split α across them (Bonferroni, α/m each): on the lab's 4-sensor synthetic data,
  **2.75 %** of held-out stable windows alerted with the correction and **13 %** without.
* Real SKAB, one-minute windows of the 7 test runs: reference **A** (pooled development burn-ins) alerted
  on **21 %** of normal windows (8 of 8 in the two `other` runs, whose temperature or vibration lies slightly
  outside anything in development) and **14 %** of fully anomalous windows (5 of 35); reference **B** (each
  run's own burn-in) on **3 %** of normal (1 of 38) and **20 %** of anomalous (7 of 35). The w4d5 detector
  catches 5 of 7 test faults. A calibrated drift monitor tolerates the variation between experiments, and a
  closing valve is smaller than that variation in most sensors' one-minute windows: drift monitoring does
  not replace fault detection. Counts are small (38 and 35 windows from 7 runs); the conclusion does not
  depend on the second decimal.

Common wrong answers. "Use a smaller α" (does not fix dependence). "0.25 is the industry standard" (a
convention whose meaning depends on n and m). "Calibrated to 5 % means 5 % in production" (the in-sample
rate was 0 % and the test runs gave 21 % under A; report held-out rates).

## 5. Kinds of shift; drift without degradation and the reverse (w7d3)

* **Covariate shift**: P(x) changes, P(y | x) does not (a recalibrated sensor). **Prior shift**: P(y)
  changes, P(x | y) does not (more faults this season; precision at a fixed threshold moves). **Concept
  shift**: P(y | x) changes (a new fault mechanism, a new definition of "fault"); input statistics may not
  move at all.
* Period B (flow sensor 1.08x + 2.5): PSI of **6.1-8.9** in every window, 9-13 times its threshold of
  **0.660**, and the detector caught **the same 11 of 20** faults as in period A. Reason: the burn-in
  z-score `|x - mean| / sd` is invariant to `a x + b` with a > 0. Drift without degradation.
* Period C (a release that doubled the threshold, 14.49 instead of 7.24): recall fell from **11/20 to
  4/20**, inputs identical to period A, so the drift monitor said exactly what it said for A. Degradation
  without drift.
* 198 samples scored **exactly** at the threshold (the flow sensor is quantised and the w4d5 operating
  point was chosen from score quantiles), so a 1e-14 rounding from the recalibration flipped their flags
  and changed one alarm's extent, not which faults were caught. Put thresholds between distinct score
  values.

Common wrong answers. "A large drift means the model is broken" (period B). "No drift means the model is
fine" (period C). "Covariate shift never harms a model" (it harms one that extrapolates badly; this
detector is invariant by construction).

## 6. Biased labels, as-of evaluation, power (w7d3)

* **Precision from investigated alarms** estimates P(y = 1 | investigated), not P(y = 1 | alarm). When
  investigation follows the score and P(fault | score) rises with the score, it is biased upward. With a
  random or known investigation probability the bias vanishes or can be corrected (inverse-probability
  weighting).
* **Recall from reported misses**: `C / (C + M_reported)` with `E[M_reported] = ρ M`; for ρ < 1 it
  overestimates recall, so it is an upper bound, and early in the label delay it is more optimistic still.
* **As-of rule**: a metric "as of day d" uses only labels with `label_time <= d`. Without it, a back-test
  sees the future.
* Power: Wilson 95 % half-width about `1.96 sqrt(r (1 - r) / n)`; at r = 0.6, about **±0.20 at 20 faults**
  and **±0.10 only at about 89**. A window needs enough labelled events, not enough samples.
* Period C (truth 4/20 = 0.20): **unknown** on day 65 (no missed-fault report yet), **0.67** on day 90,
  **0.36 [0.15, 0.65]** on day 150, so the rule said "inconclusive", because the interval overlaps the
  baseline 0.61. Period B showed the opposite failure: an early, optimistic "yes" (0.85 on day 65).
* Fraud worked example (SYNTHETIC): when half the fraud started scoring like legitimate traffic, recall
  halved (0.55 → 0.27), the PSI of the score distribution stayed at 0.001, recall estimated a week later
  said 1.00, and **precision of the reviewed alerts** (0.29 → 0.13) moved within a week. It worked because
  the number of alerts was fixed by design (a top-40 budget). With a fixed **threshold**, the same shift
  shows up as fewer alerts, not lower precision.

Common wrong answers. "Reviewer confirm rate is the model's accuracy." "Wait for enough samples" (events
are the unit). "Inconclusive means no degradation" (it means the data cannot tell yet).

## 7. The gate (w7d4)

* Superiority: promote if `L > 0`. Non-inferiority with margin δ: promote if `L > -δ`. Otherwise reject.
* Pairing: `Var(ā - b̄) = Var(ā) + Var(b̄) - 2 Cov(ā, b̄)`; when difficulty is shared across models the
  covariance is large and the interval shrinks. Worked example (SYNTHETIC, 40 stores): paired
  **[+0.046, +0.133]**, unpaired **[-0.029, +0.208]** for the same difference.
* Real gate on the 7 test experiments: 1.1.0 (re-tuned to 1 false alarm per hour) recall 0.714 → 0.857,
  difference **+0.143 [+0.000, +0.429]**: **promote** under non-inferiority, **reject** under superiority.
  The lower end is exactly 0 because 1.1.0 catches one more fault (valve1/8) and misses none, so no
  resample can be negative; with 7 experiments a one-fault improvement cannot be demonstrated. Promoting is
  a decision to accept the stakeholder's new alert budget, and the audit log says so.
* 2.0.0: (1) **worse**: recall 0.714 → 0.143, difference -0.571 [-0.857, -0.143], and slice regressions
  (other 0.00 against 1.00, valve1 0.25 against 0.75), although on development data it looked marginally
  better (12/27 against 11/27); (2) **incompatible**: it needs `accelerometer1_rms` and
  `accelerometer2_rms`, which the serving contract does not carry, so `promote` refused it before anything
  moved.
* Versioned together: model parameters, threshold and post-processing, input schema, preprocessing. A
  threshold changed outside the bundle is an unversioned model.

Common wrong answers. "The gate passed, so it is better" (non-inferior is not better). "Compare the two
models' separate intervals" (unpaired, much wider). "Promote 2.0.0, it was better on development data."

## 8. Shadow, canary, rollback (w7d4)

* **Shadow**: the candidate scores real inputs, its outputs are logged, never served. It measures
  operational behaviour (errors, latency, alert volume, disagreements) on real traffic without risk. It
  does not measure performance: without labels, disagreement is not error.
* Real shadow run (20 valve recordings): 1.1.0 differed in 15 of 20 runs and raised 4 alarms 1.0.0 did
  not (afterwards all 4 were on real faults; 15 of 20 faults caught against 11), served responses
  identical to current. Two coverage problems: all 5 of 1.1.0's development false alarms occurred in the
  `other` family, which this shadow traffic never contained; and 16 of the 20 recordings were development
  data that 1.1.0 was tuned on. A shadow period must cover the slices where the candidate behaves
  differently.
* **Canary**: a fraction f of traffic for time T at event rate λ sees about `f λ T` events; for a fault
  detector that may be zero faults, so a canary bounds frequent guardrails (errors, latency, alert rate) far
  better than recall. Each look at accumulating data is another test.
* Guardrail evidence: 0 false alarms in **1.22** normal test hours gives an exact Poisson 95 % upper bound
  of about **2.5 per hour**, above the budget of 1 per hour; on development data 1.1.0 raised 5 in 5.0 h,
  exactly the budget it was tuned to. The test set cannot confirm the guardrail.
* Reload endpoint: token from `FLOWGUARD_ADMIN_TOKEN` read at request time from the environment (never a
  file in the repository), compared with `hmac.compare_digest`; unset → 403, wrong token → 401.
  Rollback = registry pointer to the previous version + reload; the API's response for valve1/8 after
  promote → reload → rollback → reload was identical to the original, and the audit log reads
  `promote None→1.0.0`, `promote 1.0.0→1.1.0`, `rollback 1.1.0→1.0.0`.

Common wrong answers. "Shadow proves the candidate is better." "A one-week canary at 10 % will measure
recall." "Rollback means retraining the old model."

## 9. Three failure kinds; units bug; liveness versus readiness; fallback (w7d5)

| Kind | flowguard example | Caller should see |
|---|---|---|
| Down | bundle missing, checksum mismatch | `/readyz` 503, `/healthz` 200, fallback answers flagged `degraded` |
| Slow | model call stuck behind a starved CPU | a deadline answer flagged `degraded`; `429` + `Retry-After` when too much work is in flight |
| Silently wrong | NaN scores; flow sent in L/h instead of L/min | `degraded` (NaN) or the values listed in `out_of_support` (units) |

* Units bug: the burn-in z-score is invariant to scaling the input, so ×60 gives **exactly the same 313
  alarms** on valve1/13; only the support guard, comparing raw values with the range seen in development
  data, noticed it (**1,140 of 1,140** values out of support).
* Corrupt bundle: `/healthz` 200 (the process can answer; a restart would reload the same bad bundle, and a
  liveness probe that checks the model turns one bad artifact into a crash loop), `/readyz` 503 (do not send
  traffic; a rollout gate stops).
* Test set: model **5 of 7** faults, fallback envelope rule **2 of 7**, neither with false alarm events. The
  fallback is a safety net with a known cost; a consumer who knows an answer is degraded can treat a quiet
  stretch as "unknown" rather than "healthy".

Common wrong answers. "Return 500 on any model problem" (hides the difference between a bug and a known
degraded mode; clients retry 500s). "Clip out-of-range values" (turns an extrapolation into a confident
answer about a different input). "Liveness should check the model."

## 10. Retries, jitter, deadlines, bulkheads (w7d5)

* Retry: connection refused, read timeout, `429` and `503` (after `Retry-After`), `502`, `504`. Never:
  `400`, `404`, `409`, `413`, `422` (the same request fails the same way). `500`: not here (may be a
  deterministic bug).
* Full jitter: delay before retry k uniform in `[0, min(cap, base · 2^k)]`. `Retry-After` from the server
  wins, capped at the client's maximum delay. Attempts are bounded; extra load is at most
  `max_attempts - 1` times the original, and only while failures last. Side-effecting requests need an
  idempotency key reused across attempts.
* Retry storm (SYNTHETIC; 200 clients, 2 s outage, capacity 20 per 100 ms, 10 attempts, base 0.1 s, cap
  6.4 s): immediate retries **2,000 requests, 0 served**, all 200 gave up; exponential without jitter
  **1,800 requests, 100 served, 100 gave up**, with all 200 clients arriving in the same 100 ms bucket (10
  times capacity) at each step; full jitter **1,385 requests, all 200 served by 8.05 s**, never more than
  **17** per bucket after recovery.
* A deadline frees the **caller**; the model call keeps running in its worker thread (Python cannot kill a
  thread). So the bulkhead slot is released in the future's **completion callback**, not when the answer is
  sent; the check: with `max_inflight = 1`, a 0.8 s model and a 0.1 s deadline, the second request is shed
  with 429 until the first call ends.
* Little's law `L = λ W`: at 20 requests/s, 50 ms gives L = 1; 1 s gives **L = 20**. A bulkhead of 4 sheds
  beyond 4 concurrent calls, and the shed rate becomes an alertable signal of the slowdown.

Common wrong answers. "Retry everything, three times" (multiplies a persistent failure). "Exponential
backoff is enough" (deterministic schedules re-synchronise clients). "The deadline cancels the work."

## 11. The eight events (w7d6)

| Event | Problem | Expected signal |
|---|---|---|
| E1-normal | none | none (an alarm is a false alarm) |
| E2-units-bug | client sends L/h (×60) | `out_of_support` |
| E3-input-drift | pump at 80 % flow | `drift` |
| E4-fault | real valve fault (valve1/13) | `detector` |
| E5-fault | real valve fault the model is known to miss (valve1/8) | `detector` |
| E6-labels | inspection results arrive | `delayed_eval` |
| E7-bad-promotion | threshold typed as 1.5 | `alarm_rate` |
| E8-rollback | recovery | `version_restored` |

* E2: the z-score is scale invariant (w7d5), so the detector cannot see the bug; only raw values against
  the development support can (560 out-of-support values, all from E2; drift also fired). E3: 80 % flow is in
  range (no support alert) and the burn-in adapts (no alarms); only the raw-value distribution moves.
* E5: no signal fired; the report lists it as **not detected (expected detector)**. 7 of 8 events went as
  expected. Hiding a miss is worse than having one: the report is evidence only if it shows failures too.
* Event recall 0.5 from 2 labelled faults (1 detected) says almost nothing about the true rate: with n = 2
  any interval is nearly [0, 1].

Common wrong answers. "The demo should be all green." "Drift should catch the units bug, so the support
guard is redundant" (here both fired, but a units bug inside the drift threshold would only be caught by
support). "E5 is a bug in the demo."

## 12. Calibration margin; the planted problems; rollback is a process event (w7d6)

* Drift threshold = the **largest** PSI among the normal rows of the **27 development experiments**,
  **7.5253** (calibration values 3.26 to 7.53). With 27 exchangeable healthy windows, a new healthy window
  exceeds the maximum with probability about **1/28**. The healthy part of test experiment `other/1`
  reached **7.38**, within 2 % of alerting; the 80 % flow replay reached 9.62. The margin is thin because
  SKAB experiments run at different, nearly constant flow levels; per-machine references or monitoring
  normalised values would be better, and the runbook's limitations must say so.
* Three planted problems and the reviewer's question that finds each: (1) **rollback without restart**:
  "does the version column follow the registry history?" (the rollback row showed the wrong version,
  because the old process kept serving); (2) **a hand-typed number in the report**: "is every number in the
  report in `results.json`?" (a module constant instead of `results["summary"]`); (3) **a server left
  running**: "did every process the demo started stop?" (`pgrep -af flowguard.api` should print nothing).
* A running process loaded its bundle at startup. Changing the pointer changes nothing until the process is
  replaced: stop the old service, start a new one from the registry path, wait for `/readyz`, and confirm
  `GET /version` returns the restored version. Only then is it a rollback.

Common wrong answers. "Set the threshold at the 95th percentile of 27 values" (that is essentially the
second-largest value; say what false-alarm rate it implies). "The pointer file is the source of truth for
what is serving" (`/version` is). "The report can be edited after the run to fix a typo" (then it is no
longer generated evidence).
