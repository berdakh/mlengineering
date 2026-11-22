"""choose_operating_point and rate_upper_bound. SYNTHETIC data only."""
import math

import numpy as np
import pytest

from conftest import BURN_IN

BUDGET = 3.0          # false alarms per hour on the synthetic dev set


def choose(op, dev, grid, budget, **kw):
    tidy, scores = dev
    return op.choose_operating_point(tidy, scores, budget, grid["thresholds"], min_durations=grid["min_durations"],
                                     merge_gaps=grid["merge_gaps"], burn_in=BURN_IN, **kw)


def test_fixture_has_a_real_tradeoff(table):
    """Guards the checks themselves: the budget must bind and the cheapest setting must not be the best."""
    feasible = table[table["rate"] <= BUDGET]
    assert 0 < len(feasible) < len(table)
    assert table["recall"].max() > feasible["recall"].max() or table.loc[table["recall"].idxmax(), "rate"] > BUDGET
    assert feasible.loc[feasible["rate"].idxmin(), "recall"] < feasible["recall"].max()


def test_result_shape(op, dev, grid):
    c = choose(op, dev, grid, BUDGET)
    assert c["threshold"] in grid["thresholds"]
    assert c["min_duration"] in grid["min_durations"] and c["merge_gap"] in grid["merge_gaps"]
    assert c["feasible"] is True
    assert {"event_recall", "false_alarms_per_hour", "n_false_alarms", "normal_hours"} <= set(c["dev"])


def test_choice_respects_the_budget_on_dev(op, dev, grid):
    c = choose(op, dev, grid, BUDGET)
    assert c["dev"]["false_alarms_per_hour"] <= BUDGET


def test_choice_has_the_best_recall_among_feasible_settings(op, dev, grid, table):
    c = choose(op, dev, grid, BUDGET)
    feasible = table[table["rate"] <= BUDGET]
    assert c["dev"]["event_recall"] == pytest.approx(feasible["recall"].max())


def test_ties_in_recall_are_broken_by_delay(op, dev, grid, table):
    c = choose(op, dev, grid, BUDGET)
    feasible = table[table["rate"] <= BUDGET]
    best = feasible[np.isclose(feasible["recall"], feasible["recall"].max())]
    assert c["dev"]["median_delay_s"] == pytest.approx(best["delay"].min())


def test_reported_dev_result_matches_the_returned_configuration(op, dev, grid, evaluate):
    tidy, scores = dev
    c = choose(op, dev, grid, BUDGET)
    again = evaluate(tidy, scores >= c["threshold"], burn_in=BURN_IN, min_duration=c["min_duration"],
                     merge_gap=c["merge_gap"])
    assert c["dev"]["n_false_alarms"] == again["n_false_alarms"]
    assert c["dev"]["n_detected"] == again["n_detected"]


def test_burn_in_rows_are_not_alarms(op, dev, grid):
    """The first 50 rows carry a huge artefact; with burn_in passed on they must not count."""
    c = choose(op, dev, grid, BUDGET)
    assert c["dev"]["n_false_alarms"] <= BUDGET * c["dev"]["normal_hours"] + 1e-9


def test_a_looser_budget_never_lowers_recall(op, dev, grid):
    recalls = [choose(op, dev, grid, b)["dev"]["event_recall"] for b in (1.0, 3.0, 10.0, 1000.0)]
    assert all(a <= b + 1e-12 for a, b in zip(recalls, recalls[1:]))


def test_impossible_budget_is_reported_as_infeasible(op, dev, table):
    tidy, scores = dev
    c = op.choose_operating_point(tidy, scores, 0.0, (1.5, 2.0), min_durations=(1,), merge_gaps=(0,), burn_in=BURN_IN)
    assert c["feasible"] is False
    sub = table[(table["threshold"] <= 2.0) & (table["min_duration"] == 1) & (table["merge_gap"] == 0)]
    assert c["dev"]["false_alarms_per_hour"] == pytest.approx(sub["rate"].min())


def test_upper_bound_is_attached_and_is_not_the_point_estimate(op, dev, grid):
    c = choose(op, dev, grid, BUDGET)
    n, hours = c["dev"]["n_false_alarms"], c["dev"]["normal_hours"]
    assert c["dev_rate_upper_bound"] == pytest.approx(op.rate_upper_bound(n, hours))
    assert c["dev_rate_upper_bound"] > n / hours


def test_rule_of_three(op):
    assert op.rate_upper_bound(0, 10.0) == pytest.approx(-math.log(0.05) / 10.0, rel=1e-6)
    assert op.rate_upper_bound(0, 1.0, confidence=0.9) == pytest.approx(math.log(10.0), rel=1e-6)


def test_upper_bound_known_values_and_monotonicity(op):
    # exact Poisson bounds: P(N <= n | mu) = 0.05  ->  mu = 4.744 (n=1), 7.754 (n=3)
    assert op.rate_upper_bound(1, 1.0) == pytest.approx(4.7439, abs=1e-3)
    assert op.rate_upper_bound(3, 2.0) == pytest.approx(7.7537 / 2, abs=1e-3)
    bounds = [op.rate_upper_bound(n, 5.0) for n in range(6)]
    assert all(a < b for a, b in zip(bounds, bounds[1:]))
    assert op.rate_upper_bound(2, 1.0) > op.rate_upper_bound(2, 4.0)
    assert op.rate_upper_bound(2, 1.0, confidence=0.99) > op.rate_upper_bound(2, 1.0, confidence=0.9)


def test_upper_bound_without_exposure_is_infinite(op):
    assert math.isinf(op.rate_upper_bound(0, 0.0))
