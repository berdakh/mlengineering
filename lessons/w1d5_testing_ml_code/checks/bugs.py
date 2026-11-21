"""Realistic defects injected into the reference pumpwatch package.

SPOILER: reading this file before your suite is finished tells you exactly which
tests to write. If you do, record the lab as guided practice, not independent work.
"""
from harness import Bug

F = "pumpwatch/features.py"
BUGS = [
    Bug("rms_missing_sqrt", "rms returns the mean square (power), not its root",
        ((F, "return float(np.sqrt(np.mean(np.square(x))))", "return float(np.mean(np.square(x)))"),)),
    Bug("rms_is_mean_abs", "rms returns the mean absolute value (right units, right scaling, wrong number)",
        ((F, "return float(np.sqrt(np.mean(np.square(x))))", "return float(np.mean(np.abs(x)))"),)),
    Bug("line_length_missing_abs", "line_length sums signed differences, i.e. returns x[-1] - x[0]",
        ((F, "return float(np.sum(np.abs(np.diff(x))))", "return float(np.sum(np.diff(x)))"),)),
    Bug("p2p_is_abs_max", "peak_to_peak returns max(|x|) instead of max - min",
        ((F, "return float(np.max(x) - np.min(x))", "return float(np.max(np.abs(x)))"),)),
    Bug("band_power_not_one_sided", "band_power forgets to double the positive-frequency bins",
        ((F, "    psd[1:-1] *= 2.0  # fold negative frequencies into the one-sided estimate\n", ""),)),
    Bug("band_power_inclusive_upper_edge", "band is [low, high] instead of [low, high): edge bins counted twice",
        ((F, "(freqs >= low_hz) & (freqs < high_hz)", "(freqs >= low_hz) & (freqs <= high_hz)"),)),
    Bug("band_power_keeps_dc", "band_power does not remove the mean before the FFT",
        ((F, "spectrum = np.fft.rfft(x - x.mean())", "spectrum = np.fft.rfft(x)"),)),
    Bug("fill_gaps_zero_fill", "NaN gaps are replaced by 0 instead of being interpolated",
        ((F, 'return pd.Series(np.asarray(x, dtype=float)).interpolate(limit_direction="both").to_numpy()',
          "return np.nan_to_num(np.asarray(x, dtype=float), nan=0.0)"),)),
    Bug("ratio_inverted", "ratio feature is low/high instead of high/low",
        ((F, '"ratio": bp_high / bp_low,', '"ratio": bp_low / bp_high,'),)),
    Bug("feature_table_ignores_sample_order", "build_feature_table trusts row order instead of sorting by sample",
        ((F, '        g = g.sort_values("sample")\n', ""),)),
    Bug("load_windows_skips_validation", "load_windows returns frames with missing required columns",
        (("pumpwatch/io.py",
          '    if missing:\n        raise ValueError(f"{path} is missing required columns: {missing}")\n', ""),)),
    Bug("split_leaks_units", "split shuffles rows, so a unit appears in both train and test",
        (("pumpwatch/split.py", "from sklearn.model_selection import GroupShuffleSplit",
          "from sklearn.model_selection import ShuffleSplit as GroupShuffleSplit"),)),
    Bug("split_ignores_seed", "split uses a hard-coded random_state; the seed argument does nothing",
        (("pumpwatch/split.py", "test_size=test_fraction, random_state=seed)",
          "test_size=test_fraction, random_state=7)"),)),
    Bug("model_scores_wrong_class", "evaluation uses the probability of class 0 as the fault score",
        (("pumpwatch/model.py", "model.predict_proba(X[test_idx])[:, 1]",
          "model.predict_proba(X[test_idx])[:, 0]"),)),
]
