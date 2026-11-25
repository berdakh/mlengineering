"""save_bundle / verify_bundle / load_bundle. SYNTHETIC models; behaviour from the module docstring."""
from __future__ import annotations

import json
import pickle

import numpy as np
import pytest

from conftest import METADATA, make_detector, reference_arrays, rewrite_checksums, serving_batch


def test_round_trip_gives_the_same_function(fg, bundle):
    detector, card, reference = fg.artifacts.load_bundle(bundle)
    original = make_detector(fg)
    assert detector.to_config() == original.to_config()
    batch = serving_batch()
    a, _ = original.score_batch(batch)
    b, _ = detector.score_batch(batch)
    np.testing.assert_array_equal(a["score"].to_numpy(), b["score"].to_numpy())
    np.testing.assert_array_equal(a["alarm"].to_numpy(), b["alarm"].to_numpy())
    for name, array in reference_arrays().items():
        np.testing.assert_array_equal(reference[name], array)


def test_bundle_holds_exactly_the_documented_files(fg, bundle):
    assert sorted(p.name for p in bundle.iterdir()) == ["card.json", "checksums.json", "model.json", "reference.npz"]
    model = json.loads((bundle / "model.json").read_text())
    assert model["format"] == "flowguard-bundle" and model["format_version"] == fg.artifacts.FORMAT_VERSION


def test_model_card_is_complete(fg, bundle):
    _, card, _ = fg.artifacts.load_bundle(bundle)
    assert card["name"] == "flowguard-test" and card["version"] == "1.0.0"
    for field in fg.artifacts.REQUIRED_CARD_FIELDS:
        assert card[field], f"card field {field!r} is empty"
    for package in ("python", "numpy"):
        assert card["created_with"][package], f"card does not record the {package} version"


@pytest.mark.parametrize("field", ["intended_use", "limitations", "evaluation"])
def test_save_refuses_an_incomplete_card(fg, tmp_path, field):
    metadata = {k: v for k, v in METADATA.items() if k != field}
    with pytest.raises(ValueError, match=field):
        fg.artifacts.save_bundle(make_detector(fg), tmp_path / "b", metadata)


def test_save_refuses_a_non_empty_directory(fg, bundle):
    with pytest.raises(FileExistsError):
        fg.artifacts.save_bundle(make_detector(fg, version="1.0.1"), bundle, METADATA)


def test_save_refuses_object_arrays(fg, tmp_path):
    with pytest.raises(ValueError):
        fg.artifacts.save_bundle(make_detector(fg), tmp_path / "b", METADATA,
                                 {"bad": np.array([{"a": 1}, None], dtype=object)})


def test_nothing_is_pickled(fg, tmp_path, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("pickle was used")

    for name in ("dump", "dumps", "load", "loads"):
        monkeypatch.setattr(pickle, name, refuse)
    bundle = fg.artifacts.save_bundle(make_detector(fg), tmp_path / "b", METADATA, reference_arrays())
    fg.artifacts.load_bundle(bundle)
    for path in bundle.rglob("*"):
        assert path.suffix not in (".pkl", ".pickle", ".joblib"), path.name
        assert not path.read_bytes().startswith(b"\x80"), f"{path.name} starts like a pickle stream"


def test_tampered_file_is_refused_and_named(fg, bundle):
    path = bundle / "model.json"
    path.write_text(path.read_text().replace('"threshold": 4.0', '"threshold": 40.0'))
    with pytest.raises(fg.artifacts.BundleIntegrityError, match="model.json"):
        fg.artifacts.load_bundle(bundle)


def test_missing_file_is_refused(fg, bundle):
    (bundle / "card.json").unlink()
    with pytest.raises(fg.artifacts.BundleIntegrityError, match="card.json"):
        fg.artifacts.load_bundle(bundle)


def test_unlisted_file_is_refused(fg, bundle):
    (bundle / "model.pkl").write_bytes(b"\x80\x05N.")          # someone "helpfully" added a pickle
    with pytest.raises(fg.artifacts.BundleIntegrityError, match="model.pkl"):
        fg.artifacts.load_bundle(bundle)


def test_integrity_errors_are_value_errors(fg):
    assert issubclass(fg.artifacts.BundleIntegrityError, ValueError)
    assert issubclass(fg.artifacts.BundleCompatibilityError, ValueError)


def test_newer_format_version_is_refused_with_both_versions(fg, bundle):
    path = bundle / "model.json"
    model = json.loads(path.read_text())
    model["format_version"] = 2
    path.write_text(json.dumps(model))
    rewrite_checksums(bundle)                                    # integrity now passes; format must not
    with pytest.raises(fg.artifacts.BundleCompatibilityError) as info:
        fg.artifacts.load_bundle(bundle)
    assert "2" in str(info.value) and str(fg.artifacts.FORMAT_VERSION) in str(info.value)


def test_pickled_array_is_not_loaded(fg, bundle):
    """A bundle whose checksums agree but whose npz holds a pickled object array must not be loaded."""
    with open(bundle / "reference.npz", "wb") as fh:
        np.savez(fh, sneaky=np.array([{"payload": 1}], dtype=object))
    rewrite_checksums(bundle)
    with pytest.raises(ValueError):
        fg.artifacts.load_bundle(bundle)
