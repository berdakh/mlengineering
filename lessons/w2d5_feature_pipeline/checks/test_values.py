"""Agreement with a slow reference, warm-up and gap behaviour."""
from __future__ import annotations

import numpy as np

from conftest import COLUMNS, WINDOWS
from reference_impl import slow_features


def test_matches_slow_reference(tidy, build):
    fast = build(tidy)
    slow = slow_features(tidy, WINDOWS, COLUMNS, max_gap_s=5.0)
    for name in slow.columns:
        np.testing.assert_allclose(fast[name].to_numpy(dtype=float), slow[name].to_numpy(),
                                   rtol=1e-7, atol=1e-8, equal_nan=True, err_msg=name)


def test_known_answer_on_a_ramp(tidy, build):
    """x = 2*t exactly: slope 2, mean of the last w values, zero residual spread around the line."""
    ramp = tidy[tidy["experiment_id"] == "valve1/0"].copy()
    ramp["current"] = 2.0 * ramp["t"]
    out = build(ramp)
    w = WINDOWS[0]
    full = out["t"] >= w - 1
    np.testing.assert_allclose(out.loc[full, f"current__slope_{w}"], 2.0, rtol=1e-9)
    np.testing.assert_allclose(out.loc[full, f"current__mean_{w}"], 2.0 * out.loc[full, "t"] - (w - 1), rtol=1e-9)
    np.testing.assert_allclose(out.loc[out["t"] >= 1, "current__diff1"], 2.0, rtol=1e-9)


def test_warm_up_rows_are_nan(tidy, build):
    out = build(tidy)
    for w in WINDOWS:
        first = out[(out["experiment_id"] == "valve1/0") & (out["t"] < w - 1)]
        ready = out[(out["experiment_id"] == "valve1/0") & (out["t"] >= w - 1)]
        assert first[f"pressure__mean_{w}"].isna().all(), "partial windows must be NaN, not a shorter average"
        assert ready[f"pressure__mean_{w}"].notna().all()


def test_time_gap_resets_windows(tidy, build):
    """valve1/1 has a 90 s gap after t = 49: the window must not bridge it."""
    out = build(tidy)
    exp = out[out["experiment_id"] == "valve1/1"].set_index("t")
    w = max(WINDOWS)
    assert exp.loc[50:50 + w - 2, f"flow_rate__mean_{w}"].isna().all(), \
        "rows just after a long gap still have a full-window feature: the window spans the gap"
    assert np.isnan(exp.loc[50, "flow_rate__diff1"])
    assert exp.loc[50 + w - 1, f"flow_rate__mean_{w}"] == exp.loc[50 + w - 1, f"flow_rate__mean_{w}"]
    assert exp.loc[49, "segment"] != exp.loc[50, "segment"]
    assert exp.loc[50, "rows_since_reset"] == 1 and exp.loc[0, "rows_since_reset"] == 1


def test_gap_threshold_is_a_parameter(tidy, build):
    out = build(tidy, max_gap_s=600.0)  # the 90 s gap is now tolerated
    exp = out[out["experiment_id"] == "valve1/1"].set_index("t")
    assert exp.loc[50:60, f"flow_rate__mean_{max(WINDOWS)}"].notna().all()
