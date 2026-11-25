"""Temporal and group correctness of the challenge split. Data: SYNTHETIC customer-months."""
from __future__ import annotations

import numpy as np

from conftest import TEST_START, Parts, month_number


def test_parts_are_disjoint_and_nonempty(parts):
    a, b, c = set(parts.train.index), set(parts.test_known.index), set(parts.test_new.index)
    assert a and b and c, "train, test_known and test_new must all be non-empty on this table"
    assert not (a & b) and not (a & c) and not (b & c)


def test_no_training_label_looks_into_the_test_period(parts):
    latest_label_month = parts.m(parts.train).max() + parts.horizon
    assert latest_label_month < parts.start, (
        "a training row's label window reaches into (or past) the test period: the outcome it "
        "encodes was not known when the model would have been trained")


def test_test_rows_start_at_test_start(parts):
    for name in ("test_known", "test_new"):
        assert parts.m(getattr(parts, name)).min() >= parts.start, f"{name} contains rows before test_start"


def test_test_rows_are_chosen_by_calendar_not_by_label_availability(parts):
    for name in ("test_known", "test_new"):
        part = getattr(parts, name)
        assert (parts.m(part) + parts.horizon).max() <= parts.last, (
            f"{name} contains months whose label window is not fully observed; the labels that ARE "
            "known there are almost all churners (censoring)")
        assert part["churn_within_3m"].notna().all()


def test_every_evaluable_row_is_evaluated_exactly_once(parts):
    m = month_number(parts.df["month"])
    evaluable = set(parts.df.index[(m >= parts.start) & (m + parts.horizon <= parts.last)])
    assert set(parts.test_known.index) | set(parts.test_new.index) == evaluable


def test_known_and_new_mean_what_they_say(parts):
    seen = set(parts.train["customer_id"])
    assert set(parts.test_known["customer_id"]) <= seen, "test_known contains customers the model never saw"
    leaked = set(parts.test_new["customer_id"]) & seen
    assert not leaked, f"{len(leaked)} 'new' customers have rows in train, e.g. {sorted(leaked)[:3]}"


def test_requested_fraction_of_customers_is_held_out(parts):
    m = month_number(parts.df["month"])
    trainable = set(parts.df.loc[m + parts.horizon < parts.start, "customer_id"])
    held = trainable - set(parts.train["customer_id"])
    assert abs(len(held) / len(trainable) - 0.2) <= 0.05, (
        f"{len(held)} of {len(trainable)} customers with usable history were held out; asked for 20 %")


def test_training_data_is_not_thrown_away(parts):
    m = month_number(parts.df["month"])
    usable = parts.df[(m + parts.horizon < parts.start) & parts.df["customer_id"].isin(set(parts.train["customer_id"]))]
    assert set(usable.index) == set(parts.train.index), "some usable rows of training customers are missing from train"


def test_zero_fraction_holds_nobody_out_by_design(split, table):
    p = Parts(table, split(table, TEST_START, horizon_months=3, new_customer_fraction=0.0, seed=0))
    m = month_number(table["month"])
    trainable = set(table.loc[m + 3 < p.start, "customer_id"])
    assert trainable == set(p.train["customer_id"])
    assert len(p.test_new) > 0, "customers who joined too late to be trained on are still 'new' to the model"


def test_horizon_controls_the_gap(split, table):
    short = Parts(table, split(table, TEST_START, horizon_months=1, new_customer_fraction=0.0, seed=0), horizon=1)
    long = Parts(table, split(table, TEST_START, horizon_months=3, new_customer_fraction=0.0, seed=0), horizon=3)
    assert short.m(short.train).max() == short.start - 2
    assert long.m(long.train).max() == long.start - 4


def test_deterministic_and_seeded(split, table):
    a = split(table, TEST_START, seed=5)
    b = split(table, TEST_START, seed=5)
    assert {k: sorted(v) for k, v in a.items()} == {k: sorted(v) for k, v in b.items()}
    held = lambda out: frozenset(table.loc[list(out["test_new"]), "customer_id"])  # noqa: E731
    assert len({held(split(table, TEST_START, seed=s)) for s in range(4)}) >= 2, "the seed has no effect"


def test_input_is_not_modified(split, table):
    before = table.copy()
    split(table, TEST_START)
    assert table.equals(before) and list(table.columns) == list(before.columns)
    assert np.array_equal(table.index, before.index)
