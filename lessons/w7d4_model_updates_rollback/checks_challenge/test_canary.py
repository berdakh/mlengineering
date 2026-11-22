"""The canary rule on the five SYNTHETIC logs and on edge cases."""
from __future__ import annotations

import re

import pandas as pd
import pytest

from conftest import LOGS

# Reference outcomes of the rule as stated in the README (computed by the reference solution).
SEQUENTIAL = {"a_broken_release": ("stop", 2), "b_alarm_storm": ("stop", 0), "c_too_early": ("continue", 5),
              "d_healthy": ("promote", 23), "e_borderline_alerts": ("stop", 2)}
FULL = {"a_broken_release": "stop", "b_alarm_storm": "stop", "c_too_early": "continue",
        "d_healthy": "promote", "e_borderline_alerts": "continue"}


@pytest.mark.parametrize("name", sorted(SEQUENTIAL))
def test_sequential_decisions(canary, name):
    r = canary.run_canary(pd.read_csv(LOGS / f"{name}.csv"))
    assert (r["decision"], r["hour"]) == SEQUENTIAL[name]
    assert r["reasons"] and all(isinstance(x, str) for x in r["reasons"])


@pytest.mark.parametrize("name", sorted(FULL))
def test_full_log_decisions(canary, name):
    assert canary.decide(pd.read_csv(LOGS / f"{name}.csv"))["decision"] == FULL[name]


def _log(rows):
    return pd.DataFrame(rows, columns=["hour", "arm", "requests", "errors", "machine_hours", "alerts"])


def test_no_canary_rows_means_continue(canary):
    log = _log([(0, "control", 900, 9, 45.0, 4)])
    assert canary.decide(log)["decision"] == "continue"


def test_perfect_but_short_canary_is_not_promoted(canary):
    rows = []
    for h in range(10):
        rows += [(h, "control", 900, 9, 45.0, 4), (h, "canary", 1000, 0, 5.0, 0)]
    d = canary.decide(_log(rows))
    assert d["decision"] == "continue"          # 10 hours < 24, despite 10,000 requests and no errors


def test_zero_alerts_has_zero_lower_bound_and_finite_upper(canary):
    rows = []
    for h in range(30):
        rows += [(h, "control", 900, 9, 45.0, 4), (h, "canary", 100, 1, 5.0, 0)]
    d = canary.decide(_log(rows))
    assert d["decision"] == "promote"           # 150 machine-hours, 0 alerts: upper bound about 0.02/h


@pytest.mark.parametrize("heading", ["Decisions per scenario", "Repeated looks", "What a canary of this size cannot tell you"])
def test_canary_md(target, heading):
    text = (target / "CANARY.md").read_text()
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    assert m, f"heading '## {heading}' missing"
    body = m.group(1).strip()
    assert len(body.split()) >= 30 and "TODO" not in body, f"section '{heading}' needs real text"
