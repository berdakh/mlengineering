# Hint 2 - approach (w3d4)

**`extract_events`.** Pad the flags with a 0 on both sides, take `np.diff`, and read starts where the
difference is +1 and ends where it is -1 (in padded coordinates the end index is already exclusive).
Then walk the list once: if the gap `next.start - current.end <= merge_gap`, extend `current`;
finally keep runs with `end - start >= min_duration`.

**`point_adjust`.** For each true event, if `y_pred[start:end].any()`, set `y_pred[start:end] = 1` on
a copy. Do not modify the input.

**`match_events`.** Sort alarms by start. For each alarm find the true event whose window
`[start - early_tolerance, end)` contains the alarm's start (events do not overlap, so there is at
most one; `np.searchsorted` on event starts finds it in O(log n)). If none: false alarm. If that event
already has a hit: redundant. Otherwise: hit, and record which alarm. Return per-alarm labels and the
per-event hit index (or `None`).

**Recall and precision** are counts from that result. Decide the NaN cases from the docstring before
writing them.

**`detection_delay`.** For each true event: if no hit, `inf`. Otherwise the hit is raised at
`alarm_start + (min_duration - 1)` rows (the confirmation wait); convert that row and the event start
to seconds with `_seconds(times)` and take `max(0, raised - onset)`.

**`normal_hours`.** Sum the time differences between consecutive rows that are both outside every
true event; optionally cap each difference at `max_gap`. Divide by 3600.

**Challenge A.** Loop over the grid with `itertools.product`, call `evaluate_experiments` on the dev
data for each setting, keep a list of results, then sort by the stated keys. The Poisson upper bound
is `chi2.ppf(confidence, 2 * (n + 1)) / (2 * hours)`.
