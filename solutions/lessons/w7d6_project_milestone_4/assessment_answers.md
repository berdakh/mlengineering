# W7D6 assessment: model answers

## 1. False alarms implied by the threshold

If the 27 development windows and a new healthy window are exchangeable (drawn from the same population
of healthy experiments), each of the 28 is equally likely to be the largest. A new healthy window therefore
exceeds the maximum of the other 27 with probability 1/28, about 3.6 % per window. If that is too many:
use a higher quantile with more calibration windows (split experiments into shorter windows, accepting
their autocorrelation); require persistence (two consecutive windows above); or, better here, change what
is monitored so that healthy machines are not far from the reference (per-machine references, normalised
values). Raising the threshold by hand without data is not calibration.

*Common wrong answer.* "Max means no false alarms." It means no false alarms *on the calibration set*.
Figure 2 shows a healthy test experiment at 7.38 against 7.53.

## 2. Units bug: which alert

`out_of_support` names the cause (values outside the physical range seen in development: 560 of 560) and
is specific: drift fires for any distribution change, including legitimate ones (E3). The alarm rate does
not change because the burn-in z-score is scale invariant: multiplying values and burn-in by 60 leaves every
score unchanged (w7d5).

## 3. The missed fault

Only labels reveal it: the inspection of `valve1/8` weeks later (E6 counts it as a missed fault). No
proxy fired because, to the detector, the fault looks like normal operation (alarm share 0.0009, PSI 4.04,
in support). The report lists it as "not detected" because the purpose of the demo is to show what the
monitoring can and cannot see; dropping it would turn a known limitation into a hidden one.

## 4. "Rollback = edit CURRENT"

* The running process still serves the bad model → restart, then `GET /version`.
* The old process may still be running beside the new one → stop it; check `pgrep`/the pid list.
* The new process may not be ready (bundle missing, checksum) → wait for `/readyz` 200 before routing traffic.
* Other instances may not have been restarted → check `/version` on each.
* The rollback target may be wrong (rolled back twice, or to a version that was never good) → read
  `HISTORY.jsonl` and state the target explicitly.

## 5. Recall from 2 faults

1 of 2 detected: a 95 % Wilson interval is roughly 0.09 to 0.91 (w3d5), so it is almost uninformative.
"Labelled traffic only" warns of verification bias: inspections are not random. Machines with alarms are
more likely to be inspected, so detected faults get labels faster than missed ones, and recall measured on
labelled traffic is biased upward (w7d3).

## Interview rep: model answer (5 minutes) and follow-ups

**Structure.** Separate what I can see *now* from what I can see *when labels arrive*.

*Now, without labels:*
1. Service health: readiness, error and degraded rates, latency, shed rate. A broken model often shows up
   here first.
2. Inputs: schema violations (rejected at the edge), values outside the training support (counted), drift
   against a reference calibrated on healthy data. These say the model is being asked about
   something new, not that it is wrong.
3. Outputs: alarm rate per machine against the budget the business accepted. A jump right after a release
   points to the release. On a single machine it is more likely a real fault or a sensor.

*When labels arrive:* event recall, false alarm events per hour and detection delay on inspected
machines, with intervals. Account for verification bias: inspected machines are not a random sample.

*Process:* every signal has an alert with a runbook entry, a scripted replay proves each alert fires,
and releases are reversible: rollback by restart, confirmed with `/version`.

*Honest limits:* some failures look like normal operation to every proxy (our E5). Only labels catch those,
weeks later. In this project the drift monitor has a thin margin (a healthy experiment at 7.38 against a
threshold of 7.53).

**Follow-ups an interviewer may ask**
1. Your drift alert fires; what do you do? (Check for an intended operating change; look at alarms on that
   machine; do not retrain on reflex.)
2. How did you choose the alarm-rate budget? (From the alert budget the stakeholder accepted, 1 false alarm
   per 8 h, measured on development data.)
3. Why not monitor accuracy directly with a sample of labelled data? (Cost and delay. Do it, but randomise
   which machines are inspected to avoid verification bias.)
4. What if drift and alarm rate both fire after a release? (Roll back first, then investigate.)
5. How do you avoid alert fatigue? (Calibrate on healthy data, require persistence, route by severity, delete
   alerts nobody acts on.)

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Separates proxies from labelled performance | no | implicitly | explicitly, with the delay |
| Concrete signals with thresholds and their origin | none | named only | named with how they are calibrated |
| Drift vs degradation | conflated | mentioned | explained with an example |
| Labels: coverage and bias | ignored | coverage mentioned | verification bias explained |
| Operability (alerts, runbook, rollback verified) | absent | partial | complete and tested |

8-10 strong; 5-7 adequate; below 5: reread section 2 and the runbook.
