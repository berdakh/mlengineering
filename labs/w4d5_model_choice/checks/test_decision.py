"""Checks for flowguard.decision. SYNTHETIC inputs only; no data download, no network.

What is checked is behaviour stated in the module docstring, not one implementation.
"""
from __future__ import annotations

import pickle
import time

import numpy as np
import pandas as pd
import pytest


# ----------------------------------------------------------------------------- helpers
class FakeClock:
    """Returns pre-programmed readings. Each scorer call consumes two readings (start, end)."""

    def __init__(self, durations_s):
        self.readings, t = [], 0.0
        for d in durations_s:
            self.readings += [t, t + d]
            t += d + 1.0
        self.i = 0

    def __call__(self):
        value = self.readings[self.i]
        self.i += 1
        return value


class RecordingScorer:
    def __init__(self):
        self.batches = []

    def score(self, rows):
        self.batches.append(rows.copy())
        return np.zeros(len(rows))


def frame(n=10):
    return pd.DataFrame({"x": np.arange(n, dtype=float), "row": np.arange(n)})


# ----------------------------------------------------------------------------- latency
def test_latency_percentiles_exact_with_fake_clock(dec):
    durations = [0.001 * k for k in range(1, 101)]          # 1 ms .. 100 ms, no warm-up
    res = dec.measure_latency(RecordingScorer(), frame(), n_warmup=0, n_repeat=100, clock=FakeClock(durations))
    ms = np.array(durations) * 1000
    assert res["n"] == 100
    assert res["p50_ms"] == pytest.approx(np.percentile(ms, 50))
    assert res["p95_ms"] == pytest.approx(np.percentile(ms, 95))
    assert res["p99_ms"] == pytest.approx(np.percentile(ms, 99))
    assert res["mean_ms"] == pytest.approx(ms.mean())
    assert res["max_ms"] == pytest.approx(100.0)


def test_latency_excludes_warmup(dec):
    # the first 20 calls are slow (cold caches, lazy imports); they must not reach the percentiles
    durations = [0.5] * 20 + [0.002] * 200
    res = dec.measure_latency(RecordingScorer(), frame(), n_warmup=20, n_repeat=200, clock=FakeClock(durations))
    assert res["max_ms"] == pytest.approx(2.0)
    assert res["p99_ms"] == pytest.approx(2.0)


def test_latency_calls_and_batches(dec):
    scorer = RecordingScorer()
    dec.measure_latency(scorer, frame(10), n_warmup=3, n_repeat=12, batch_size=4)
    assert len(scorer.batches) == 15, "warm-up calls are made, then n_repeat timed calls"
    assert all(len(b) == 4 for b in scorer.batches), "every call gets exactly batch_size rows"
    # batch i starts at row (i * batch_size) % n and wraps around
    assert scorer.batches[0]["row"].tolist() == [0, 1, 2, 3]
    assert scorer.batches[2]["row"].tolist() == [8, 9, 0, 1]


def test_latency_real_clock_smoke(dec):
    class Sleepy:
        def score(self, rows):
            time.sleep(0.002)
            return np.zeros(len(rows))
    res = dec.measure_latency(Sleepy(), frame(), n_warmup=2, n_repeat=10)
    assert 1.5 <= res["p50_ms"] < 200, "a 2 ms scorer should time at roughly 2 ms per call"
    assert res["p50_ms"] <= res["p95_ms"] <= res["p99_ms"] <= res["max_ms"]


def test_latency_rejects_bad_arguments(dec):
    with pytest.raises(ValueError):
        dec.measure_latency(RecordingScorer(), frame(), n_warmup=0, n_repeat=0)
    with pytest.raises(ValueError):
        dec.measure_latency(RecordingScorer(), frame(0), n_warmup=0, n_repeat=5)


# ----------------------------------------------------------------------------- size
def test_size_is_a_real_file(dec, tmp_path):
    model = {"weights": np.ones(1000)}
    path = tmp_path / "model.pkl"
    size = dec.model_size_bytes(model, path)
    assert path.is_file(), "with a path, the serialised model must be written there"
    assert size == path.stat().st_size
    with path.open("rb") as fh:
        restored = pickle.load(fh)
    assert np.array_equal(restored["weights"], model["weights"])


def test_size_counts_contents_not_the_wrapper(dec):
    small = {"w": np.zeros(10)}
    big = {"w": np.zeros(200_000)}
    s_small, s_big = dec.model_size_bytes(small), dec.model_size_bytes(big)
    assert s_big >= 200_000 * 8, "a 200,000-float model takes at least 1.6 MB on disk"
    assert s_small < 5_000
    assert s_big > 100 * s_small


# ----------------------------------------------------------------------------- dominance
TABLE = [
    {"name": "A", "auc": 0.80, "lat": 1.0},
    {"name": "B", "auc": 0.85, "lat": 5.0},
    {"name": "C", "auc": 0.78, "lat": 2.0},     # dominated by A (worse on both)
    {"name": "D", "auc": 0.85, "lat": 6.0},     # dominated by B (tie on auc, worse on latency)
    {"name": "E", "auc": 0.90, "lat": 40.0},
]
OBJ = {"auc": "max", "lat": "min"}


def test_pareto_known_answer(dec):
    assert dec.pareto_front(TABLE, OBJ) == ["A", "B", "E"]


