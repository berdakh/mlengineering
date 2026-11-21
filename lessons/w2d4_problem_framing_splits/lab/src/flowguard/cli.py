"""Command-line entry point - STARTER. Add the `split` subcommand (Task 5).

    flowguard split --raw-dir data/raw/skab --out splits/v1.json [--seed 0] [--n-folds 4]
                    [--test-fraction 0.25] [--force]

Exit code 0 on success; non-zero with a one-line message on stderr (no traceback) when the data
is missing or the manifest already exists and --force was not given.
"""
from __future__ import annotations

import argparse
import sys

from flowguard import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flowguard", description="SKAB fault detection (educational prototype).")
    parser.add_argument("--version", action="version", version=f"flowguard {__version__}")
    parser.add_subparsers(dest="command", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
