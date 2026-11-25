"""SLI arithmetic, budgets, burn rates and the multi-window paging rule (known answers)."""
from __future__ import annotations

import math
import re

import pytest

from conftest import access


def test_availability_excludes_client_errors_and_counts_503_as_bad(slo):
    events = ([access(200)] * 90 + [access(422)] * 30 + [access(404)] * 5 + [access(503)] * 4
              + [access(500)] * 6 + [access(200, route="/healthz")] * 50
              + [{"event": "prediction", "route": "/predict", "status": 200}] * 7)
    good, valid = slo.availability_sli(events)
    assert (good, valid) == (90, 100), f"expected (90, 100): 4xx excluded, 5xx bad, other routes ignored; got {(good, valid)}"


def test_latency_counts_only_successful_requests(slo):
    events = [access(200, 100.0)] * 8 + [access(200, 300.0)] * 2 + [access(500, 1.0)] * 5 + [access(422, 1.0)] * 3
    assert slo.latency_sli(events, 250.0) == (8, 10)
    assert slo.latency_sli(events, 300.0) == (10, 10), "the threshold is inclusive (<=)"


def test_error_budget_and_burn_rate_known_answers(slo):
    assert math.isclose(slo.error_budget(0.999, 1_000_000), 1000.0, rel_tol=1e-9)
    assert math.isclose(slo.error_budget(0.995, 1_728_000), 8640.0, rel_tol=1e-9)
    assert math.isclose(slo.burn_rate(20, 1000, 0.999), 20.0, rel_tol=1e-9)
    assert math.isclose(slo.burn_rate(5, 1000, 0.995), 1.0, rel_tol=1e-9)
    assert slo.burn_rate(0, 0, 0.999) == 0.0
    with pytest.raises(ValueError):
        slo.error_budget(1.0, 10)


def test_paging_needs_both_windows(slo):
    target = 0.999
    rules = (("1h", "5m", 14.4), ("6h", "30m", 6.0))
    # long window burning hard, short window already recovered -> no page
    assert not slo.should_page({"1h": (200, 10_000), "5m": (0, 800)}, target, rules)
    # a 5-minute blip: short window very hot, long window barely touched -> no page
    assert not slo.should_page({"1h": (20, 10_000), "5m": (20, 800)}, target, rules)
    # both windows of the fast rule burning -> page
    assert slo.should_page({"1h": (150, 10_000), "5m": (15, 800)}, target, rules)
    # only the slow rule fires -> page
    assert slo.should_page({"1h": (50, 10_000), "5m": (4, 800), "6h": (400, 60_000), "30m": (40, 5_000)},
                           target, rules)
    # missing windows mean no traffic
    assert not slo.should_page({}, target, rules)


def test_slo_document_is_filled_in(target):
    path = target / "SLO.md"
    assert path.is_file(), "write SLO.md next to slo.py"
    text = path.read_text()
    assert "TODO" not in text, "SLO.md still contains TODO"
    for n in range(1, 7):
        assert re.search(rf"^##\s*{n}\.", text, re.M), f"SLO.md lacks section {n}"
    sections = re.split(r"^##\s*\d\.", text, flags=re.M)
    for n in (3, 4, 5):
        assert re.search(r"\d", sections[n]), f"section {n} has no numbers"
    assert len(text.split()) >= 250, "SLO.md is too short to justify its choices"
