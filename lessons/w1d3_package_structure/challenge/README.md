# w1d3 independent challenge — a two-stage command-line pipeline

**Time:** about 45 minutes. **Assistance:** none to begin with; hints are in
[`../hints/`](../hints/) and cost you the "independent" flag from hint 3 onward.

## Situation

Feature extraction is the slow part of real pipelines (on the project dataset it will
be minutes, not milliseconds), and several people want the feature table without
training anything. A teammate also runs tools as `python -m <package>` because their
scheduler does not put a virtual environment's `bin/` on `PATH`.

Extend `pumpwatch` so that features can be computed once, saved, and reused.

## Setup

Copy your finished lab package into this directory and install *this* copy:

```bash
cp -r lessons/w1d3_package_structure/lab/pyproject.toml lessons/w1d3_package_structure/lab/src \
      lessons/w1d3_package_structure/challenge/
python -m pip install -e lessons/w1d3_package_structure/challenge
python -c "import pumpwatch; print(pumpwatch.__file__)"     # must now point into challenge/
```

(One distribution name can be installed once per environment; the second install
replaces the first. Re-install `lab/` later if you want it back.)

## Acceptance criteria

1. `pumpwatch features --data <raw.csv> --out <features.csv>` writes a CSV with exactly
   one row per `(unit_id, window_id)` and at least the columns
   `unit_id, window_id, rms, line_length, p2p, bp_low, bp_high, ratio, temp, label`.
   Missing parent directories of `--out` are created. Exit code 0. Nothing but data in the file
   (no index column). Standard output is either empty or not relied upon.
2. `pumpwatch train --features <features.csv>` trains from the saved table and prints the
   same JSON metrics as `pumpwatch train --data <raw.csv>` (to 1e-6).
3. `train` takes **exactly one** of `--data` / `--features`: neither, or both, is a usage
   error with a non-zero exit code.
4. `python -m pumpwatch <args>` behaves identically to `pumpwatch <args>`.
5. A missing input file — for either subcommand and either option — gives a one-line
   message on stderr, **exit code 2**, no traceback, and leaves no output file behind.
6. `pumpwatch train --features <a file that is not a feature table>` (for example the raw
   CSV) fails the same clean way: exit code 2, readable message, no traceback.
7. The version is `0.2.0` — in `pyproject.toml`, in `pumpwatch.__version__`, and in
   `pumpwatch --version`.
8. All of the above hold when the command is run from a directory outside the repository.

## Check yourself

```bash
python -m pytest lessons/w1d3_package_structure/checks_challenge -q     # expect: 9 passed
```

## What to hand in for feedback

The `challenge/` directory, plus three or four sentences in `challenge/NOTES.md`:
where you put the new read/write functions and why there; what you had to re-run after
editing `pyproject.toml`; and one thing about the saved-features design you would
question before using it on a real project (think: what does the file *not* record?).

## Out of scope

Configuration files and logging (w1d4), unit tests (w1d5), Parquet or other formats.
