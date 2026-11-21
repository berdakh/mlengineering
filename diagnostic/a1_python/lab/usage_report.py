"""Usage report for StreamBox viewing events.  (Inherited code - it has bugs.)

An event line looks like:   C00017,2025-03-02T21:15:00,42.5
                            customer_id, ISO timestamp, minutes watched

See ../README.md for the specification each function must satisfy.
"""
from datetime import datetime


def parse_line(line):
    try:
        parts = line.strip().split(",")
        cid = parts[0]
        ts = datetime.fromisoformat(parts[1])
        minutes = int(parts[2])
        return (cid, ts, minutes)
    except:
        return None


def load_events(lines, seen=[]):
    events = []
    for line in lines:
        if line in seen:
            continue
        seen.append(line)
        ev = parse_line(line)
        if ev is not None:
            events.append(ev)
    return events


def sessionize(events, gap_minutes=30):
    sessions = {}
    for cid, ts, minutes in events:
        if cid not in sessions:
            sessions[cid] = [{"start": ts, "end": ts, "minutes": minutes, "n_events": 1}]
        else:
            last = sessions[cid][-1]
            if (ts - last["end"]).seconds / 60 > gap_minutes:
                sessions[cid].append({"start": ts, "end": ts, "minutes": minutes, "n_events": 1})
            else:
                last["end"] = ts
                last["minutes"] = last["minutes"] + minutes
                last["n_events"] = last["n_events"] + 1
    return sessions


def rolling_mean(values, window):
    out = []
    for i in range(len(values)):
        chunk = values[i - window:i]
        out.append(sum(chunk) / window)
    return out


def top_customers(totals, k=3):
    items = sorted(totals.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    return items[:k]


def build_report(lines, gap_minutes=30, k=3):
    events = load_events(lines)
    sessions = sessionize(events, gap_minutes)
    # total minutes per customer
    totals = {}
    for cid in sessions:
        t = 0
        for s in sessions[cid]:
            t = t + s["minutes"]
        totals[cid] = t
    # number of sessions per customer
    counts = {}
    for cid in sessions:
        c = 0
        for s in sessions[cid]:
            c = c + 1
        counts[cid] = c
    # longest session per customer
    longest = {}
    for cid in sessions:
        m = 0
        for s in sessions[cid]:
            if s["minutes"] > m:
                m = s["minutes"]
        longest[cid] = m
    report = {}
    report["n_events"] = len(events)
    report["n_customers"] = len(sessions)
    report["total_minutes"] = totals
    report["n_sessions"] = counts
    report["longest_session_minutes"] = longest
    report["top_customers"] = top_customers(totals, k)
    return report
