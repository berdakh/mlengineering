# Forecast-residual detectors on SKAB — notes (w4d1)

Fill in after running `python labs/w4d1_timeseries_fundamentals/lab/forecast_vs_z.py`.

## Burn-in autocorrelation (paste section 1 of the output)

## AR order chosen on development data (paste section 2)

## Test table (paste section 3)

## Answers (3-5 sentences each)

1. Why does the naive residual score near the no-skill floor on SKAB, when it detects every step
   change instantly? Refer to how SKAB faults look over time.
2. The AR(2) residual and the flow-rate z-score: what can you claim about their difference from this
   table, and what can you not?
3. Adding CUSUM lowered PR-AUC but cut false alarms per hour by a factor of about 70. When is that the
   better detector? Name what you would need from the stakeholder to decide.
4. The AR forecaster is fitted on 100 burn-in rows per sensor. Name two ways this fit could be wrong
   for a given experiment, and what each would do to the scores.
