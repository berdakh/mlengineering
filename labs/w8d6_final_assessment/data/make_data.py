"""Generate the SYNTHETIC data for the w8d6 final assessment.

Two invented businesses, both simulated from the seeded processes below. They exist so the
assessment has known, planted properties (data-quality defects, a join fan-out, leaky columns,
a generator ground truth). Scores obtained on them say nothing about real logistics or restaurants.

* "Parcelo" - a B2B parcel-shipping platform. Used by the parallel form of the diagnostic (f1-f6).
* "TableTop" - a restaurant-reservation service. Used by the final transfer task (t1).

    python labs/w8d6_final_assessment/data/make_data.py            # (re)write all files
    python labs/w8d6_final_assessment/data/make_data.py --check    # regenerate, compare with disk

Outputs (schemas in data/README.md):
    parcelo.db                 SQLite: accounts, shipments, complaints        (f2_sql)
    accounts_dirty.csv         dirty CRM export of business accounts          (f3_cleaning)
    lapse_train.csv / lapse_test.csv   monthly account snapshots, prepared    (f4_baseline)
    lapse_export_full.csv      monthly snapshots incl. extra export columns   (f5_leakage)
    reservations.csv           TableTop reservations (no generator truth)     (t1_transfer)
    ../f3_cleaning/checks/expected_clean.csv   ground truth for the cleaning checks
"""
from __future__ import annotations

import argparse
import hashlib
import io
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261206
N_ACCOUNTS = 700
HERE = Path(__file__).resolve().parent
EXPECTED_CLEAN = HERE.parent / "f3_cleaning" / "checks" / "expected_clean.csv"
FEES = {"starter": 49.0, "business": 149.0, "enterprise": 399.0}
STARTER_FEE_AFTER_INCREASE = 59.0
FEE_INCREASE = pd.Timestamp("2025-09-01")
SNAPSHOTS = pd.date_range("2025-01-01", "2025-12-01", freq="MS")
MONTHS = pd.date_range("2024-01-01", "2025-12-01", freq="MS")
TRAIN_END = pd.Timestamp("2025-08-01")  # f4: train = snapshots up to and including this date
REGIONS = ["ALA", "AST", "SHY", "KRG", "AKT"]


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


