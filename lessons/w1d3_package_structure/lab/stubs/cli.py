"""Command-line entry point: ``pumpwatch train --data <csv>``."""
from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, run, print ONE JSON object to stdout, return an exit code.

    `argv=None` means "use sys.argv[1:]" (what argparse does by default); accepting
    a list makes the function callable from tests without touching sys.argv.
    Exit codes: 0 success, 2 for a missing or malformed input file (message on stderr).
    Options: --data (required), --fs, --test-fraction, --seed, --C.
    """
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
