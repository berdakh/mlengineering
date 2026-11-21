# `coldchain.db` - SYNTHETIC cold-chain monitoring data

Six refrigeration units over three days (2026-03-01 00:00 to 2026-03-04 00:00 UTC), simulated by
`make_db.py` (seed 2202). The file is a standard SQLite database (344 kB, committed).

**What cannot be concluded from it.** It was built to contain specific traps, so nothing about real
refrigeration equipment, failure rates or feature usefulness follows from it. In particular the 38
maintenance labels were generated so that the consequence of a failure appears only *after* the
label time; any feature that predicts them well is reading the future.

```bash
python lessons/w2d2_sql_windows_timeseries/data/make_db.py            # rebuild
python lessons/w2d2_sql_windows_timeseries/data/make_db.py --check    # compare table contents with the committed file
```

`--check` compares a hash of the table contents, not file bytes (file bytes depend on the SQLite
version). Verified equal on Python 3.13.18 / SQLite 3.53.1.

## Tables

All timestamps exist twice: `ts` as text `YYYY-MM-DD HH:MM:SS` (UTC) and `ts_epoch` as Unix seconds.
Use the integer for arithmetic and ordering, the text for display.

| Table | Grain (one row per ...) | Rows | Columns |
|---|---|---|---|
| `devices` | device | 6 | `device_id` (D01-D06), `site` (north/south) |
| `sensor_readings` | transmitted reading; a measurement can be transmitted twice | 4,811 | `reading_id` (arrival order), `device_id`, `ts`, `ts_epoch`, `temperature` (deg C as reported), `alert` (0/1 firmware flag) |
| `device_status_events` | status change logged by the device | 90 | `event_id` (log order), `device_id`, `ts`, `ts_epoch`, `status` (running, idle, defrost, fault) |
| `calibration` | (device, validity start); slowly changing | 18 | `device_id`, `valid_from`, `valid_from_epoch`, `offset_c`, `alert_threshold_c` |
| `maintenance_labels` | inspection (used in the challenge) | 38 | `label_id`, `device_id`, `label_ts`, `label_ts_epoch`, `failed` (1 if the unit failed within the hour after the inspection; 15 of 38) |
| `readings_dedup` (view) | (device, timestamp): the transmission with the highest `reading_id` | 4,707 | same columns as `sensor_readings` |

## Properties built in on purpose

* **Irregular sampling.** Nominal cadence 5 minutes with +-60 s jitter, 4 % of samples lost, and
  occasional outages; the median gap is 302 s and the largest is 7,734 s in the shipped file.
* **Re-sent readings.** 103 (device, timestamp) pairs occur twice in `sensor_readings`; the later
  transmission (higher `reading_id`) is the corrected one and may differ in `temperature` and `alert`.
* **Tied status timestamps.** Every device has log lines that share a timestamp, including its last two.
  `event_id` is the only thing that orders them.
* **Calibration before data, and data before calibration.** D06's first calibration starts six hours
  after its first reading. One of D01's calibration rows starts at exactly the timestamp of a reading.
* **Boundary readings.** Each device has a reading exactly 1,800 s after another reading, and readings
  at exactly the time of two of its labels.
* **Post-label signal.** After a failing inspection the temperature rises for an hour and a `fault`
  status is logged 5-20 minutes later.
