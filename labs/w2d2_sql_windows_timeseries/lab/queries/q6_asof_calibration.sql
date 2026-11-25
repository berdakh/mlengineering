-- q6  As-of join to a slowly changing table
--
-- Sources: readings_dedup, calibration
-- Grain  : one row per de-duplicated reading (no reading may disappear)
-- Columns: reading_id, device_id, ts, corrected_temperature, alert_threshold_c, over_threshold
-- Rules  : the calibration row that applies to a reading is the device's row with the greatest
--          valid_from_epoch that is <= the reading's ts_epoch (valid_from is inclusive).
--          corrected_temperature = temperature + offset_c
--          over_threshold        = 1 if corrected_temperature > alert_threshold_c else 0
--          A reading taken before its device's first calibration has NULL in all three columns.

SELECT NULL AS reading_id, NULL AS device_id, NULL AS ts, NULL AS corrected_temperature,
       NULL AS alert_threshold_c, NULL AS over_threshold WHERE 0;
