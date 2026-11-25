"""Unit tests for the given monitoring and registry modules (SYNTHETIC data)."""
from __future__ import annotations

import numpy as np
import pytest

from flowguard.bundle import save_bundle
from flowguard.monitoring import DriftMonitor, delayed_label_report, extract_events, psi
from flowguard.registry import Registry, RegistryError
from flowguard.scoring import ZScoreModel


def test_psi_zero_for_identical_and_positive_for_shift():
    rng = np.random.default_rng(0)
    ref = rng.normal(100, 2, 5000)
    edges = DriftMonitor.calibrate(ref, [ref]).edges
    assert psi(ref, ref, edges) == pytest.approx(0.0, abs=1e-9)
    assert psi(ref, ref * 0.8, edges) > 1.0


def test_extract_events_merges_and_filters():
    flags = [True] * 5 + [False] * 2 + [True] * 5 + [False] * 10 + [True] * 3
    assert extract_events(flags, min_duration=10, merge_gap=2) == [(0, 12)]


def test_delayed_label_report_counts():
    rep = delayed_label_report([{"events": [(5, 9)], "labels": [0] * 4 + [1] * 6},
                                {"events": [(0, 2)], "labels": [0] * 10}])
    assert rep["faults"] == 1 and rep["faults_detected"] == 1 and rep["false_alarm_events"] == 1


def test_registry_promote_rollback(tmp_path):
    reg = Registry(tmp_path / "reg")
    for v, thr in (("v1", 7.0), ("v2", 1.5)):
        reg.register(save_bundle(ZScoreModel("flow_rate", 10, thr, 1, 0, v), tmp_path / v))
    reg.promote("v1")
    reg.promote("v2")
    assert reg.rollback() == "v1" and reg.current() == "v1"
    with pytest.raises(RegistryError):
        reg.register(tmp_path / "v1")
