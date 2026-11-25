"""Optional live test (WB_DOCKER=1): build, deploy, break with scenario 2, roll back, clean up.

Uses Docker on this machine, ports 5005, 8101 and 8102 on 127.0.0.1 only, and takes 1-3 minutes.
Behind a TLS-intercepting proxy set PIP_INSTALL_OPTS and fill service/wheels/ first (see the lesson).
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("WB_DOCKER") != "1", reason="set WB_DOCKER=1 to run the Docker test")


def test_bad_promotion_is_recovered_by_rollback(target, tmp_path):
    lab = tmp_path / "lab"
    shutil.copytree(target, lab, ignore=shutil.ignore_patterns("__pycache__", "state"))
    sys.path.insert(0, str(lab / "ops"))
    spec = importlib.util.spec_from_file_location("fgops_live", lab / "ops" / "fgops.py")
    fg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fg)
    spec = importlib.util.spec_from_file_location("rollback_live", lab / "ops" / "rollback.py")
    rb = importlib.util.module_from_spec(spec)
    sys.modules["fgops"] = fg
    spec.loader.exec_module(rb)
    try:
        fg.registry_up()
        fg.build("a1b2c3d4e5f6", quiet=True)
        assert fg.deploy("staging", "a1b2c3d4e5f6", quiet=True)["status"] == "good"
        assert fg.promote("staging", "production")["status"] == "good"
        fg.scenario(2)
        assert fg.current("production")["status"] == "failed"
        assert rb.main(["production", "--apply"]) == 0
        assert fg.http_status(fg.runtime()["production"]["port"], "/readyz") == 200
    finally:
        fg.cleanup()
