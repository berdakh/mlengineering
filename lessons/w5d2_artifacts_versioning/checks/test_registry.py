"""register / promote / resolve / list_versions. SYNTHETIC bundles in a temporary registry."""
from __future__ import annotations

import os

import pytest

from conftest import METADATA, make_detector


def saved(fg, tmp_path, version, threshold=4.0):
    return fg.artifacts.save_bundle(make_detector(fg, version, threshold), tmp_path / f"b-{version}", METADATA)


def snapshot(path):
    return {p.name: p.read_bytes() for p in path.iterdir()}


def test_register_creates_an_immutable_version(fg, tmp_path):
    root = tmp_path / "registry"
    dest = fg.artifacts.register(root, saved(fg, tmp_path, "1.0.0"))
    assert dest == root / "flowguard-test" / "1.0.0"
    fg.artifacts.verify_bundle(dest)
    before = snapshot(dest)
    other = fg.artifacts.save_bundle(make_detector(fg, "1.0.0", 9.0), tmp_path / "again", METADATA)
    with pytest.raises(fg.artifacts.RegistryError):
        fg.artifacts.register(root, other)
    assert snapshot(dest) == before, "the registered version was modified"


@pytest.mark.parametrize("version", ["1.0", "latest", "v1.0.0", "1.0.0-rc1"])
def test_register_refuses_versions_that_are_not_semver(fg, tmp_path, version):
    with pytest.raises(fg.artifacts.RegistryError):
        fg.artifacts.register(tmp_path / "registry", saved(fg, tmp_path, version))


def test_register_refuses_a_tampered_bundle(fg, tmp_path):
    bundle = saved(fg, tmp_path, "1.0.0")
    (bundle / "card.json").write_text("{}")
    with pytest.raises(fg.artifacts.BundleIntegrityError):
        fg.artifacts.register(tmp_path / "registry", bundle)
    assert not (tmp_path / "registry" / "flowguard-test" / "1.0.0").exists()


def test_promote_resolve_and_roll_back(fg, tmp_path):
    root = tmp_path / "registry"
    for v in ("1.0.0", "1.1.0"):
        fg.artifacts.register(root, saved(fg, tmp_path, v))
    with pytest.raises(fg.artifacts.RegistryError):
        fg.artifacts.resolve(root, "flowguard-test")                 # nothing promoted yet
    fg.artifacts.promote(root, "flowguard-test", "1.1.0")
    assert fg.artifacts.resolve(root, "flowguard-test") == root / "flowguard-test" / "1.1.0"
    fg.artifacts.promote(root, "flowguard-test", "1.0.0")              # rollback is a promote
    assert fg.artifacts.resolve(root, "flowguard-test", "current") == root / "flowguard-test" / "1.0.0"
    assert fg.artifacts.resolve(root, "flowguard-test", "1.1.0") == root / "flowguard-test" / "1.1.0"
    detector, _, _ = fg.artifacts.load_bundle(fg.artifacts.resolve(root, "flowguard-test"))
    assert detector.version == "1.0.0"


def test_promote_and_resolve_refuse_unknown_versions(fg, tmp_path):
    root = tmp_path / "registry"
    fg.artifacts.register(root, saved(fg, tmp_path, "1.0.0"))
    with pytest.raises(fg.artifacts.RegistryError):
        fg.artifacts.promote(root, "flowguard-test", "2.0.0")
    with pytest.raises(fg.artifacts.RegistryError):
        fg.artifacts.resolve(root, "flowguard-test", "2.0.0")


def test_promote_refuses_a_version_tampered_after_registration(fg, tmp_path):
    root = tmp_path / "registry"
    dest = fg.artifacts.register(root, saved(fg, tmp_path, "1.0.0"))
    (dest / "model.json").write_text((dest / "model.json").read_text().replace("4.0", "0.5"))
    with pytest.raises(fg.artifacts.BundleIntegrityError):
        fg.artifacts.promote(root, "flowguard-test", "1.0.0")


def test_promote_moves_the_pointer_atomically(fg, tmp_path, monkeypatch):
    root = tmp_path / "registry"
    fg.artifacts.register(root, saved(fg, tmp_path, "1.0.0"))
    moved = []
    real_replace = os.replace

    def recording_replace(src, dst, *a, **k):
        moved.append(os.path.basename(os.fspath(dst)))
        return real_replace(src, dst, *a, **k)

    monkeypatch.setattr(os, "replace", recording_replace)
    fg.artifacts.promote(root, "flowguard-test", "1.0.0")
    assert "current" in moved, "write the pointer to a temporary file and os.replace it onto 'current'"
    assert (root / "flowguard-test" / "current").read_text().strip() == "1.0.0"


def test_versions_are_listed_in_semantic_order(fg, tmp_path):
    root = tmp_path / "registry"
    for v in ("1.10.0", "1.9.0", "1.9.10", "0.1.0", "1.9.2"):
        fg.artifacts.register(root, saved(fg, tmp_path, v))
    assert fg.artifacts.list_versions(root, "flowguard-test") == ["0.1.0", "1.9.0", "1.9.2", "1.9.10", "1.10.0"]
