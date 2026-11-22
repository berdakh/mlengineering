"""Project leak probes: audit_features, time_monotone_columns, clock_probe (SYNTHETIC frames)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from conftest import SENSORS, synth_tidy


def test_audit_accepts_sensor_features(leakcheck):
    leakcheck.audit_features([*SENSORS, "flow_rate_mean_30", "pressure_diff"])


@pytest.mark.parametrize("bad", ["t", "datetime", "anomaly", "changepoint", "experiment_id"])
def test_audit_rejects_forbidden_names_and_names_them(leakcheck, bad):
    with pytest.raises(ValueError) as err:
        leakcheck.audit_features(["flow_rate", bad, "pressure"])
    assert bad in str(err.value)


def test_audit_honours_custom_forbidden_list(leakcheck):
    with pytest.raises(ValueError):
        leakcheck.audit_features(["flow_rate", "run_counter"], forbidden=["run_counter"])


def test_time_monotone_columns_finds_disguised_clocks(leakcheck):
    tidy = synth_tidy(rows=60)
    rng = np.random.default_rng(0)
    t = tidy["t"].to_numpy(dtype=float)
    features = pd.DataFrame({
        "noise": rng.normal(size=len(tidy)),
        "samples_seen": t * 2.0 + 5.0,                        # a clock
        "cooling": -np.sqrt(t) + rng.normal(0, 0.01, len(tidy)),   # monotone decreasing, tiny noise
        "flow_rate": tidy["flow_rate"].to_numpy(),
        "constant": 1.0,
    })
    flagged = set(leakcheck.time_monotone_columns(features, tidy))
    assert flagged == {"samples_seen", "cooling"}, flagged


def test_time_monotone_is_judged_within_experiments(leakcheck):
    """A counter that restarts in every experiment is uncorrelated with a global row number,
    but it is still a clock."""
    tidy = synth_tidy(rows=30).sample(frac=1.0, random_state=1).reset_index(drop=True)
    features = pd.DataFrame({"elapsed_minutes": tidy["t"] / 60.0,
                             "noise": np.random.default_rng(1).normal(size=len(tidy))})
    assert leakcheck.time_monotone_columns(features, tidy) == ["elapsed_minutes"]


def test_time_monotone_rejects_misaligned_input(leakcheck):
    tidy = synth_tidy(rows=20)
    with pytest.raises(ValueError):
        leakcheck.time_monotone_columns(pd.DataFrame({"x": [1.0, 2.0]}), tidy)


def test_clock_probe_exposes_a_fixed_protocol(leakcheck):
    tidy = synth_tidy(rows=60, onset="half")
    labelled = tidy[tidy["family"] != "anomaly-free"]
    probe = leakcheck.clock_probe(labelled)
    assert probe["prevalence"] == pytest.approx(0.5)
    assert probe["pr_auc_clock"] == pytest.approx(1.0)
    assert probe["lift"] == pytest.approx(probe["pr_auc_clock"] - probe["prevalence"])
    assert probe["onset_t_median"] == pytest.approx(30)


def test_clock_probe_is_near_zero_when_onsets_are_randomised(leakcheck):
    tidy = synth_tidy(sizes={"valve1": 60, "other": 60}, rows=40, onset="random", seed=5)
    labelled = tidy[tidy["family"] != "anomaly-free"]
    probe = leakcheck.clock_probe(labelled)
    assert abs(probe["lift"]) < 0.12, probe


def test_clock_probe_respects_experiments_and_burn_in(leakcheck):
    tidy = synth_tidy(rows=60, onset="half")
    chosen = ["valve1/0", "other/3"]
    probe = leakcheck.clock_probe(tidy, experiments=chosen, burn_in=20)
    assert probe["n_experiments"] == 2
    assert probe["n_rows"] == 2 * 40
    assert probe["prevalence"] == pytest.approx(30 / 40)


def test_clock_probe_needs_positives(leakcheck):
    tidy = synth_tidy(rows=20)
    with pytest.raises(ValueError):
        leakcheck.clock_probe(tidy[tidy["family"] == "anomaly-free"])
