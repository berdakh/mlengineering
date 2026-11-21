# Hint 2 (approach): an order of work and the hostile cases

Opening this hint means the unit is recorded as *guided*.

## Commit plan that works

1. `Add notebook export as received` (the `.py` and its captured output under `notes/`).
2. `Add package skeleton and .gitignore` (`pyproject.toml`, `src/flowguard/__init__.py`, empty test).
3. `Add load_experiment with tests` - new code, no notebook behaviour involved yet.
4. `Add load_raw with tests`.
5. `Add summarize and the summary command`.
6. `Record notebook discrepancies in NOTES.md`.
7. `Add README stub`, then `Add commit self-review`.

Because the package is new code rather than edited notebook code, the "behaviour change" here shows
up as *disagreement with the recorded notebook output*, and `NOTES.md` is where each disagreement is
attributed. If instead you edit the notebook in place first (also legitimate), then each fix to the
notebook is its own commit, as in the worked example.

## The four hostile fixtures

Build these as tiny files in `tmp_path` (semicolon-separated, raw SKAB column names):

| Fixture | Catches |
|---|---|
| a family folder containing `0.csv`, `2.csv`, `10.csv` with **different row counts** | ids taken from sort position (`0, 10, 2` is the lexicographic order) |
| a file **without** `anomaly` and `changepoint` columns | rows lost to `dropna()`; labels left as NaN or float |
| a file whose rows are **shuffled** | missing sort; `t` not a time index |
| a file whose columns are in a **different order** | renaming by position |

Assert on exact row counts per `experiment_id`, on `t == 0..n-1` within each experiment, and on a
sensor value landing in the right column (give each synthetic sensor a distinct mean).

## Design decisions to make deliberately

* `experiment_id` = parent folder name + `/` + file stem. Nothing else.
* Rename with a mapping (`df.rename(columns=...)`) and check that required names are present; raise `ValueError` listing what is missing.
* The fault-free file has no labels: fill `0` and say so in the docstring. That is a labelling decision, so it also belongs in `NOTES.md`.
* Sort and index **within** each experiment; never sort the combined table by `datetime` alone.
* The CLI prints only JSON to stdout. Catch `FileNotFoundError` and `ValueError` at the entry point, print one line to stderr, return 2.

## For the challenge

`groupby("experiment_id")["datetime"].diff()` or `.shift(1)`. The first row of each experiment then
has no predecessor (NaN), and a comparison of NaN with a threshold is False, which is what you want.
Test the threshold with an interval exactly equal to it.
