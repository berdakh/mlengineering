# W7D2 assessment

Answer in writing before opening `solutions/lessons/w7d2_input_monitoring_drift/assessment_answers.md`.

## Reasoning questions

1. A colleague computes W1 as `np.mean(np.abs(np.sort(ref) - np.sort(cur)))`. When is this correct, and
   what does it do with a 60-row window against a 9,000-row reference?
2. Why are rows with `flow_rate = -9999` excluded from the drift statistics instead of being "the
   biggest drift of all"? What would the dashboard show if they were included?
3. The KS test on one-minute windows of a 1 Hz pump sensor gives p < 0.05 in most windows of a week with
   no known change. Give the mechanism and what you would use instead.
4. Explain why "PSI > 0.1" has a different false-alarm rate for 60-sample and 480-sample windows.
5. In the real replay, reference A raised no alert on any of the 24 anomalous `valve1` test windows, but
   alerted on every normal window of the two `other` test runs. Explain both observations with the
   calibration data used.
6. The monitor alerts on `price` for a week after a planned price change. Is the model's accuracy worse?
   What would you need to know?

## Design-choice explanation (150-250 words)

For `flowguard` in production (one model, a fleet of pumps with different set-points), choose a
reference for input monitoring, a window length, a statistic and a target false-alarm rate. Say what an
alert will mean to the reliability engineer and what it will not mean.

## Rubric (open-ended answers)

| Criterion | Does not meet | Meets | Exceeds |
|---|---|---|---|
| Statistics | Confuses statistic with p-value; wrong for unequal sizes | Correct definitions; units of W1; role of the PSI floor | Uses invariances (KS monotone, W1 shift) to argue for a choice |
| Calibration | Uses a rule of thumb | Thresholds from stable data with a multiple-testing correction, rate measured on held-out data | Discusses autocorrelation, few windows, and reference choice in the calibration data |
| Separation of concerns | Treats violations, missingness and drift as one alarm | Three separate signals with owners | Adds quarantine or rejection policy for violations |
| Drift vs performance | Treats drift as degradation | States drift is evidence of change, not of lower accuracy | Uses the real replay to show a drift monitor missing faults and alerting on normal new conditions |

## Interview rep (15 minutes, ML fundamentals: two-sample tests)

Answer aloud or in writing without notes, then compare with the answers file.

1. Define the two-sample KS statistic. What is its null distribution based on, and which assumption fails
   for sensor time series?
2. You have 10 million rows in each of two months. A KS test gives p < 1e-50 for a feature. What do you
   report to the product team instead?
3. Sketch a classifier two-sample test. What does an AUC of 0.5 mean, and what does 0.65 mean?
4. Why can monitoring each feature separately miss a change that matters?
