# Hint 3 — partial implementation

Skeletons with the aggregations and conditions left out. They show shape, not answers.

## Two children under one parent (q3; the pattern for c4)

```sql
WITH wo AS (
    SELECT machine_id, /* aggregates of work_orders */ 
    FROM work_orders
    GROUP BY machine_id
),
dt AS (
    SELECT machine_id, /* aggregate of downtime_events */
    FROM downtime_events
    GROUP BY machine_id
)
SELECT m.machine_id, /* COALESCE each measure */
FROM machines AS m
LEFT JOIN wo ON wo.machine_id = m.machine_id
LEFT JOIN dt ON dt.machine_id = m.machine_id;
```

For `c4` the result grain is the site, so each CTE must be grouped by `site_id`. A child table that has
no `site_id` gets it by joining *up* to `machines` inside the CTE (many-to-one, no duplication).
Parts cost needs two upward steps: part line → work order → machine.

## Parent measure plus child measure (q7; the pattern for c1)

```sql
WITH wo_parts AS (                       -- one row per work order that used parts
    SELECT pu.wo_id, /* cost */ AS parts_cost
    FROM parts_used AS pu JOIN parts AS p ON p.part_id = pu.part_id
    GROUP BY pu.wo_id
)
SELECT /* grouping columns */, COUNT(w.wo_id), SUM(w.labor_hours), SUM(wp.parts_cost)
FROM /* driving table and joins down to work_orders: which join type keeps every site? */
LEFT JOIN wo_parts AS wp ON wp.wo_id = w.wo_id
GROUP BY /* ... */;
```

After the join to `wo_parts` each work order still appears once, so `COUNT` and `SUM(labor_hours)` are safe.

## Filter that must not remove left rows (q4)

```sql
FROM sites AS s
LEFT JOIN machines AS m    ON m.site_id = s.site_id
LEFT JOIN work_orders AS w ON w.machine_id = m.machine_id
                          AND /* conditions on w go HERE */
GROUP BY s.site_id
```

Count a column of `w` that is never NULL in the base table, not `*`.

## Anti-join with a condition (q2, c5)

```sql
SELECT p.part_id, p.part_name
FROM parts AS p
WHERE NOT EXISTS (
    SELECT 1
    FROM parts_used AS pu
    JOIN /* the table that knows the order type */ 
    WHERE pu.part_id = p.part_id
      AND /* the condition that defines a disqualifying use */
);
```

## Distinct across a path (c2)

`COUNT(DISTINCT pu.part_id)` over the rows of one machine counts each part once however many orders
used it; `SUM(pu.quantity)` over the same rows is safe because every part line appears exactly once on
the path machine → work order → part line (a chain, not two sibling branches).
