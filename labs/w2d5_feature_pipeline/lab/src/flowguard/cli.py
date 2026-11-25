"""Command line: ``flowguard features --data <tidy.csv> --out-dir <dir>``."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from flowguard import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flowguard")
    parser.add_argument("--version", action="version", version=f"flowguard {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    feat = sub.add_parser("features", help="build the causal feature table (content-addressed)")
    feat.add_argument("--data", required=True, help="tidy CSV, e.g. data/interim/skab.csv")
    feat.add_argument("--out-dir", required=True, help="parent directory of the feature cache")
    feat.add_argument("--windows", type=int, nargs="+", default=[10, 30, 60])
    feat.add_argument("--max-gap-s", type=float, default=5.0)
    return parser


def run_features(args: argparse.Namespace) -> dict:
    """Build (or reuse) the feature table. Task 5 of the w2d5 lab.

    Contract checked by the lab:
      * output goes to  <out-dir>/<first 16 hex chars of key>/features.csv  and  .../meta.json
      * meta.json holds at least: key, data_sha256 (of the --data file bytes), feature_version,
        params (with "windows"), n_rows, columns
      * returns {"key": <full key>, "path": <features.csv path>, "cache_hit": <bool>};
        main() prints it as one JSON line on stdout
      * identical data + parameters -> same key, cache_hit true, nothing rewritten
    """
    raise NotImplementedError("Task 5 of the w2d5 lab")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_features(args)
    except NotImplementedError as exc:
        print(f"not implemented: {exc}", file=sys.stderr)
        return 3
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
