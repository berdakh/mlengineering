"""Milestone 4 checks: the demo command, its report, the service lifecycle and the runbook."""
from __future__ import annotations

import os
import re

import pytest


def table(md: str, heading: str) -> list[list[str]]:
    """Rows (cells) of the first Markdown table after ``## heading``."""
    part = md.split(f"## {heading}", 1)
    assert len(part) == 2, f"the report has no '## {heading}' section"
    rows = []
    for line in part[1].splitlines():
        s = line.strip()
        if s.startswith("## "):
            break
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            rows.append(cells)
        elif rows and not s:
            break
    return rows[1:]                                  # drop the header row


def test_demo_command_succeeds(first):
    assert first["proc"].returncode == 0, first["proc"].stdout[-1500:] + first["proc"].stderr[-2000:]


def test_every_scenario_event_in_results_and_timeline(first, scenario):
    ids = [e["id"] for e in scenario["event"]]
    assert [e["id"] for e in first["results"]["events"]] == ids, "results.json must list every event, in order"
    timeline_ids = [row[1] for row in table(first["report"], "Timeline")]
    assert timeline_ids == ids, f"the timeline must have one row per scripted event, in order; got {timeline_ids}"


def test_timeline_states_detection_explicitly(first):
    for row in table(first["report"], "Timeline"):
        verdict = row[-1].lower()
        assert verdict in ("as expected", "unexpected alert") or verdict.startswith("not detected"), \
            f"event {row[1]}: the last column must say 'as expected', 'not detected ...' or 'UNEXPECTED ALERT'"


@pytest.mark.parametrize("event_id,signal", [("S2-units", "out_of_support"), ("S3-drift", "drift"),
                                             ("S4-fault", "detector"), ("S6-promote-bad", "alarm_rate"),
                                             ("S7-rollback", "version_restored")])
def test_scripted_problems_are_detected(first, event_id, signal):
    ev = {e["id"]: e for e in first["results"]["events"]}[event_id]
    assert signal in ev["signals"] and ev["as_expected"], f"{event_id}: expected signal {signal!r}, got {ev['signals']}"


def test_quiet_normal_operation(first):
    ev = first["results"]["events"][0]
    assert ev["signals"] == [] and ev["as_expected"], f"normal operation raised {ev['signals']}"


def test_versions_follow_the_registry(first):
    ev = {e["id"]: e for e in first["results"]["events"]}
    good = ev["S1-normal"]["model_version"]
    assert ev["S6-promote-bad"]["model_version"] == "synthetic-bad-rc", "after the promotion /version must show it"
    assert ev["S7-rollback"]["model_version"] == good, "after the rollback the service must serve the old version"
    actions = [(h["action"], h["version"]) for h in first["results"]["registry_history"]]
    assert actions == [("promote", good), ("promote", "synthetic-bad-rc"), ("rollback", good)]


def test_delayed_label_report(first):
    o = {e["id"]: e for e in first["results"]["events"]}["S5-labels"]["observed"]
    assert o["faults"] == 1 and o["faults_detected"] == 1 and o["false_alarm_events"] == 0


def _num(cell: str) -> float:
    return float(cell)


def test_report_summary_matches_results(first):
    rows = {r[0]: r[1] for r in table(first["report"], "Summary")}
    summary = first["results"]["summary"]
    assert set(summary) <= set(rows), f"summary keys missing from the report: {sorted(set(summary) - set(rows))}"
    for k, v in summary.items():
        assert _num(rows[k]) == pytest.approx(float(v), abs=5e-5), f"report says {k} = {rows[k]}, results.json {v}"


def test_report_observations_match_results(first):
    rows = {r[0]: r for r in table(first["report"], "Per-event observations")}
    for e in first["results"]["events"]:
        o = e["observed"]
        if "values" not in o:
            continue
        r = rows[e["id"]]
        assert int(r[1]) == o["values"] and int(r[3]) == o["alarm_events"] and int(r[4]) == o["out_of_support_values"]
        assert _num(r[2]) == pytest.approx(o["alarm_rate"], abs=5e-5)
        assert _num(r[5]) == pytest.approx(o["psi"], abs=5e-5)


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def test_every_server_was_stopped(runs):
    results = [r["results"] for r in runs]
    assert all(res is not None for res in results), "a run wrote no results.json"
    leaked = [p for res in results for p in res["server"]["pids"] if _alive(p)]
    for p in leaked:                                    # clean up before failing
        try:
            os.kill(p, 15)
        except OSError:
            pass
    assert not leaked, f"service processes still running after the demo: {leaked}"
    for res in results:
        assert len(res["server"]["pids"]) >= 3, \
            "expected one service process at start, one after the promotion and one after the rollback"


def test_rerun_reproduces_every_number(runs):
    a, b = runs[0]["results"], runs[1]["results"]
    assert a["summary"] == b["summary"]
    assert [e["observed"] for e in a["events"]] == [e["observed"] for e in b["events"]]


REQUIRED = ["Service overview", "Dashboards and queries", "Alerts", "Common incidents", "Rollback",
            "Escalation", "Known limitations"]


def test_runbook_sections(target):
    path = target / "RUNBOOK.md"
    assert path.is_file(), "RUNBOOK.md is missing"
    text = path.read_text()
    assert "TODO" not in text, "replace every TODO in RUNBOOK.md"
    headings = [h.strip().lower() for h in re.findall(r"^## (.+)$", text, flags=re.M)]
    missing = [s for s in REQUIRED if s.lower() not in headings]
    assert not missing, f"RUNBOOK.md lacks sections: {missing}"


def test_every_alert_has_a_runbook_entry(target, alerts):
    text = (target / "RUNBOOK.md").read_text()
    for alert in alerts:
        m = re.search(rf"^### {re.escape(alert['name'])}\s*$(.*?)(?=^#{{2,3}} |\Z)", text, flags=re.M | re.S)
        assert m, f"no '### {alert['name']}' section in RUNBOOK.md"
        body = m.group(1)
        for label in ("Meaning", "First actions", "Escalate"):
            assert re.search(rf"\*\*{label}:?\*\*", body), f"{alert['name']}: add a **{label}:** line"
        assert len(body.split()) >= 40, f"{alert['name']}: the entry is too short to act on"
