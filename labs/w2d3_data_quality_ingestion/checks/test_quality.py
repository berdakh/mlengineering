"""run_checks: reports every planted defect, blames the right experiment, passes clean data, never raises."""
from __future__ import annotations

import pandas as pd
import pytest

import synth
from conftest import failed


def _api():
    from flowguard.data import load_raw
    from flowguard.quality import run_checks
    return load_raw, run_checks


def test_clean_data_passes_every_check(raw_dir):
    load_raw, run_checks = _api()
    results = run_checks(load_raw(raw_dir()))
    assert len(results) >= 6, "expected one result per check, for at least six distinct checks"
    for r in results:
        assert isinstance(r.name, str) and r.name, "every result needs a name"
        assert isinstance(r.detail, str), "detail must be a string"
        assert r.severity in ("error", "warning"), f"severity must be 'error' or 'warning', got {r.severity!r}"
        assert r.passed in (True, False)
    assert len({r.name for r in results}) == len(results), "check names must be unique"
    bad = failed(results)
    assert not bad, "clean synthetic data must pass; failed: " + "; ".join(f"{r.name}: {r.detail}" for r in bad)


@pytest.mark.parametrize("defect", sorted(synth.DEFECTS))
def test_each_defect_is_reported_against_the_right_experiment(raw_dir, defect):
    load_raw, run_checks = _api()
    severity = synth.DEFECTS[defect][1]
    bad = failed(run_checks(load_raw(raw_dir(defect))))
    assert bad, f"defect '{defect}' in {synth.BAD} was not reported by any check"
    hits = [r for r in bad if synth.BAD in r.detail]
    assert hits, f"a check failed but no failing detail names the experiment {synth.BAD}: {[r.detail for r in bad]}"
    assert any(r.severity == severity for r in hits), \
        f"defect '{defect}' should fail a check of severity '{severity}' (see the lab contract)"
    for clean in synth.CLEAN_LABELLED:
        assert not any(clean in r.detail for r in bad), f"clean experiment {clean} was blamed: {[r.detail for r in bad]}"


def test_two_defects_in_one_table_are_both_reported(tmp_path):
    load_raw, run_checks = _api()
    frames = synth.clean_frames()
    frames["valve1/1"] = synth.gap_300s(frames["valve1/1"])
    frames["other/1"] = synth.duplicate_timestamps(frames["other/1"])
    bad = failed(run_checks(load_raw(synth.write_raw(tmp_path / "raw", frames))))
    text = " | ".join(r.detail for r in bad)
    assert "valve1/1" in text and "other/1" in text, "run_checks must evaluate every check, not stop at the first failure"


def test_missing_column_is_reported_not_raised(raw_dir):
    load_raw, run_checks = _api()
    tidy = load_raw(raw_dir()).drop(columns=["pressure"])
    results = run_checks(tidy)          # must not raise
    bad = [r for r in failed(results) if r.severity == "error"]
    assert bad and any("pressure" in r.detail for r in bad), "a missing column must fail an error check that names it"


def test_checks_do_not_modify_or_repair_their_input(raw_dir):
    load_raw, run_checks = _api()
    tidy = load_raw(raw_dir("unsorted_rows"))
    before = tidy.copy(deep=True)
    run_checks(tidy)
    pd.testing.assert_frame_equal(tidy, before)


def test_thresholds_tolerate_ordinary_jitter_and_quantisation(tmp_path):
    """Real loggers skip a second now and then and quantise slow signals; neither is a defect."""
    load_raw, run_checks = _api()
    frames = synth.clean_frames()
    df = frames["valve1/0"].copy()
    stamps = pd.to_datetime(df["datetime"])
    stamps[200:] = stamps[200:] + pd.Timedelta(seconds=1)      # one 2 s step
    df["datetime"] = stamps.dt.strftime("%Y-%m-%d %H:%M:%S")
    df["Volume Flow RateRMS"] = df["Volume Flow RateRMS"].round(0)   # quantised: short repeats
    df.loc[10:39, "Volume Flow RateRMS"] = 74.0                      # a 30-sample plateau
    frames["valve1/0"] = df
    bad = failed(run_checks(load_raw(synth.write_raw(tmp_path / "raw", frames))))
    assert not bad, "a 2 s step and a 30-sample plateau are normal in this data: " + "; ".join(r.detail for r in bad)
