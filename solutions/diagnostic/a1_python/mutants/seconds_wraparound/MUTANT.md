Fixes everything except `timedelta.seconds` (kept instead of `total_seconds()`): gaps longer than a day
wrap around and events on different days merge into one session. Plausible because same-day tests pass.
