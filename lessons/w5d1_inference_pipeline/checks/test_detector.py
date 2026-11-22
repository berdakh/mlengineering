"""Detector.score_batch: parity with the evaluated path, fixed configuration, per-run failures.

SYNTHETIC runs. The 'evaluated path' is the w4d5 code shipped in the lab (flowguard.detectors).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from conftest import as_tidy, make_run

RTOL = 1e-12     # same arithmetic in a different order may differ in the last bits, nothing more


def evaluated_scores(fg, df: pd.DataFrame, n_burn: int) -> np.ndarray:
    tidy = as_tidy(df)
    flow = next(c for c in fg.detectors.candidates(n_burn) if c.name == "flow-rate |z|")
    return fg.detectors.score_experiments(flow, tidy, n_burn), tidy


def expected_alarms(fg, tidy, scores, det) -> np.ndarray:
    alarm = np.zeros(len(tidy), dtype=int)
    for _, g in tidy.groupby("experiment_id"):
        g = g[g["t"] >= det.n_burn].sort_values("t")
        idx = g.index.to_numpy()
        for s, e in fg.evaluation.extract_events(scores[idx] >= det.threshold, det.min_duration, det.merge_gap):
            alarm[idx[s:e]] = 1
    return alarm


def test_output_has_the_contract_columns_and_input_order(fg, detector, batch_df):
    frame, errors = detector.score_batch(batch_df)
    assert list(frame.columns) == list(fg.inference.OUTPUT_COLUMNS)
    assert errors == {}
    assert len(frame) == len(batch_df)
    assert (frame["run_id"].astype(str).to_numpy() == batch_df["run_id"].to_numpy()).all()
    assert (pd.to_datetime(frame["datetime"]).to_numpy() == batch_df["datetime"].to_numpy()).all()


def test_scores_match_the_evaluated_path(fg, detector, batch_df):
    frame, _ = detector.score_batch(batch_df)
    expected, tidy = evaluated_scores(fg, batch_df, detector.n_burn)
    scored = tidy["t"].to_numpy() >= detector.n_burn
    np.testing.assert_allclose(frame["score"].to_numpy()[scored], expected[scored], rtol=RTOL, atol=0)


def test_burn_in_rows_are_reported_not_scored(fg, detector, batch_df):
    frame, _ = detector.score_batch(batch_df)
    burn = as_tidy(batch_df)["t"].to_numpy() < detector.n_burn
    assert (frame["status"].to_numpy()[burn] == "burn_in").all()
    assert np.isnan(frame["score"].to_numpy()[burn]).all()
    assert (frame["alarm"].to_numpy()[burn] == 0).all()
    assert (frame["status"].to_numpy()[~burn] == "scored").all()


def test_alarms_match_the_evaluated_post_processing(fg, detector, batch_df):
    frame, _ = detector.score_batch(batch_df)
    expected, tidy = evaluated_scores(fg, batch_df, detector.n_burn)
    np.testing.assert_array_equal(frame["alarm"].to_numpy().astype(int), expected_alarms(fg, tidy, expected, detector))
    assert frame["alarm"].sum() > 0, "the planted faults should raise alarms at threshold 4"


def test_planted_shift_is_not_normalised_away(fg, detector):
    run = make_run("f", n=260, seed=4, shift_at=150, shift_sd=6.0)
    frame, _ = detector.score_batch(run)
    burn = run["flow_rate"].iloc[:100].to_numpy()
    expected = np.abs((run["flow_rate"].to_numpy() - burn.mean()) / burn.std())
    after = frame["score"].to_numpy()[150:]
    np.testing.assert_allclose(after, expected[150:], rtol=RTOL)
    assert np.median(after) > 5


def test_a_later_fault_does_not_change_earlier_scores(fg, detector):
    """Calibration uses the burn-in rows only: what happens later in the run cannot move earlier scores."""
    quiet = make_run("q", n=260, seed=5)
    faulty = quiet.copy()
    faulty.loc[200:, "flow_rate"] += 50.0
    a, _ = detector.score_batch(quiet)
    b, _ = detector.score_batch(faulty)
    np.testing.assert_allclose(a["score"].to_numpy()[100:200], b["score"].to_numpy()[100:200], rtol=RTOL)


@pytest.mark.parametrize("threshold, expect_all", [(0.0, True), (1e9, False)])
def test_threshold_comes_from_the_configuration(fg, detector, batch_df, threshold, expect_all):
    detector.threshold, detector.min_duration, detector.merge_gap = threshold, 1, 0
    frame, _ = detector.score_batch(batch_df)
    scored = frame["status"] == "scored"
    alarms = frame.loc[scored, "alarm"].to_numpy()
    assert (alarms == 1).all() if expect_all else (alarms == 0).all()
    assert (frame["threshold"] == threshold).all()


def test_output_carries_the_model_identity(fg, detector, batch_df):
    frame, _ = detector.score_batch(batch_df)
    assert (frame["model_name"] == "flowguard-test").all()
    assert (frame["model_version"].astype(str) == "9.9.9").all()


def test_unscorable_runs_fail_alone(fg, detector, batch_df):
    short = make_run("short", n=100, seed=11)                    # burn-in only: nothing to score
    holey = make_run("holey", n=200, seed=12)
    holey.loc[120, "flow_rate"] = np.nan
    other_gap = make_run("other_gap", n=200, seed=13)
    other_gap.loc[120, "current"] = np.nan                     # a sensor this detector does not use
    df = pd.concat([batch_df, short, holey, other_gap], ignore_index=True)
    frame, errors = detector.score_batch(df)
    assert set(errors) == {"short", "holey"}
    assert all(isinstance(v, str) and v for v in errors.values())
    for run in ("short", "holey"):
        rows = frame["run_id"] == run
        assert (frame.loc[rows, "status"] == "error").all() and (frame.loc[rows, "alarm"] == 0).all()
        assert frame.loc[rows, "score"].isna().all()
    alone, _ = detector.score_batch(batch_df)
    np.testing.assert_allclose(frame["score"].to_numpy()[: len(batch_df)], alone["score"].to_numpy(), rtol=RTOL)
    assert (frame.loc[frame["run_id"] == "other_gap", "status"] != "error").all()


def test_configuration_round_trips_through_json(fg, detector):
    config = json.loads(json.dumps(detector.to_config()))
    again = fg.inference.Detector.from_config(config)
    assert again.to_config() == detector.to_config()
    del config["threshold"]
    with pytest.raises(ValueError, match="threshold"):
        fg.inference.Detector.from_config(config)
