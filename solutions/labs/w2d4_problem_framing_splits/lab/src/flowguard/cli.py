"""Command-line entry point: ``flowguard split``."""
from __future__ import annotations

import argparse
import sys

from flowguard import __version__
from flowguard.data import load_raw
from flowguard.splits import make_splits, save_splits, validate_splits


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flowguard", description="SKAB fault detection (educational prototype).")
    parser.add_argument("--version", action="version", version=f"flowguard {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    split = sub.add_parser("split", help="create and freeze the split manifest")
    split.add_argument("--raw-dir", required=True, help="directory with <family>/<n>.csv files")
    split.add_argument("--out", required=True, help="manifest path, e.g. splits/v1.json")
    split.add_argument("--seed", type=int, default=0)
    split.add_argument("--n-folds", type=int, default=4)
    split.add_argument("--test-fraction", type=float, default=0.25)
    split.add_argument("--force", action="store_true", help="replace an existing manifest (invalidates past results)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
        manifest = make_splits(tidy, seed=args.seed, n_folds=args.n_folds, test_fraction=args.test_fraction)
        validate_splits(manifest, tidy)
        path = save_splits(manifest, args.out, overwrite=args.force)
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sizes = [len(f) for f in manifest["dev_folds"]]
    print(f"wrote {path}: test={len(manifest['test'])} experiments, dev folds={sizes}, "
          f"reference_normal={len(manifest['reference_normal'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
