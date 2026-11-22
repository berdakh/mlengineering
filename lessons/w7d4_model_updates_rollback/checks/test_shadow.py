"""Task 3: shadow mode never changes what is served."""
from __future__ import annotations

from conftest import make_run


class Exploding:
    label = "boom-9.9.9"

    def score_run(self, run):
        run["flow_rate"] = 0.0          # mutates its input, then fails
        raise RuntimeError("candidate crashed")


def test_shadow_serves_the_current_response_exactly(fg):
    m = fg["models"]
    current = m.BurnInZ(version="1.0.0", threshold=6.0, min_duration=5, merge_gap=2)
    candidate = m.BurnInZ(version="1.1.0", threshold=4.0, min_duration=5, merge_gap=2)
    runner = fg["update"].ShadowRunner(current, candidate)
    for seed in range(3):
        run = make_run(seed)
        assert runner.score(f"r{seed}", run) == fg["serving"].respond(current, make_run(seed))
    assert len(runner.log) == 3
    rec = runner.log[0]
    assert rec["current_version"] == "flowguard-1.0.0" and rec["candidate_version"] == "flowguard-1.1.0"
    assert rec["candidate_error"] is None and rec["candidate_alarms"] is not None


def test_a_crashing_mutating_candidate_cannot_touch_serving(fg):
    m = fg["models"]
    current = m.BurnInZ(version="1.0.0", threshold=6.0, min_duration=5, merge_gap=2)
    runner = fg["update"].ShadowRunner(current, Exploding())
    run = make_run(1)
    expected = fg["serving"].respond(current, make_run(1))
    assert runner.score("r1", run) == expected
    assert runner.log[-1]["candidate_error"] and "candidate crashed" in runner.log[-1]["candidate_error"]
    assert runner.score("r1-again", run) == expected        # the caller's frame was not mutated either


def test_disagreements_summary(fg):
    log = [
        {"run_id": "a", "current_alarms": [[10, 20]], "candidate_alarms": [[10, 20]], "candidate_error": None},
        {"run_id": "b", "current_alarms": [[10, 20]], "candidate_alarms": [[12, 25], [40, 50]], "candidate_error": None},
        {"run_id": "c", "current_alarms": [[5, 8]], "candidate_alarms": [], "candidate_error": None},
        {"run_id": "d", "current_alarms": [], "candidate_alarms": None, "candidate_error": "RuntimeError: x"},
    ]
    d = fg["update"].disagreements(log)
    assert d == {"runs": 4, "runs_differ": 2, "only_current": 1, "only_candidate": 1, "candidate_errors": 1}
