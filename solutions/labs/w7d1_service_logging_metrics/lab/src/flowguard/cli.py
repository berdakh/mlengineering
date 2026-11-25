"""Command line for the w7d1 tools. REFERENCE SOLUTION (w7d1).

    python -m flowguard.cli logs --file service.log --request-id <id> [--json]

Exit codes: 0 found, 1 no events for that request id, 2 the file cannot be read.
"""
from __future__ import annotations

import argparse
import json
import sys

from flowguard.logquery import describe, find_request


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="flowguard")
    sub = ap.add_subparsers(dest="command", required=True)
    logs = sub.add_parser("logs", help="show every log event of one request")
    logs.add_argument("--file", required=True, help="JSON-lines log file")
    logs.add_argument("--request-id", required=True)
    logs.add_argument("--json", action="store_true", help="print the events as JSON lines")
    args = ap.parse_args(argv)
    try:
        with open(args.file, encoding="utf-8", errors="replace") as fh:
            result = find_request(fh, args.request_id)
    except OSError as exc:
        print(f"error: cannot read {args.file}: {exc}", file=sys.stderr)
        return 2
    if args.json:
        for event in result.events:
            print(json.dumps(event, sort_keys=True))
    else:
        print(describe(result))
    return 0 if result.found else 1


if __name__ == "__main__":
    sys.exit(main())
