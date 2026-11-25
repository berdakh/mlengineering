# Hint 2 (approach)

* **Task 1.** Filter verdicts by `label_time <= as_of`. Split them into known alarm ids and orphans
  (`isin`). Sort the known ones by `label_time` (stable sort), `drop_duplicates("alarm_id", keep="last")`,
  then left-merge onto the alarms on `alarm_id`. Convert `verdict` with `.astype("boolean")` so pending
  rows are `<NA>`. `superseded` = known non-orphan verdicts minus the number of rows kept.
* **Task 2.** `labelled = joined["verdict"].dropna()`; k = number of True, n = len(labelled). One helper
  `_proportion(k, n, min_n, level)` that returns the status dict serves tasks 2 and 3.
* **Task 3.** Use sets of `fault_id`. Caught: from rows whose verdict is True. Missed: from reports
  known at `as_of`, minus caught. Denominator: caught + missed.
* **Task 4.** Build the window edges with a loop (`edges.append(edges[-1] + pd.Timedelta(freq))` until
  past `end`). Join once with `as_of`, filter reports once by `as_of`, then slice both by `start_time`.
  Reuse tasks 2 and 3 on each slice.
* **Task 5.** Write a helper that judges one metric against its baseline and returns one of
  `not_monitored / unknown / no / yes / inconclusive`, then combine with a fixed priority.