# ====================================================================== Parcelo
def simulate_parcelo(seed: int = SEED) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    ids = [f"A{i:05d}" for i in range(1, N_ACCOUNTS + 1)]
    span = (pd.Timestamp("2025-10-31") - pd.Timestamp("2023-01-01")).days
    signup = pd.Timestamp("2023-01-01") + pd.to_timedelta(rng.integers(0, span + 1, N_ACCOUNTS), unit="D")
    region = rng.choice(REGIONS, N_ACCOUNTS, p=[0.35, 0.25, 0.15, 0.15, 0.10]).astype(object)
    region[rng.random(N_ACCOUNTS) < 0.05] = None
    tier = rng.choice(["starter", "business", "enterprise"], N_ACCOUNTS, p=[0.5, 0.32, 0.18])
    channel = rng.choice(["inbound", "outbound", "partner", "marketplace"], N_ACCOUNTS, p=[0.4, 0.25, 0.2, 0.15])
    activity = rng.standard_normal(N_ACCOUNTS)  # latent, never exported
    employees = np.round(np.exp(rng.normal(3.2, 1.1, N_ACCOUNTS))).astype(int).clip(1, 40000)
    accounts = pd.DataFrame({"account_id": ids, "signup_date": signup, "region": region,
                             "tier": tier, "sales_channel": channel})

    shipments, complaints, snaps = [], [], []
    for i, aid in enumerate(ids):
        a, s_date, tr = activity[i], signup[i], tier[i]
        lost_hist: list[pd.Timestamp] = []
        complaint_times: list[pd.Timestamp] = []
        lapse_date = None
        acct_ships = []
        for m in MONTHS:
            if m <= s_date:
                continue
            fee = STARTER_FEE_AFTER_INCREASE if (tr == "starter" and m >= FEE_INCREASE) else FEES[tr]
            # --- snapshot on the 1st of each 2025 month, before anything of that month is known
            if m >= SNAPSHOTS[0]:
                tenure = (m - s_date).days
                ships_30d = sum(1 for r in acct_ships if m - pd.Timedelta(days=30) <= r["ship_date"] < m)
                kg = float(np.round(rng.gamma(3.0, 1.6 * np.exp(0.15 * a)), 2))
                if rng.random() < 0.03:
                    kg = np.nan
                c90 = sum(1 for t in complaint_times if m - pd.Timedelta(days=90) <= t < m)
                l90 = sum(1 for d in lost_hist if m - pd.Timedelta(days=90) <= d < m)
                promo = int(rng.random() < 0.15)
                increase = int(tr == "starter" and m >= FEE_INCREASE)
                logit = (-2.9 - 0.18 * (ships_30d - 4) + 0.55 * c90 + 0.8 * l90 - 0.5 * promo
                         + 0.6 * (tenure < 90) + 0.6 * increase - 0.5 * a)
                lapsed = int(rng.random() < _sigmoid(logit))
                snaps.append({
                    "account_id": aid, "snapshot_date": m, "tier": tr, "region": region[i],
                    "sales_channel": channel[i], "tenure_days": tenure, "monthly_fee": fee,
                    "employees": int(employees[i]), "shipments_30d": ships_30d, "avg_parcel_kg": kg,
                    "complaints_90d": c90, "lost_parcels_90d": l90, "promo_active": promo,
                    "lapsed_30d": lapsed,
                    # written AFTER the outcome window by the account-management CRM:
                    "winback_call_logged": int(rng.random() < (0.65 if lapsed else 0.03)),
                })
                if lapsed:
                    lapse_date = m + pd.Timedelta(days=int(rng.integers(1, 30)))
            # --- this month's shipments
            n = int(rng.poisson(np.exp(0.9 + 0.35 * a)))
            for _ in range(n):
                day = m + pd.Timedelta(days=int(rng.integers(0, 28)))
                if lapse_date is not None and day >= lapse_date:
                    continue
                status = "lost" if rng.random() < 0.05 else ("returned" if rng.random() < 0.04 else "delivered")
                cost = float(np.round(rng.uniform(6, 45), 2))
                acct_ships.append({"account_id": aid, "ship_date": day, "fee": cost, "status": status})
                if status == "lost":
                    lost_hist.append(day)
                    if rng.random() < 0.6:  # re-shipped the same day; it arrives
                        acct_ships.append({"account_id": aid, "ship_date": day, "fee": cost, "status": "delivered"})
            # --- complaints during this month
            if m >= pd.Timestamp("2024-10-01"):
                for _ in range(int(rng.poisson(0.1 * np.exp(-0.3 * a)))):
                    opened = m + pd.Timedelta(days=int(rng.integers(0, 28)), minutes=int(rng.integers(0, 1440)))
                    if lapse_date is None or opened < lapse_date:
                        complaint_times.append(opened)
                        resolved = None if rng.random() < 0.1 else opened + pd.Timedelta(hours=int(rng.integers(1, 120)))
                        complaints.append({"account_id": aid, "opened_at": opened,
                                           "category": str(rng.choice(["damage", "delay", "billing", "other"])),
                                           "resolved_at": resolved})
            if lapse_date is not None:
                break
        last_ship = max((r["ship_date"] for r in acct_ships), default=None)
        for r in snaps[::-1]:
            if r["account_id"] != aid:
                break
            # warehouse-system export column: computed from the FULL shipment history
            r["last_pickup_offset_days"] = (last_ship - r["snapshot_date"]).days if last_ship is not None else -999
        shipments.extend(acct_ships)

    for _ in range(50):  # complaints from the public web form, not linked to an account
        opened = pd.Timestamp("2025-01-01") + pd.Timedelta(minutes=int(rng.integers(0, 365 * 1440)))
        complaints.append({"account_id": None, "opened_at": opened, "category": "other", "resolved_at": None})

    shipments = pd.DataFrame(shipments).sort_values(["ship_date", "account_id"], kind="stable").reset_index(drop=True)
    shipments.insert(0, "shipment_id", np.arange(1, len(shipments) + 1))
    complaints = pd.DataFrame(complaints).sort_values("opened_at", kind="stable").reset_index(drop=True)
    complaints.insert(0, "complaint_id", np.arange(1, len(complaints) + 1))
    export = pd.DataFrame(snaps).sort_values(["snapshot_date", "account_id"], kind="stable").reset_index(drop=True)
    export["last_pickup_offset_days"] = export["last_pickup_offset_days"].astype(int)

    clean_cols = [c for c in export.columns if c not in ("winback_call_logged", "last_pickup_offset_days")]
    lapse_train = export.loc[export.snapshot_date <= TRAIN_END, clean_cols]
    lapse_test = export.loc[export.snapshot_date > TRAIN_END, clean_cols]
    dirty, expected = _dirty_accounts(rng, accounts, employees)
    return {"accounts": accounts, "shipments": shipments, "complaints": complaints, "export": export,
            "lapse_train": lapse_train, "lapse_test": lapse_test, "dirty": dirty, "expected_clean": expected}


