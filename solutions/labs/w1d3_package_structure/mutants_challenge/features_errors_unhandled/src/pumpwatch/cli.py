"""Command-line entry point.

    pumpwatch features --data <csv> --out <features.csv>
    pumpwatch train (--data <csv> | --features <features.csv>)
"""
from __future__ import annotations

import argparse
import json
import sys

from pumpwatch import __version__
from pumpwatch.features import build_feature_table
from pumpwatch.io import load_features, load_windows, save_features
from pumpwatch.model import train_and_evaluate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pumpwatch", description="Pump fault detection.")
    parser.add_argument("--version", action="version", version=f"pumpwatch {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    features = sub.add_parser("features", help="compute the per-window feature table and save it")
    features.add_argument("--data", required=True, help="path to the long-format window CSV")
    features.add_argument("--out", required=True, help="where to write the feature CSV")
    features.add_argument("--fs", type=float, default=256.0, help="sampling rate in Hz")

    train = sub.add_parser("train", help="train and print test metrics as JSON")
    source = train.add_mutually_exclusive_group(required=True)
    source.add_argument("--data", help="raw window CSV (features are computed in memory)")
    source.add_argument("--features", help="feature CSV written by `pumpwatch features`")
    train.add_argument("--fs", type=float, default=256.0, help="sampling rate in Hz (with --data)")
    train.add_argument("--test-fraction", type=float, default=0.3)
    train.add_argument("--seed", type=int, default=7)
    train.add_argument("--C", type=float, default=1.0, help="inverse L2 regularisation strength")
    return parser


def _run(args: argparse.Namespace) -> int:
    if args.command == "features":
        table = build_feature_table(load_windows(args.data), fs=args.fs)
        out = save_features(table, args.out)
        print(f"wrote {len(table)} rows to {out}", file=sys.stderr)
        return 0
    if args.features:
        table = load_features(args.features)
    else:
        table = build_feature_table(load_windows(args.data), fs=args.fs)
    print(json.dumps(train_and_evaluate(table, args.test_fraction, args.seed, args.C), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "features":
        return _run(args)
    try:
        return _run(args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
