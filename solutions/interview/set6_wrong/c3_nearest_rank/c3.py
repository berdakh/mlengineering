"""C3 reference: per-endpoint p95 latency and error rate over a sliding window of JSON log lines."""
from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Iterable


def percentile(values: list[float], q: float) -> float:
    """Linear interpolation between closest ranks (numpy's default method)."""
    xs = sorted(values)
    if not xs:
        raise ValueError("percentile of an empty list")
    k = max(0, math.ceil(q / 100.0 * len(xs)) - 1)
    return xs[k]


def parse_request(line: str) -> dict | None:
    """Return {'ts', 'path', 'status', 'duration_ms'} for a valid request record, else None.

    Raises ValueError for a line that is not a valid record at all (so the caller can count it);
    returns None for a well-formed record of another event type.
    """
    try:
        obj = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ValueError("not JSON") from exc
    if not isinstance(obj, dict):
        raise ValueError("not an object")
    if obj.get("event") != "request":
        return None
    try:
        ts = datetime.fromisoformat(obj["ts"])
        path = str(obj["path"]).split("?", 1)[0]
        status = obj["status"]
        duration = obj["duration_ms"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("missing or malformed field") from exc
    if ts.tzinfo is None:
        raise ValueError("timestamp without offset")
    if isinstance(status, bool) or not isinstance(status, int):
        raise ValueError("status is not an integer")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) \
            or duration < 0:
        raise ValueError("bad duration")
    return {"ts": ts, "path": path, "status": status, "duration_ms": float(duration)}


def window_summary(lines: Iterable[str], end: str, window_s: float = 300.0) -> dict:
    end_ts = datetime.fromisoformat(end)
    if end_ts.tzinfo is None:
        raise ValueError("end must carry a UTC offset")
    endpoints: dict[str, dict] = {}
    skipped = 0
    for line in lines:
        if not line.strip():
            continue
        try:
            rec = parse_request(line)
        except ValueError:
            skipped += 1
            continue
        if rec is None:
            continue
        age = (end_ts - rec["ts"]).total_seconds()
        if not (0.0 <= age < window_s):          # window is (end - window_s, end]
            continue
        e = endpoints.setdefault(rec["path"], {"n": 0, "errors": 0, "ok": []})
        e["n"] += 1
        if rec["status"] >= 500:
            e["errors"] += 1
        if 200 <= rec["status"] < 300:
            e["ok"].append(rec["duration_ms"])
    out = {path: {"count": e["n"],
                  "error_rate": e["errors"] / e["n"],
                  "p95_ms": percentile(e["ok"], 95) if e["ok"] else None}
           for path, e in sorted(endpoints.items())}
    return {"endpoints": out, "skipped": skipped}
