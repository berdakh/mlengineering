"""Known-answer and invariance tests for the signal features.

Oracles used here come from mathematics, never from the implementation:
  * RMS of A*sin over whole periods is A/sqrt(2)
  * Parseval: one-sided PSD integrated over all bins equals the (population) variance
  * a pure tone of amplitude A carries power A^2/2, all of it in its own bin
  * scaling x by a scales amplitude features by |a| and power features by a^2
"""
import numpy as np
import pytest

from signals import FS, N, tone
from pumpwatch.features import (
    band_power, build_feature_table, fill_gaps, line_length, peak_to_peak, rms, window_features,
)

DF = FS / N  # frequency resolution (2 Hz)


# ---- known answers -------------------------------------------------------------------

@pytest.mark.parametrize("amplitude", [0.5, 1.0, 3.0])
def test_rms_of_sine_is_amplitude_over_root_two(amplitude):
    x = tone(24.0, amplitude)  # 12 whole periods in the window
    assert rms(x) == pytest.approx(amplitude / np.sqrt(2), rel=0.15)


def test_rms_of_constant_is_its_magnitude():
    assert rms(np.full(50, -3.0)) == pytest.approx(3.0)


def test_line_length_of_ramp_and_zigzag():
    assert line_length(np.arange(5.0)) == pytest.approx(4.0)
    # A monotone ramp cannot distinguish sum|dx| from sum(dx); a zigzag can.
    assert line_length(np.array([0.0, 1.0, 0.0, 1.0, 0.0])) == pytest.approx(4.0)


def test_peak_to_peak_is_max_minus_min_not_max_abs():
    assert peak_to_peak(np.array([3.0, 5.0, 4.0])) == pytest.approx(2.0)
    assert peak_to_peak(np.array([-1.0, 4.0])) == pytest.approx(5.0)


def test_band_power_parseval_total_power_equals_variance(rng):
    x = rng.standard_normal(N) + 5.0  # the offset must not count as power
    total = band_power(x, FS, 0.0, FS / 2 + DF)  # upper edge is exclusive: go past Nyquist
    assert total == pytest.approx(np.var(x), rel=0.15)


@pytest.mark.parametrize("freq_hz, amplitude", [(24.0, 1.0), (92.0, 0.5)])
def test_band_power_of_pure_tone_is_half_amplitude_squared(freq_hz, amplitude):
    x = tone(freq_hz, amplitude)
    assert band_power(x, FS, freq_hz - 10, freq_hz + 10) == pytest.approx(amplitude**2 / 2, rel=0.15)


def test_band_power_tone_outside_band_contributes_nothing():
    assert band_power(tone(92.0), FS, 10.0, 40.0) == pytest.approx(0.0, abs=1e-12)


def test_band_edges_are_half_open():
    x = tone(40.0)  # exactly on the shared edge of the two bands
    assert band_power(x, FS, 10.0, 40.0) == pytest.approx(0.0, abs=1e-12)
    assert band_power(x, FS, 40.0, 70.0) == pytest.approx(0.5, rel=0.15)


def test_band_power_is_additive_over_adjacent_bands(rng):
    x = rng.standard_normal(N)
    whole = band_power(x, FS, 10.0, 70.0)
    assert band_power(x, FS, 10.0, 40.0) + band_power(x, FS, 40.0, 70.0) == pytest.approx(whole, rel=0.15)


def test_window_features_known_two_tone_signal():
    x = tone(24.0, 1.0) + tone(92.0, 0.5)
    feats = window_features(x, FS)
    assert feats["bp_low"] == pytest.approx(0.5, rel=0.15)
    assert feats["bp_high"] == pytest.approx(0.125, rel=0.15)
    assert feats["ratio"] == pytest.approx(0.25, rel=0.15)  # high / low


# ---- invariances (metamorphic relations) ---------------------------------------------

@pytest.mark.parametrize("a", [-2.0, 0.1, 7.0])
def test_scaling_laws(rng, a):
    x = rng.standard_normal(N)
    assert rms(a * x) == pytest.approx(abs(a) * rms(x), rel=0.15)
    assert line_length(a * x) == pytest.approx(abs(a) * line_length(x), rel=0.15)
    assert peak_to_peak(a * x) == pytest.approx(abs(a) * peak_to_peak(x), rel=0.15)
    assert band_power(a * x, FS, 10, 40) == pytest.approx(a**2 * band_power(x, FS, 10, 40), rel=0.15)


def test_band_power_ignores_constant_offset(rng):
    x = rng.standard_normal(N)
    assert band_power(x + 100.0, FS, 0.0, 40.0) == pytest.approx(band_power(x, FS, 0.0, 40.0), rel=0.15)


# ---- gaps ----------------------------------------------------------------------------

def test_fill_gaps_interpolates_linearly_and_extends_edges():
    np.testing.assert_allclose(fill_gaps(np.array([0.0, 1.0, np.nan, 3.0, 4.0])), [0, 1, 2, 3, 4])
    np.testing.assert_allclose(fill_gaps(np.array([np.nan, 1.0, 2.0, np.nan])), [1, 1, 2, 2])


def test_fill_gaps_does_not_modify_its_input():
    x = np.array([0.0, np.nan, 2.0])
    fill_gaps(x)
    assert np.isnan(x[1])


def test_window_features_with_gap_are_finite_and_close_to_gap_free():
    clean = tone(24.0)
    gappy = clean.copy()
    gappy[[10, 11, 60]] = np.nan
    feats, ref = window_features(gappy, FS), window_features(clean, FS)
    assert all(np.isfinite(v) for v in feats.values())
    assert feats["rms"] == pytest.approx(ref["rms"], rel=0.05)  # interpolation error, not exactness


# ---- feature table -------------------------------------------------------------------

def test_feature_table_one_row_per_unit_window(make_frame):
    df = make_frame(n_units=3, n_windows=4)
    table = build_feature_table(df, FS)
    assert len(table) == 12
    assert not table.duplicated(["unit_id", "window_id"]).any()
    assert not table.isna().any().any()
    expected_labels = df.groupby(["unit_id", "window_id"])["label"].first()
    got = table.set_index(["unit_id", "window_id"])["label"]
    assert got.sort_index().tolist() == expected_labels.sort_index().tolist()


def test_feature_table_does_not_depend_on_row_order(make_frame):
    df = make_frame(n_units=2, n_windows=2)
    shuffled = df.sample(frac=1.0, random_state=0)
    keys = ["unit_id", "window_id"]
    a = build_feature_table(df, FS).sort_values(keys).reset_index(drop=True)
    b = build_feature_table(shuffled, FS).sort_values(keys).reset_index(drop=True)
    np.testing.assert_allclose(a["line_length"], b["line_length"], rtol=1e-9)
    np.testing.assert_allclose(a["bp_high"], b["bp_high"], rtol=1e-9)