def _dirty_accounts(rng, accounts: pd.DataFrame, employees: np.ndarray):
    """A CRM export of business accounts with planted defects, plus the ground truth."""
    rows, truth = [], []
    for i, c in enumerate(accounts.itertuples(index=False)):
        d = c.signup_date
        u = rng.random()
        if u < 0.55:
            s_date = d.strftime("%Y-%m-%d")
        elif u < 0.85:
            s_date = d.strftime("%d.%m.%Y")
        else:  # local timestamp with UTC offset; the UTC calendar date is the true date
            utc = d + pd.Timedelta(hours=int(rng.integers(0, 24)), minutes=int(rng.integers(0, 60)))
            off = int(rng.choice([-7, -4, 0, 3, 5, 6]))
            local = utc + pd.Timedelta(hours=off)
            s_date = local.strftime("%Y-%m-%dT%H:%M:%S") + f"{'+' if off >= 0 else '-'}{abs(off):02d}:00"
        if pd.isna(c.region):
            s_region, t_region = str(rng.choice(["", "n/a", "?"])), None
        else:
            t_region = c.region
            s_region = str(rng.choice([c.region, c.region.lower(), f"{c.region} ", f" {c.region.title()}"],
                                      p=[0.7, 0.1, 0.1, 0.1]))
        if rng.random() < 0.012:
            s_tier, t_tier = "platinum", None
        else:
            t_tier = c.tier
            s_tier = str(rng.choice([c.tier, c.tier.upper(), f" {c.tier}", c.tier.title() + " "], p=[0.7, 0.1, 0.1, 0.1]))
        fee = FEES[c.tier]
        u = rng.random()
        if u < 0.55:
            s_fee, s_unit = f"{fee:.2f}", "usd_month"
        elif u < 0.75:
            s_fee, s_unit = f"USD {fee:.2f}", "usd_month"
        else:  # billed annually; the export holds the annual amount
            s_fee, s_unit = f"{fee * 12:.2f}", "usd_year"
        u = rng.random()
        if u < 0.90:
            s_emp, t_emp = str(int(employees[i])), float(employees[i])
        elif u < 0.96:
            s_emp, t_emp = str(rng.choice(["-1", "99999"])), np.nan
        else:
            s_emp, t_emp = str(rng.choice(["0", "250000", "-40"])), np.nan
        upd = pd.Timestamp("2025-11-01") + pd.Timedelta(minutes=int(rng.integers(0, 30 * 1440)))
        row = {"account_id": c.account_id, "signup_date": s_date, "region": s_region, "tier": s_tier,
               "fee": s_fee, "fee_unit": s_unit, "employees": s_emp,
               "updated_at": upd.strftime("%Y-%m-%d %H:%M:%S")}
        rows.append(row)
        truth.append({"account_id": c.account_id, "signup_date": d.strftime("%Y-%m-%d"), "region": t_region,
                      "tier": t_tier, "monthly_fee_usd": fee, "employees": t_emp})
        u = rng.random()
        if u < 0.03:
            rows.append(dict(row))
        elif u < 0.08:  # stale earlier version: different tier, older updated_at
            stale = dict(row)
            other = [p for p in FEES if p != c.tier]
            stale_tier = str(rng.choice(other))
            stale["tier"] = stale_tier
            stale["fee"], stale["fee_unit"] = f"{FEES[stale_tier]:.2f}", "usd_month"
            stale["updated_at"] = (upd - pd.Timedelta(days=int(rng.integers(1, 200)))).strftime("%Y-%m-%d %H:%M:%S")
            rows.append(stale)
    dirty = pd.DataFrame(rows).iloc[rng.permutation(len(rows))].reset_index(drop=True)
    return dirty, pd.DataFrame(truth)


