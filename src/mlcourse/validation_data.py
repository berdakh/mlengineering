"""Small, seeded, synthetic datasets for Week 6 (validation and leakage). All data here is SYNTHETIC.

Every generator is deterministic for a given seed, fast (well under a second), and needs only NumPy and pandas,
so the notebooks run the same way in Colab and on your computer.

    from mlcourse.validation_data import make_machines, make_returns, make_saas_churn
    machines = make_machines()        # rows that belong together: many days per machine
    orders = make_returns()           # rows ordered in time, with a slowly changing world
    seats, data_dict = make_saas_churn()   # the Week 6 lab: a churn table with planted leaks

`plot_splits(...)` draws train / test folds as coloured bars, used in notebooks 21-23.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


# ============================================================================== machines (grouped rows)
def make_machines(n_machines: int = 40, days: int = 30, seed: int = 0) -> pd.DataFrame:
    """Daily sensor summaries of factory machines; label: did the machine report a fault the next day?

    Each machine has its own typical readings (an offset per sensor) and its own fault tendency that the sensors
    do not explain. So a flexible model can recognise a machine from its readings and "remember" how often it
    fails: that works for machines it has seen, and not at all for a new machine.

    Columns: machine_id, day (1..days), temperature, vibration, pressure, rpm, fault (0/1).
    """
    rng = np.random.default_rng(seed)
    offsets = rng.normal(0, 1.0, size=(n_machines, 4)) * np.array([6.0, 0.8, 4.0, 120.0])
    base = np.array([70.0, 2.0, 30.0, 1500.0])
    machine_bias = rng.normal(0, 1.6, size=n_machines)   # hidden: not visible in any sensor
    rows = []
    for m in range(n_machines):
        noise = rng.normal(0, 1.0, size=(days, 4)) * np.array([1.0, 0.25, 0.8, 15.0])
        readings = base + offsets[m] + noise
        vib = (readings[:, 1] - base[1]) / 0.5          # vibration above the fleet's normal level
        heat = (readings[:, 0] - base[0]) / 6.0
        p = _sigmoid(-0.8 + 1.0 * vib + 0.5 * heat + machine_bias[m])
        fault = (rng.random(days) < p).astype(int)
        for d in range(days):
            rows.append((f"M{m + 1:03d}", d + 1, *readings[d].round(2), fault[d]))
    return pd.DataFrame(rows, columns=["machine_id", "day", "temperature", "vibration", "pressure", "rpm", "fault"])


# ============================================================================== returns (time-ordered rows)
def make_returns(n_days: int = 240, orders_per_day: int = 20, seed: int = 0) -> pd.DataFrame:
    """Online orders over time; label: was the order returned?

    Part of the return rate depends on the order (price, discount, delivery time), and part on a slowly changing
    situation (a supplier with quality problems, a season) that no column records directly. The column
    `warehouse_backlog` drifts slowly too, so it acts like a clock: a flexible model can use it to look up "what
    was going on around that date" - possible when training rows surround the test day, impossible for the future.

    Columns: order_id, order_date, price, discount, delivery_days, warehouse_backlog, returned (0/1).
    Rows are sorted by date.
    """
    rng = np.random.default_rng(seed)
    regime = np.cumsum(rng.normal(0, 0.15, size=n_days))
    regime = regime - regime.mean()
    backlog = 200 + np.cumsum(rng.normal(0, 6.0, size=n_days))
    start = pd.Timestamp("2024-01-01")
    n = n_days * orders_per_day
    day = np.repeat(np.arange(n_days), orders_per_day)
    price = rng.lognormal(3.5, 0.6, size=n)
    discount = rng.choice([0.0, 0.1, 0.2, 0.3], size=n, p=[0.5, 0.25, 0.15, 0.1])
    delivery = rng.integers(1, 9, size=n)
    z = -1.4 + 0.8 * (np.log(price) - 3.5) + 3.0 * discount + 0.25 * (delivery - 4) + 0.9 * regime[day]
    returned = (rng.random(n) < _sigmoid(z)).astype(int)
    return pd.DataFrame({
        "order_id": np.arange(1, n + 1),
        "order_date": start + pd.to_timedelta(day, unit="D"),
        "price": price.round(2),
        "discount": discount,
        "delivery_days": delivery,
        "warehouse_backlog": (backlog[day] + rng.normal(0, 2.0, size=n)).round(1),
        "returned": returned,
    })


# ============================================================================== leakage demos (notebook 22)
def make_churn_with_leak(n: int = 1500, seed: int = 0) -> pd.DataFrame:
    """A customer churn table (one row per customer) with one planted target leak.

    `retention_call` is 1 when the retention team phoned the customer, which they do *after* a customer asks to
    cancel. It is recorded in the same export as the features, so it looks like any other column.
    Columns: customer_id, tenure_months, orders_90d, spend_90d, tickets_90d, discount_share, retention_call, churned.
    """
    rng = np.random.default_rng(seed)
    tenure = rng.integers(1, 60, size=n)
    orders = rng.poisson(3.0, size=n)
    spend = np.round(orders * rng.lognormal(3.3, 0.4, size=n), 2)
    tickets = rng.poisson(0.6, size=n)
    disc = np.round(rng.beta(2, 6, size=n), 3)
    z = 0.4 - 0.02 * tenure - 0.35 * orders + 0.45 * tickets + 1.0 * disc
    churned = (rng.random(n) < _sigmoid(z)).astype(int)
    call = np.where(churned == 1, rng.random(n) < 0.93, rng.random(n) < 0.03).astype(int)
    return pd.DataFrame({"customer_id": np.arange(10001, 10001 + n), "tenure_months": tenure, "orders_90d": orders,
                         "spend_90d": spend, "tickets_90d": tickets, "discount_share": disc,
                         "retention_call": call, "churned": churned})


def make_noise(n: int = 200, p: int = 2000, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Pure noise: `p` random features and a random 0/1 label. No model can beat 50% accuracy here."""
    rng = np.random.default_rng(seed)
    return rng.normal(size=(n, p)), rng.integers(0, 2, size=n)


