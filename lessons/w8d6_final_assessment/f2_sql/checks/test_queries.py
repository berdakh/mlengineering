"""Result-set checks for f2. Row order is never checked; numbers are compared to 2 decimals."""
import pandas as pd


def norm(rows):
    """Order-insensitive, type-tolerant view of a result set."""
    def cell(v):
        if v is None or (isinstance(v, float) and v != v):
            return None
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return f"{float(v):.2f}"
        return str(v)
    return sorted((tuple(cell(v) for v in row) for row in rows), key=repr)


def assert_same(got_rows, ncols, expected_rows, columns):
    assert ncols == len(columns), f"expected {len(columns)} columns {columns}, got {ncols}"
    got, exp = norm(got_rows), norm(expected_rows)
    assert len(got) == len(exp), f"expected {len(exp)} rows, got {len(got)}"
    diff = [(g, e) for g, e in zip(got, exp) if g != e]
    assert not diff, f"{len(diff)} rows differ; first (got, expected): {diff[0]}"


def delivered_2025(sh):
    return sh[(sh.status == "delivered") & sh.ship_date.between("2025-01-01", "2025-12-31")]


def test_q1_fee_by_region(run_sql, tables):
    m = delivered_2025(tables["shipments"]).merge(tables["accounts"], on="account_id")
    m["region"] = m["region"].fillna("UNKNOWN")
    g = m.groupby("region").agg(n=("account_id", "nunique"), fee=("fee", "sum")).reset_index()
    rows, ncols = run_sql("q1.sql")
    assert_same(rows, ncols, g.itertuples(index=False, name=None), ["region", "n_shipping_accounts", "total_fee"])


def test_q2_signups_without_complaints(run_sql, tables):
    a = tables["accounts"]
    with_complaint = set(tables["complaints"].account_id.dropna())
    exp = a[a.signup_date.between("2025-01-01", "2025-12-31") & ~a.account_id.isin(with_complaint)]
    assert len(exp) > 0
    rows, ncols = run_sql("q2.sql")
    assert_same(rows, ncols, [(x,) for x in exp.account_id], ["account_id"])


def test_q3_enterprise_fee_and_complaints(run_sql, tables):
    a = tables["accounts"]
    ent = a[a.tier == "enterprise"][["account_id"]]
    sh = tables["shipments"]
    fee = sh[sh.status == "delivered"].groupby("account_id").fee.sum()
    nc = tables["complaints"].dropna(subset=["account_id"]).groupby("account_id").size()
    exp = ent.assign(total=ent.account_id.map(fee).fillna(0.0), n=ent.account_id.map(nc).fillna(0).astype(int))
    rows, ncols = run_sql("q3.sql")
    assert_same(rows, ncols, exp.itertuples(index=False, name=None),
                ["account_id", "total_delivered_fee", "n_complaints"])


def test_q4_latest_shipment_lost(run_sql, tables):
    sh = tables["shipments"].sort_values(["ship_date", "shipment_id"])
    last = sh.groupby("account_id").tail(1)
    exp = last[last.status == "lost"][["account_id", "shipment_id", "ship_date"]]
    assert len(exp) > 0
    rows, ncols = run_sql("q4.sql")
    assert_same(rows, ncols, exp.itertuples(index=False, name=None), ["account_id", "shipment_id", "ship_date"])


def test_q5_monthly_fee_change(run_sql, tables):
    d = delivered_2025(tables["shipments"])
    g = d.groupby(d.ship_date.str[:7]).fee.sum().sort_index()
    exp = pd.DataFrame({"month": g.index, "fee": g.values, "change": g.diff().values})
    exp_rows = [(m, f, None if pd.isna(ch) else ch) for m, f, ch in exp.itertuples(index=False, name=None)]
    rows, ncols = run_sql("q5.sql")
    assert_same(rows, ncols, exp_rows, ["month", "total_fee", "change_vs_prev"])
