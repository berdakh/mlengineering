"""OPTIONAL live test: build the image, run it on loopback, ask it for scores, stop it.

Skipped unless WB_DOCKER=1 and a Docker daemon answers. Takes 30-90 s on the first build.
Extra build options (e.g. a proxy CA base image) can be passed in WB_DOCKER_BUILD_ARGS.
Everything it creates (one image, one container) is removed at the end, pass or fail.
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import socket
import subprocess
import time
import urllib.request
import uuid

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("WB_DOCKER") != "1", reason="live Docker test: set WB_DOCKER=1")


def _docker(*args, check=True, timeout=600):
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=check, timeout=timeout)


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_live_build_run_predict_stop(target):
    if shutil.which("docker") is None or _docker("info", check=False, timeout=30).returncode != 0:
        pytest.skip("no Docker daemon")
    tag = f"wb-w6d1-live:{uuid.uuid4().hex[:8]}"
    name = f"wb-w6d1-{uuid.uuid4().hex[:8]}"
    port = _free_port()
    extra = shlex.split(os.environ.get("WB_DOCKER_BUILD_ARGS", ""))
    try:
        _docker("build", *extra, "-t", tag, str(target))
        _docker("run", "-d", "--name", name, "-p", f"127.0.0.1:{port}:8000", tag)
        deadline, ready = time.monotonic() + 60, False
        while time.monotonic() < deadline and not ready:
            try:
                ready = urllib.request.urlopen(f"http://127.0.0.1:{port}/readyz", timeout=2).status == 200
            except OSError:
                time.sleep(0.5)
        assert ready, "the container never answered /readyz with 200: " + _docker("logs", name, check=False).stderr[-800:]
        body = (target / "smoke" / "request.json").read_bytes()
        req = urllib.request.Request(f"http://127.0.0.1:{port}/predict", data=body,
                                     headers={"Content-Type": "application/json"})
        got = json.load(urllib.request.urlopen(req, timeout=30))
        want = json.loads((target / "smoke" / "expected.json").read_text())
        assert got["model_version"] == want["model_version"]
        assert [r["score"] for r in got["results"]] == want["scores"]
        uid = _docker("exec", name, "id", "-u").stdout.strip()
        assert uid != "0", "the server runs as root inside the container"
        started = time.monotonic()
        _docker("stop", name, timeout=60)
        took = time.monotonic() - started
        assert took < 5, f"`docker stop` took {took:.1f} s: SIGTERM did not reach the server (shell-form CMD?)"
        state = _docker("inspect", "--format", "{{.State.ExitCode}}", name).stdout.strip()
        assert state == "0", f"exit code {state} after docker stop (137 means it had to be killed)"
    finally:
        _docker("rm", "-f", name, check=False)
        _docker("image", "rm", "-f", tag, check=False)
