"""Expected results, computed independently of SQL with pandas.

Each function takes the tables as DataFrames and returns (columns, rows).
The oracle deliberately does not reuse any SQL, so a mistake shared by a query and
its expected answer is unlikely.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

TABLES = ("sites", "machines", "technicians", "work_orders", "parts", "parts_used", "downtime_events")


def load_tables(db: Path) -> dict[str, pd.DataFrame]:
    con = sqlite3.connect(db)
    try:
        return {t: pd.read_sql_query(f"SELECT * FROM {t}", con) for t in TABLES}
    finally:
        con.close()


def _rows(df: pd.DataFrame, columns: list[str]):
    out = []
    for rec in df[columns].itertuples(index=False):
        out.append(tuple(None if pd.isna(v) else (v.item() if hasattr(v, "item") else v) for v in rec))
    return columns, out


def _wo_parts_cost(t) -> pd.Series:
    pu = t["parts_used"].merge(t["parts"], on="part_id")
    return (pu["quantity"] * pu["unit_cost"]).groupby(pu["wo_id"]).sum()


def _wo_with_site(t) -> pd.DataFrame:
    wo = t["work_orders"].merge(t["machines"][["machine_id", "site_id"]], on="machine_id")
    wo["parts_cost"] = wo["wo_id"].map(_wo_parts_cost(t)).fillna(0.0)
    return wo


# ------------------------------------------------------------------ lab
def q1_machines_per_site(t):
    m = t["machines"]
    out = t["sites"][["site_id", "site_name"]].copy()
    out["n_machines"] = out["site_id"].map(m.groupby("site_id").size()).fillna(0).astype(int)
    active = m[m["decommissioned_date"].isna()].groupby("site_id").size()
    out["n_active"] = out["site_id"].map(active).fillna(0).astype(int)
    return _rows(out, ["site_id", "site_name", "n_machines", "n_active"])


def q2_unassigned_technicians(t):
    used = set(t["work_orders"]["tech_id"].dropna().astype(int))
    out = t["technicians"][~t["technicians"]["tech_id"].isin(used)]
    return _rows(out, ["tech_id", "tech_name"])


def q3_machine_hours(t):
    wo, de = t["work_orders"], t["downtime_events"]
    out = t["machines"][["machine_id"]].copy()
    out["n_work_orders"] = out["machine_id"].map(wo.groupby("machine_id").size()).fillna(0).astype(int)
    out["labor_hours"] = out["machine_id"].map(wo.groupby("machine_id")["labor_hours"].sum()).fillna(0.0)
    out["downtime_hours"] = out["machine_id"].map(de.groupby("machine_id")["hours"].sum()).fillna(0.0)
    return _rows(out, ["machine_id", "n_work_orders", "labor_hours", "downtime_hours"])


def q4_corrective_2025_per_site(t):
    wo = _wo_with_site(t)
    sel = wo[(wo["wo_type"] == "corrective") & wo["opened_date"].between("2025-01-01", "2025-12-31")]
    out = t["sites"][["site_id"]].copy()
    out["n_corrective_2025"] = out["site_id"].map(sel.groupby("site_id").size()).fillna(0).astype(int)
    return _rows(out, ["site_id", "n_corrective_2025"])


def q5_type_summary(t):
    wo = t["work_orders"]
    g = wo.groupby("wo_type")
    out = pd.DataFrame({
        "n_orders": g.size(),
        "n_open": g["closed_date"].apply(lambda s: int(s.isna().sum())),
        "n_unassigned": g["tech_id"].apply(lambda s: int(s.isna().sum())),
        "avg_labor_hours": g["labor_hours"].mean(),   # pandas mean skips NaN, as SQL AVG skips NULL
    }).reset_index()
    return _rows(out, ["wo_type", "n_orders", "n_open", "n_unassigned", "avg_labor_hours"])


Q6_THRESHOLD = 1500.0


def q6_expensive_orders(t):
    pu = t["parts_used"].merge(t["parts"], on="part_id").merge(t["work_orders"][["wo_id", "wo_type"]], on="wo_id")
    pu = pu[pu["wo_type"] == "corrective"].assign(cost=lambda d: d["quantity"] * d["unit_cost"])
    out = pu.groupby("wo_id").agg(n_part_lines=("part_id", "size"), parts_cost=("cost", "sum")).reset_index()
    out = out[out["parts_cost"] >= Q6_THRESHOLD].sort_values(["parts_cost", "wo_id"], ascending=[False, True])
    return _rows(out, ["wo_id", "n_part_lines", "parts_cost"])


def q7_site_costs_fixed(t):
    wo = _wo_with_site(t)
    g = wo.groupby("site_id")
    out = t["sites"][["site_id"]].copy()
    out["n_work_orders"] = out["site_id"].map(g.size()).fillna(0).astype(int)
    out["labor_hours"] = out["site_id"].map(g["labor_hours"].sum()).fillna(0.0)
    out["parts_cost"] = out["site_id"].map(g["parts_cost"].sum()).fillna(0.0)
    return _rows(out, ["site_id", "n_work_orders", "labor_hours", "parts_cost"])


# ------------------------------------------------------------------ challenge
def c1_site_type_costs(t):
    wo = _wo_with_site(t)
    out = wo.groupby(["site_id", "wo_type"]).agg(n_orders=("wo_id", "size"), parts_cost=("parts_cost", "sum")).reset_index()
    return _rows(out, ["site_id", "wo_type", "n_orders", "parts_cost"])


def c2_machine_parts(t):
    pu = t["parts_used"].merge(t["work_orders"][["wo_id", "machine_id"]], on="wo_id")
    g = pu.groupby("machine_id")
    out = t["machines"][["machine_id"]].copy()
    out["n_distinct_parts"] = out["machine_id"].map(g["part_id"].nunique()).fillna(0).astype(int)
    out["total_quantity"] = out["machine_id"].map(g["quantity"].sum()).fillna(0).astype(int)
    return _rows(out, ["machine_id", "n_distinct_parts", "total_quantity"])


def c3_technician_load(t):
    wo = t["work_orders"].dropna(subset=["tech_id"])
    g = wo.groupby("tech_id")
    out = t["technicians"][["tech_id"]].copy()
    out["n_orders"] = out["tech_id"].map(g.size()).fillna(0).astype(int)
    out["labor_hours"] = out["tech_id"].map(g["labor_hours"].sum()).fillna(0.0)
    out["n_machines"] = out["tech_id"].map(g["machine_id"].nunique()).fillna(0).astype(int)
    return _rows(out, ["tech_id", "n_orders", "labor_hours", "n_machines"])


def c4_site_scorecard(t):
    m = t["machines"]
    wo = _wo_with_site(t)
    de = t["downtime_events"].merge(m[["machine_id", "site_id"]], on="machine_id")
    out = t["sites"][["site_id"]].copy()
    out["n_machines"] = out["site_id"].map(m.groupby("site_id").size()).fillna(0).astype(int)
    out["downtime_hours"] = out["site_id"].map(de.groupby("site_id")["hours"].sum()).fillna(0.0)
    out["labor_hours"] = out["site_id"].map(wo.groupby("site_id")["labor_hours"].sum()).fillna(0.0)
    out["parts_cost"] = out["site_id"].map(wo.groupby("site_id")["parts_cost"].sum()).fillna(0.0)
    return _rows(out, ["site_id", "n_machines", "downtime_hours", "labor_hours", "parts_cost"])


def c5_parts_never_corrective(t):
    pu = t["parts_used"].merge(t["work_orders"][["wo_id", "wo_type"]], on="wo_id")
    used = set(pu.loc[pu["wo_type"] == "corrective", "part_id"])
    out = t["parts"][~t["parts"]["part_id"].isin(used)]
    return _rows(out, ["part_id", "part_name"])


LAB = {
    "q1_machines_per_site": (q1_machines_per_site, False),
    "q2_unassigned_technicians": (q2_unassigned_technicians, False),
    "q3_machine_hours": (q3_machine_hours, False),
    "q4_corrective_2025_per_site": (q4_corrective_2025_per_site, False),
    "q5_type_summary": (q5_type_summary, False),
    "q6_expensive_orders": (q6_expensive_orders, True),
    "q7_site_costs_fixed": (q7_site_costs_fixed, False),
}

# name -> (oracle, minimal key of the result)
CHALLENGE = {
    "c1_site_type_costs": (c1_site_type_costs, ["site_id", "wo_type"]),
    "c2_machine_parts": (c2_machine_parts, ["machine_id"]),
    "c3_technician_load": (c3_technician_load, ["tech_id"]),
    "c4_site_scorecard": (c4_site_scorecard, ["site_id"]),
    "c5_parts_never_corrective": (c5_parts_never_corrective, ["part_id"]),
}