# ============================================================================== the lab (notebook 24)
LAB_ISSUES = {
    "retention_offer_after_cancel": "a column that is filled in after the customer has already decided to leave",
    "last_login_measured_at_export": "a column measured on the export date, long after the prediction date",
    "duplicate_rows": "the same row appears more than once, so copies can land in train and test",
    "selection_fitted_on_all_rows": "a preprocessing step learned from every row, including the test rows",
    "same_company_in_train_and_test": "seats of one company are split between training and test",
    "training_on_future_months": "the model is trained on months that come after the months it is tested on",
    "class_imbalance": "fewer churned than staying rows",
    "missing_values_in_industry": "some companies have no industry recorded",
    "unscaled_features": "the numeric columns have very different scales",
    "too_many_trees": "the random forest has more trees than it needs",
    "plan_price_is_too_predictive": "the monthly price is a strong predictor of churn",
}
PLANTED = frozenset(["retention_offer_after_cancel", "last_login_measured_at_export", "duplicate_rows",
                     "selection_fitted_on_all_rows", "same_company_in_train_and_test",
                     "training_on_future_months"])
LAB_LEAKY_COLUMNS = ("retention_offer", "days_since_last_login")
LAB_ID_COLUMNS = ("seat_id", "company_id", "month")
LAB_TARGET = "churned"
N_EVENTS = 12


def _lab_companies(rng, n_companies: int, months: np.ndarray) -> list[tuple]:
    plans = np.array(["basic", "pro", "enterprise"])
    industries = np.array(["retail", "finance", "health", "education", "software", "logistics"])
    out = []
    for c in range(n_companies):
        plan = rng.choice(plans, p=[0.5, 0.35, 0.15])
        base_price = {"basic": 29.0, "pro": 79.0, "enterprise": 199.0}[plan]
        size = int(rng.integers(3, 13))
        out.append(dict(plan=plan, industry=rng.choice(industries), size=size,
                        price=round(base_price * rng.uniform(0.85, 1.15), 2), month=int(months[c]),
                        hidden=rng.normal(0, 1.5), engagement=rng.normal(0, 1.0)))
    return out


def _lab_rows(rng, companies: list[dict], first_company: int) -> pd.DataFrame:
    rows = []
    seat = 0
    for i, co in enumerate(companies):
        m = co["month"]
        drift = 0.05 * (m - 6)        # the world changes slowly: churn gets a little likelier month by month
        price_effect = 0.6 * (np.log(co["price"]) - 4.0) * (1.0 if m <= 8 else 1.6)   # a price rise after month 8
        seats = []
        for _ in range(co["size"]):
            logins = max(0, int(rng.normal(14 + 6 * co["engagement"], 5)))
            reports = int(rng.poisson(max(0.2, 3 + 1.5 * co["engagement"])))
            tickets = int(rng.poisson(0.5))
            events = rng.poisson(4.0, size=N_EVENTS)
            seats.append((logins, reports, tickets, events))
        mean_logins = np.mean([s[0] for s in seats])
        z = (-1.2 + drift + price_effect - 0.09 * (mean_logins - 14) - 0.6 * co["engagement"] + co["hidden"]
             + 0.2 * np.mean([s[2] for s in seats]))
        churned = int(rng.random() < _sigmoid(z))
        offer = int(rng.random() < (0.9 if churned else 0.02))
        for logins, reports, tickets, events in seats:
            seat += 1
            last_login = (rng.integers(40, 150) if churned else rng.integers(0, 12)) + int(rng.integers(0, 5))
            industry = co["industry"] if rng.random() > 0.08 else None
            rows.append(dict(seat_id=first_company * 100 + seat, company_id=f"C{first_company + i:04d}", month=m,
                             plan=co["plan"], industry=industry, company_size=co["size"], monthly_price=co["price"],
                             logins_30d=logins, reports_30d=reports, tickets_90d=tickets,
                             **{f"ev_{k + 1:02d}": int(events[k]) for k in range(N_EVENTS)},
                             retention_offer=offer, days_since_last_login=int(last_login), churned=churned))
    return pd.DataFrame(rows)


