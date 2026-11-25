# Hint 2 — suggested approach (challenge)

Work in this order, running the command by hand after each step.

1. **`__main__.py`.** Add `src/pumpwatch/__main__.py`. It needs three lines: import
   `main` from the CLI module and exit with its return value. Check with
   `python -m pumpwatch --version`.
2. **I/O functions** in `io.py`:
   - `save_features(features, path) -> Path`: create `path.parent` (`parents=True,
     exist_ok=True`), then `to_csv(..., index=False)`.
   - `load_features(path) -> DataFrame`: same shape as `load_windows` — existence check,
     read, required-column check raising `ValueError`.
3. **Parser.** Add a `features` subparser (`--data`, `--out`, `--fs`). In the `train`
   subparser replace the required `--data` with a *mutually exclusive group* that is
   itself required, holding `--data` and `--features`.
4. **Dispatch.** Put the work in one function that takes the parsed arguments and
   returns an exit code, and wrap the *single call to it* in the `try/except` that maps
   `FileNotFoundError` / `ValueError` to exit code 2. That way a third subcommand cannot
   forget the handling.
5. **Order of operations for `features`.** Load and compute first, write last. If the
   input is missing you fail before anything is created on disk (criterion 5).
6. **Version.** Change it in `pyproject.toml` and `__init__.py`, then reinstall with
   `python -m pip install -e …/challenge` and look at `pumpwatch --version`.
7. **Round-trip sanity check.** `pumpwatch features … --out /tmp/x/y/f.csv` then
   `pumpwatch train --features /tmp/x/y/f.csv` and compare with `--data`. If the metrics
   differ slightly, look at what `to_csv` did to your floats or your column order
   (`FEATURE_COLUMNS` should select by *name*, never by position).
