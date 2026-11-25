# Comparison protocol: current-threshold alarm versus waveform transformer (reference)

**Unit and hold-out.** The pump is the unit: 40 pumps, 12 with a bearing failure. Before anyone trains
anything, freeze a manifest: 10 test pumps (3 with failures), chosen by a seeded draw stratified by
failure and by pump model, never moved afterwards. The remaining 30 pumps are split into 5 grouped folds
for development. Within each pump, only data before the evaluation time feeds features or
normalisation. The test pumps are scored once, after the decision rule below is signed off.

**Held equal.** Same pumps in every split for both detectors; same evaluation periods (from 30 days after
installation, so neither detector is judged on its own warm-up); same event definition (a failure is
detected if an alarm fires in the 14 days before the maintenance record, a false alarm is any other
alarm episode); same metric pair: event recall at a false-alarm budget of 1 per pump-month, and median
detection lead time. Tuning budget: the threshold rule gets its threshold and hysteresis tuned on dev
folds; the transformer gets a declared budget (e.g. 20 configurations and early stopping on dev folds).
**Not equal and stated:** the transformer sees raw waveforms the rule never sees, and has far more
capacity; its result is "this architecture with this budget", not "deep learning".

**Seeds and uncertainty.** Transformer: 5 seeds of the chosen configuration, all reported; the shipped
candidate is an average of the 5 or the median seed by dev score, decided now. Report (a) seed mean ± sd,
(b) a pump-level paired bootstrap interval for the difference in recall at the budget (3 failures in test
make this wide; say so), (c) the dev-fold nested estimate. Verdict with the Part A rule:
margin = max(2 x seed standard error, test half-width).

**Cost and operations.** Inference latency at 1 kHz on the edge gateway (p99 under 200 ms per second of
signal), model size on the gateway, retraining cadence and who owns it, GPU dependency, behaviour when a
sensor drops out, and the ability to explain an alarm to a maintenance technician.

**Decision rule (written in advance).** Switch only if the transformer is better by more than the margin
on recall at the budget, is not worse on lead time, and meets the latency and operational criteria.
"Cannot tell" means: keep the threshold alarm, run the transformer in shadow mode for six months to
collect more failures, and repeat the comparison on the new data.
