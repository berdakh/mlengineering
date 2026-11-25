# Monitoring notes (w7d2, task 4)

Write these after running `python labs/w7d2_input_monitoring_drift/lab/replay_drift.py`.

1. Paste the table the script printed.
2. Reference A: what was the false-alarm rate in-sample (calibration) and on the test runs? Where did the
   test false alarms come from, and why did calibration not anticipate them?
3. Reference B: same questions.
4. Of the fully anomalous test windows, how many raised a drift alert under A and B? Compare with the
   w4d5 detector (5 of 7 test faults). What does this say about using a drift monitor as a fault detector?
5. How many windows are these rates based on, and how much would you trust the second decimal?
6. Which reference would you deploy for `flowguard`, for what purpose, and what would its alerts mean?
