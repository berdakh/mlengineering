"""Usage report for StreamBox viewing events (reference solution).

An event line looks like:   C00017,2025-03-02T21:15:00,42.5
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime
from typing import Iterable, NamedTuple


class Event(NamedTuple):
    customer_id: str
    timestamp: datetime
    minutes: float


def parse_line(line: str) -> Event | None:
    """Parse one line; return None for anything that violates the format."""
    parts = line.strip().split(",")
    if len(parts) != 3 or not parts[0]:
        return None
    try:
        timestamp = datetime.fromisoformat(parts[1])
        minutes = float(parts[2])
    except ValueError:  # only the failures we expect; a bare except would hide real bugs
        return None
    if not math.isfinite(minutes) or minutes < 0:
        return None
    return Event(parts[0], timestamp, minutes)


def load_events(lines: Iterable[str]) -> list[Event]:
    """Parse lines, skipping malformed lines and exact duplicates *within this call*."""
    seen: set[str] = set()  # local: no state survives between calls
    events = []
    for line in lines:
        key = line.strip()
        if key in seen:
            continue
        seen.add(key)
        event = parse_line(line)
        if event is not None:
            events.append(event)
    return events


def sessionize(events: Iterable[Event], gap_minutes: float = 30) -> dict[str, list[dict]]:
    """Group each customer's events into sessions, in chronological order."""
    sessions: dict[str, list[dict]] = defaultdict(list)
    for cid, ts, minutes in sorted(events, key=lambda e: (e[0], e[1])):  # input may be unsorted
        current = sessions[cid][-1] if sessions[cid] else None
        # total_seconds(), not .seconds: .seconds discards whole days
        if current is None or (ts - current["end"]).total_seconds() / 60 > gap_minutes:
            sessions[cid].append({"start": ts, "end": ts, "minutes": minutes, "n_events": 1})
        else:
            current["end"] = ts
            current["minutes"] += minutes
            current["n_events"] += 1
    return dict(sessions)


def rolling_mean(values: list[float], window: int) -> list[float]:
    """Trailing mean including the current element; shorter windows at the start."""
    if window < 1:
        raise ValueError("window must be >= 1")
    out = []
    for i in range(len(values)):
        chunk = values[max(0, i - window + 1): i + 1]
        out.append(sum(chunk) / window)
    return out


def top_customers(totals: dict[str, float], k: int = 3) -> list[tuple[str, float]]:
    """Largest totals first; ties broken by customer_id ascending."""
    return sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))[:k]


def build_report(lines: Iterable[str], gap_minutes: float = 30, k: int = 3) -> dict:
    events = load_events(lines)
    sessions = sessionize(events, gap_minutes)
    totals = {cid: sum(s["minutes"] for s in ss) for cid, ss in sessions.items()}
    return {
        "n_events": len(events),
        "n_customers": len(sessions),
        "total_minutes": totals,
        "n_sessions": {cid: len(ss) for cid, ss in sessions.items()},
        "longest_session_minutes": {cid: max(s["minutes"] for s in ss) for cid, ss in sessions.items()},
        "top_customers": top_customers(totals, k),
    }
