import json

import pytest

from flowguard import __version__
from flowguard.bundle import BundleError, load_bundle, read_manifest


def test_round_trip(bundle_dir, model):
    assert load_bundle(bundle_dir) == model
    manifest = read_manifest(bundle_dir)
    assert manifest["package_version"] == __version__
    assert manifest["provenance"]["splits_sha256"]


def test_edited_bundle_refused(bundle_dir):
    params = json.loads((bundle_dir / "model.json").read_text())
    params["threshold"] = 1.0
    (bundle_dir / "model.json").write_text(json.dumps(params))
    with pytest.raises(BundleError):
        load_bundle(bundle_dir)
