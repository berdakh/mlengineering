# Five adversarial questions (reference - for the FICTIONAL example project)

## A1

Question: Fourteen patients is tiny. Why should anyone trust this?
Concede: It is small, and I would not claim a precise detection rate.
Quantify: The patient-level interval is 0.58 to 0.82, so the honest claim is "well above the line-length baseline", not "71 %".
Redirect: The design choices - leave-one-patient-out, event scoring, thresholds from training patients - are what make even a small study interpretable.

## A2

Question: Didn't the network just need more tuning?
Concede: Possibly; it got the same tuning budget as the simpler models, no more.
Quantify: Its result lay inside the logistic model's interval across patients.
Redirect: Under equal budgets the evidence did not justify its cost; with more patients I would rerun the comparison rather than tune harder now.

## A3

Question: Your labels are uncertain. Aren't your latencies meaningless?
Concede: Onsets are uncertain by several seconds, which limits latency precision.
Quantify: The tolerance window was set wider than that uncertainty, and latency is reported as a median with that caveat.

## A4

Question: Two patients produced most false detections. Did you just drop them?
Concede: They dominate the false-detection count.
Quantify: Pooled false-detection rates hide this, so I reported per-patient rates; without those two the rate falls sharply.
Redirect: I kept them in the headline numbers, because a deployed detector meets such patients too.

## A5

Question: Why is this relevant to an engineering job?
Concede: The study produced a paper, not a service.
Quantify: Its evaluation design - unit of independence, event metrics, leakage control - is exactly what my flowguard project reuses.
Redirect: flowguard then adds what the study lacked: packaging, an API, monitoring and rollback.
