"""Checks for lesson w5d3: streaming scorer and registry. SYNTHETIC data only."""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from conftest import assert_parity, make_run, stream_scores


# --------------------------------------------------------------------------- parity and warm-up
@pytest.mark.parametrize("seed,level", [(0, 120.0), (1, 1.0e6), (2, 0.5)])
def test_parity_with_batch_over_a_full_run(stream, detector, seed, level):
    run = make_run(seed=seed, level=level)
    assert_parity(detector.score_batch(run), stream_scores(stream.StreamScorer(detector), run))


def test_parity_when_the_burn_in_is_constant(stream, detector):
    run = make_run(seed=3)
    run.loc[: detector.n_burn - 1, "flow_rate"] = 42.0     # sigma would be 0 -> the detector uses 1
    assert_parity(detector.score_batch(run), stream_scores(stream.StreamScorer(detector), run))


def test_warm_up_returns_no_score_and_says_so(stream, detector):
    scorer = stream.StreamScorer(detector, machine_id="m1")
    rows = make_run(seed=4).to_dict("records")
    for i, row in enumerate(rows[: detector.n_burn]):
        r = scorer.update(row)
        assert r.score is None, f"sample {i + 1} is in the burn-in but got score {r.score!r}"
        assert r.status == "warming_up" and r.exceeds is None
        assert r.n_seen == i + 1 and r.machine_id == "m1"
    r = scorer.update(rows[detector.n_burn])
    assert r.status == "ok" and isinstance(r.score, float) and isinstance(r.exceeds, bool)
    assert r.exceeds == (r.score >= detector.threshold)


def test_exceeds_matches_the_threshold_after_the_fault(stream, detector):
    run = make_run(seed=5)
    scorer = stream.StreamScorer(detector)
    results = [scorer.update(row) for row in run.to_dict("records")]
    batch = detector.score_batch(run)
    assert [r.exceeds for r in results[detector.n_burn:]] == list(batch[detector.n_burn:] >= detector.threshold)
    assert any(r.exceeds for r in results[300:]), "the synthetic step fault should exceed the threshold"


# --------------------------------------------------------------------------- invalid, order, duplicates
@pytest.mark.parametrize("bad", [
    {"flow_rate": 1.0},                                              # no timestamp
    {"datetime": "2026-01-01 00:10:00"},                             # no sensor value
    {"datetime": "2026-01-01 00:10:00", "flow_rate": float("nan")},
    {"datetime": "2026-01-01 00:10:00", "flow_rate": float("inf")},
    {"datetime": "2026-01-01 00:10:00", "flow_rate": "abc"},
])
def test_invalid_samples_are_rejected_without_changing_state(stream, detector, bad):
    run = make_run(seed=6)
    rows = run.to_dict("records")
    scorer = stream.StreamScorer(detector)
    for row in rows[:120]:
        scorer.update(row)
    with pytest.raises(stream.InvalidSampleError):
        scorer.update(bad)
    assert issubclass(stream.InvalidSampleError, stream.StreamError) and issubclass(stream.StreamError, ValueError)
    tail = np.array([scorer.update(r).score for r in rows[120:]], dtype=float)
    assert_parity(detector.score_batch(run)[120:], tail)


@pytest.mark.parametrize("at", [10, 200])        # during warm-up and after it
def test_out_of_order_sample_is_rejected_and_state_unchanged(stream, detector, at):
    run = make_run(seed=7)
    rows = run.to_dict("records")
    scorer = stream.StreamScorer(detector)
    for row in rows[:at]:
        scorer.update(row)
    late = dict(rows[at - 5], flow_rate=rows[at - 5]["flow_rate"] + 100.0)
    with pytest.raises(stream.OutOfOrderError):
        scorer.update(late)
    assert scorer.update(rows[at]).n_seen == at + 1, "a rejected sample must not be counted"
    rest = np.array([np.nan if (r := scorer.update(row)).score is None else r.score for row in rows[at + 1:]])
    assert_parity(detector.score_batch(run)[at + 1:], rest)


