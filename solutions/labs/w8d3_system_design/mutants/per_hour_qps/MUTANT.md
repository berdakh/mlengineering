# per_hour_qps
Divides by seconds per hour instead of seconds per day: a classic unit slip that inflates peak QPS 24x.
Caught by: test_peak_qps_matches_definition, test_peak_qps_known_value.
