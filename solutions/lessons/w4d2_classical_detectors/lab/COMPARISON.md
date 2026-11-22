# Classical detectors on SKAB — comparison (w4d2) — REFERENCE

Tables: see the lesson README, section 4, Task 5 (identical output from the reference run).

## Recommendation

The labels support a supervised model for the valve families, where many labelled experiments exist:
on the frozen test set the GBT has the best point estimate (0.920) and about a quarter of the other
detectors' false alarms per hour at its development threshold. They do not support it beyond those
families: trained without `other`, the GBT drops to 0.636 on that family, no better than one sensor's
z-score, while the isolation forest (0.783) and PCA T² (0.761) keep their level. I would deploy the GBT
with the isolation forest as a second, independent score for faults outside the labelled mechanisms,
and report protocol B next to protocol A with their intervals (7 and 8 independent units, so neither
ranking is established). Before any of this reaches an operator, the operating point must be set from
an alarm budget: every detector here raises tens to hundreds of false alarms per hour at a best-F1 threshold.
