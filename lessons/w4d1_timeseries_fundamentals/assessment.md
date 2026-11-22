# W4D1 assessment

Write answers before opening `solutions/lessons/w4d1_timeseries_fundamentals/assessment_answers.md`.
Two to five sentences each unless stated.

## Reasoning questions

**Q1.** A sensor's ACF is 0.95 at lag 1 and still 0.6 at lag 30. A colleague computes a 30-sample
rolling mean and says "averaging 30 samples cuts the noise by a factor of about 5.5". What is wrong,
and roughly how much does the rolling mean actually reduce the noise of the level estimate?

**Q2.** You fit an AR(3) on the first 100 rows of each SKAB experiment. On one experiment the fitted
coefficients sum to 0.99. What does that do to the residual score during a sustained fault, and why?

**Q3.** The PACF of a burn-in series is large at lags 1 and 2 and inside the `±2/√n` band after that;
the ACF decays slowly. Which model do you fit, and what would you check after fitting?

**Q4.** Two-sided CUSUM with `k = 0.5`, `h = 5` on standardised residuals at 1 Hz. The plant's alarm
budget is one false alarm per 8-hour shift. Is this chart within budget if the residuals are truly
independent? What if they have lag-1 autocorrelation 0.5? Give a qualitative answer for the second.

**Q5.** In the lab the naive residual scored near the no-skill floor on SKAB. Describe a monitoring
problem where it would be the *right* choice, and say why.

**Q6.** A team evaluates a forecasting-based detector by its forecast RMSE on held-out data and picks
the model with the lowest RMSE. Give a concrete way this choice can select the worse detector.

## Design-choice explanation

**Q7.** (8-10 sentences.) The lab fits every forecaster on the first 100 rows of *each* experiment
(burn-in), rather than once on the fault-free reference recording or on pooled normal rows of the
development experiments. Defend this choice, name what it costs, and describe a situation in a real
plant where it would be the wrong choice.

## Rubric (Q7 and open answers)

| Level | Description |
|---|---|
| Strong | Names the specific failure the choice avoids (the reference recording sits far from the operating point of most experiments, so a global model flags whole experiments); names the costs (100 rows per sensor is little data, especially for persistent sensors; assumes the first rows are normal; no learning across experiments); gives a realistic counter-case (a fault present at start-up, a sensor that only drifts slowly, or a fleet where one global model is cheaper to validate and govern). |
| Adequate | Correct direction with one of the three elements missing or vague. |
| Not yet | Restates the procedure, or argues from convenience only, or claims the choice has no cost. |

## Interview rep (10-15 minutes, ML fundamentals: time series)

Timed, no notes. Speak the explanation part aloud.

1. (Explain, 3 minutes.) Why does random K-fold cross-validation overestimate performance on a single
   long autocorrelated series, and what would you use instead?
2. (Code, 10 minutes.) Write `effective_sample_size(x, max_lag)` returning
   `n / (1 + 2 * sum_{k=1}^{max_lag} r_k)` using the sample autocorrelation, clipped to `[1, n]`.
   Write two tests: white noise gives about `n`; an AR(1) with `φ = 0.8` gives about
   `n (1 − φ)/(1 + φ)` for a long series. State one reason the estimate is unreliable for short series.

A reference implementation with tests is in `solutions/lessons/w4d1_timeseries_fundamentals/interview_rep/`.
