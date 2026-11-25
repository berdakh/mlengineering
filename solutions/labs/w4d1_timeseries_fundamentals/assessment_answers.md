# W4D1 assessment — model answers

## Q1
The factor √30 ≈ 5.5 assumes independent samples. With lag-1 autocorrelation 0.95 the 30 values are
nearly copies of each other. For an AR(1) with φ = 0.95 the variance of a 30-sample mean is
`σ²/n² [n + 2 Σ_{k=1}^{n−1} (n−k) φ^k]` ≈ 0.64 σ², so the standard deviation drops by a factor of
about 1.25, not 5.5 (computed in the authoring session). The window is far shorter than the
decorrelation time; to reduce noise materially the window must span many decorrelation times — or the
"noise" is really slow signal and should be modelled, not averaged.

*Common incorrect answers.* "It is fine because the CLT applies" (it needs many effectively
independent terms); "the reduction is √(n_eff) with n_eff = n(1−φ)/(1+φ) ≈ 0.8" — that large-n
formula breaks down when the window is shorter than the memory; use the exact sum.

## Q2
Σφ close to 1 means the fitted process is nearly a random walk: the implied mean `c/(1−Σφ)` is poorly
determined and the forecast hardly pulls towards it. The model behaves like the naive forecaster: the
residual spikes at the fault onset and returns to noise while the fault persists, so point-level
scores during the fault are low. It also signals that 100 rows were too few, or contained a drift,
for that sensor.

## Q3
An AR(2): PACF cutting off after lag 2 with a decaying ACF is the AR(2) signature. After fitting,
check the residual ACF (inside the noise band at all small lags), that the coefficients describe a
stationary process (roots outside the unit circle; for AR(2) e.g. |φ₂| < 1, φ₁ + φ₂ < 1, φ₂ − φ₁ < 1),
and that the residual scale is stable across the fit window (no variance change).

## Q4
No. With independent residuals, ARL₀ for this chart is about 460 samples (simulated in the lesson), so
an 8-hour shift (28,800 samples) has about 60 false alarms, against a budget of 1. With positively
autocorrelated residuals it is worse: the running sums accumulate correlated noise, whose variance is
inflated (by about (1+φ)/(1−φ) = 3 for φ = 0.5 over long stretches), so `h` is crossed far more often.
Remedies: larger `h` (chosen by simulation or on development data against the budget), whitening the
residuals with a better model, or alarming on a slower time scale.

*Common incorrect answer.* "ARL₀ of a few hundred sounds large, so it is fine" — always convert run
lengths into alarms per shift at the actual sampling rate.

## Q5
When the event of interest is a *change* and the signal level itself is uninformative or wanders:
e.g. detecting step changes in a random-walk-like quantity (inventory level after a mis-scan, a
sensor recalibration, a sudden jump in a price series), or detecting onsets when another system
handles the sustained state. The naive forecast is optimal for a random walk and needs no fitting, so
it cannot be wrong about the level; it only reports changes.

## Q6
Example: after a sustained level shift, the naive forecaster's RMSE is low (it follows the new level
after one sample) while an AR model anchored to the normal mean has a persistent error. Lowest RMSE
selects the naive model, which is blind to the sustained fault (figure 2 and the SKAB table). More
generally RMSE rewards adaptation to *any* change, including the anomalies the detector should report;
detectors must be selected by detection metrics on held-out units under the deployment protocol.

## Q7 (key points for the rubric)
* **Avoids:** the reference recording is at a different operating point from most labelled
  experiments (project/README findings; w2d5/w2d6), so a global model of "normal" flags entire
  experiments, normal parts included. Burn-in normalisation conditions on each experiment's own
  operating point; it is also what was found to work in w2d5/w2d6 and keeps comparisons fair.
* **Costs:** only 100 rows per sensor (for persistent sensors that is a handful of effective samples;
  coefficients and sigma are noisy; quantised sensors give degenerate scales); assumes the first 100
  rows are normal (true in SKAB by construction, which is itself a property of the protocol, not of
  the world); the first 100 rows cannot be scored; nothing is learned across experiments.
* **Wrong when:** faults can be present at start-up (a machine restarted with a bad bearing); faults
  develop slowly from start-up so the burn-in already drifts; or the fleet runs at a few known
  operating points, where a model per operating point trained on many machines is better estimated and
  easier to validate and govern than thousands of per-run fits.

## Interview rep — what a strong answer contains
1. Random K-fold puts rows adjacent in time on both sides; with autocorrelation the held-out rows are
   predictable from their neighbours, so the estimate measures interpolation, not forecasting or
   detection on new periods. Use blocked or forward-chaining splits with a gap (purging/embargo, w3d2),
   or split by independent unit (experiment, machine).
2. Code and tests: `solutions/labs/w4d1_timeseries_fundamentals/interview_rep/` (executed: 3 tests
   pass). Unreliability for short series: each `r_k` has sd about 1/√n, and summing many lags adds
   their noise; truncating `max_lag` too early ignores long memory, too late adds noise.
