"""Independent expected results, computed in plain Python loops from the raw tables.

Deliberately uses no window functions and no pandas, so it shares no code path with
either the SQL or the pandas a learner writes. Used by the lab and challenge checks.
"""
from __future__ import annotations

import sqlite3
from bisect import bisect_right
from collections import defaultdict

REPORT_END_EPOCH = 1772582400          # 2026-03-04 00:00:00 UTC


def _rows(con: sqlite3.Connection, sql: str) -> list[dict]:
    cur = con.execute(sql)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def dedup_readings(con) -> dict[str, list[dict]]:
    """Per device: readings in time order, one per timestamp (highest reading_id wins)."""
    best: dict[tuple, dict] = {}
    for r in _rows(con, "SELECT * FROM sensor_readings"):
        key = (r["device_id"], r["ts_epoch"])
        if key not in best or r["reading_id"] > best[key]["reading_id"]:
            best[key] = r
    out = defaultdict(list)
    for (dev, _), r in sorted(best.items()):
        out[dev].append(r)
    return out


def status_by_device(con) -> dict[str, list[dict]]:
    out = defaultdict(list)
    for e in sorted(_rows(con, "SELECT * FROM device_status_events"), key=lambda e: (e["ts_epoch"], e["event_id"])):
        out[e["device_id"]].append(e)
    return out


def latest_status(con) -> list[dict]:
    return [{"device_id": d, "status": ev[-1]["status"], "ts": ev[-1]["ts"]} for d, ev in status_by_device(con).items()]


def time_in_state(con) -> list[dict]:
    total: dict[tuple, int] = defaultdict(int)
    for dev, ev in status_by_device(con).items():
        for i, e in enumerate(ev):
            end = ev[i + 1]["ts_epoch"] if i + 1 < len(ev) else REPORT_END_EPOCH
            total[(dev, e["status"])] += end - e["ts_epoch"]
    return [{"device_id": d, "status": s, "total_seconds": v} for (d, s), v in total.items()]


def running_alerts(con) -> list[dict]:
    out, count = [], defaultdict(int)
    for r in sorted(_rows(con, "SELECT * FROM sensor_readings"), key=lambda r: (r["ts_epoch"], r["reading_id"])):
        count[r["device_id"]] += r["alert"]
        out.append({"reading_id": r["reading_id"], "device_id": r["device_id"], "running_alerts": count[r["device_id"]]})
    return out


def rolling_features(con, window_s: int = 1800) -> list[dict]:
    out = []
    for dev, rs in dedup_readings(con).items():
        for i, r in enumerate(rs):
            inside = [x["temperature"] for x in rs[: i + 1] if x["ts_epoch"] >= r["ts_epoch"] - window_s]
            prev = rs[i - 1] if i else None
            out.append({
                "reading_id": r["reading_id"], "device_id": dev, "ts": r["ts"],
                "temp_mean_30m": sum(inside) / len(inside), "n_30m": len(inside),
                "delta_prev": None if prev is None else r["temperature"] - prev["temperature"],
                "gap_s": None if prev is None else r["ts_epoch"] - prev["ts_epoch"],
            })
    return out


def alert_episodes(con) -> list[dict]:
    out = []
    for dev, rs in dedup_readings(con).items():
        run: list[dict] = []
        number = 0
        for r in rs + [None]:
            if r is not None and r["alert"] == 1:
                run.append(r)
                continue
            if run:
                number += 1
                out.append({"device_id": dev, "episode_no": number, "start_ts": run[0]["ts"], "end_ts": run[-1]["ts"],
                            "n_samples": len(run), "peak_temperature": max(x["temperature"] for x in run)})
                run = []
    return out


def asof_calibration(con) -> list[dict]:
    cal = defaultdict(list)
    for c in sorted(_rows(con, "SELECT * FROM calibration"), key=lambda c: c["valid_from_epoch"]):
        cal[c["device_id"]].append(c)
    out = []
    for dev, rs in dedup_readings(con).items():
        starts = [c["valid_from_epoch"] for c in cal[dev]]
        for r in rs:
            k = bisect_right(starts, r["ts_epoch"])            # rows with valid_from <= ts
            c = cal[dev][k - 1] if k else None
            corrected = None if c is None else r["temperature"] + c["offset_c"]
            out.append({
                "reading_id": r["reading_id"], "device_id": dev, "ts": r["ts"],
                "corrected_temperature": corrected,
                "alert_threshold_c": None if c is None else c["alert_threshold_c"],
                "over_threshold": None if c is None else int(corrected > c["alert_threshold_c"]),
            })
    return out


def label_features(con) -> list[dict]:
    readings, status = dedup_readings(con), status_by_device(con)
    out = []
    for lab in _rows(con, "SELECT * FROM maintenance_labels"):
        t, dev = lab["label_ts_epoch"], lab["device_id"]
        past = [r for r in readings[dev] if r["ts_epoch"] <= t]
        hour = [r["temperature"] for r in past if r["ts_epoch"] > t - 3600]
        day_alerts = sum(r["alert"] for r in past if r["ts_epoch"] > t - 86400)
        past_events = [e for e in status[dev] if e["ts_epoch"] <= t]
        faults = [e["ts_epoch"] for e in past_events if e["status"] == "fault"]
        out.append({
            "label_id": lab["label_id"], "failed": lab["failed"],
            "last_temperature": past[-1]["temperature"] if past else None,
            "mean_temp_60m": sum(hour) / len(hour) if hour else None,
            "n_alerts_24h": day_alerts,
            "seconds_since_fault": t - max(faults) if faults else None,
            "status_at_label": past_events[-1]["status"] if past_events else None,
        })
    return out