# ====================================================================== TableTop
TT_START, TT_END = pd.Timestamp("2024-01-01"), pd.Timestamp("2024-12-31")
TT_CUTOFF = pd.Timestamp("2024-10-01")
TT_LEAKY = ["customer_no_show_rate", "table_released_at", "reminder_reply"]


def simulate_tabletop(seed: int = SEED, with_truth: bool = False) -> pd.DataFrame:
    """Reservations at 10 restaurants in 2024. One row per reservation, sorted by service date."""
    rng = np.random.default_rng(seed + 1)
    n_rest, n_cust = 10, 2600
    rest_ids = [f"R{i:02d}" for i in range(1, n_rest + 1)]
    rest_effect = rng.normal(0, 0.35, n_rest)
    reliability = rng.normal(0, 0.9, n_cust)  # latent per customer
    days = pd.date_range(TT_START, TT_END, freq="D")
    rows = []
    for day in days:
        weekend = day.dayofweek >= 4
        for r in range(n_rest):
            for _ in range(int(rng.poisson(3.2 if weekend else 1.8))):
                cust = int(rng.integers(0, n_cust))
                lead = int(min(rng.geometric(0.12) - 1, 60))
                booked = day - pd.Timedelta(days=lead) + pd.Timedelta(minutes=int(rng.integers(8 * 60, 22 * 60)))
                party = int(min(1 + rng.poisson(1.6), 12))
                channel = str(rng.choice(["phone", "web", "app", "partner"], p=[0.3, 0.35, 0.25, 0.1]))
                deposit = int(party >= 6 or rng.random() < 0.15)
                slot = str(rng.choice(["lunch", "dinner"], p=[0.35, 0.65]))
                logit = (-2.3 + 0.045 * lead + 0.55 * (channel == "partner") + 0.2 * (channel == "web")
                         - 1.1 * deposit + 0.08 * (party - 2) + 0.25 * weekend + rest_effect[r]
                         - 0.6 * reliability[cust] + 0.3 * (slot == "dinner"))
                rows.append({"restaurant_id": rest_ids[r], "customer_id": f"U{cust:05d}", "booked_at": booked,
                             "service_date": day, "slot": slot, "party_size": party, "lead_days": lead,
                             "channel": channel, "deposit_paid": deposit, "_logit": logit})
    df = pd.DataFrame(rows).sort_values(["service_date", "booked_at"], kind="stable").reset_index(drop=True)
    df["p_true"] = _sigmoid(df["_logit"].to_numpy())
    df["no_show"] = (rng.random(len(df)) < df["p_true"]).astype(int)
    # point-in-time history (correct): earlier service dates only
    df["prior_visits"] = df.groupby("customer_id").cumcount()
    shifted = df.groupby("customer_id")["no_show"].transform(lambda s: s.shift(1).fillna(0).cumsum())
    df["prior_no_shows"] = shifted.astype(int)
    # --- leaky columns written after the reservation's outcome or from the full history
    df["customer_no_show_rate"] = df.groupby("customer_id")["no_show"].transform("mean").round(3)
    released = df["service_date"] + pd.Timedelta(hours=20) + pd.to_timedelta(rng.integers(15, 45, len(df)), unit="m")
    df["table_released_at"] = released.where(df["no_show"] == 1)
    reply = np.where(df["no_show"] == 1, rng.choice(["none", "confirmed"], len(df), p=[0.8, 0.2]),
                     rng.choice(["none", "confirmed"], len(df), p=[0.25, 0.75]))
    df["reminder_reply"] = reply
    df.insert(0, "reservation_id", [f"B{i:06d}" for i in range(1, len(df) + 1)])
    cols = ["reservation_id", "restaurant_id", "customer_id", "booked_at", "service_date", "slot", "party_size",
            "lead_days", "channel", "deposit_paid", "prior_visits", "prior_no_shows",
            "customer_no_show_rate", "table_released_at", "reminder_reply", "no_show"]
    if with_truth:
        cols = cols + ["p_true"]
    return df[cols]


