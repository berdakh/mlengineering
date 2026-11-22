# Forecast-residual detectors on SKAB — notes (w4d1) — REFERENCE

Numbers from the authoring run (reference implementation, frozen v2 manifest, 2,000 bootstrap replicates).

## Burn-in autocorrelation

```
accelerometer1_rms   r1 = +0.08   r10 = +0.04   (n = 27)
accelerometer2_rms   r1 = +0.09   r10 = +0.02   (n = 27)
current              r1 = +0.33   r10 = +0.18   (n = 27)
pressure             r1 = +0.02   r10 = +0.03   (n = 27)
temperature          r1 = +0.70   r10 = +0.48   (n = 27)
thermocouple         r1 = +0.89   r10 = +0.55   (n = 27)
voltage              r1 = +0.03   r10 = +0.05   (n = 27)
flow_rate            r1 = -0.09   r10 = +0.02   (n = 27)
```

## AR order

p = 1: 0.763, p = 2: 0.777, p = 3: 0.775, p = 5: 0.763 (development PR-AUC); chosen p = 2. The
differences between orders are small relative to anything the 27 development experiments can resolve;
p = 2 is a reasonable default, not a discovery.

## Test table

| detector | test PR-AUC [95% CI] | events detected | false alarms / h | median delay (s) |
|---|---|---|---|---|
| flow_rate abs z, burn-in (w2d6) | 0.884 [0.811, 0.928] | 7/7 | 238.6 | 4 |
| max abs z over sensors, burn-in | 0.746 [0.576, 0.855] | 6/7 | 178.5 | 5 |
| naive residual, max over sensors | 0.401 [0.351, 0.443] | 1/7 | 5.8 | inf |
| AR(2) residual, max over sensors | 0.809 [0.664, 0.899] | 6/7 | 222.9 | 2 |
| AR(2) residual + CUSUM (k=0.5) | 0.605 [0.532, 0.693] | 4/7 | 3.3 | 111 |

## Answers

1. SKAB faults are sustained segments of several minutes. The naive residual is a first difference,
   so it responds to the change at the onset (and at the end) and then returns to noise while the
   fault persists. Point-level PR-AUC rewards scoring every anomalous row, so it ends near prevalence
   (0.401 vs 0.373). Its single event detection also shows that the onset steps are not large relative
   to the sample-to-sample noise of these sensors.
2. Point estimates: AR(2) 0.809 vs flow-rate z 0.884; the intervals overlap heavily and come from 7
   experiments. The table does not establish which is better; a paired comparison per experiment
   (w3d5) would be the right test and would still have little power. It also cannot say the AR model
   is worse "because of" the model: the flow-rate scorer is a single sensor picked in w2d6 on
   development data, whereas the AR score is a max over eight sensors.
3. When false alarms are expensive (an operator must respond, a line is stopped) and a delay of about
   two minutes is acceptable. To decide I need the alarm budget (false alarms per hour or shift that
   operators accept), the cost of a missed or late fault, and whether a slower alarm still allows
   useful action. 3.3 per hour is still too many for most control rooms; the operating point would be
   tuned further on development data against the budget.
4. (a) The burn-in is not normal for that experiment (a fault or a transient in the first 100 rows):
   the model treats the fault as normal and later normal rows look anomalous. (b) The burn-in is too
   short or unrepresentative for a persistent sensor: 100 rows of a series with r1 ~ 0.9 are worth
   about 5 independent samples, so sigma and the coefficients are noisy and limits are mis-scaled; a
   quantised sensor (flow rate) also gives a tiny or degenerate sigma, which is why scores are capped.
