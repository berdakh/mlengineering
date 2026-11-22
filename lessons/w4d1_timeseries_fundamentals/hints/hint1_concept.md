# Hint 1 — concept

**Lab.** Every function in `forecast.py` answers one question: "what would I have expected at row `i`,
knowing only rows before `i`?" Write that down for each forecaster as an index expression before
coding. For AR(p), the row of the design matrix that predicts `x_t` contains `1, x_{t-1}, ..., x_{t-p}`
— the value being predicted is never in its own row. `sigma_` is the spread of the one-step
*residuals* on the fit data.

**Challenge.** Think about what a promotion week does to the forecasts made *from* it. A seasonal-naive
forecaster predicts next Tuesday from this Tuesday; an AR forecaster with lag 1 predicts tomorrow from
today. For each one, sketch the residual on day 1 of a 5-day promotion, on day 3, and on the same
weekdays one week later. Which direction is each residual? Then ask which of those you want to alarm on.