# ====================================================================== serialisation
def _csv(df: pd.DataFrame) -> bytes:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            vals = out[col].dropna()
            fmt = "%Y-%m-%d" if (vals.dt.normalize() == vals).all() else "%Y-%m-%d %H:%M:%S"
            out[col] = out[col].dt.strftime(fmt)
    buf = io.StringIO()
    out.to_csv(buf, index=False, lineterminator="\n")
    return buf.getvalue().encode()


SCHEMA = """
CREATE TABLE accounts (
    account_id TEXT PRIMARY KEY, signup_date TEXT NOT NULL, region TEXT,
    tier TEXT NOT NULL, sales_channel TEXT NOT NULL);
CREATE TABLE shipments (
    shipment_id INTEGER PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(account_id),
    ship_date TEXT NOT NULL, fee REAL NOT NULL, status TEXT NOT NULL);
CREATE TABLE complaints (
    complaint_id INTEGER PRIMARY KEY, account_id TEXT REFERENCES accounts(account_id),
    opened_at TEXT NOT NULL, category TEXT NOT NULL, resolved_at TEXT);
"""
TABLES = ("accounts", "shipments", "complaints")


def _db_rows(data):
    def rows(df, date_fmt):
        out = df.copy().astype(object)
        for col, fmt in date_fmt.items():
            out[col] = [None if pd.isna(v) else pd.Timestamp(v).strftime(fmt) for v in df[col]]

        def native(v):
            v = v.item() if hasattr(v, "item") else v
            return None if v is None or (isinstance(v, float) and v != v) or v is pd.NaT else v
        return [tuple(native(v) for v in r) for r in out.itertuples(index=False, name=None)]
    day, sec = "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"
    return {"accounts": rows(data["accounts"], {"signup_date": day}),
            "shipments": rows(data["shipments"], {"ship_date": day}),
            "complaints": rows(data["complaints"], {"opened_at": sec, "resolved_at": sec})}


def write_db(path: Path, data) -> None:
    path.unlink(missing_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    for table, rows in _db_rows(data).items():
        conn.executemany(f"INSERT INTO {table} VALUES ({','.join('?' * len(rows[0]))})", rows)
    conn.commit()
    conn.execute("VACUUM")
    conn.close()


def _db_digest_from_file(path: Path) -> str:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    h = hashlib.sha256()
    for table in TABLES:
        h.update(repr(conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()).encode())
    conn.close()
    return h.hexdigest()


def _db_digest_from_data(data) -> str:
    h = hashlib.sha256()
    rows = _db_rows(data)
    for table in TABLES:
        h.update(repr(sorted(rows[table], key=lambda r: r[0])).encode())
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate the synthetic w8d6 assessment data.")
    ap.add_argument("--check", action="store_true", help="compare regenerated data with the files on disk")
    args = ap.parse_args()
    data = simulate_parcelo()
    files = {HERE / "accounts_dirty.csv": _csv(data["dirty"]),
             HERE / "lapse_train.csv": _csv(data["lapse_train"]),
             HERE / "lapse_test.csv": _csv(data["lapse_test"]),
             HERE / "lapse_export_full.csv": _csv(data["export"]),
             HERE / "reservations.csv": _csv(simulate_tabletop()),
             EXPECTED_CLEAN: _csv(data["expected_clean"])}
    if args.check:
        ok = True
        for path, content in files.items():
            same = path.is_file() and path.read_bytes() == content
            ok &= same
            print(f"{'same     ' if same else 'DIFFERENT'} {path.relative_to(HERE.parent)}")
        same = _db_digest_from_file(HERE / "parcelo.db") == _db_digest_from_data(data)
        ok &= same
        print(f"{'same     ' if same else 'DIFFERENT'} data/parcelo.db (table contents)")
        return 0 if ok else 1
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        print(f"wrote {path.relative_to(HERE.parent)}  {len(content) / 1e3:.0f} kB")
    write_db(HERE / "parcelo.db", data)
    print(f"wrote data/parcelo.db  {(HERE / 'parcelo.db').stat().st_size / 1e3:.0f} kB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
