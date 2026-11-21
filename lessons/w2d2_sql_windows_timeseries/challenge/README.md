# W2D2 challenge — a point-in-time-correct feature table

**Type:** independent transfer task. No walkthrough, no starter beyond a placeholder.
**Time:** 15 minutes inside the essential path to get a first version; about 30 more to pass the checks.
**Data:** `data/coldchain.db`, SYNTHETIC (see [`../data/README.md`](../data/README.md)).

## Scenario

The operations team inspects refrigeration units. Each row of `maintenance_labels` is one
inspection: `label_ts` is the moment a prediction would have been made, and `failed` says whether
the unit failed within the following hour. You are asked for the feature table a first failure
model would be trained on. The model will run at inspection time, so a feature may use only what
was recorded at or before `label_ts` for that unit.

## Task

Write **one SQL statement** in [`features.sql`](features.sql) that returns exactly one row per
label with these columns:

| Column | Definition (all for the label's own device) |
|---|---|
| `label_id` | from `maintenance_labels` |
| `failed` | from `maintenance_labels`, unchanged |
| `last_temperature` | `temperature` of the most recent reading with `ts_epoch <= label_ts_epoch`; `NULL` if there is none |
| `mean_temp_60m` | mean `temperature` of readings with `label_ts_epoch - 3600 < ts_epoch <= label_ts_epoch`; `NULL` if there are none |
| `n_alerts_24h` | number of readings with `alert = 1` and `label_ts_epoch - 86400 < ts_epoch <= label_ts_epoch`; `0` if there are none |
| `seconds_since_fault` | `label_ts_epoch` minus the `ts_epoch` of the most recent `fault` status event at or before the label; `NULL` if there is none |
| `status_at_label` | the device status in force at `label_ts` (latest status event at or before it; log order breaks ties); `NULL` if there is none |

"Reading" means a row of the view `readings_dedup`. Status events come from `device_status_events`.

## Acceptance criteria

1. `python wb.py check w2d2 --challenge` passes. The checks require that
   - the result matches the definitions above on the shipped database and on a re-seeded one;
   - every label yields exactly one row, including a label whose device has no history at all;
   - **for every label, rewriting all readings and status events later than its `label_ts` leaves that
     label's five features unchanged.**
2. Each CTE in your query has a one-line comment stating its grain.
3. In `progress/notes.md` (`python wb.py note w2d2 "..."`), three or four sentences answering: which
   single condition in your query is responsible for point-in-time correctness of each feature, and
   how would you convince a reviewer who does not read SQL?

## Then look at what you built (5 minutes, part of the task)

Compute, for each feature, how well it separates `failed = 1` from `failed = 0` (for example the
ROC AUC of the raw feature with scikit-learn). Write down what you see and what you conclude,
keeping in mind there are 38 labels. Then change one of your windows to look one hour *past* the
label and repeat. This comparison is discussed in the assessment answers; do it before reading them.

## Out of scope

No model training, no pandas version (optional: reproduce the table with `merge_asof` and
`rolling`, and assert equality with your SQL result).
