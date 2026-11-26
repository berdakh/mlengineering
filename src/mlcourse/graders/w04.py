"""Week 4 graders: from data to features (notebooks 13-16).

The churn problem used all week (and defined in notebook 13):
* cutoff: a date; everything we know is what happened on or before it;
* active customer: at least one non-cancelled order on or before the cutoff;
* churned: an active customer with no non-cancelled order in the `horizon_days` days after the cutoff
  (cutoff < order_date <= cutoff + horizon_days).

Reference implementations below are deliberately written differently from the solutions in the notebooks,
so that the tests check behaviour, not one way of writing it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mlcourse.grader import exercise, register_quiz

# ---------------------------------------------------------------------------------------------- data
_DAY = pd.Timedelta(days=1)


def _orders_small() -> pd.DataFrame:
    """A tiny, hand-made orders table with every edge case we care about."""
    rows = [
        (1, 10, "2025-01-05", "delivered"), (2, 10, "2025-03-01", "delivered"), (3, 10, "2025-04-10", "delivered"),
        (4, 11, "2025-02-01", "cancelled"),  # customer 11: only a cancelled order before the cutoff -> not active
        (5, 11, "2025-04-02", "delivered"),
        (6, 12, "2025-03-31", "delivered"),  # exactly on the cutoff -> counts as "before"
        (7, 12, "2025-06-29", "delivered"),  # exactly cutoff + 90 days -> inside the label window
        (8, 13, "2025-01-20", "returned"), (9, 13, "2025-07-15", "delivered"),  # 13 buys again, but too late
        (10, 14, "2025-02-14", "delivered"), (11, 14, "2025-05-01", "cancelled"),  # cancelled later -> churned
        (12, 15, "2025-04-01", "delivered"),  # first order after the cutoff -> not active
        (13, 16, "2024-12-01", "shipped"), (14, 16, "2025-03-15", "delivered"), (15, 16, "2025-05-20", "shipped"),
    ]
    df = pd.DataFrame(rows, columns=["order_id", "customer_id", "order_date", "status"])
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["channel"] = "web"
    return df


SMALL_CUTOFF = pd.Timestamp("2025-03-31")


def _shop():
    from mlcourse.sql import sql

    orders = sql("SELECT * FROM orders", "shop")
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    items = sql("SELECT * FROM order_items", "shop")
    customers = sql("SELECT * FROM customers", "shop")
    customers["signup_date"] = pd.to_datetime(customers["signup_date"])
    tickets = sql("SELECT * FROM support_tickets", "shop")
    tickets["opened_at"] = pd.to_datetime(tickets["opened_at"])
    return orders, items, customers, tickets


_CACHE: dict = {}


def shop():
    if "shop" not in _CACHE:
        _CACHE["shop"] = _shop()
    o, i, c, t = _CACHE["shop"]
    return o.copy(), i.copy(), c.copy(), t.copy()


SHOP_CUTOFF = pd.Timestamp("2025-09-30")

# ----------------------------------------------------------------------------------- references


def _ref_order_values(items: pd.DataFrame) -> pd.Series:
    v = items.quantity * items.unit_price * (1 - items.discount)
    return v.groupby(items.order_id).sum().rename("order_value")


def _valid(orders):
    return orders[orders.status != "cancelled"]


def _ref_active(orders, cutoff):
    o = _valid(orders)
    return sorted(set(o.loc[o.order_date <= cutoff, "customer_id"]))


def _ref_labels(orders, cutoff, horizon_days=90):
    active = _ref_active(orders, cutoff)
    o = _valid(orders)
    later = o[(o.order_date > cutoff) & (o.order_date <= cutoff + horizon_days * _DAY)]
    bought = set(later.customer_id)
    return pd.DataFrame({"customer_id": active, "churned": [cid not in bought for cid in active]})


def _ref_recency(orders, cutoff):
    o = _valid(orders)
    o = o[o.order_date <= cutoff]
    return (cutoff - o.groupby("customer_id").order_date.max()).dt.days


def _ref_window_count(orders, cutoff, days):
    o = _valid(orders)
    active = _ref_active(orders, cutoff)
    w = o[(o.order_date > cutoff - days * _DAY) & (o.order_date <= cutoff)]
    return w.groupby("customer_id").size().reindex(active, fill_value=0)


def _ref_window_spend(orders, values, cutoff, days):
    o = _valid(orders).merge(values.rename("v"), left_on="order_id", right_index=True, how="left")
    active = _ref_active(orders, cutoff)
    w = o[(o.order_date > cutoff - days * _DAY) & (o.order_date <= cutoff)]
    return w.groupby("customer_id").v.sum().reindex(active, fill_value=0.0)


def _ref_cancel_rate(orders, cutoff):
    o = orders[orders.order_date <= cutoff]
    g = o.groupby("customer_id")
    return g.status.apply(lambda s: (s == "cancelled").mean())


# ------------------------------------------------------------------------------------- helpers


def _as_series(x, what):
    if isinstance(x, pd.DataFrame) and x.shape[1] == 1:
        x = x.iloc[:, 0]
    assert isinstance(x, pd.Series), f"{what} should return a pandas Series (got {type(x).__name__})"
    return x


def _ids(x):
    if isinstance(x, (pd.Series, pd.Index, np.ndarray, list, tuple, set)):
        return sorted(int(v) for v in x)
    raise AssertionError(f"expected a list/array/Series of customer ids, got {type(x).__name__}")


def _same_series(got, want, what, atol=1e-6):
    got = _as_series(got, what)
    missing = set(want.index) - set(got.index)
    extra = set(got.index) - set(want.index)
    assert not missing, f"{what}: {len(missing)} customer(s) missing, e.g. {sorted(missing)[:3]}"
    assert not extra, (f"{what}: {len(extra)} unexpected customer(s), e.g. {sorted(extra)[:3]} "
                       "(are you including customers who are not active at the cutoff?)")
    g = got.reindex(want.index).astype(float)
    bad = ~np.isclose(g.values, want.astype(float).values, atol=atol, equal_nan=True)
    if bad.any():
        k = want.index[bad][0]
        raise AssertionError(f"{what}: wrong value for customer {k}: got {g[k]}, expected {want[k]}")


# ======================================================================== notebook 13: EDA


@exercise("w04.order_values", hint="value of one line = quantity x unit_price x (1 - discount); then add up per order")
def _(fn):
    items = pd.DataFrame({"order_id": [1, 1, 2, 3, 3, 3], "product_id": [1, 2, 1, 1, 2, 3],
                          "quantity": [2, 1, 1, 3, 1, 1], "unit_price": [10.0, 5.0, 8.0, 1.0, 2.0, 4.0],
                          "discount": [0.0, 0.1, 0.5, 0.0, 0.0, 0.25]})
    _same_series(fn(items), _ref_order_values(items), "order_values (small example)")
    _, real, _, _ = shop()
    got = _as_series(fn(real), "order_values")
    assert len(got) == real.order_id.nunique(), "one value per order expected"
    _same_series(got, _ref_order_values(real), "order_values (shop data)", atol=1e-4)


@exercise("w04.active_customers", hint="keep non-cancelled orders on or before the cutoff (<=), then unique customers")
def _(fn):
    o = _orders_small()
    got = _ids(fn(o, SMALL_CUTOFF))
    want = _ref_active(o, SMALL_CUTOFF)
    assert 11 not in got, "customer 11 only has a CANCELLED order before the cutoff: they are not active"
    assert 15 not in got, "customer 15's first order is after the cutoff: they are not active yet"
    assert 12 in got, "customer 12 ordered exactly ON the cutoff date: that counts as before (use <=)"
    assert got == want, f"expected {len(want)} active customers, got {len(got)}"
    real, *_ = shop()
    assert _ids(fn(real, SHOP_CUTOFF)) == _ref_active(real, SHOP_CUTOFF), "wrong result on the shop data"


@exercise("w04.churn_labels", hint="a customer churned if they have NO non-cancelled order with cutoff < date <= cutoff + horizon")
def _(fn):
    o = _orders_small()
    for horizon in (90, 30):
        got = fn(o, SMALL_CUTOFF, horizon)
        assert isinstance(got, pd.DataFrame), "return a DataFrame with columns customer_id and churned"
        assert {"customer_id", "churned"} <= set(got.columns), "columns must be customer_id and churned"
        want = _ref_labels(o, SMALL_CUTOFF, horizon).set_index("customer_id").churned
        g = got.set_index("customer_id").churned.astype(bool)
        assert sorted(g.index) == sorted(want.index), ("one row per ACTIVE customer expected "
                                                      f"({len(want)} rows), got {len(g)}")
        for cid in want.index:
            if bool(g[cid]) != bool(want[cid]):
                note = {12: "customer 12's next order is exactly 90 days later: inside the window (<=).",
                        13: "customer 13 buys again only after the window closes.",
                        14: "customer 14's later order was cancelled: cancelled orders do not count."}.get(cid, "")
                raise AssertionError(f"horizon {horizon} days: customer {cid} should have churned={bool(want[cid])}. {note}")
    real, *_ = shop()
    got = fn(real, SHOP_CUTOFF, 90)
    want = _ref_labels(real, SHOP_CUTOFF, 90)
    assert len(got) == len(want), f"shop data: {len(want)} active customers expected, got {len(got)}"
    rate = got.churned.astype(float).mean()
    assert abs(rate - want.churned.mean()) < 1e-9, f"shop data: churn rate {rate:.3f}, expected {want.churned.mean():.3f}"


@exercise("w04.churn_rate", hint="the mean of a True/False column is the share of True values")
def _(fn):
    for vals in ([True, False, False, True], [False] * 5, [1, 1, 1, 0]):
        df = pd.DataFrame({"customer_id": range(len(vals)), "churned": vals})
        got = fn(df)
        want = float(np.mean(np.array(vals, dtype=float)))
        assert np.isscalar(got) or isinstance(got, (float, np.floating)), "return one number"
        assert abs(float(got) - want) < 1e-9, f"for churned={vals} expected {want:.3f}, got {got}"
    assert 0 <= float(fn(pd.DataFrame({"customer_id": [1], "churned": [True]}))) <= 1, "a rate is between 0 and 1"


@exercise("w04.value_histogram", hint="fig, ax = plt.subplots(); ax.hist(values, bins=bins); then set the title and both axis labels")
def _(fn):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rng = np.random.default_rng(1)
    values = pd.Series(np.r_[rng.exponential(50, 300), [np.nan, np.nan]])
    for bins in (10, 25):
        out = fn(values, bins)
        assert isinstance(out, tuple) and len(out) == 2, "return (fig, ax)"
        fig, ax = out
        n_bars = len(ax.patches)
        assert n_bars == bins, f"expected {bins} bars for bins={bins}, got {n_bars}"
        heights = sum(p.get_height() for p in ax.patches)
        assert heights == 300, f"the bars should count the 300 non-missing values, they add up to {heights:.0f}"
        assert ax.get_title(), "give the chart a title"
        assert ax.get_xlabel() and ax.get_ylabel(), "label both axes (what is on x? what is on y?)"
        plt.close(fig)


@exercise("w04.churn_rate_by", hint="group by the column, take the mean of churned, sort from highest to lowest")
def _(fn):
    df = pd.DataFrame({"segment": ["a", "a", "b", "b", "b", "c"], "churned": [1, 0, 1, 1, 0, 0],
                       "city": ["x", "y", "x", "x", "y", "y"]})
    got = _as_series(fn(df, "segment"), "churn_rate_by")
    want = df.groupby("segment").churned.mean().sort_values(ascending=False)
    assert list(got.index) == list(want.index), f"expected groups in order {list(want.index)} (highest churn first), got {list(got.index)}"
    assert np.allclose(got.values.astype(float), want.values), "wrong churn rate for at least one group"
    got2 = _as_series(fn(df, "city"), "churn_rate_by")
    assert set(got2.index) == {"x", "y"}, "the function must work for any column name you pass"


@exercise("w04.rate_bar_chart", hint="ax.bar(rates.index, rates.values) - one bar per group - then label the y axis")
def _(fn):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rates = pd.Series({"consumer": 0.5, "student": 0.4, "small_business": 0.2})
    out = fn(rates)
    assert isinstance(out, tuple) and len(out) == 2, "return (fig, ax)"
    fig, ax = out
    heights = sorted(round(p.get_height(), 6) for p in ax.patches)
    assert heights == sorted(rates.round(6).tolist()), f"expected 3 bars with heights {sorted(rates.tolist())}, got {heights}"
    assert ax.get_ylabel(), "label the y axis (it is a churn rate)"
    plt.close(fig)


@exercise("w04.monthly_orders", hint="drop cancelled orders, then count orders per calendar month (dt.to_period('M'))")
def _(fn):
    o = _orders_small()
    got = _as_series(fn(o), "monthly_orders")
    keys = [str(k)[:7] for k in got.index]
    valid = _valid(o)
    want = valid.groupby(valid.order_date.dt.to_period("M")).size()
    want.index = [str(k) for k in want.index]
    assert sorted(keys) == sorted(want.index), f"expected months {sorted(want.index)}, got {sorted(keys)}"
    g = dict(zip(keys, got.values))
    for m, n in want.items():
        assert int(g[m]) == int(n), f"{m}: expected {n} non-cancelled orders, got {g[m]}"
    assert keys == sorted(keys), "months should be in time order"


register_quiz(
    "w04.13_q1", "c",
    "The cutoff splits time: features may only use what was known on or before it, labels come from after it.",
    {"a": "Using the whole history for features lets the future leak into the inputs.",
     "b": "Churn is about the future: a label needs a window after the cutoff.",
     "d": "The cutoff is a modelling choice made before looking at results, not a tuning knob."})
register_quiz(
    "w04.13_q2", "b",
    "About 47% churned: neither class is rare, so plain accuracy is not hopeless, but a model must beat about 53% "
    "(always predicting 'stays') to be useful.",
    {"a": "Balance does not depend on the model; it is a property of the labels.",
     "c": "A model that always predicts the majority class already gets about 53% right.",
     "d": "Class balance is measured, not guessed: it is the churn rate."})
register_quiz(
    "w04.13_q3", "d",
    "A histogram shows the distribution of one numeric variable: where values pile up, how spread out they are, outliers.",
    {"a": "Comparing groups is a job for a bar chart (or box plots).",
     "b": "Change over time is a line chart.",
     "c": "Two variables together is a scatter plot."})
register_quiz(
    "w04.13_q4", "a",
    "A difference between groups in exploration is a hint, not a cause: small groups are noisy and the groups may "
    "differ in other ways (for example, how long customers have been with the shop).",
    {"b": "Exploration suggests features; it does not prove that the feature causes churn.",
     "c": "Even large differences can come from a third variable.",
     "d": "Removing a group because it churns more would bias the data."})
register_quiz(
    "w04.13_q5", "b",
    "Each exploration should answer a question that changes a decision (which features to build, which window, "
    "whether the label definition is sensible).",
    {"a": "Many plots without questions produce pictures, not decisions.",
     "c": "Exploration comes before modelling: it shapes the features and the label.",
     "d": "Pretty plots are welcome, but a plot that changes nothing was not needed."})

# ======================================================================== notebook 14: features


def _future_invariance(fn_builder, what):
    """Changing anything AFTER the cutoff must not change the features."""
    o = _orders_small()
    base = fn_builder(o)
    o2 = o.copy()
    late = o2.order_date > SMALL_CUTOFF
    o2.loc[late, "status"] = "delivered"
    o2.loc[late, "order_date"] = o2.loc[late, "order_date"] + pd.Timedelta(days=3)
    extra = pd.DataFrame({"order_id": [99], "customer_id": [10], "order_date": [pd.Timestamp("2025-04-05")],
                          "status": ["delivered"], "channel": ["web"]})
    o2 = pd.concat([o2, extra], ignore_index=True)
    again = fn_builder(o2)
    a = base if isinstance(base, pd.DataFrame) else base.to_frame()
    b = again if isinstance(again, pd.DataFrame) else again.to_frame()
    assert a.sort_index().equals(b.sort_index()) or np.allclose(
        a.sort_index().astype(float).values, b.sort_index().astype(float).values, equal_nan=True), (
        f"{what} changed when we edited orders AFTER the cutoff: the feature is looking into the future")


@exercise("w04.recency_days", hint="last non-cancelled order on or before the cutoff, then (cutoff - that date).days")
def _(fn):
    o = _orders_small()
    _same_series(fn(o, SMALL_CUTOFF), _ref_recency(o, SMALL_CUTOFF), "recency_days")
    _future_invariance(lambda d: fn(d, SMALL_CUTOFF), "recency_days")
    real, *_ = shop()
    _same_series(fn(real, SHOP_CUTOFF), _ref_recency(real, SHOP_CUTOFF), "recency_days (shop data)")


@exercise("w04.orders_in_window", hint="window = (cutoff - days, cutoff]; count per active customer and fill 0 for those with none")
def _(fn):
    o = _orders_small()
    for days in (30, 90, 365):
        _same_series(fn(o, SMALL_CUTOFF, days), _ref_window_count(o, SMALL_CUTOFF, days), f"orders_in_window(days={days})")
    _future_invariance(lambda d: fn(d, SMALL_CUTOFF, 90), "orders_in_window")
    real, *_ = shop()
    _same_series(fn(real, SHOP_CUTOFF, 90), _ref_window_count(real, SHOP_CUTOFF, 90), "orders_in_window (shop data)")


@exercise("w04.spend_in_window", hint="join order values onto orders, keep the window, sum per customer, fill 0.0")
def _(fn):
    o = _orders_small()
    values = pd.Series(np.arange(1, len(o) + 1) * 10.0, index=o.order_id, name="order_value")
    for days in (60, 120):
        _same_series(fn(o, values, SMALL_CUTOFF, days), _ref_window_spend(o, values, SMALL_CUTOFF, days),
                     f"spend_in_window(days={days})")
    _future_invariance(lambda d: fn(d, pd.Series(10.0, index=range(1, 200)), SMALL_CUTOFF, 90), "spend_in_window")


@exercise("w04.tenure_days", hint="customers who signed up on or before the cutoff; (cutoff - signup_date).days")
def _(fn):
    c = pd.DataFrame({"customer_id": [1, 2, 3, 4], "signup_date": pd.to_datetime(
        ["2024-01-01", "2025-03-31", "2025-04-01", "2025-01-01"]), "segment": "consumer"})
    got = _as_series(fn(c, SMALL_CUTOFF), "tenure_days")
    want = pd.Series({1: 455, 2: 0, 4: 89})
    assert 3 not in set(got.index), "customer 3 signed up AFTER the cutoff: leave them out"
    _same_series(got, want, "tenure_days")


@exercise("w04.safe_ratio", hint="divide where the denominator is not zero; put 0.0 where it is")
def _(fn):
    num = pd.Series([1.0, 2.0, 0.0, 5.0], index=list("abcd"))
    den = pd.Series([2.0, 0.0, 0.0, 4.0], index=list("abcd"))
    got = _as_series(fn(num, den), "safe_ratio")
    assert not got.isna().any(), "no NaN allowed: a zero denominator should give 0.0"
    assert not np.isinf(got.astype(float)).any(), "no infinity allowed: a zero denominator should give 0.0"
    assert np.allclose(got.reindex(list("abcd")).astype(float), [0.5, 0.0, 0.0, 1.25]), "wrong ratio for at least one row"


@exercise("w04.cancel_rate", hint="all orders (any status) on or before the cutoff, then share of 'cancelled' per customer")
def _(fn):
    o = _orders_small()
    _same_series(fn(o, SMALL_CUTOFF), _ref_cancel_rate(o, SMALL_CUTOFF), "cancel_rate")
    _future_invariance(lambda d: fn(d, SMALL_CUTOFF), "cancel_rate")


@exercise("w04.one_hot", hint="one 0/1 column per KNOWN category, named f'{name}={category}'; unknown or missing -> all zeros")
def _(fn):
    s = pd.Series(["web", "app", None, "fax", "web"], name="channel")
    cats = ["app", "web", "marketplace"]
    got = fn(s, cats)
    assert isinstance(got, pd.DataFrame), "return a DataFrame"
    want_cols = [f"channel={c}" for c in cats]
    assert list(got.columns) == want_cols, f"expected columns {want_cols} (in this order), got {list(got.columns)}"
    assert len(got) == len(s), "one output row per input row"
    vals = got.astype(int).values
    assert vals[0].tolist() == [0, 1, 0] and vals[1].tolist() == [1, 0, 0], "wrong encoding for a known category"
    assert vals[2].sum() == 0, "a missing value should become a row of zeros"
    assert vals[3].sum() == 0, "an unknown category ('fax') should become a row of zeros, not a new column"
    assert vals[:, 2].sum() == 0, "a known category that never appears still gets its (all-zero) column"


@exercise("w04.standardize", hint="mean and std come from TRAIN only; apply the same numbers to both; std 0 -> zeros")
def _(fn):
    train = pd.Series([1.0, 2.0, 3.0, 4.0])
    other = pd.Series([10.0, 2.5])
    tr, ot = fn(train, other)
    mu, sd = train.mean(), train.std(ddof=0)
    assert np.allclose(np.asarray(tr, float), (train - mu) / sd), "train values are not standardised with the train mean and std (ddof=0)"
    assert np.allclose(np.asarray(ot, float), (other - mu) / sd), (
        "the other values must use the TRAIN mean and std, not their own (otherwise test data leaks into the scaling)")
    tr0, ot0 = fn(pd.Series([3.0, 3.0]), pd.Series([5.0]))
    assert np.allclose(np.asarray(tr0, float), 0) and np.allclose(np.asarray(ot0, float), 0), (
        "a constant column (std 0) should become zeros, not NaN or infinity")


@exercise("w04.fill_with_train_median", hint="median of the train values (ignoring NaN); fill both with that one number")
def _(fn):
    train = pd.Series([1.0, np.nan, 3.0, 100.0])
    other = pd.Series([np.nan, 7.0])
    a, b, med = fn(train, other)
    assert float(med) == 3.0, f"the train median is 3.0, got {med} (the median ignores missing values and is robust to the 100)"
    assert not pd.isna(a).any() and not pd.isna(b).any(), "no missing values may remain"
    assert list(np.asarray(b, float)) == [3.0, 7.0], "fill the other series with the TRAIN median, not its own"


@exercise("w04.customer_features", hint="build each feature with your earlier functions, all at the same cutoff, then join them on customer_id")
def _(fn):
    real, items, customers, _ = shop()
    values = _ref_order_values(items)
    got = fn(real, values, customers, SHOP_CUTOFF)
    assert isinstance(got, pd.DataFrame), "return a DataFrame indexed by customer_id"
    need = ["recency_days", "orders_90d", "spend_90d", "tenure_days", "cancel_rate"]
    missing = [c for c in need if c not in got.columns]
    assert not missing, f"missing columns: {missing}"
    active = _ref_active(real, SHOP_CUTOFF)
    assert sorted(got.index) == active, f"one row per active customer expected ({len(active)}), got {len(got)}"
    assert not got[need].isna().any().any(), "no missing values expected in these features"
    _same_series(got["recency_days"], _ref_recency(real, SHOP_CUTOFF), "recency_days column")
    _same_series(got["orders_90d"], _ref_window_count(real, SHOP_CUTOFF, 90), "orders_90d column")
    _same_series(got["spend_90d"], _ref_window_spend(real, values, SHOP_CUTOFF, 90), "spend_90d column", atol=1e-4)
    cr = _ref_cancel_rate(real, SHOP_CUTOFF).reindex(active)
    _same_series(got["cancel_rate"], cr, "cancel_rate column")
    # the future must not matter
    future = real.order_date > SHOP_CUTOFF
    real2 = real.copy()
    real2.loc[future, "status"] = "cancelled"
    again = fn(real2, values, customers, SHOP_CUTOFF)
    assert np.allclose(got[need].sort_index().values.astype(float), again[need].sort_index().values.astype(float)), (
        "the features changed when only orders AFTER the cutoff were edited: something looks into the future")


register_quiz(
    "w04.14_q1", "b",
    "At prediction time you only know the past. A feature computed with later data cannot be computed in "
    "production, so the model would be evaluated on information it will never have.",
    {"a": "Speed is not the issue; correctness is.",
     "c": "Future data is not 'extra signal'; it is the answer leaking into the question.",
     "d": "The rule applies to every feature, not only to the label."})
register_quiz(
    "w04.14_q2", "c",
    "The scaler's mean and standard deviation are learned parameters, like model weights. Learning them from the "
    "test set lets test information shape the model, so the test score is no longer a clean estimate of E_out.",
    {"a": "Scaling does change values, but that is the point; the issue is which rows the numbers come from.",
     "b": "Scaling test data is required; it must use the train parameters.",
     "d": "The effect can be small, but the estimate is still contaminated, and on small data it can be large."})
register_quiz(
    "w04.14_q3", "a",
    "Fixing the category list at training time means new categories cannot create new columns, so the model always "
    "receives the same inputs.",
    {"b": "pandas get_dummies on new data would create different columns, which breaks the model.",
     "c": "Dropping rows with new categories throws away real customers in production.",
     "d": "Alphabetical order is irrelevant; consistency is the point."})
register_quiz(
    "w04.14_q4", "d",
    "The median is not dragged by a few huge values, so it is a safer fill value for skewed amounts like spend.",
    {"a": "The mean is pulled by outliers: one big spender changes it a lot.",
     "b": "Zero is a real value for spend and would look like 'spent nothing'.",
     "c": "Dropping rows loses customers and can bias who is left."})
register_quiz(
    "w04.14_q5", "b",
    "A missing-indicator column lets the model learn that 'unknown' itself carries information "
    "(for example, customers who never gave a city).",
    {"a": "The indicator adds information; it does not remove rows.",
     "c": "It does not replace imputation; you still fill the value.",
     "d": "Models cannot use NaN directly in most scikit-learn estimators, which is why we fill."})

# ======================================================================== notebook 15: scikit-learn


def _toy_frame(n=200, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "recency_days": rng.integers(0, 300, n).astype(float),
        "orders_90d": rng.integers(0, 6, n).astype(float),
        "segment": rng.choice(["consumer", "student", "small_business"], n),
        "city": rng.choice(["Almaty", "Astana", None], n),
        "note": "ignore me",
    })
    df.loc[rng.choice(n, 10, replace=False), "recency_days"] = np.nan
    logit = 0.01 * df["recency_days"].fillna(150) - 0.8 * df["orders_90d"] + (df["segment"] == "student") * 0.5
    df["churned"] = (rng.random(n) < 1 / (1 + np.exp(-logit + 1))).astype(int)
    return df


NUM, CAT = ["recency_days", "orders_90d"], ["segment", "city"]


@exercise("w04.split_train_test", hint="train_test_split(X, y, test_size=..., random_state=seed, stratify=y)")
def _(fn):
    df = _toy_frame(200)
    Xtr, Xte, ytr, yte = fn(df, "churned", 0.25, 7)
    assert len(Xtr) == 150 and len(Xte) == 50, f"expected 150 train / 50 test rows, got {len(Xtr)} / {len(Xte)}"
    assert "churned" not in Xtr.columns, "the label column must not be in X (that would hand the answer to the model)"
    assert set(Xtr.index).isdisjoint(Xte.index), "a row appears in both train and test"
    assert len(ytr) == len(Xtr) and (ytr.index == Xtr.index).all(), "y_train must line up with X_train"
    rate = df.churned.mean()
    assert abs(ytr.mean() - rate) < 0.02 and abs(yte.mean() - rate) < 0.03, (
        "train and test churn rates differ too much from the overall rate: use stratify=y")
    again = fn(df, "churned", 0.25, 7)
    assert list(again[1].index) == list(Xte.index), "the same seed must give the same split (set random_state)"
    other = fn(df, "churned", 0.25, 8)
    assert list(other[1].index) != list(Xte.index), "a different seed should give a different split"


@exercise("w04.fitted_scaler", hint="StandardScaler().fit(X_train) returns the fitted scaler")
def _(fn):
    from sklearn.preprocessing import StandardScaler

    X = np.array([[1.0, 10.0], [3.0, 30.0], [5.0, 20.0]])
    sc = fn(X)
    assert isinstance(sc, StandardScaler), "return a StandardScaler"
    assert hasattr(sc, "mean_"), "the scaler has not been fitted (call .fit)"
    assert np.allclose(sc.mean_, X.mean(axis=0)), "the scaler should be fitted on exactly the rows you were given"


@exercise("w04.scale_train_test", hint="fit ONE scaler on X_train; transform both X_train and X_test with it")
def _(fn):
    Xtr = np.array([[0.0], [2.0], [4.0]])
    Xte = np.array([[100.0], [102.0]])
    a, b = fn(Xtr, Xte)
    mu, sd = 2.0, np.sqrt(8 / 3)
    assert np.allclose(np.asarray(a).ravel(), (Xtr.ravel() - mu) / sd), "train is not scaled with its own mean/std"
    assert np.allclose(np.asarray(b).ravel(), (Xte.ravel() - mu) / sd), (
        "the test rows should be scaled with the TRAIN mean/std, so they come out large (around 60): "
        "it looks like the scaler was fitted on the test rows")


@exercise("w04.numeric_transformer", hint="Pipeline([('impute', SimpleImputer(strategy='median')), ('scale', StandardScaler())])")
def _(fn):
    t = fn()
    assert hasattr(t, "fit_transform"), "return an (unfitted) transformer or Pipeline"
    X = pd.DataFrame({"a": [1.0, np.nan, 3.0, 5.0], "b": [10.0, 20.0, np.nan, 40.0]})
    out = np.asarray(t.fit_transform(X), float)
    assert out.shape == (4, 2), f"expected shape (4, 2), got {out.shape}"
    assert not np.isnan(out).any(), "missing values remain: add an imputer before the scaler"
    assert np.allclose(out.mean(axis=0), 0, atol=1e-9), "columns should be centred (mean 0) after scaling"
    filled_a = t.transform(pd.DataFrame({"a": [np.nan], "b": [20.0]}))
    assert np.isfinite(np.asarray(filled_a, float)).all(), "transforming new data with NaN must work too"


@exercise("w04.categorical_transformer", hint="impute the most frequent value, then OneHotEncoder(handle_unknown='ignore')")
def _(fn):
    t = fn()
    X = pd.DataFrame({"segment": ["a", "b", "a", None]})
    out = t.fit_transform(X)
    out = out.toarray() if hasattr(out, "toarray") else np.asarray(out)
    assert out.shape == (4, 2), f"2 categories seen in training -> 2 columns expected, got shape {out.shape}"
    assert not np.isnan(out.astype(float)).any(), "missing categories must be imputed, not left as NaN"
    try:
        new = t.transform(pd.DataFrame({"segment": ["zzz"]}))
    except Exception as err:  # noqa: BLE001
        raise AssertionError(f"a category never seen in training made it crash ({type(err).__name__}); "
                             "production data always contains surprises") from None
    new = new.toarray() if hasattr(new, "toarray") else np.asarray(new)
    assert new.sum() == 0, "an unseen category should become all zeros"


@exercise("w04.make_preprocessor", hint="ColumnTransformer([('num', numeric_transformer(), num_cols), ('cat', categorical_transformer(), cat_cols)])")
def _(fn):
    df = _toy_frame(120, seed=3)
    pre = fn(NUM, CAT)
    out = pre.fit_transform(df)
    out = out.toarray() if hasattr(out, "toarray") else np.asarray(out)
    n_cat = df["segment"].nunique() + df["city"].nunique()  # imputation fills None with a seen city
    assert out.shape == (120, 2 + n_cat), (f"expected {2 + n_cat} columns (2 numeric + {n_cat} one-hot), got {out.shape[1]}. "
                                          "Columns not listed (like 'note' or the label) must be dropped")
    assert not np.isnan(out.astype(float)).any(), "missing values remain in the output"
    new = df.head(3).copy()
    new["segment"] = ["unknown_segment", "consumer", "student"]
    try:
        pre.transform(new)
    except Exception as err:  # noqa: BLE001
        raise AssertionError(f"new data with an unseen category crashed the preprocessor ({type(err).__name__})") from None


@exercise("w04.make_model_pipeline", hint="Pipeline([('prep', make_preprocessor(...)), ('model', LogisticRegression(max_iter=1000))])")
def _(fn):
    df = _toy_frame(200, seed=4)
    pipe = fn(NUM, CAT)
    assert hasattr(pipe, "fit") and hasattr(pipe, "predict_proba"), "return a Pipeline that ends in a classifier"
    X, y = df.drop(columns="churned"), df["churned"]
    pipe.fit(X, y)
    p = pipe.predict_proba(X.head(5))
    assert p.shape == (5, 2) and np.allclose(p.sum(axis=1), 1), "predict_proba should give two probabilities per row"
    new = X.head(2).copy()
    new["city"] = ["Mars", None]
    pipe.predict(new)


@exercise("w04.train_test_accuracy", hint="pipe.fit(X_train, y_train) once; accuracy = (predictions == truth).mean() on each set")
def _(fn):
    from sklearn.base import clone
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    rng = np.random.default_rng(5)
    X = rng.normal(size=(300, 4))
    y = (X[:, 0] + 0.5 * rng.normal(size=300) > 0).astype(int)
    Xtr, Xte, ytr, yte = X[:200], X[200:], y[:200], y[200:]
    pipe = make_pipeline(StandardScaler(), LogisticRegression())
    ref = clone(pipe).fit(Xtr, ytr)
    out = fn(pipe, Xtr, ytr, Xte, yte)
    assert isinstance(out, tuple) and len(out) == 2, "return (train_accuracy, test_accuracy)"
    tr, te = map(float, out)
    assert abs(tr - (ref.predict(Xtr) == ytr).mean()) < 1e-9, "train accuracy is not what the model fitted on X_train gives"
    assert abs(te - (ref.predict(Xte) == yte).mean()) < 1e-9, "test accuracy is not what the model fitted on X_train gives"
    assert np.array_equal(pipe.predict(Xte), ref.predict(Xte)), (
        "after your function the pipeline should be the one fitted on the TRAINING data only")


@exercise("w04.cv_accuracy", hint="cross_val_score(pipe, X, y, cv=StratifiedKFold(k, shuffle=True, random_state=seed), scoring='accuracy')")
def _(fn):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_score

    rng = np.random.default_rng(6)
    X = rng.normal(size=(150, 3))
    y = (X[:, 1] > 0.2).astype(int)
    for k, seed in ((5, 0), (3, 42)):
        got = np.asarray(fn(LogisticRegression(), X, y, k, seed), float)
        want = cross_val_score(LogisticRegression(), X, y, cv=StratifiedKFold(k, shuffle=True, random_state=seed),
                               scoring="accuracy")
        assert got.shape == (k,), f"expected {k} scores (one per fold), got shape {got.shape}"
        assert np.allclose(np.sort(got), np.sort(want)), (f"k={k}, seed={seed}: scores differ from stratified, "
                                                          "shuffled k-fold with that seed")


register_quiz(
    "w04.15_q1", "a",
    "fit learns parameters from data; transform applies them; predict uses a fitted model. Every scikit-learn object "
    "speaks this same language, which is why they can be chained.",
    {"b": "transform does not learn anything new; it only applies what fit learned.",
     "c": "predict does not re-fit; a model must be fitted first.",
     "d": "fit_transform is a shortcut for fit then transform on the same data, nothing more."})
register_quiz(
    "w04.15_q2", "c",
    "Training accuracy is E_in: it is measured on the data the model saw, so it is optimistic. The test accuracy "
    "estimates E_out, which is what you will get on new customers.",
    {"a": "A higher number on seen data is expected, not a sign of a better model.",
     "b": "The gap is normal; a very large gap suggests overfitting.",
     "d": "Both are measured; they answer different questions."})
register_quiz(
    "w04.15_q3", "b",
    "In a Pipeline, cross-validation and fit see the whole chain, so the imputer and scaler are re-fitted inside "
    "each training fold and never see the validation rows.",
    {"a": "Pipelines do not make models more accurate by themselves.",
     "c": "You still need a separate test set; a Pipeline prevents leakage, it does not replace testing.",
     "d": "Pipelines work with any estimator, not only linear models."})
register_quiz(
    "w04.15_q4", "d",
    "handle_unknown='ignore' turns a category never seen in training into all-zero columns instead of an error, "
    "which is what you want when tomorrow's data contains a new city.",
    {"a": "It does not learn new categories after training.",
     "b": "It does not drop rows.",
     "c": "Unknown categories are not mapped to the most frequent one by the encoder."})
register_quiz(
    "w04.15_q5", "b",
    "Five folds give five estimates; their spread shows how much the score depends on which rows happened to be held "
    "out, which a single split hides.",
    {"a": "Cross-validation does not make the model better; it measures it.",
     "c": "The test set stays untouched; cross-validation runs on the training data.",
     "d": "Each fold is scored on rows it did not train on."})

# ======================================================================== notebook 16: lab


def _ref_lab_features(customers, orders, items, tickets, cutoff):
    values = _ref_order_values(items)
    active = _ref_active(orders, cutoff)
    f = pd.DataFrame(index=pd.Index(active, name="customer_id"))
    f["recency_days"] = _ref_recency(orders, cutoff)
    f["orders_30d"] = _ref_window_count(orders, cutoff, 30)
    f["orders_90d"] = _ref_window_count(orders, cutoff, 90)
    f["orders_365d"] = _ref_window_count(orders, cutoff, 365)
    f["spend_90d"] = _ref_window_spend(orders, values, cutoff, 90)
    f["spend_365d"] = _ref_window_spend(orders, values, cutoff, 365)
    f["cancel_rate"] = _ref_cancel_rate(orders, cutoff).reindex(active)
    c = customers.set_index("customer_id")
    f["tenure_days"] = (cutoff - c["signup_date"]).dt.days.reindex(active)
    t = tickets[(tickets.opened_at <= cutoff) & (tickets.opened_at > cutoff - 90 * _DAY)]
    f["tickets_90d"] = t.groupby("customer_id").size().reindex(active, fill_value=0)
    f["segment"] = c["segment"].reindex(active)
    f["city"] = c["city"].reindex(active)
    return f


LAB_NUMERIC = ["recency_days", "orders_30d", "orders_90d", "orders_365d", "spend_90d", "spend_365d",
               "cancel_rate", "tenure_days", "tickets_90d"]
LAB_CATEGORICAL = ["segment", "city"]


@exercise("w04.lab_labels", hint="reuse the churn definition: active at the cutoff, churned if no non-cancelled order within 90 days after")
def _(fn):
    real, *_ = shop()
    for cutoff in (SHOP_CUTOFF, pd.Timestamp("2025-06-30")):
        got = fn(real, cutoff)
        want = _ref_labels(real, cutoff, 90)
        assert isinstance(got, pd.DataFrame) and {"customer_id", "churned"} <= set(got.columns), (
            "return a DataFrame with customer_id and churned")
        assert len(got) == len(want), f"cutoff {cutoff.date()}: {len(want)} active customers expected, got {len(got)}"
        g = got.set_index("customer_id").churned.astype(bool).reindex(want.customer_id)
        assert (g.values == want.churned.values).all(), f"cutoff {cutoff.date()}: some labels are wrong"


@exercise("w04.lab_features", hint="one row per active customer; build each column with the window helpers; segment and city come from customers")
def _(fn):
    real, items, customers, tickets = shop()
    got = fn(customers, real, items, tickets, SHOP_CUTOFF)
    want = _ref_lab_features(customers, real, items, tickets, SHOP_CUTOFF)
    assert isinstance(got, pd.DataFrame), "return a DataFrame indexed by customer_id"
    missing = [c for c in want.columns if c not in got.columns]
    assert not missing, f"missing columns: {missing}"
    assert sorted(got.index) == sorted(want.index), f"one row per active customer expected ({len(want)}), got {len(got)}"
    for col in LAB_NUMERIC:
        _same_series(got[col], want[col], col, atol=1e-4)
    for col in LAB_CATEGORICAL:
        g = got[col].reindex(want.index)
        same = (g == want[col]) | (g.isna() & want[col].isna())
        assert same.all(), f"{col}: values do not match the customers table (keep missing as missing; the pipeline imputes)"
    real2 = real.copy()
    real2.loc[real2.order_date > SHOP_CUTOFF, "status"] = "cancelled"
    t2 = tickets.copy()
    t2.loc[t2.opened_at > SHOP_CUTOFF, "topic"] = "refund"
    t2 = pd.concat([t2, t2[t2.opened_at > SHOP_CUTOFF]], ignore_index=True)
    again = fn(customers, real2, items, t2, SHOP_CUTOFF)
    assert np.allclose(got[LAB_NUMERIC].sort_index().values.astype(float),
                       again[LAB_NUMERIC].sort_index().values.astype(float)), (
        "features changed when only events AFTER the cutoff were edited: a feature is looking into the future")


@exercise("w04.lab_table", hint="join labels onto features by customer_id; every active customer must keep exactly one row")
def _(fn):
    real, items, customers, tickets = shop()
    feats = _ref_lab_features(customers, real, items, tickets, SHOP_CUTOFF)
    labels = _ref_labels(real, SHOP_CUTOFF, 90)
    got = fn(feats, labels)
    assert isinstance(got, pd.DataFrame) and "churned" in got.columns, "return the feature table with a churned column"
    assert len(got) == len(feats), f"{len(feats)} rows expected (one per customer), got {len(got)}: check the join"
    g = got["churned"].astype(int)
    if "customer_id" in got.columns:
        g.index = got["customer_id"]
    assert g.sort_index().tolist() == labels.set_index("customer_id").churned.astype(int).sort_index().tolist(), (
        "labels are attached to the wrong customers")
    for c in LAB_NUMERIC:
        assert c in got.columns, f"feature {c} was lost in the join"


@exercise("w04.lab_split", hint="stratified split on churned with test_size=0.25 and random_state=seed; drop churned (and customer_id) from X")
def _(fn):
    real, items, customers, tickets = shop()
    table = _ref_lab_features(customers, real, items, tickets, SHOP_CUTOFF).join(
        _ref_labels(real, SHOP_CUTOFF, 90).set_index("customer_id"))
    Xtr, Xte, ytr, yte = fn(table, 0)
    n = len(table)
    assert len(Xte) == round(0.25 * n) or abs(len(Xte) - 0.25 * n) <= 1, f"test should be 25% of {n} rows, got {len(Xte)}"
    assert "churned" not in Xtr.columns, "the label must not be a feature"
    assert set(Xtr.index).isdisjoint(Xte.index), "train and test overlap"
    assert abs(ytr.astype(float).mean() - yte.astype(float).mean()) < 0.03, "churn rates differ between train and test: stratify"


@exercise("w04.lab_pipeline", hint="the preprocessor from notebook 15 with these column lists, then LogisticRegression(max_iter=1000)")
def _(fn):
    real, items, customers, tickets = shop()
    table = _ref_lab_features(customers, real, items, tickets, SHOP_CUTOFF).join(
        _ref_labels(real, SHOP_CUTOFF, 90).set_index("customer_id"))
    pipe = fn(LAB_NUMERIC, LAB_CATEGORICAL)
    X, y = table.drop(columns="churned"), table["churned"].astype(int)
    pipe.fit(X, y)
    new = X.head(3).copy()
    new["city"] = ["Atlantis", None, "Almaty"]
    new["segment"] = ["enterprise", "student", "consumer"]
    p = pipe.predict_proba(new)
    assert p.shape == (3, 2) and np.isfinite(p).all(), "the pipeline must handle unseen and missing categories"


@exercise("w04.lab_report", hint="fit on train only; accuracy on train and test; the baseline always predicts the most common TRAIN label")
def _(fn):
    from sklearn.base import clone

    real, items, customers, tickets = shop()
    table = _ref_lab_features(customers, real, items, tickets, SHOP_CUTOFF).join(
        _ref_labels(real, SHOP_CUTOFF, 90).set_index("customer_id"))
    from sklearn.model_selection import train_test_split

    X, y = table.drop(columns="churned"), table["churned"].astype(int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    pipe = Pipeline([("prep", ColumnTransformer([
        ("num", Pipeline([("i", SimpleImputer(strategy="median")), ("s", StandardScaler())]), LAB_NUMERIC),
        ("cat", Pipeline([("i", SimpleImputer(strategy="most_frequent")), ("o", OneHotEncoder(handle_unknown="ignore"))]),
         LAB_CATEGORICAL)])), ("model", LogisticRegression(max_iter=1000))])
    out = fn(clone(pipe), Xtr, ytr, Xte, yte)
    assert isinstance(out, dict), "return a dict with train_accuracy, test_accuracy, baseline_accuracy"
    for k in ("train_accuracy", "test_accuracy", "baseline_accuracy"):
        assert k in out, f"missing key {k!r}"
    ref = clone(pipe).fit(Xtr, ytr)
    assert abs(out["train_accuracy"] - (ref.predict(Xtr) == ytr).mean()) < 1e-9, "train accuracy does not match a fit on X_train"
    assert abs(out["test_accuracy"] - (ref.predict(Xte) == yte).mean()) < 1e-9, "test accuracy does not match a fit on X_train"
    majority = ytr.mode()[0]
    assert abs(out["baseline_accuracy"] - (yte == majority).mean()) < 1e-9, (
        "baseline accuracy: predict the most common TRAINING label for every test customer, then score on test")


register_quiz(
    "w04.16_q1", "c",
    "Each feature is computed from events on or before the cutoff, and the label from the 90 days after, so the "
    "table reproduces exactly what you will know on the day you score customers.",
    {"a": "Using all history is what makes the future leak in.",
     "b": "The test split is a separate question; the cutoff protects the features themselves.",
     "d": "Dropping customers does not make features honest."})
register_quiz(
    "w04.16_q2", "a",
    "A model is only useful if it beats the trivial rule; reporting the baseline next to the model makes that visible.",
    {"b": "The baseline uses no features at all.",
     "c": "Accuracy above 50% can still be worse than predicting the majority class.",
     "d": "The baseline is cheap to compute and always worth reporting."})


# ================================================================ reference versions for later cells
# Later cells of a notebook use the results of earlier exercises. `use(fn, ...)` calls YOUR function; if you have
# not written it yet (it raises NotImplementedError), it runs the course's reference version instead and says so,
# so the rest of the notebook still works while you come back to the exercise.


def _ref_tenure(customers, cutoff):
    c = customers[customers.signup_date <= cutoff].set_index("customer_id")
    return (cutoff - c.signup_date).dt.days


def _ref_customer_features(orders, values, customers, cutoff):
    active = _ref_active(orders, cutoff)
    f = pd.DataFrame(index=pd.Index(active, name="customer_id"))
    f["recency_days"] = _ref_recency(orders, cutoff)
    f["orders_90d"] = _ref_window_count(orders, cutoff, 90)
    f["spend_90d"] = _ref_window_spend(orders, values, cutoff, 90)
    f["tenure_days"] = _ref_tenure(customers, cutoff).reindex(active)
    f["cancel_rate"] = _ref_cancel_rate(orders, cutoff).reindex(active)
    return f


def _ref_numeric():
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    return Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])


def _ref_categorical():
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    return Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                     ("onehot", OneHotEncoder(handle_unknown="ignore"))])


def _ref_preprocessor(num, cat):
    from sklearn.compose import ColumnTransformer

    return ColumnTransformer([("num", _ref_numeric(), list(num)), ("cat", _ref_categorical(), list(cat))])


def _ref_model_pipeline(num, cat):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    return Pipeline([("prep", _ref_preprocessor(num, cat)), ("model", LogisticRegression(max_iter=1000))])


def _ref_split(df, label, test_size, seed):
    from sklearn.model_selection import train_test_split

    return train_test_split(df.drop(columns=[label]), df[label], test_size=test_size, random_state=seed,
                            stratify=df[label])


def _ref_train_test_accuracy(pipe, Xtr, ytr, Xte, yte):
    pipe.fit(Xtr, ytr)
    return float((pipe.predict(Xtr) == ytr).mean()), float((pipe.predict(Xte) == yte).mean())


def _ref_cv(est, X, y, k, seed):
    from sklearn.model_selection import StratifiedKFold, cross_val_score

    return cross_val_score(est, X, y, cv=StratifiedKFold(k, shuffle=True, random_state=seed), scoring="accuracy")


def _ref_bar(rates):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.bar(rates.index.astype(str), rates.values)
    ax.set_ylabel("churn rate")
    return fig, ax


def _ref_lab_table(features, labels):
    return features.join(labels.set_index("customer_id")["churned"])


def _ref_lab_split(table, seed):
    X, y = table.drop(columns=["churned"]), table["churned"].astype(int)
    from sklearn.model_selection import train_test_split

    return train_test_split(X, y, test_size=0.25, random_state=seed, stratify=y)


def _ref_lab_report(pipe, Xtr, ytr, Xte, yte):
    tr, te = _ref_train_test_accuracy(pipe, Xtr, ytr, Xte, yte)
    return {"train_accuracy": tr, "test_accuracy": te, "baseline_accuracy": float((yte == ytr.mode()[0]).mean())}


_REFERENCES = {
    "order_values": _ref_order_values,
    "active_customers": _ref_active,
    "churn_labels": _ref_labels,
    "churn_rate": lambda labels: float(labels["churned"].mean()),
    "churn_rate_by": lambda df, col: df.groupby(col)["churned"].mean().sort_values(ascending=False),
    "rate_bar_chart": _ref_bar,
    "monthly_orders": lambda o: _valid(o).groupby(_valid(o).order_date.dt.to_period("M")).size(),
    "recency_days": _ref_recency,
    "orders_in_window": _ref_window_count,
    "spend_in_window": _ref_window_spend,
    "tenure_days": _ref_tenure,
    "cancel_rate": _ref_cancel_rate,
    "safe_ratio": lambda n, d: (n / d.where(d != 0)).fillna(0.0),
    "customer_features": _ref_customer_features,
    "split_train_test": _ref_split,
    "numeric_transformer": _ref_numeric,
    "categorical_transformer": _ref_categorical,
    "make_preprocessor": _ref_preprocessor,
    "make_model_pipeline": _ref_model_pipeline,
    "train_test_accuracy": _ref_train_test_accuracy,
    "cv_accuracy": _ref_cv,
    "lab_labels": lambda orders, cutoff: _ref_labels(orders, cutoff, 90),
    "lab_features": _ref_lab_features,
    "lab_table": _ref_lab_table,
    "lab_split": _ref_lab_split,
    "lab_pipeline": _ref_model_pipeline,
    "lab_report": _ref_lab_report,
}


def use(fn, *args, **kwargs):
    """Call your function `fn`; if it is not written yet, use the course's reference version (and say so)."""
    try:
        return fn(*args, **kwargs)
    except NotImplementedError:
        name = getattr(fn, "__name__", "")
        if name not in _REFERENCES:
            raise
        print(f"(note: `{name}` is not finished yet, so the course's reference version was used here. "
              "Come back to that exercise.)")
        return _REFERENCES[name](*args, **kwargs)


register_quiz(
    "w04.16_q3", "a",
    "Because every feature and label function takes the cutoff as an argument, scoring customers on a new day means "
    "calling the same code with a new cutoff and applying the already-fitted pipeline.",
    {"b": "Rewriting feature code for production is how training and serving drift apart.",
     "c": "Nothing is ever fitted on test or production rows.",
     "d": "On the scoring day the future has not happened: there are no labels yet, and none are needed to predict."})
register_quiz(
    "w04.16_q4", "b",
    "Counting tickets over the whole table includes tickets opened after the cutoff, some of them by customers who are "
    "already leaving: the future leaks into the feature. Restrict it to a backward window ending at the cutoff.",
    {"a": "More data is not better when it is data you will not have on the scoring day.",
     "c": "Scaling does not remove information from the future.",
     "d": "Tickets can be a fine feature; only the time filter is wrong."})
