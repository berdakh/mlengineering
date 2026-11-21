"""Result-set checks for a2. Row order is never checked; numbers are compared to 2 decimals."""
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


def paid_2025(inv):
    return inv[(inv.status == "paid") & inv.invoice_date.between("2025-01-01", "2025-12-31")]


def test_q1_revenue_by_country(run_sql, tables):
    m = paid_2025(tables["invoices"]).merge(tables["customers"], on="customer_id")
    m["country"] = m["country"].fillna("UNKNOWN")
    g = m.groupby("country").agg(n=("customer_id", "nunique"), revenue=("amount", "sum")).reset_index()
    rows, ncols = run_sql("q1.sql")
    assert_same(rows, ncols, g.itertuples(index=False, name=None), ["country", "n_paying_customers", "revenue"])


def test_q2_signups_without_tickets(run_sql, tables):
    c = tables["customers"]
    with_ticket = set(tables["tickets"].customer_id.dropna())
    exp = c[c.signup_date.between("2025-01-01", "2025-12-31") & ~c.customer_id.isin(with_ticket)]
    assert len(exp) > 0
    rows, ncols = run_sql("q2.sql")
    assert_same(rows, ncols, [(x,) for x in exp.customer_id], ["customer_id"])


def test_q3_premium_paid_and_tickets(run_sql, tables):
    c = tables["customers"]
    prem = c[c.plan == "premium"][["customer_id"]]
    inv = tables["invoices"]
    paid = inv[inv.status == "paid"].groupby("customer_id").amount.sum()
    ntk = tables["tickets"].dropna(subset=["customer_id"]).groupby("customer_id").size()
    exp = prem.assign(total_paid=prem.customer_id.map(paid).fillna(0.0),
                      n_tickets=prem.customer_id.map(ntk).fillna(0).astype(int))
    rows, ncols = run_sql("q3.sql")
    assert_same(rows, ncols, exp.itertuples(index=False, name=None), ["customer_id", "total_paid", "n_tickets"])


def test_q4_latest_invoice_failed(run_sql, tables):
    inv = tables["invoices"].sort_values(["invoice_date", "invoice_id"])
    last = inv.groupby("customer_id").tail(1)
    exp = last[last.status == "failed"][["customer_id", "invoice_id", "invoice_date"]]
    assert len(exp) > 0
    rows, ncols = run_sql("q4.sql")
    assert_same(rows, ncols, exp.itertuples(index=False, name=None), ["customer_id", "invoice_id", "invoice_date"])


def test_q5_monthly_revenue_change(run_sql, tables):
    p = paid_2025(tables["invoices"])
    g = p.groupby(p.invoice_date.str[:7]).amount.sum().sort_index()
    exp = pd.DataFrame({"month": g.index, "revenue": g.values, "change": g.diff().values})
    exp_rows = [(m, r, None if pd.isna(ch) else ch) for m, r, ch in exp.itertuples(index=False, name=None)]
    rows, ncols = run_sql("q5.sql")
    assert_same(rows, ncols, exp_rows, ["month", "revenue", "change_vs_prev"])
