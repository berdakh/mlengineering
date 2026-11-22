# Seasonal forecast from the following week

Uses the same weekday one period AHEAD (x[t+7]) when it exists, the way a centred smoother would.
Offline it looks excellent; at prediction time next week's sales do not exist.