def test_identical_duplicates_are_idempotent(stream, detector):
    run = make_run(seed=8)
    scorer = stream.StreamScorer(detector)
    streamed = []
    for row in run.to_dict("records"):
        first = scorer.update(row)
        again = scorer.update(dict(row))               # e.g. a client retry after a timeout
        assert again.duplicate and not first.duplicate
        assert again.score == first.score and again.n_seen == first.n_seen and again.timestamp == first.timestamp
        streamed.append(np.nan if first.score is None else first.score)
    assert_parity(detector.score_batch(run), np.array(streamed))


def test_conflicting_duplicate_is_rejected(stream, detector):
    rows = make_run(seed=9).to_dict("records")
    scorer = stream.StreamScorer(detector)
    for row in rows[:80]:
        scorer.update(row)
    with pytest.raises(stream.ConflictingDuplicateError):
        scorer.update(dict(rows[79], flow_rate=rows[79]["flow_rate"] + 1.0))
    assert scorer.update(rows[80]).n_seen == 81


# --------------------------------------------------------------------------- gaps
def _with_gap(run: pd.DataFrame, at: int, seconds: float) -> pd.DataFrame:
    run = run.copy()
    run.loc[at:, "datetime"] = run.loc[at:, "datetime"] + pd.Timedelta(seconds=seconds)
    return run


def test_gap_flag_policy_flags_and_keeps_scoring(stream, detector):
    run = _with_gap(make_run(seed=10), at=200, seconds=60)
    scorer = stream.StreamScorer(detector, max_gap_s=5.0, gap_policy="flag")
    results = [scorer.update(row) for row in run.to_dict("records")]
    assert [i for i, r in enumerate(results) if r.after_gap] == [200]
    assert_parity(detector.score_batch(run), np.array([np.nan if r.score is None else r.score for r in results]))


def test_gap_at_the_threshold_is_not_a_gap(stream, detector):
    run = _with_gap(make_run(seed=11), at=200, seconds=4.0)     # 5 s step: equal to max_gap_s
    scorer = stream.StreamScorer(detector, max_gap_s=5.0)
    assert not any(scorer.update(row).after_gap for row in run.to_dict("records"))


def test_gap_reset_policy_restarts_calibration(stream, detector):
    run = _with_gap(make_run(seed=12, shift_at=None), at=200, seconds=600)
    run.loc[200:, "flow_rate"] += 30.0                             # the pump restarted at a new level
    scorer = stream.StreamScorer(detector, max_gap_s=5.0, gap_policy="reset")
    results = [scorer.update(row) for row in run.to_dict("records")]
    assert results[200].after_gap and results[200].status == "warming_up"
    assert all(r.score is None for r in results[200:200 + detector.n_burn])
    tail = np.array([np.nan if r.score is None else r.score for r in results[200:]])
    assert_parity(detector.score_batch(run.iloc[200:].reset_index(drop=True)), tail)


def test_constructor_validates_policy(stream, detector):
    with pytest.raises(ValueError):
        stream.StreamScorer(detector, gap_policy="ignore")
    with pytest.raises(ValueError):
        stream.StreamScorer(detector, max_gap_s=0)


# --------------------------------------------------------------------------- persistence and memory
@pytest.mark.parametrize("cut", [1, 30, 50, 51, 250])
def test_snapshot_restore_continues_identically(stream, detector, cut):
    run = make_run(seed=13)
    rows = run.to_dict("records")
    original = stream.StreamScorer(detector, machine_id="m7")
    for row in rows[:cut]:
        original.update(row)
    snap = json.loads(json.dumps(original.snapshot()))       # must survive a trip through JSON
    restored = stream.StreamScorer.restore(detector, snap)
    for row in rows[cut:]:
        a, b = original.update(row), restored.update(row)
        assert a == b, f"restored scorer diverged at sample {a.n_seen}: {a} vs {b}"
    if cut > 1:                                                # the last timestamp survived too
        with pytest.raises(stream.OutOfOrderError):
            stream.StreamScorer.restore(detector, snap).update(dict(rows[0], flow_rate=0.0))


