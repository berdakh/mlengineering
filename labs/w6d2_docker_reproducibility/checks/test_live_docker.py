"""OPTIONAL live test: build the multi-stage image, run it on loopback, run YOUR smoke test against it.

Skipped unless WB_DOCKER=1 and a Docker daemon answers. Extra build options can be passed in
WB_DOCKER_BUILD_ARGS (e.g. --build-arg PYTHON_BASE=... behind a TLS-intercepting proxy).
The image and container are removed at the end, pass or fail.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import uuid

import pytest

import servers

pytestmark = pytest.mark.skipif(os.environ.get("WB_DOCKER") != "1", reason="live Docker test: set WB_DOCKER=1")


def _docker(*args, check=True, timeout=900):
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=check, timeout=timeout)


def test_live_multistage_image_passes_the_smoke_test(target):
    if shutil.which("docker") is None or _docker("info", check=False, timeout=30).returncode != 0:
        pytest.skip("no Docker daemon")
    tag, name, port = f"wb-w6d2-live:{uuid.uuid4().hex[:8]}", f"wb-w6d2-{uuid.uuid4().hex[:8]}", servers.free_port()
    extra = shlex.split(os.environ.get("WB_DOCKER_BUILD_ARGS", ""))
    try:
        _docker("build", *extra, "--build-arg", "REVISION=wb-live-test", "-t", tag, str(target))
        labels = _docker("image", "inspect", "--format", "{{json .Config.Labels}}", tag).stdout
        assert "wb-live-test" in labels, f"the revision build argument did not reach the labels: {labels}"
        _docker("run", "-d", "--name", name, "-p", f"127.0.0.1:{port}:8000", tag)
        proc = subprocess.run([sys.executable, str(target / "scripts" / "smoke_test.py"),
                               "--base-url", f"http://127.0.0.1:{port}", "--timeout", "60"],
                              capture_output=True, text=True, timeout=120)
        assert proc.returncode == 0, proc.stdout + proc.stderr + _docker("logs", name, check=False).stderr[-800:]
        assert _docker("exec", name, "id", "-u").stdout.strip() != "0"
    finally:
        _docker("rm", "-f", name, check=False)
        _docker("image", "rm", "-f", tag, check=False)
