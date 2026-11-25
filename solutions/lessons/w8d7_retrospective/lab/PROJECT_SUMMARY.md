# flowguard - one-page summary (reference EXAMPLE)

**What it is.** An educational fault detector for a laboratory water-pump testbed (SKAB: 34 recorded
experiments, eight sensors at one hertz), delivered as a tested service. Not validated on a real plant.

**Problem.** Alert a reliability engineer soon after abnormal operation begins, with few false alarms.
Scored as events: faults caught, detection delay, false alarms per hour.

**What made it hard.** Thirty-four independent experiments; rows duplicated across files with
contradictory labels; a protocol leak (fault onsets near the same row) that lets a clock "detector"
score well.

**What was done.** Split by experiment keeping duplicated files together; past-only features; every
choice made on 27 development experiments, one look at 7 test experiments. Compared baselines,
multivariate detectors, boosted trees and a neural autoencoder; chose a single-sensor burn-in z-score
because no alternative was shown better within its interval at a pre-set minimum difference, and it is
the cheapest to run and explain. Built one inference object for evaluation, batch and API; a
versioned artifact without pickle; a FastAPI service with explicit failure modes; a container; CI; a
gated AWS deployment path; monitoring that separates input validity, drift and degradation; rollback.

**Results.** Test: 5 of 7 faults caught with no false-alarm events (event recall interval roughly
0.36 to 0.92). Serving parity exact over 46,806 rows. Monitoring demo: 7 of 8 scripted events
detected, the miss reported.

**Limitations.** Laboratory data with induced faults; seven test experiments; contradictory labels;
the drift monitor does not detect faults; the fallback rule catches 2 of 7.
