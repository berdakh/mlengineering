# W7D2 challenge: expected and unexpected drift

**Data (SYNTHETIC).** `data/make_stream.py` generates a shop's session stream: 70 days x 400 sessions,
columns `day`, `price`, `basket_size` (may be missing), `session_length_s`, `page_views`. Weekends have
slightly larger baskets and longer sessions. `data/calendar.csv` is the change calendar: it lists only
PLANNED changes (one: a price increase on day 30), as a real calendar would. Other events happen in the
data and are not in the calendar; the generator's docstring describes them, but design your monitor
without relying on their days or sizes, as you would in production.

```bash
python lessons/w7d2_input_monitoring_drift/challenge/data/make_stream.py --seed 0 --out /tmp/stream.csv
```

**Task.** Implement `monitor_stream(df, calendar, reference_days=14)` in `stream_monitor.py`. It returns
alerts as dicts `{"day": int, "feature": str, "kind": ...}` with kind:

* `"unexpected"`: a distribution change that the calendar does not explain;
* `"expected"`: a change on a feature listed in the calendar, during a settling period after the
  planned day (an annotation for the dashboard, not a page);
* `"missing"`: the share of missing values of a feature on a day is too high.

Design requirements (how you meet them is up to you; justify the choices in a docstring):

* daily windows; a reference built from the first `reference_days` days;
* thresholds derived from the reference period, not from a rule of thumb;
* after a planned change, the affected feature must be monitored again later (an unplanned change to the
  same feature must still be caught); other features are unaffected by the calendar;
* missingness monitored separately from distribution shift.

## Acceptance criteria (`python wb.py check w7d2 --challenge`, seeds 0-7)

* The planned price change produces at least one `expected` annotation within 3 days, and no
  `unexpected` price alert during days 30-36.
* The unplanned events are reported: `unexpected` on the right feature within 2-3 days of their start, and
  `missing` within 2 days.
* At most 4 `unexpected` alerts per stream on feature-days where nothing changed, and no `missing` alert
  where nothing is missing.
* Deterministic output.
