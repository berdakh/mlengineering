"""Command-line entry point: ``flowguard summary|gaps --raw-dir <dir>``."""
from __future__ import annotations

import argparse
import json
import sys

from flowguard import __version__
from flowguard.data import find_gaps, load_raw, summarize


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flowguard", description="SKAB fault detection (prototype).")
    parser.add_argument("--version", action="version", version=f"flowguard {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    summary = sub.add_parser("summary", help="print per-experiment row counts and anomaly fraction as JSON")
    summary.add_argument("--raw-dir", required=True, help="directory containing <family>/<name>.csv files")
    gaps = sub.add_parser("gaps", help="print sampling gaps within experiments as JSON")
    gaps.add_argument("--raw-dir", required=True, help="directory containing <family>/<name>.csv files")
    gaps.add_argument("--max-gap-seconds", type=float, default=5.0,
                      help="report intervals strictly longer than this (default 5)")
    return parser


def gaps_report(tidy, max_gap_seconds: float) -> dict:
    gaps = find_gaps(tidy, max_gap_seconds)
    records = [
        {"experiment_id": row.experiment_id, "t": int(row.t),
         "gap_start": row.gap_start.isoformat(sep=" "), "gap_end": row.gap_end.isoformat(sep=" "),
         "gap_seconds": float(row.gap_seconds)}
        for row in gaps.itertuples(index=False)
    ]
    return {"max_gap_seconds": float(max_gap_seconds), "n_gaps": len(records), "gaps": records}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
        report = summarize(tidy) if args.command == "summary" else gaps_report(tidy, 5.0)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
