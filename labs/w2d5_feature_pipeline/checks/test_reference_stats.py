"""ReferenceStats: statistics come from the rows given to fit, and from nowhere else."""
from __future__ import annotations

import numpy as np
import pytest

from conftest import COLUMNS, WINDOWS

COLS = [f"{c}__mean_{WINDOWS[0]}" for c in COLUMNS] + [f"{COLUMNS[0]}__std_{WINDOWS[1]}"]


@pytest.fixture()
def parts(tidy, build):
    feats = build(tidy)
    ref = feats[feats["experiment_id"] == "anomaly-free/anomaly-free"]
    other = feats[feats["experiment_id"] == "valve1/0"]
    return feats, ref, other


def _fit(features_module, frame, columns=COLS):
    try:
        return features_module.ReferenceStats.fit(frame, columns=columns)
    except NotImplementedError:
        pytest.fail("ReferenceStats.fit is not implemented yet", pytrace=False)


def test_transform_uses_fitted_statistics(features_module, parts):
    _, ref, other = parts
    z = _fit(features_module, ref).transform(other)
    for c in COLS:
        expected = (other[c] - ref[c].mean()) / ref[c].std()
        np.testing.assert_allclose(z[c].to_numpy(), expected.to_numpy(), rtol=1e-9, equal_nan=True, err_msg=c)


def test_statistics_do_not_depend_on_the_data_being_transformed(features_module, parts):
    """The same row must get the same z-score whether it is transformed alone or inside a larger frame."""
    feats, ref, other = parts
    stats = _fit(features_module, ref)
    together = stats.transform(feats).loc[other.index, COLS].to_numpy()
    alone = stats.transform(other)[COLS].to_numpy()
    np.testing.assert_allclose(together, alone, rtol=1e-9, equal_nan=True)
    shifted = other.copy()
    shifted[COLS] = shifted[COLS] + 5.0
    moved = stats.transform(shifted)[COLS].to_numpy() - alone
    assert np.nanmin(np.abs(moved)) > 0, "shifting the input did not shift the z-scores: transform re-centres on its input"


def test_reference_rows_are_standardised_and_others_are_not(features_module, parts):
    _, ref, other = parts
    stats = _fit(features_module, ref)
    z_ref = stats.transform(ref)[COLS]
    np.testing.assert_allclose(z_ref.mean().to_numpy(), 0.0, atol=1e-9)
    np.testing.assert_allclose(z_ref.std().to_numpy(), 1.0, rtol=1e-9)
    assert np.abs(stats.transform(other)[COLS].mean().to_numpy()).max() > 0.05


def test_non_feature_columns_and_input_untouched(features_module, parts):
    _, ref, other = parts
    snapshot = other.copy(deep=True)
    z = _fit(features_module, ref).transform(other)
    assert z["t"].tolist() == other["t"].tolist() and z["experiment_id"].tolist() == other["experiment_id"].tolist()
    assert other.equals(snapshot), "transform modified its input in place"


def test_round_trip_through_plain_dict(features_module, parts):
    import json
    _, ref, other = parts
    stats = _fit(features_module, ref)
    restored = features_module.ReferenceStats.from_dict(json.loads(json.dumps(stats.to_dict())))
    np.testing.assert_allclose(restored.transform(other)[COLS].to_numpy(), stats.transform(other)[COLS].to_numpy(),
                               rtol=1e-12, equal_nan=True)


def test_fit_on_no_rows_is_an_error(features_module, parts):
    _, ref, _ = parts
    with pytest.raises(ValueError):
        features_module.ReferenceStats.fit(ref.iloc[0:0], columns=COLS)
