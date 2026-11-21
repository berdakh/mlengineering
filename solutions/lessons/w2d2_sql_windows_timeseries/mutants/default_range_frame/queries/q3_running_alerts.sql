SELECT reading_id, device_id,
       SUM(alert) OVER (PARTITION BY device_id ORDER BY ts_epoch) AS running_alerts
FROM sensor_readings;
