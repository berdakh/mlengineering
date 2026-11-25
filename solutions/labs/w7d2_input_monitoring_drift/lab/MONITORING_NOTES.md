# Monitoring notes (w7d2, task 4) — reference answer

1. Table (reference run, 2026-11-22):

   | | A global, calibration (in-sample) | A global, test | B per run, test |
   |---|---|---|---|
   | normal windows | 107 | 38 | 38 |
   | alert rate, normal | 0.0 | 0.211 | 0.026 |
   | anomalous windows | 0 | 35 | 35 |
   | alert rate, anomalous | - | 0.143 | 0.200 |
   | normal, other family | 0.0 | 1.000 | 0.125 |

2. **A.** 0 % in-sample, because with 107 windows and a per-sensor level of 1 - 0.05/8 the threshold is
   essentially the largest value seen. 21 % on test: all 8 false alarms are the 8 normal windows of
   `other/1` (temperature) and `other/14` (accelerometer 1). Their normal operation sits just outside
   every development burn-in. The calibration data did not contain these operating conditions, so the
   monitor correctly reports "new conditions"; it is the wrong alarm if the question is "fault?".
3. **B.** 1 false alarm in 38 normal windows (`other/14`, voltage, ratio 1.07). Comparing each run with
   its own first five minutes removes set-point differences between runs.
4. **Faults.** A flags 5 of 35 fully anomalous windows, B 7. No `valve1` fault window alerts under A,
   one under B. The w4d5 detector catches 5 of 7 test faults. A calibrated drift monitor tolerates
   between-run variation, which is larger than a closing valve's effect on one-minute distributions of
   most sensors. Drift monitoring is not a fault detector.
5. 38 + 35 windows from 7 runs, strongly dependent within a run: these rates have wide intervals; only
   the qualitative conclusions (A is noisy across operating conditions; neither catches most faults)
   should be relied on.
6. Deploy **both, for different purposes**: B (per machine) as an input-change monitor whose alert means
   "this pump's inputs changed during the run: check the sensor or the process"; A as a slower,
   daily "outside the model's development domain" report whose alert means "this machine runs in
   conditions the model was not validated on", not a page. Fault detection remains the detector's job.
