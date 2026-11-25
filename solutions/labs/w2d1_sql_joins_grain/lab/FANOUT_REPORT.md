# Fan-out bug report: "Maintenance cost by site" tile

Reference answer. Numbers were measured on `data/maintenance.db` (SYNTHETIC).

reported_total_labor_hours: 838.8
true_total_labor_hours: 633.8
work_orders_missing_from_broken_query: 36

## 1. Symptom (what the tile shows versus an independent total)

Summing the tile over sites gives 838.8 labour hours, while `SELECT SUM(labor_hours) FROM work_orders`
gives 633.8: the tile is 32 % too high in total. The tile also reports 121 "work orders" although the
table holds 93, shows only 5 of the 6 sites, and for site 2 it is too LOW (80.7 against 95.5 true hours).
One query therefore over-counts and under-counts at the same time. The parts-cost column is correct
(71,388.73 in both), which is why the tile looked plausible for so long.

## 2. Mechanism (grain of each table in the join, and where the row count changes)

`work_orders` has one row per work order; `parts_used` has one row per (work order, part). After
`JOIN parts_used` the intermediate result has one row per part line, so a work order with k part lines
appears k times and its `labor_hours` is added k times. `COUNT(w.wo_id)` counts those part lines (121 =
number of rows in `parts_used`), not orders. Independently, the INNER join removes the 36 work orders
that used no parts, together with their labour hours, and the inner join to `machines` removes the site
that has no machines. Parts cost is right because part lines are exactly the grain at which cost is
defined; labour is wrong because it is defined at a coarser grain than the rows being summed.

## 3. Evidence (the smallest query or example that proves the mechanism)

`SELECT w.wo_id, w.labor_hours, COUNT(*) FROM work_orders w JOIN parts_used pu USING (wo_id) GROUP BY
w.wo_id HAVING COUNT(*) > 1` lists the duplicated orders; work order 1 has six part lines and would be
counted six times. `SELECT COUNT(*) FROM work_orders w WHERE NOT EXISTS (SELECT 1 FROM parts_used pu WHERE
pu.wo_id = w.wo_id)` returns 36, the dropped orders. Row counts along the join chain: 93 work orders
before the join to `parts_used`, 121 rows after it.

## 4. Fix, and the invariant that would have caught it

Aggregate `parts_used` to one row per work order in a CTE, then LEFT JOIN it, and LEFT JOIN from `sites`
downward so that nothing disappears. Invariants to assert whenever the query changes: the result has one
row per site (6); the sum of `n_work_orders` equals `COUNT(*)` of `work_orders` (93); the sum of
`labor_hours` equals `SUM(labor_hours)` of `work_orders` (633.8); the sum of `parts_cost` equals the total
computed from `parts_used` alone (71,388.73).
