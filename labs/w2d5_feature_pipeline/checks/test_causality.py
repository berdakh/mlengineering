"""The central property: a feature at row i may use only past-and-present rows of its own experiment."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from conftest import COLUMNS, WINDOWS

FEATURES = [f"{c}__{s}_{w}" for c in COLUMNS for w in WINDOWS for s in ("mean", "std", "min", "max", "slope", "ewma")]
FEATURES += [f"{c}__diff1" for c in COLUMNS]


def _same(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    return np.allclose(a.to_numpy(dtype=float), b.to_numpy(dtype=float), rtol=1e-9, atol=1e-9, equal_nan=True)


def test_output_is_row_aligned_with_input(tidy, build):
    out = build(tidy)
    assert len(out) == len(tidy)
    assert out["experiment_id"].tolist() == tidy["experiment_id"].tolist()
    assert out["t"].tolist() == tidy["t"].tolist()
    missing = [c for c in FEATURES if c not in out.columns]
    assert not missing, f"missing feature columns, e.g. {missing[:4]}"


@pytest.mark.parametrize("cut", [20, 37, 60])
def test_no_look_ahead(tidy, build, cut):
    """Change every sensor value AFTER row `cut` of an experiment: features up to `cut` must not move."""
    before = build(tidy)
    perturbed = tidy.copy()
    later = (perturbed["experiment_id"] == "valve1/0") & (perturbed["t"] > cut)
    perturbed.loc[later, list(COLUMNS)] += 1000.0
    after = build(perturbed)
    earlier = ((tidy["experiment_id"] == "valve1/0") & (tidy["t"] <= cut)).to_numpy()
    assert _same(before.loc[earlier, FEATURES], after.loc[earlier, FEATURES]), (
        f"features at t <= {cut} changed when only rows with t > {cut} were modified: the window sees the future")
    assert not _same(before.loc[later.to_numpy(), FEATURES], after.loc[later.to_numpy(), FEATURES]), \
        "features after the perturbation did not change at all"


def test_no_contamination_between_experiments(tidy, build):
    """Rewrite one experiment completely: every other experiment's features must be identical."""
    before = build(tidy)
    altered = tidy.copy()
    victim = altered["experiment_id"] == "valve1/0"
    altered.loc[victim, list(COLUMNS)] = altered.loc[victim, list(COLUMNS)].to_numpy()[::-1] * 3.0 + 50.0
    after = build(altered)
    others = (~victim).to_numpy()
    assert _same(before.loc[others, FEATURES], after.loc[others, FEATURES]), \
        "changing experiment valve1/0 changed features of another experiment: windows cross experiment boundaries"


def test_experiment_order_does_not_matter(tidy, build):
    """Feeding the experiments in a different order gives the same features for each (experiment, t)."""
    reordered = pd.concat([tidy[tidy["experiment_id"] == e] for e in
                           ("anomaly-free/anomaly-free", "valve1/1", "valve1/0")], ignore_index=True)
    a = build(tidy).set_index(["experiment_id", "t"]).sort_index()
    b = build(reordered).set_index(["experiment_id", "t"]).sort_index()
    assert _same(a[FEATURES], b[FEATURES])


def test_input_is_not_modified(tidy, build):
    snapshot = tidy.copy(deep=True)
    build(tidy)
    pd.testing.assert_frame_equal(tidy, snapshot)