def make_saas_churn(seed: int = 0, n_companies: int = 360, dup_fraction: float = 0.12
                    ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The lab table: one row per user seat of a business customer (a company), with planted problems.

    A company is reviewed once, in its renewal `month` (1..12 of one year). `churned` = 1 if the company cancelled
    within 90 days after that month; every seat of a company has the same label. Returns (table, data_dictionary).
    """
    rng = np.random.default_rng(seed)
    months = rng.integers(1, 13, size=n_companies)
    df = _lab_rows(rng, _lab_companies(rng, n_companies, months), first_company=1)
    dups = df.sample(frac=dup_fraction, random_state=seed)
    df = pd.concat([df, dups]).sort_values(["month", "company_id", "seat_id"]).reset_index(drop=True)
    data_dict = pd.DataFrame([
        ("seat_id", "id of the user seat", "account creation"),
        ("company_id", "id of the customer company", "account creation"),
        ("month", "renewal month (1-12) in which the company was reviewed: the prediction date", "-"),
        ("plan", "subscription plan: basic, pro or enterprise", "renewal month"),
        ("industry", "industry of the company (sometimes missing)", "account creation"),
        ("company_size", "number of seats the company pays for", "renewal month"),
        ("monthly_price", "price per seat per month, in dollars", "renewal month"),
        ("logins_30d", "logins of this seat in the 30 days before the renewal month", "renewal month"),
        ("reports_30d", "reports created in the 30 days before the renewal month", "renewal month"),
        ("tickets_90d", "support tickets in the 90 days before the renewal month", "renewal month"),
        ("ev_01 ... ev_12", "counts of 12 product events in the 30 days before the renewal month", "renewal month"),
        ("retention_offer", "1 if the retention team sent a discount offer", "when the customer clicks 'cancel'"),
        ("days_since_last_login", "days since this seat last logged in", "export date (2026-03-31)"),
        ("churned", "label: the company cancelled within 90 days after the renewal month", "90 days after renewal"),
    ], columns=["column", "meaning", "known_at"])
    return df, data_dict


def make_saas_future(seed: int = 0, n_companies: int = 3000) -> pd.DataFrame:
    """Brand-new companies reviewed in the three months AFTER the lab table (months 13-15), without duplicates.

    This is what the model would really meet after deployment; the graders use it as the ground truth for the
    honest score. (Students do not get this data on the job, which is the whole point of honest validation.)
    """
    rng = np.random.default_rng(10_000 + seed)
    months = rng.integers(13, 16, size=n_companies)
    return _lab_rows(rng, _lab_companies(rng, n_companies, months), first_company=50_000)


# ============================================================================== pictures
def plot_splits(splits, n_rows: int | None = None, groups=None, title: str = "", ax=None):
    """Draw each (train_idx, test_idx) split as one horizontal bar: blue = train, orange = test, grey = unused.

    If `groups` is given, a thin strip at the bottom colours rows by group so you can see where groups go.
    """
    import matplotlib.pyplot as plt

    splits = [(np.asarray(a), np.asarray(b)) for a, b in splits]
    if n_rows is None:
        n_rows = 1 + max(int(max(a.max(initial=0), b.max(initial=0))) for a, b in splits)
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 0.45 * (len(splits) + (1 if groups is not None else 0)) + 0.9))
    for i, (tr, te) in enumerate(splits):
        row = np.full(n_rows, 0.0)
        row[tr] = 1.0
        row[te] = 2.0
        colours = np.array([[0.85, 0.85, 0.85], [0.22, 0.45, 0.75], [0.95, 0.55, 0.15]])[row.astype(int)]
        ax.imshow(colours[None, :, :], aspect="auto", extent=(0, n_rows, i + 0.9, i + 0.1))
    n_bars = len(splits)
    if groups is not None:
        codes = pd.factorize(pd.Series(groups))[0]
        cmap = plt.get_cmap("tab20")
        ax.imshow(np.array([cmap(c % 20)[:3] for c in codes])[None, :, :], aspect="auto",
                  extent=(0, n_rows, n_bars + 0.7, n_bars + 0.2))
        ax.set_yticks(list(np.arange(n_bars) + 0.5) + [n_bars + 0.45])
        ax.set_yticklabels([f"split {i + 1}" for i in range(n_bars)] + ["group"])
        ax.set_ylim(n_bars + 0.8, 0)
    else:
        ax.set_yticks(np.arange(n_bars) + 0.5)
        ax.set_yticklabels([f"split {i + 1}" for i in range(n_bars)])
        ax.set_ylim(n_bars, 0)
    ax.set_xlabel("row number (blue = train, orange = test, grey = not used)")
    ax.set_title(title)
    return ax
