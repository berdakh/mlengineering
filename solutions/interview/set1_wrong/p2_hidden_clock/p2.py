"""WRONG: summarize() still asks the clock, so `now` is ignored and the function is untestable."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

WINDOW = timedelta(hours=24)


def parse_line(line: str) -> dict | None:
    parts = line.strip().split(" ", 2)
    if len(parts) != 3:
        return None
    try:
        ts = datetime.fromisoformat(parts[0])
    except ValueError:
        return None
    return {"ts": ts, "level": parts[1], "message": parts[2]}


def summarize(events: list[dict], now: datetime) -> dict:
    now = datetime.now()
    counts: dict[str, int] = {}
    last_error: dict | None = None
    for event in events:
        if not (now - WINDOW < event["ts"] <= now):
            continue
        counts[event["level"]] = counts.get(event["level"], 0) + 1
        if event["level"] == "ERROR" and (last_error is None or event["ts"] > last_error["ts"]):
            last_error = event
    return {"counts": counts, "last_error": last_error["message"] if last_error else None}


def load_events(path: Path) -> list[dict]:
    with path.open() as fh:
        return [event for event in map(parse_line, fh) if event is not None]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    path = Path(argv[0])
    if not path.is_file():
        print(f"error: no such file: {path}", file=sys.stderr)
        return 2
    print(json.dumps(summarize(load_events(path), datetime.now())))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Most valuable tests, in priority order:
# 1. window boundaries: exactly 24 h old is out, exactly `now` is in, later than `now` is out
# 2. `now` is honoured: a fixed past `now` selects only events around it (no hidden clock)
# 3. last_error is the most recent ERROR by timestamp, independent of input order
# 4. malformed and blank lines are skipped by parse_line, never raised
# 5. empty input -> {"counts": {}, "last_error": None}; main() on a missing file returns 2