def test_restore_refuses_another_detector_version(stream, detector, mods):
    scorer = stream.StreamScorer(detector)
    for row in make_run(seed=14).to_dict("records")[:10]:
        scorer.update(row)
    other = mods[0].Detector(n_burn=50, threshold=3.0, version="synthetic-test-2")
    with pytest.raises(ValueError):
        stream.StreamScorer.restore(other, scorer.snapshot())


def _sizes(obj) -> list[int]:
    found = []
    for value in vars(obj).values():
        if isinstance(value, (list, tuple, dict, set, np.ndarray)) or hasattr(value, "__len__") and not isinstance(value, (str, bytes)):
            try:
                found.append(len(value))
            except TypeError:
                pass
    return found


def test_state_does_not_grow_with_the_stream(stream, detector):
    long_run = make_run(n=6000, seed=15, shift_at=None)
    scorer = stream.StreamScorer(detector)
    rows = long_run.to_dict("records")
    for row in rows[:600]:
        scorer.update(row)
    size_600 = len(json.dumps(scorer.snapshot()))
    for row in rows[600:]:
        scorer.update(row)
    size_6000 = len(json.dumps(scorer.snapshot()))
    assert abs(size_6000 - size_600) < 64, f"snapshot grew from {size_600} to {size_6000} characters"
    assert max(_sizes(scorer), default=0) <= 2 * detector.n_burn, \
        "the scorer holds a collection that grows with the stream; keep O(1) accumulators instead"


# --------------------------------------------------------------------------- registry
def test_registry_keeps_machines_independent(stream, detector):
    a, b = make_run(seed=16), make_run(seed=17, level=60.0, shift_at=150)
    reg = stream.StreamRegistry(detector)
    assert reg.register("pump-a") is True and reg.register("pump-b") is True
    assert reg.register("pump-a") is False
    out = {"pump-a": [], "pump-b": []}
    for ra, rb in zip(a.to_dict("records"), b.to_dict("records")):          # interleaved arrival
        for mid, row in (("pump-a", ra), ("pump-b", rb)):
            r = reg.update(mid, row)
            assert r.machine_id == mid
            out[mid].append(np.nan if r.score is None else r.score)
    assert_parity(detector.score_batch(a), np.array(out["pump-a"]))
    assert_parity(detector.score_batch(b), np.array(out["pump-b"]))
    assert reg.machines() == ["pump-a", "pump-b"]


def test_registry_unknown_machine_and_remove(stream, detector):
    reg = stream.StreamRegistry(detector)
    row = make_run(seed=18).to_dict("records")[0]
    with pytest.raises(stream.UnknownMachineError):
        reg.update("ghost", row)
    assert issubclass(stream.UnknownMachineError, KeyError)
    reg.register("p1")
    reg.update("p1", row)
    reg.remove("p1")
    with pytest.raises(stream.UnknownMachineError):
        reg.update("p1", row)
    with pytest.raises(stream.UnknownMachineError):
        reg.remove("p1")


def test_registering_again_keeps_state(stream, detector):
    reg = stream.StreamRegistry(detector)
    rows = make_run(seed=19).to_dict("records")
    reg.register("p1")
    for row in rows[:70]:
        reg.update("p1", row)
    assert reg.register("p1") is False
    assert reg.update("p1", rows[70]).n_seen == 71


def test_registry_snapshot_restore(stream, detector):
    reg = stream.StreamRegistry(detector, max_gap_s=5.0)
    runs = {"p1": make_run(seed=20), "p2": make_run(seed=21, level=80.0)}
    for mid, run in runs.items():
        reg.register(mid)
        for row in run.to_dict("records")[:130]:
            reg.update(mid, row)
    restored = stream.StreamRegistry.restore(detector, json.loads(json.dumps(reg.snapshot())))
    assert restored.machines() == ["p1", "p2"]
    for mid, run in runs.items():
        for row in run.to_dict("records")[130:]:
            assert reg.update(mid, row) == restored.update(mid, row)


def test_score_result_fields(stream, detector):
    r = stream.StreamScorer(detector, machine_id="x").update(make_run(seed=22).to_dict("records")[0])
    assert isinstance(r.timestamp, pd.Timestamp)
    assert (r.after_gap, r.duplicate) == (False, False)
    assert math.isclose(r.n_seen, 1)
