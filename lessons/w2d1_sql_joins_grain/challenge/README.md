# W2D1 independent challenge — five questions, grain first

**Conditions:** 40 minutes, no hints, no solutions, same database (`../data/maintenance.db`, SYNTHETIC).
Record in `progress/notes.md` how long you took and whether you opened a hint; set the `independent`
flag only if you did not.

Write one query per file in `challenge/queries/`. Each file already states the question and the
required column names. Before writing SQL, replace two header lines:

```sql
-- grain: one row per <what a row of YOUR result represents, and which entities are included>
-- key: <comma-separated column names forming the MINIMAL key of the result>
```

| File | Question |
|---|---|
| `c1_site_type_costs.sql` | Per site and work-order type: number of work orders and their total parts cost |
| `c2_machine_parts.sql` | For every machine: number of distinct parts ever used on it and total quantity |
| `c3_technician_load.sql` | For every technician: orders assigned, recorded labour hours, distinct machines serviced |
| `c4_site_scorecard.sql` | For every site: machines, downtime hours, labour hours, parts cost |
| `c5_parts_never_corrective.sql` | Parts never used on a corrective work order |

The exact wording, including which entities must appear with zeros, is in each file's header.

## Acceptance criteria

1. Each file contains a single `SELECT` (CTEs allowed) returning exactly the required columns.
2. Results are correct on the committed database **and** on a re-seeded database you have not seen.
3. The declared key is unique in the result on both databases and is minimal (no measures in it).
4. "Every …" means every row of that table appears, with 0 (not NULL) where there is nothing to count or sum.
5. For `c4`, you can state three reconciliation checks your result satisfies, and you have run them.

```bash
python wb.py check w2d1 --challenge
```

## Deliverable

The five query files, plus three or four sentences in `progress/notes.md`: which question had a trap
you did not see at first, and which invariant exposed it.

## Optional extension

Run your queries on a second engine and look for differences (DuckDB is not a course dependency):

```bash
python -m pip install duckdb
python lessons/w2d1_sql_joins_grain/example/run_on_duckdb.py lessons/w2d1_sql_joins_grain/challenge/queries
```
