"""Challenge checks: causality, development-only selection, consistency and a quality bar."""
from __future__ import annotations

import numpy as np
import pytest

from conftest import DEV_END

SEEDS = (11, 12, 13)


@pytest.mark.parametrize("method", ["seasonal_naive", "ar"])
@pytest.mark.parametrize("fit_end,cut", [(DEV_END, "2025-09-01"), ("2024-06-01", "2024-09-01")])
def test_scores_never_use_later_dates(det, fresh, method, fit_end, cut):
    """Changing sales from ``cut`` onwards (cut is after the fit window) must leave every earlier
    score unchanged: parameters come from dates < fit_end, forecasts from earlier dates only."""
    df = fresh(11)
    base = np.asarray(det.store_scores(df, method, fit_end), dtype=float)
    assert base.shape == (len(df),)
    changed = df.copy()
    later = changed["date"] >= cut
    changed.loc[later, "sales"] *= 3.0
    after = np.asarray(det.store_scores(changed, method, fit_end), dtype=float)
    early = (~later).to_numpy()
    np.testing.assert_allclose(after[early], base[early], equal_nan=True, atol=1e-9,
                               err_msg=f"{method}: scores before {cut} changed when later sales changed")


def test_choice_ignores_the_test_period(det, fresh):
    df = fresh(12)
    choice = det.choose(df, DEV_END)
    assert choice["method"] in ("seasonal_naive", "ar")
    poisoned = df.copy()
    test = poisoned["date"] >= DEV_END
    rng = np.random.default_rng(0)
    poisoned.loc[test, "promo"] = rng.integers(0, 2, int(test.sum()))
    poisoned.loc[test, "sales"] = rng.uniform(1, 1000, int(test.sum()))
    again = det.choose(poisoned, DEV_END)
    assert again["method"] == choice["method"]
    assert again["threshold"] == pytest.approx(choice["threshold"])


def test_evaluate_is_consistent_with_the_scores(det, fresh):
    df = fresh(13)
    choice = det.choose(df, DEV_END)
    result = det.evaluate(df, DEV_END, choice)
    s = np.nan_to_num(np.asarray(det.store_scores(df, choice["method"], DEV_END), dtype=float), nan=-np.inf)
    test = (df["date"] >= DEV_END).to_numpy()
    flag = s[test] >= choice["threshold"]
    y = df["promo"].to_numpy()[test]
    tp = int((flag & (y == 1)).sum())
    assert result["recall"] == pytest.approx(tp / (y == 1).sum(), abs=1e-9)
    assert result["precision"] == pytest.approx(tp / max(flag.sum(), 1), abs=1e-9)


@pytest.mark.parametrize("seed", SEEDS)
def test_detector_meets_the_quality_bar_on_fresh_stores(det, fresh, seed):
    df = fresh(seed)
    result = det.evaluate(df, DEV_END, det.choose(df, DEV_END))
    assert result["f1"] >= 0.75, f"test F1 {result['f1']:.3f} < 0.75 on generator seed {seed}"
