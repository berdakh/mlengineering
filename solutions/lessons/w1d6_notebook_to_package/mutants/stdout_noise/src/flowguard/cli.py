"""Command-line entry point: ``flowguard summary --raw-dir <dir>``."""
from __future__ import annotations

import argparse
import json
import sys

from flowguard import __version__
from flowguard.data import load_raw, summarize


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flowguard", description="SKAB fault detection (prototype).")
    parser.add_argument("--version", action="version", version=f"flowguard {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    summary = sub.add_parser("summary", help="print per-experiment row counts and anomaly fraction as JSON")
    summary.add_argument("--raw-dir", required=True, help="directory containing <family>/<name>.csv files")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"loaded {len(tidy)} rows from {args.raw_dir}")
    print(json.dumps(summarize(tidy), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
