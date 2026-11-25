"""Checks for the w5d3 challenge: alarm hysteresis. SYNTHETIC sequences only."""
from __future__ import annotations

import json
import re

import numpy as np
import pytest

T, F, N = True, False, None


def run(hyst, seq, k, m):
    h = hyst.AlarmHysteresis(k, m)
    return [h.update(x) for x in seq]


def test_raises_after_exactly_k_consecutive(hyst):
    assert run(hyst, [T, T, T, T], 3, 1) == [F, F, T, T]
    assert run(hyst, [T, T, F, T, T, T], 3, 5) == [F, F, F, F, F, T]


def test_clears_after_exactly_m_consecutive(hyst):
    seq = [T, F, F, T, F, F, F]
    assert run(hyst, seq, 1, 3) == [T, T, T, T, T, T, F]


def test_exceedance_resets_the_clear_count(hyst):
    assert run(hyst, [T, F, T, F, F], 1, 2) == [T, T, T, T, F]


def test_none_resets_runs_and_keeps_state(hyst):
    assert run(hyst, [T, T, N, T, T], 3, 1) == [F, F, F, F, F]
    assert run(hyst, [T, F, N, F, F], 1, 2) == [T, T, T, T, F]


def test_k1_m1_is_the_raw_exceedance(hyst):
    rng = np.random.default_rng(0)
    seq = list(rng.random(500) > 0.7)
    assert run(hyst, seq, 1, 1) == seq


def test_alarm_property_and_initial_state(hyst):
    h = hyst.AlarmHysteresis(2, 2)
    assert h.alarm is False
    h.update(True), h.update(True)
    assert h.alarm is True


@pytest.mark.parametrize("bad", [(0, 1), (1, 0), (2.5, 1), (-1, 3)])
def test_rejects_invalid_parameters(hyst, bad):
    with pytest.raises(ValueError):
        hyst.AlarmHysteresis(*bad)


@pytest.mark.parametrize("k,m", [(1, 1), (3, 2), (5, 10), (30, 10)])
def test_batch_equals_streaming(hyst, k, m):
    rng = np.random.default_rng(k * 100 + m)
    seq = [None if r < 0.05 else bool(r > 0.6) for r in rng.random(3000)]
    expected = run(hyst, seq, k, m)
    got = hyst.hysteresis_batch(seq, k, m)
    assert isinstance(got, np.ndarray) and got.dtype == bool
    assert got.tolist() == expected
    as_float = np.array([np.nan if x is None else float(x) for x in seq])
    assert hyst.hysteresis_batch(as_float, k, m).tolist() == expected


def test_batch_does_not_backdate_the_alarm(hyst):
    # a batch min-duration filter would mark the run from its first sample; a stream cannot
    assert hyst.hysteresis_batch([F, T, T, T, T, F], 3, 1).tolist() == [F, F, F, T, T, F]


def test_snapshot_restore(hyst):
    rng = np.random.default_rng(7)
    seq = [bool(x) for x in rng.random(400) > 0.5]
    a = hyst.AlarmHysteresis(4, 3)
    for x in seq[:200]:
        a.update(x)
    b = hyst.AlarmHysteresis.restore(json.loads(json.dumps(a.snapshot())))
    assert [a.update(x) for x in seq[200:]] == [b.update(x) for x in seq[200:]]


def test_dev_report_is_filled_in(target):
    report = target / "DEV_REPORT.md"
    assert report.is_file(), "write DEV_REPORT.md in your challenge directory"
    text = report.read_text()
    assert "(the exact command you ran)" not in text, "replace the template placeholder with your command"
    assert len(re.findall(r"\|\s*\d+\s*/\s*\d+\s*\|", text)) >= 3, \
        "the results table needs at least three rules with 'detected/total' counts"
    assert len(text.split("## Recommendation", 1)[-1].split()) >= 60, "the recommendation needs 5-8 sentences"
    assert any(p.is_file() for p in [target / "evaluate_hysteresis.py"]), "commit the script that produced the table"
