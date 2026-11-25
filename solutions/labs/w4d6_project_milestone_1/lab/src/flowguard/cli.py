"""Command-line interface for the milestone-1 pipeline. Given to you; you do not need to edit it.

    python -m flowguard ingest   --raw-dir data/raw/skab --out data/interim/skab.csv
    python -m flowguard evaluate --tidy data/interim/skab.csv --splits splits/v2.json --out results/results.json
                                 [--burn-in 100] [--n-boot 2000] [--seed 0]
    python -m flowguard report   --results results/results.json --out reports/evaluation.md

Each command reads only its inputs and writes only its output (plus reports/figures/ for `report`),
which is what lets make decide what to rebuild.
"""
from __future__ import annotations

import argparse
import json
import sys

from flowguard import __version__


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="flowguard", description="flowguard milestone-1 pipeline")
    ap.add_argument("--version", action="version", version=f"flowguard {__version__}")
    sub = ap.add_subparsers(dest="command", required=True)
    i = sub.add_parser("ingest", help="raw SKAB files -> tidy CSV")
    i.add_argument("--raw-dir", required=True)
    i.add_argument("--out", required=True)
    e = sub.add_parser("evaluate", help="tidy CSV + split manifest -> results JSON")
    e.add_argument("--tidy", required=True)
    e.add_argument("--splits", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--burn-in", type=int, default=100)
    e.add_argument("--n-boot", type=int, default=2000)
    e.add_argument("--seed", type=int, default=0)
    r = sub.add_parser("report", help="results JSON -> markdown report and figures")
    r.add_argument("--results", required=True)
    r.add_argument("--out", required=True)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from flowguard import pipeline  # imported here so `--help` works even while pipeline.py is unfinished
    try:
        if args.command == "ingest":
            print(f"wrote {pipeline.ingest(args.raw_dir, args.out)}")
        elif args.command == "evaluate":
            results = pipeline.evaluate(args.tidy, args.splits, burn_in=args.burn_in, n_boot=args.n_boot, seed=args.seed)
            print(f"wrote {pipeline.write_results(results, args.out)}")
        else:
            with open(args.results) as fh:
                results = json.load(fh)
            print(f"wrote {pipeline.render(results, args.out)}")
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
