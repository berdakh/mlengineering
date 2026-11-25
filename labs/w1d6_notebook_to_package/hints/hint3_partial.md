# Hint 3 (partial implementation)

Opening this hint means the unit is recorded as *guided*. The reference solution is still more complete.

## Shape of `load_experiment`

```python
RAW_TO_CANONICAL = {
    "datetime": "datetime",
    "Accelerometer1RMS": "accelerometer1_rms",
    # ... six more sensors ...
    "Volume Flow RateRMS": "flow_rate",
    "anomaly": "anomaly",
    "changepoint": "changepoint",
}
LABEL_COLUMNS = ("anomaly", "changepoint")


def load_experiment(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"experiment file not found: {path}")
    df = pd.read_csv(path, sep=";")
    required = [raw for raw, name in RAW_TO_CANONICAL.items() if name not in LABEL_COLUMNS]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")
    df = df.rename(columns=RAW_TO_CANONICAL)
    for label in LABEL_COLUMNS:
        ...            # absent in the fault-free file: decide, fill, cast to int
    ...                # parse datetime, sort by it, reset the index
    return df[[...]]   # canonical order
```

`load_raw` iterates `sorted(raw_dir.glob("*/*.csv"))`, calls `load_experiment`, and adds
`experiment_id`, `family` and `t` **per file, before concatenating**. That placement is what makes
the three per-experiment properties true by construction.

## One hostile test, complete

```python
def test_ids_come_from_file_names_not_positions(tmp_path):
    root = tmp_path / "skab"
    write_experiment(root / "valve1" / "0.csv", n_rows=20, start="2020-03-09 10:00:00")
    write_experiment(root / "valve1" / "2.csv", n_rows=22, start="2020-03-09 11:00:00")
    write_experiment(root / "valve1" / "10.csv", n_rows=30, start="2020-03-09 12:00:00")
    sizes = load_raw(root).groupby("experiment_id").size().to_dict()
    assert sizes == {"valve1/0": 20, "valve1/2": 22, "valve1/10": 30}
```

`write_experiment` is yours to write: a frame with a `datetime` column from `pd.date_range`, the
eight raw sensor names, optional label columns, saved with `sep=";"`.

## Challenge: the core three lines

```python
ordered = tidy.sort_values(["experiment_id", "datetime"])
previous = ordered.groupby("experiment_id")["datetime"].shift(1)
seconds = (ordered["datetime"] - previous).dt.total_seconds()
```

What remains is the strict comparison, assembling the result columns, the empty case and the CLI.
