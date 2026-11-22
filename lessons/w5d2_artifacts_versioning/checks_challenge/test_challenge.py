"""w5d2 challenge: the logistic candidate as a trustworthy bundle. SYNTHETIC runs."""
from __future__ import annotations

import json
import pickle
import re

import numpy as np
import pytest

from conftest import METADATA, make_run, rewrite_checksums


def trained_scores(model, run):
    return model.calibrate(run.iloc[: model.n_burn]).score(run.iloc[model.n_burn:])


@pytest.fixture()
def bundle(mods, trained, tmp_path):
    return mods.lb.save_logistic(trained, tmp_path / "bundle", METADATA, version="0.1.0")


@pytest.mark.parametrize("seed, fault, size", [(100, None, 0.0), (101, 7, 5.0), (102, 2, -6.0), (103, 4, 500.0)])
def test_loaded_model_scores_like_the_trained_one(mods, trained, bundle, seed, fault, size):
    run = make_run("x", seed, fault=fault, size=size)
    loaded = mods.lb.load_logistic(bundle)
    np.testing.assert_allclose(loaded.score_run(run), trained_scores(trained, run), rtol=1e-12, atol=1e-12)


def test_nothing_is_pickled(mods, trained, tmp_path, monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("pickle was used")

    for name in ("dump", "dumps", "load", "loads"):
        monkeypatch.setattr(pickle, name, refuse)
    bundle = mods.lb.save_logistic(trained, tmp_path / "b", METADATA, version="0.1.0")
    mods.lb.load_logistic(bundle).score_run(make_run("x", 1))
    for path in bundle.rglob("*"):
        assert path.suffix not in (".pkl", ".pickle", ".joblib"), path.name
        assert not path.read_bytes().startswith(b"\x80"), f"{path.name} starts like a pickle stream"


def test_bundle_registers_and_loads_from_the_registry(mods, trained, bundle, tmp_path):
    mods.artifacts.verify_bundle(bundle)
    root = tmp_path / "registry"
    dest = mods.artifacts.register(root, bundle)
    mods.artifacts.promote(root, "flowguard-logistic", "0.1.0")
    resolved = mods.artifacts.resolve(root, "flowguard-logistic")
    assert resolved == dest
    run = make_run("x", 7, fault=7, size=5.0)
    np.testing.assert_allclose(mods.lb.load_logistic(resolved).score_run(run), trained_scores(trained, run),
                               rtol=1e-12, atol=1e-12)


def test_a_modified_bundle_is_refused(mods, bundle):
    victim = next(p for p in sorted(bundle.iterdir()) if p.name not in ("checksums.json", "card.json"))
    data = bytearray(victim.read_bytes())
    data[len(data) // 2] ^= 0x01                         # one flipped bit in a file that defines the function
    victim.write_bytes(bytes(data))
    with pytest.raises(ValueError):
        mods.lb.load_logistic(bundle)


def test_an_unimplemented_feature_layout_is_refused(mods, bundle):
    path = bundle / "model.json"
    spec = json.loads(path.read_text())
    layout = next((k for k, v in spec.items() if isinstance(v, list) and len(v) == 16), None)
    assert layout is not None, "model.json should record the 16-feature layout by name"
    spec[layout] = spec[layout][8:] + spec[layout][:8]     # |z| block first: same shape, different meaning
    path.write_text(json.dumps(spec, indent=2))
    rewrite_checksums(bundle)
    with pytest.raises(ValueError, match="(?i)feature"):
        mods.lb.load_logistic(bundle)


def test_a_newer_format_version_is_refused(mods, bundle):
    path = bundle / "model.json"
    spec = json.loads(path.read_text())
    spec["format_version"] = 2
    path.write_text(json.dumps(spec, indent=2))
    rewrite_checksums(bundle)
    with pytest.raises(ValueError):
        mods.lb.load_logistic(bundle)


def test_compatibility_policy_is_written(target):
    path = target / "COMPATIBILITY.md"
    assert path.is_file(), "missing COMPATIBILITY.md"
    text = path.read_text()
    assert "TODO" not in text, "COMPATIBILITY.md still contains TODO"
    assert len(text.split()) >= 150, "the policy is too short to cover format, refusals and versioning"
    assert re.search(r"(?i)scikit-learn|sklearn", text), "say what the policy means for scikit-learn versions"
