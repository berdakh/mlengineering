"""Command-line entry point: ``flowguard ingest --raw-dir ... --out-dir ...``.

Exit codes: 0 success (warnings allowed), 1 data-quality errors, 2 unusable input.
"""
from __future__ import annotations

import argparse
import json
import sys

from flowguard import __version__
from flowguard.ingest import QualityError, ingest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flowguard", description="Fault detection on testbed recordings.")
    parser.add_argument("--version", action="version", version=f"flowguard {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("ingest", help="validate raw files and write the tidy interim table")
    p.add_argument("--raw-dir", required=True, help="directory holding <family>/<n>.csv files")
    p.add_argument("--out-dir", required=True, help="where skab.csv and the two JSON records are written")
    return parser


def _print_failures(report: dict) -> None:
    for r in report["results"]:
        if not r["passed"]:
            print(f"[{r['severity']}] {r['name']}: {r['detail']}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        provenance = ingest(args.raw_dir, args.out_dir)
    except QualityError as exc:
        _print_failures(exc.report)
        print(f"error: {exc}; no table written", file=sys.stderr)
        return 1
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    with open(f"{args.out_dir}/quality_report.json") as fh:
        _print_failures(json.load(fh))
    print(json.dumps({"rows": provenance["n_rows"], "experiments": provenance["n_experiments"],
                      **provenance["quality"], "sha256": provenance["output"]["sha256"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
