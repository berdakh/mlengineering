# AR fitted without an intercept

Regresses x_t on its lags only. Works for zero-mean simulations and silently biases the coefficients
(towards a unit root) for any series with a non-zero level, which is every real sensor.
