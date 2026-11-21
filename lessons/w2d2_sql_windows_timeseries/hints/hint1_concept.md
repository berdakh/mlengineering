# Hint 1 — concept

Every feature in the challenge is a function of "this device's rows up to the label time". Build
that set once per source table and everything else is ordinary aggregation or top-1-per-group.

* The label table drives the query: the result has **its** grain, one row per `label_id`. Any join
  that can produce zero matches for a label must be a `LEFT JOIN`, or the label disappears.
* The time condition belongs **in the join condition** (`ON ... AND r.ts_epoch <= l.label_ts_epoch`),
  not in a later `WHERE`. In a `LEFT JOIN`, a `WHERE` on the right-hand table removes the
  NULL-extended rows and silently turns the join into an inner join.
* Two of the five features are "the latest row at or before t" (as-of lookups), two are aggregates
  over a trailing interval, and one is an as-of lookup restricted to one kind of event. Decide the
  category of each before writing anything.
* Half-open intervals: `(t − W, t]` means `>` on the old side and `<=` on the label side. A reading
  exactly at the label time is in; the data contains such readings on purpose.

If your query passes the "matches specification" checks but fails the future-change check, some
condition is symmetric in time (an `ABS`, a `BETWEEN` around the label, a "nearest") or a join is
missing its time bound.
