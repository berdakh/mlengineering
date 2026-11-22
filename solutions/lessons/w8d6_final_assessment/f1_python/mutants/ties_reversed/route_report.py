"""Routing report for Parcelo depot scans (reference solution).

A scan line looks like:   P004512,2025-06-02T08:15:00,ALA,2.75
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime
from typing import Iterable, NamedTuple


class Scan(NamedTuple):
    parcel_id: str
    timestamp: datetime
    depot: str
    weight_kg: float


def parse_scan(line: str) -> Scan | None:
    """Parse one line; return None for anything that violates the format."""
    parts = [p.strip() for p in line.strip().split(",")]
    if len(parts) != 4 or not parts[0] or not parts[2]:
        return None
    try:
        timestamp = datetime.fromisoformat(parts[1])
        weight = float(parts[3])
    except ValueError:  # only the failures we expect; a bare except would hide real bugs
        return None
    if not math.isfinite(weight) or weight <= 0:
        return None
    return Scan(parts[0], timestamp, parts[2], weight)


def load_scans(lines: Iterable[str]) -> list[Scan]:
    """Parse lines, skipping malformed lines and exact duplicates *within this call*."""
    seen: set[str] = set()  # local: no state survives between calls
    scans = []
    for line in lines:
        key = line.strip()
        if key in seen:
            continue
        seen.add(key)
        scan = parse_scan(line)
        if scan is not None:
            scans.append(scan)
    return scans


def _hours(leg: dict) -> float:
    # total_seconds(), not .seconds: .seconds discards whole days
    return (leg["end"] - leg["start"]).total_seconds() / 3600


def group_legs(scans: Iterable[Scan], max_idle_hours: float = 12) -> dict[str, list[dict]]:
    """Group each parcel's scans into legs, in chronological order. Does not modify `scans`."""
    legs: dict[str, list[dict]] = defaultdict(list)
    for pid, ts, depot, _ in sorted(scans, key=lambda s: (s[0], s[1])):  # sorted() copies
        current = legs[pid][-1] if legs[pid] else None
        if current is None or (ts - current["end"]).total_seconds() / 3600 > max_idle_hours:
            legs[pid].append({"start": ts, "end": ts, "n_scans": 1, "depots": [depot]})
        else:
            current["end"] = ts
            current["n_scans"] += 1
            current["depots"].append(depot)
    return dict(legs)


def trailing_average(values: list[float], window: int) -> list[float]:
    """Trailing mean including the current element; shorter windows at the start."""
    if window < 1:
        raise ValueError("window must be >= 1")
    out = []
    for i in range(len(values)):
        chunk = values[max(0, i - window + 1): i + 1]
        out.append(sum(chunk) / len(chunk))
    return out


def busiest_depots(counts: dict[str, int], k: int = 3) -> list[tuple[str, int]]:
    """Largest counts first; ties broken by depot code ascending."""
    return sorted(counts.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)[:k]


def build_report(lines: Iterable[str], max_idle_hours: float = 12, k: int = 3) -> dict:
    scans = load_scans(lines)
    legs = group_legs(scans, max_idle_hours)
    return {
        "n_scans": len(scans),
        "n_parcels": len(legs),
        "n_legs": {pid: len(ls) for pid, ls in legs.items()},
        "transit_hours": {pid: sum(_hours(leg) for leg in ls) for pid, ls in legs.items()},
        "longest_leg_hours": {pid: max(_hours(leg) for leg in ls) for pid, ls in legs.items()},
        "busiest_depots": busiest_depots(dict(Counter(s.depot for s in scans)), k),
    }
