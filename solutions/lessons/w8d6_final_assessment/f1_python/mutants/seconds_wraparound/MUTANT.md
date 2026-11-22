Leg hours use timedelta.seconds, which drops whole days: a 30 h leg (scans every 10 h, never idle for more than 12 h) is reported as 6 h. Grouping is correct; only the reported hours are wrong.