def test_pareto_respects_direction(dec):
    assert dec.pareto_front(TABLE, {"auc": "max", "lat": "max"}) == ["E"]
    assert dec.pareto_front(TABLE, {"auc": "min", "lat": "min"}) == ["A", "C"]


def test_pareto_identical_rows_are_both_kept(dec):
    rows = [{"name": "X", "auc": 0.8, "lat": 1.0}, {"name": "Y", "auc": 0.8, "lat": 1.0},
            {"name": "Z", "auc": 0.7, "lat": 1.0}]
    assert dec.pareto_front(rows, OBJ) == ["X", "Y"]


def test_pareto_accepts_dataframe_and_keeps_order(dec):
    df = pd.DataFrame(TABLE[::-1])
    assert dec.pareto_front(df, OBJ) == ["E", "B", "A"]


def test_dominated_by_names(dec):
    by = dec.dominated_by(TABLE, OBJ)
    assert by["A"] == [] and by["E"] == []
    assert by["C"] == ["A"]
    assert set(by["D"]) == {"B"}


def test_pareto_rejects_bad_input(dec):
    with pytest.raises(ValueError):
        dec.pareto_front(TABLE, {"auc": "bigger"})
    with pytest.raises(ValueError):
        dec.pareto_front(TABLE, {"missing": "max"})
    with pytest.raises(ValueError):
        dec.pareto_front([{"name": "A", "auc": float("nan"), "lat": 1.0}, TABLE[1]], OBJ)


# ----------------------------------------------------------------------------- practical difference
@pytest.mark.parametrize("lo, hi, expected", [
    (0.06, 0.10, "better"),
    (-0.10, -0.06, "worse"),
    (-0.02, 0.03, "equivalent"),
    (0.01, 0.08, "inconclusive"),      # excludes 0, but not shown to exceed the MPID
    (-0.08, 0.08, "inconclusive"),
    (-0.08, -0.01, "inconclusive"),
    (0.05, 0.09, "inconclusive"),      # touches the boundary: not wholly above +MPID
    (0.0, 0.0, "equivalent"),
])
def test_classify_difference(dec, lo, hi, expected):
    assert dec.classify_difference(lo, hi, 0.05) == expected


def test_classify_rejects_bad_input(dec):
    for args in [(0.0, 0.1, 0.0), (0.2, 0.1, 0.05), (float("nan"), 0.1, 0.05)]:
        with pytest.raises(ValueError):
            dec.classify_difference(*args)


# ----------------------------------------------------------------------------- table and recommendation
def candidates_table(dec, rows):
    return dec.decision_table(rows, {"primary": "max", "p95_ms": "min"}, mpid=0.05)


ROWS = [
    {"name": "simple", "complexity": 0, "primary": 0.76, "p95_ms": 0.4, "diff_lo": 0.0, "diff_hi": 0.0},
    {"name": "medium", "complexity": 1, "primary": 0.70, "p95_ms": 0.5, "diff_lo": -0.21, "diff_hi": 0.07},
    {"name": "forest", "complexity": 2, "primary": 0.56, "p95_ms": 7.4, "diff_lo": -0.30, "diff_hi": -0.12},
    {"name": "learned", "complexity": 3, "primary": 0.83, "p95_ms": 0.7, "diff_lo": 0.02, "diff_hi": 0.13},
]


def test_decision_table_columns(dec):
    t = candidates_table(dec, ROWS)
    assert list(t["name"]) == ["simple", "medium", "forest", "learned"], "row order is kept"
    assert t["pareto"].tolist() == [True, False, False, True]
    assert t["vs_reference"].tolist() == ["equivalent", "inconclusive", "worse", "inconclusive"]
    assert t.loc[t["name"] == "forest", "dominated_by"].item().split(";") != [""]
    assert t.loc[t["name"] == "simple", "dominated_by"].item() == ""


def test_recommend_prefers_simple_when_nothing_is_better(dec):
    rec = dec.recommend(candidates_table(dec, ROWS), {"p95_ms": ("<=", 20.0)})
    assert rec["choice"] == "simple", "+0.07 [0.02, 0.13] with MPID 0.05 is not shown to matter"
    assert "forest" not in rec["eligible"], "a candidate shown to be worse is never eligible"


def test_recommend_takes_the_better_candidate(dec):
    rows = [dict(r) for r in ROWS]
    rows[3].update(diff_lo=0.06, diff_hi=0.15)
    rec = dec.recommend(candidates_table(dec, rows), {"p95_ms": ("<=", 20.0)})
    assert rec["choice"] == "learned"


def test_recommend_applies_hard_constraints_first(dec):
    rows = [dict(r) for r in ROWS]
    rows[3].update(diff_lo=0.06, diff_hi=0.15, p95_ms=50.0)     # better, but too slow
    rec = dec.recommend(candidates_table(dec, rows), {"p95_ms": ("<=", 20.0)})
    assert rec["choice"] == "simple"
    rec = dec.recommend(candidates_table(dec, rows), {"p95_ms": ("<=", 0.1)})
    assert rec["choice"] is None and rec["reason"], "no feasible candidate: say so, do not pick one"


def test_recommend_breaks_complexity_ties_by_primary(dec):
    rows = [dict(r) for r in ROWS]
    rows[1].update(complexity=0, primary=0.80, diff_lo=-0.02, diff_hi=0.03)
    rec = dec.recommend(candidates_table(dec, rows), {"p95_ms": ("<=", 20.0)})
    assert rec["choice"] == "medium"
