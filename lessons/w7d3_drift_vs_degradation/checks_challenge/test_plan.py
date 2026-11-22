"""Structural and consistency checks of the monitoring plan. They cannot judge whether the numbers are
wise; they reject plans that contradict themselves or the lesson's three rules."""
from __future__ import annotations

import re

import pytest

JOIN_KEYS = {"alarm_id", "fault_id", "prediction_id"}


def _todo(value) -> bool:
    return isinstance(value, str) and "TODO" in value


def test_required_tables(plan):
    for key in ("context", "input_drift", "actions"):
        assert isinstance(plan.get(key), dict), f"missing table [{key}]"
    for key in ("input_validity", "performance", "label_sources"):
        assert isinstance(plan.get(key), list) and plan[key], f"need at least one [[{key}]] entry"


def test_no_placeholders_left(plan):
    found = []

    def walk(x, path):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, f"{path}.{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{path}[{i}]")
        elif _todo(x):
            found.append(path)
    walk(plan, "plan")
    assert not found, f"TODO left in {found}"


def test_context_rates_positive(plan):
    ctx = plan["context"]
    assert ctx["expected_faults_per_week"] > 0 and ctx["expected_alarms_per_week"] > 0


def test_input_validity_entries(plan):
    for e in plan["input_validity"]:
        assert e.get("name") and e.get("check") and e.get("on_failure"), e


def test_drift_threshold_is_calibrated(plan):
    d = plan["input_drift"]
    assert d["statistic"] in {"psi", "ks", "wasserstein"}
    assert d["threshold_method"] == "calibrated", "drift thresholds must be calibrated on reference data"
    assert 0.9 <= d["calibration_quantile"] < 1.0
    assert d["window_days"] > 0 and d["columns"] and d["reference"]


def _sources(plan):
    return {s["name"]: s for s in plan["label_sources"]}


def test_label_sources_are_joinable_and_have_delays(plan):
    for s in plan["label_sources"]:
        assert s["join_key"] in JOIN_KEYS, f"{s['name']}: join_key must be one of {sorted(JOIN_KEYS)}"
        assert s["covers"] in {"alarms", "missed_faults"}
        lo, hi = s["expected_delay_days"]
        assert 0 <= lo <= hi, f"{s['name']}: delay range must satisfy 0 <= low <= high"


def test_performance_metrics_are_measurable(plan):
    ctx, sources = plan["context"], _sources(plan)
    rate = {"alarm_precision": ctx["expected_alarms_per_week"], "event_recall": ctx["expected_faults_per_week"]}
    for p in plan["performance"]:
        assert p["metric"] in rate, f"unknown metric {p['metric']}"
        assert p["label_source"] in sources, f"{p['metric']}: label source {p['label_source']!r} is not defined"
        assert p["min_labels"] >= 1
        assert p["when_insufficient"] == "report_unknown", "insufficient data must be reported as unknown"
        assert 0 < p["baseline"] <= 1 and 0 < p["margin"] < 1
        expected = rate[p["metric"]] * p["window_days"] / 7
        assert expected >= p["min_labels"], (
            f"{p['metric']}: a {p['window_days']}-day window collects about {expected:.1f} labels, "
            f"fewer than min_labels = {p['min_labels']}")


def test_metrics_wait_for_their_labels(plan):
    sources = _sources(plan)
    for p in plan["performance"]:
        hi = sources[p["label_source"]]["expected_delay_days"][1]
        assert p["evaluate_after_days"] >= hi, (
            f"{p['metric']} is evaluated after {p['evaluate_after_days']} days but its labels take up to {hi}")


def test_recall_needs_a_missed_fault_source(plan):
    metrics = {p["metric"] for p in plan["performance"]}
    if "event_recall" in metrics:
        covers = {s["covers"] for s in plan["label_sources"]}
        assert "missed_faults" in covers, "event recall is not measurable without a source of missed faults"


def test_actions_keep_the_questions_apart(plan):
    a = plan["actions"]
    for key in ("drift_only", "degradation_only", "drift_and_degradation", "insufficient"):
        assert a.get(key), f"actions.{key} missing"
    assert not re.search(r"retrain|rollback", a["drift_only"], re.I), "drift alone must not retrain or roll back"
    assert a["degradation_only"].strip().lower() not in {"no_action", "none", "ignore"}


@pytest.mark.parametrize("heading", ["Three questions", "Label backfill", "What this plan cannot detect"])
def test_prose_sections(target, heading):
    path = target / "MONITORING_PLAN.md"
    assert path.is_file(), "missing MONITORING_PLAN.md"
    text = path.read_text()
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    assert m, f"heading '## {heading}' missing"
    body = m.group(1).strip()
    assert len(body.split()) >= 40 and "TODO" not in body, f"section '{heading}' needs real text (40+ words)"
