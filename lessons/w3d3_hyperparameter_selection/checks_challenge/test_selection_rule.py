"""The selection procedure and, above all, the honesty of the number it reports.

Graded on 200 freshly generated SYNTHETIC tables whose true scores the checks know. A reported
estimate is honest if, on average, it neither flatters nor undersells the trial that was chosen.
"""
import json

import numpy as np
import pandas as pd
import pytest

import gen
from conftest import SHIPPED

N_TABLES = 200


@pytest.fixture(scope="module")
def outcomes(rule):
    rows = []
    for seed in range(N_TABLES):
        table, truth, _ = gen.make_table(5000 + seed)
        out = rule.choose(table.copy())
        assert set(out) >= {"trial", "estimate"}, "choose() returns a dict with at least 'trial' and 'estimate'"
        trial = int(out["trial"])
        assert trial in set(table["trial"]), f"choose() returned an unknown trial id {trial}"
        rows.append({"error": float(out["estimate"]) - truth[trial], "truth": truth[trial], "average": truth.mean()})
    return pd.DataFrame(rows)


def test_estimate_is_unbiased_for_the_chosen_trial(outcomes):
    bias = outcomes["error"].mean()
    assert abs(bias) < 0.008, (
        f"over {N_TABLES} tables your estimate differs from the chosen trial's true score by {bias:+.4f} on average. "
        "A dev score that was used to choose the trial cannot also be the estimate of that trial.")


def test_the_choice_is_better_than_not_selecting(outcomes):
    gain = (outcomes["truth"] - outcomes["average"]).mean()
    assert gain > 0.008, f"the chosen trials are only {gain:+.4f} better than the average trial; selection should help"


def test_choose_is_deterministic_and_does_not_modify_its_input(rule):
    table = pd.read_csv(SHIPPED)
    before = table.copy()
    a, b = rule.choose(table), rule.choose(table)
    assert a["trial"] == b["trial"] and a["estimate"] == pytest.approx(b["estimate"])
    pd.testing.assert_frame_equal(table, before)


def test_choose_does_not_depend_on_row_order(rule):
    table = pd.read_csv(SHIPPED)
    shuffled = table.sample(frac=1.0, random_state=0).reset_index(drop=True)
    assert rule.choose(table)["trial"] == rule.choose(shuffled)["trial"]


def test_exactly_one_test_look_and_it_is_the_chosen_trial(rule, target):
    log = target / "test_looks.json"
    assert log.is_file(), "run reveal_test.py once, for the trial your procedure chose; the log is part of the submission"
    looks = json.loads(log.read_text())
    assert len(looks) == 1, f"{len(looks)} test looks are logged; the budget is one"
    assert looks[0]["trial"] == rule.choose(pd.read_csv(SHIPPED))["trial"], "the trial you looked at is not the one choose() selects"


def test_report_is_written(target):
    report = target / "REPORT.md"
    assert report.is_file()
    text = report.read_text()
    assert len(text.split()) >= 120 and "TODO" not in text, "REPORT.md is still the template"
    assert any(ch.isdigit() for ch in text)
    assert np.isfinite(1.0)
