"""Challenge part 2b: SampleOrderGuard."""
from __future__ import annotations


def test_first_sample_and_in_order(res):
    g = res.SampleOrderGuard(max_gap_s=5)
    assert [g.check("m1", t) for t in (0.0, 1.0, 2.0, 7.0)] == ["ok", "ok", "ok", "ok"]


def test_duplicate_is_dropped_without_state_change(res):
    g = res.SampleOrderGuard(max_gap_s=5)
    g.check("m1", 10.0)
    assert g.check("m1", 10.0) == "duplicate"
    assert g.check("m1", 11.0) == "ok"


def test_out_of_order_rejected_and_state_kept(res):
    g = res.SampleOrderGuard(max_gap_s=5)
    g.check("m1", 10.0)
    assert g.check("m1", 9.0) == "out_of_order"
    assert g.check("m1", 9.5) == "out_of_order", "the rejected sample must not move the clock back"
    assert g.check("m1", 11.0) == "ok"


def test_gap_reported_and_accepted(res):
    g = res.SampleOrderGuard(max_gap_s=5)
    g.check("m1", 0.0)
    assert g.check("m1", 5.0) == "ok", "a gap of exactly max_gap_s is not a gap"
    assert g.check("m1", 10.5) == "gap"
    assert g.check("m1", 11.5) == "ok", "after a gap the sample is accepted"


def test_machines_are_independent(res):
    g = res.SampleOrderGuard(max_gap_s=5)
    g.check("m1", 100.0)
    assert g.check("m2", 1.0) == "ok"
    assert g.check("m2", 1.0) == "duplicate" and g.check("m1", 101.0) == "ok"
