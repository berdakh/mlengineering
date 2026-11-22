# Mutant: each sensor calibrated to the target rate on its own

With m sensors the chance that ANY of them alerts in a window is roughly m times the per-sensor rate. Measured on the held-out stable data: 13 % of windows instead of <= 10 %. Caught by `test_calibrated_thresholds_hold_the_false_alarm_rate_on_new_stable_data`.
