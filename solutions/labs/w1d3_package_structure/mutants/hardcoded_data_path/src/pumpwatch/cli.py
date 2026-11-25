"""Command-line entry point: ``pumpwatch train --data <csv>``."""
from __future__ import annotations

import argparse
import json
import sys

from pumpwatch import __version__
from pumpwatch.features import build_feature_table
from pumpwatch.io import load_windows
from pumpwatch.model import train_and_evaluate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pumpwatch", description="Pump fault detection.")
    parser.add_argument("--version", action="version", version=f"pumpwatch {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    train = sub.add_parser("train", help="build features, train, print test metrics as JSON")
    train.add_argument("--data", required=True, help="path to the long-format window CSV")
    train.add_argument("--fs", type=float, default=256.0, help="sampling rate in Hz")
    train.add_argument("--test-fraction", type=float, default=0.3)
    train.add_argument("--seed", type=int, default=7)
    train.add_argument("--C", type=float, default=1.0, help="inverse L2 regularisation strength")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        df = load_windows("data/synthetic/pump_vibration.csv")
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    features = build_feature_table(df, fs=args.fs)
    metrics = train_and_evaluate(features, args.test_fraction, args.seed, args.C)
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
