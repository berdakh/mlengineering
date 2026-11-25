"""I/O boundary: parse arguments, read the file, print the result, return an exit code."""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from tempstats.stats import summarize


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tempstats", description="Per-room temperature summary.")
    parser.add_argument("csv", help="CSV with columns room, timestamp, temp_c")
    args = parser.parse_args(argv)
    try:
        readings = pd.read_csv(args.csv)
        summary = summarize(readings)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for row in summary.itertuples(index=False):
        print(row.room, row.mean, row.range, row.n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
