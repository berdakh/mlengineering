"""Independent pandas answers for the w8d4 SQL problems (used by the checks; written without SQL)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


def tables(db: Path) -> dict[str, pd.DataFrame]:
    con = sqlite3.connect(db)
    out = {t: pd.read_sql_query(f"SELECT * FROM {t}", con) for t in ("cities", "drivers", "trips", "payments")}
    con.close()
    return out


def _march_completed(trips: pd.DataFrame) -> pd.DataFrame:
    t = trips[trips["status"] == "completed"]
    return t[(t["requested_at"] >= "2026-03-01") & (t["requested_at"] < "2026-04-01")]


def q1(db: Path) -> list[tuple]:
    T = tables(db)
    m = _march_completed(T["trips"])
    ok = T["payments"][T["payments"]["status"] == "succeeded"].groupby("trip_id")["amount_cents"].sum()
    rows = []
    for _, c in T["cities"].iterrows():
        trips = m[m["city_id"] == c["city_id"]]
        paid = ok[ok.index.isin(trips["trip_id"])]
        rows.append((c["name"], len(trips), len(paid), round(paid.sum() / 100.0, 2)))
    return sorted(rows)


def q2(db: Path) -> list[tuple]:
    T = tables(db)
    m = _march_completed(T["trips"])
    counts = m.groupby(["city_id", "driver_id"]).size().reset_index(name="n")
    names = dict(zip(T["cities"]["city_id"], T["cities"]["name"]))
    rows = []
    for city_id, g in counts.groupby("city_id"):
        g = g.sort_values(["n", "driver_id"], ascending=[False, True]).head(2)
        for rank, (_, r) in enumerate(g.iterrows(), start=1):
            rows.append((names[city_id], int(r["driver_id"]), int(r["n"]), rank))
    return sorted(rows, key=lambda r: (r[0], r[3]))


def q3(db: Path) -> list[tuple]:
    T = tables(db)
    t = T["trips"][T["trips"]["status"] == "completed"]
    rows = []
    for driver, g in t.groupby("driver_id"):
        days = sorted({pd.Timestamp(x).date() for x in g["requested_at"]})
        best_start, best_len = days[0], 1
        start, length = days[0], 1
        for prev, day in zip(days, days[1:]):
            if (day - prev).days == 1:
                length += 1
            else:
                start, length = day, 1
            if length > best_len:
                best_start, best_len = start, length
        rows.append((int(driver), best_start.isoformat(), best_len))
    return sorted(rows)
