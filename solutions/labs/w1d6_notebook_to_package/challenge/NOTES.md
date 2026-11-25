# NOTES: where `flowguard` v0.1 disagrees with the notebook, and why

All numbers below come from runs on the real SKAB files (commit `b2c0d46`, fetched by
`project/get_skab.py`) in the authoring session of 2026-11-21. "Notebook" means
`explore_skab.py` run top to bottom.

## Discrepancies

| # | Quantity | Notebook | Package | Mechanism | Which is right |
|---|---|---|---|---|---|
| 1 | Rows after loading | 37,401 | 46,806 | `all_df.dropna()` in the "clean up" cell. The fault-free file has no label columns, so its labels are NaN after `concat` and all 9,405 of its rows are dropped. | Package. 46,806 = 37,401 labelled + 9,405 fault-free. The notebook's own first shape print, `(46806, 13)`, agrees. |
| 2 | Number of experiments | 34 | 35 | Same cause: `anomaly-free/anomaly-free` vanished. | Package. |
| 3 | Experiment identities | `other/0` ... `other/13`, `valve1/0` ... `valve1/15` | `other/1` ... `other/14`, `valve1/0` ... `valve1/15` | Ids built from `enumerate(sorted(glob(...)))`. Lexicographic order is `1, 10, 11, 12, 13, 14, 2, ...`, so position and file name disagree for **28 of 34** labelled files (all 14 in `other/`, 14 of 16 in `valve1/`; `valve2/` has four files and is unaffected). | Package: id = folder name + file stem. |
| 4 | "other/2": rows, longest interval | 1,190 rows, 2.0 s | 780 rows, 247 s | Consequence of 3: the notebook's `other/2` is really `other/11.csv`. The cell meant to inspect "the one with the long gap" inspected a different recording and reported no gap. | Package. |
| 5 | Intervals longer than 5 s | 19 | 9, in 6 experiments | `datetime.diff()` over the whole table after a global sort: intervals *between* recordings are counted, and several within-experiment intervals are distorted by interleaving. `max dt 1887107` s (21.8 days) is the distance between two recording days. | Package (see the challenge solution's `find_gaps`). |
| 6 | `t` | global row number | 0-based index within each experiment | `sort_values("datetime").reset_index()` then `t = index`. | Package: a rolling window indexed by `t` must not span two recordings. |
| 7 | Overall anomaly fraction | 0.349 | 0.279 over all rows; 0.349 over labelled experiments | Not a bug in the arithmetic: the notebook's denominator silently excluded the fault-free recording (1). Both numbers are legitimate if the denominator is stated. | State the denominator. Per family (labelled): other 0.351, valve1 0.347, valve2 0.352, same as the notebook. |
| 8 | Median max-abs z-score, normal vs anomalous samples | 85.64 vs 86.52 | 57.48 vs 58.70 against the fault-free recording | The notebook computed mean and standard deviation from `df`, which at that point holds one labelled experiment (its `other/2`, really `other/11`, anomalous segment included), not "normal" data. | Neither is useful; see "Things found" below. |

The notebook assigns column names by position (`df.columns = NEW_NAMES`). On today's files this
gives the same result as renaming by name, so it produces no discrepancy. It is still replaced:
it would silently swap sensors if a file's column order changed.

## Labelling decision

The fault-free file has no `anomaly`/`changepoint` columns. `load_experiment` fills both with 0.
That is a statement about the data ("this recording is labelled normal by construction"), taken from
the upstream description of the file, not something the file itself says. It is revisited in w2d4.

## Things found once the loading was right

These are observations for w2d3 (data quality) and w2d4 (splits), not fixed here.

1. **Recordings overlap in wall-clock time, and the overlapping rows are duplicates.** 1,290 rows
   (timestamp plus all eight sensor values identical) appear in two different files:

   | Pair | Shared rows | Labels in first / second | Rows where the labels disagree |
   |---|---|---|---|
   | `anomaly-free` and `other/5` | 572 | all 0 / all 0 | 0 |
   | `other/10` and `other/11` | 21 | all 0 / all 0 | 0 |
   | `other/12` and `other/13` | 349 | 51 % anomalous / all 0 | 178 |
   | `other/2` and `other/3` | 120 | all 0 / all 0 | 0 |
   | `other/3` and `other/4` | 228 | 25 % anomalous / all 0 | 57 |

   Consequences: a global sort by `datetime` interleaves two experiments (discrepancy 6); the same
   physical samples can land in both training and test sets unless overlapping files are kept on the
   same side of a split; and 235 samples carry two contradictory labels. There are no duplicated
   timestamps *within* an experiment.
2. **Six experiments contain sampling gaps longer than 5 s** (nine gaps; longest 247 s in `other/2`):
   `other/13` (four gaps: 33, 19, 21, 16 s), `other/2`, `valve1/2` (76 s), `valve1/4` (54 s),
   `valve1/7` (65 s), `valve2/1` (64 s). Five further intervals are exactly 5 s long (three in
   `other/12`, two in `other/13`), so the count becomes 14 if the comparison is `>=` instead of `>`.
3. **A global z-score against the fault-free recording does not separate the classes.** Median
   max-abs z is 1.52 inside the fault-free recording, 57.48 for *normal* samples of the labelled
   experiments and 58.70 for anomalous ones. The labelled experiments' normal operating point is far
   from the fault-free recording's (different sessions), which swamps the fault effect. This is the
   between-session shift seen in any sensor recorded over several sessions, and it means "fit on the fault-free file, threshold the
   distance" cannot be assumed to work; w2d6 tests it properly.
4. The upstream folder listing numbers `valve1` files from 1; the files are numbered from 0. `other/`
   is numbered from 1.

## Commit history of the reference (what the learner's should resemble)

```
Add notebook export as received
Add package skeleton and .gitignore
Add load_experiment with tests
Add load_raw with tests
Add summarize and the summary command
Record notebook discrepancies in NOTES.md
Add README stub
Add commit self-review
```

The reference solution directory is a snapshot, not a Git repository, so this list is the intended
sequence rather than recorded history.

## Challenge addition: sampling gaps (`find_gaps`, `flowguard gaps`)

Real data, threshold 5 s (strict): **9 gaps in 6 experiments, longest 247 s** (`other/2`, after row 103).
The notebook's 19 was wrong twice over: it differenced timestamps across the whole table, so
boundaries between recordings counted as gaps; and it did so after `dropna()` and a global sort, on
a table missing one recording and with overlapping recordings interleaved. With threshold 2 s the
package reports 70 intervals.

First three rows of `flowguard gaps --raw-dir data/raw/skab`:

```
{'experiment_id': 'other/13', 't': 515, 'gap_start': '2020-02-08 18:57:52', 'gap_end': '2020-02-08 18:58:25', 'gap_seconds': 33.0}
{'experiment_id': 'other/13', 't': 750, 'gap_start': '2020-02-08 19:02:32', 'gap_end': '2020-02-08 19:02:51', 'gap_seconds': 19.0}
{'experiment_id': 'other/13', 't': 754, 'gap_start': '2020-02-08 19:02:54', 'gap_end': '2020-02-08 19:03:15', 'gap_seconds': 21.0}
```

Answer to the optional extension question: see "Things found", item 1. The two recordings that
appear to overlap at 18:10-18:11 are `other/10` and `other/11`; they share 21 identical rows.
