# Hint 3 — partial implementation (challenge)

Using this hint means the unit is recorded as guided, not independent.

`src/pumpwatch/__main__.py`:

```python
import sys

from pumpwatch.cli import main

sys.exit(main())
```

Parser fragment:

```python
train = sub.add_parser("train", help="train and print test metrics as JSON")
source = train.add_mutually_exclusive_group(required=True)
source.add_argument("--data", help="raw window CSV")
source.add_argument("--features", help="feature CSV written by `pumpwatch features`")
```

`main` skeleton — the body of `_run` and the two I/O functions are yours:

```python
def _run(args) -> int:
    if args.command == "features":
        ...  # load raw -> build table -> save; return 0
    ...      # train: pick the source, then train_and_evaluate; print JSON; return 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _run(args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
```

Loader skeleton:

```python
def load_features(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(...)
    features = pd.read_csv(path)
    missing = [c for c in FEATURE_TABLE_COLUMNS if c not in features.columns]
    ...  # what should happen here, and which exception type keeps main() simple?
```

Still stuck? The full solution is in
`solutions/lessons/w1d3_package_structure/challenge/`. Read it, close it, and redo the
challenge from an empty directory tomorrow.
