# 5-minute walkthrough of flowguard (reference)

## Problem

A reliability engineer wants to know soon after a pump starts misbehaving, and does not want to be
woken by false alarms. I used the Skoltech Anomaly Benchmark: thirty-four laboratory experiments on
a water-circulation testbed, eight sensors at one hertz, one induced fault per experiment. The task I
framed is per-timestamp anomaly scoring from past data only, turned into alerts by a threshold, and
scored as events: was the fault caught, how late, and how many false alarms per hour of normal
running. It is an educational prototype; nothing here is validated on a real plant.

## Constraint

Three constraints shaped everything. First, there are only thirty-four labelled experiments, so the
experiment, not the sample, is the unit of evaluation, exactly as the patient is in a clinical study.
Second, the benchmark leaks its protocol: in most experiments the fault starts around the same row,
so a detector that only looks at the clock already scores well. Third, files share duplicated rows,
some with contradictory labels, so a careless split puts the same minute on both sides. On the
engineering side, the detector has to run as a small service that scores a sample in milliseconds.

## Decision

I froze a split by experiment that keeps duplicated files together, used only past data in every
feature, and made every choice on twenty-seven development experiments, leaving seven for one final
look. I compared trivial baselines, the clock, single-sensor z-scores, multivariate detectors,
gradient-boosted trees and a small neural autoencoder under one protocol. Then I chose the
burn-in flow-rate z-score: the supervised alternative was ahead on development data, but not by
enough to clear the minimum difference I had set in advance, and it costs more to run and explain.
Around it I built one inference object shared by evaluation, batch and API, a versioned artifact
without pickle, a FastAPI service, a container and monitoring.

## Evidence

On the seven test experiments the chosen detector reached PR-AUC 0.88 and caught 5 of 7 faults with
no false-alarm events; the event recall interval is wide, 0.36 to 0.92, because seven is small.
Its development PR-AUC was 0.76 [0.68, 0.84]. The neural model averaged 0.75 over five seeds with a
standard deviation of 0.07. Boosted trees looked best on test but fell to 0.64 on an unseen fault
family. Serving parity was exact over 46,806 rows, and the monitoring demo detected seven of eight
scripted events and reported the one miss. The clock baseline stays in every table as a reminder:
on this benchmark, a number only means something next to what the experimental protocol alone
would give, and next to its interval.

## Next step

More independent experiments before more modelling, resolving the contradictory labels with the
people who ran the testbed, and a pilot on real equipment with delayed labels joined back to logged
predictions. If a future model is promoted, it goes through the offline gate, shadow mode and a
one-step rollback that I have already exercised.
