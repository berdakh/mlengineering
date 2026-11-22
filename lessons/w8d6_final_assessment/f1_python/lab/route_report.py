"""Routing report for Parcelo depot scans.  (Inherited code - it has bugs.)

A scan line looks like:   P004512,2025-06-02T08:15:00,ALA,2.75
                          parcel_id, ISO timestamp, depot code, weight in kg

See ../README.md for the specification each function must satisfy.
"""
from datetime import datetime


def parse_scan(line):
    try:
        parts = line.strip().split(",")
        pid = parts[0]
        ts = datetime.fromisoformat(parts[1])
        depot = parts[2]
        weight = int(parts[3])
        return (pid, ts, depot, weight)
    except:
        return None


def load_scans(lines, seen=set()):
    scans = []
    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        s = parse_scan(line)
        if s is not None:
            scans.append(s)
    return scans


def group_legs(scans, max_idle_hours=12):
    scans.sort(key=lambda s: s[1])
    legs = {}
    for pid, ts, depot, weight in scans:
        if pid not in legs:
            legs[pid] = [{"start": ts, "end": ts, "n_scans": 1, "depots": [depot]}]
        else:
            last = legs[pid][-1]
            if (ts - last["end"]).seconds / 3600 > max_idle_hours:
                legs[pid].append({"start": ts, "end": ts, "n_scans": 1, "depots": [depot]})
            else:
                last["end"] = ts
                last["n_scans"] = last["n_scans"] + 1
                last["depots"].append(depot)
    return legs


def trailing_average(values, window):
    out = []
    for i in range(len(values)):
        chunk = values[i - window + 1:i + 1]
        out.append(sum(chunk) / window)
    return out


def busiest_depots(counts, k=3):
    items = sorted(counts.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    return items[:k]


def build_report(lines, max_idle_hours=12, k=3):
    scans = load_scans(lines)
    legs = group_legs(scans, max_idle_hours)
    # legs per parcel
    n_legs = {}
    for pid in legs:
        c = 0
        for leg in legs[pid]:
            c = c + 1
        n_legs[pid] = c
    # transit hours per parcel
    transit = {}
    for pid in legs:
        t = 0
        for leg in legs[pid]:
            t = t + (leg["end"] - leg["start"]).seconds / 3600
        transit[pid] = t
    # longest leg per parcel
    longest = {}
    for pid in legs:
        m = 0
        for leg in legs[pid]:
            h = (leg["end"] - leg["start"]).seconds / 3600
            if h > m:
                m = h
        longest[pid] = m
    # scans per depot
    counts = {}
    for pid, ts, depot, weight in scans:
        counts[depot] = counts.get(depot, 0) + 1
    report = {}
    report["n_scans"] = len(scans)
    report["n_parcels"] = len(legs)
    report["n_legs"] = n_legs
    report["transit_hours"] = transit
    report["longest_leg_hours"] = longest
    report["busiest_depots"] = busiest_depots(counts, k)
    return report
