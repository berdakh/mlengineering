"""w6d2 challenge: the drifted build, fixed with a hash-checked lock.

The checks install the learner's lock into a temporary directory from the LOCAL wheelhouse
(`pip install --no-index --find-links wheelhouse --require-hashes --target ...`), run the service, and
compare the scores with the expected ones recorded two weeks ago.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys

import pytest


@pytest.fixture(scope="module")
def lock_text(target):
    path = target / "service" / "requirements.lock"
    if not path.is_file():
        pytest.fail("missing service/requirements.lock", pytrace=False)
    return path.read_text()


def _requirement_lines(text):
    logical = re.sub(r"\\\s*\n", " ", text)
    return [ln.split(" #")[0].strip() for ln in logical.splitlines()
            if ln.strip() and not ln.strip().startswith("#") and not ln.strip().startswith("-")]


def test_lock_pins_the_validated_version_exactly(lock_text):
    lines = [ln for ln in _requirement_lines(lock_text) if ln.lower().startswith("zscorelib")]
    assert len(lines) == 1, "the lock must contain exactly one zscorelib requirement"
    spec = re.split(r"\s--", lines[0])[0].replace(" ", "")
    assert re.fullmatch(r"zscorelib==\d+(\.\d+)*", spec, flags=re.I), f"{spec!r} is not an exact == pin"
    assert spec.lower() == "zscorelib==1.0.0", (
        f"{spec}: the expected scores were recorded with the version current two weeks ago; the lock "
        "must pin the version that was validated, not the newest one")


def test_lock_hash_is_the_hash_of_that_wheel(lock_text, target):
    wheel = target / "wheelhouse" / "zscorelib-1.0.0-py3-none-any.whl"
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    hashes = re.findall(r"--hash=sha256:([0-9a-f]{64})", lock_text)
    assert hashes, "no --hash=sha256:... in the lock"
    assert digest in hashes, "none of the hashes in the lock is the sha256 of zscorelib-1.0.0-py3-none-any.whl"


def test_installing_the_lock_reproduces_the_recorded_scores(target, tmp_path):
    site = tmp_path / "site"
    env = dict(os.environ, PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_ROOT_USER_ACTION="ignore")
    proc = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--no-index", "--find-links",
                           str(target / "wheelhouse"), "--require-hashes", "--target", str(site),
                           "-r", str(target / "service" / "requirements.lock")],
                          capture_output=True, text=True, env=env, timeout=120)
    assert proc.returncode == 0, f"pip refused the lock in hash-checking mode:\n{proc.stderr[-800:]}"
    run = subprocess.run([sys.executable, str(target / "service" / "driftsvc.py"), str(target / "expected" / "input.json")],
                         capture_output=True, text=True, env=dict(env, PYTHONPATH=str(site)), timeout=60)
    assert run.returncode == 0, run.stderr
    got = json.loads(run.stdout)
    want = json.loads((target / "expected" / "scores.json").read_text())
    same = len(got["scores"]) == len(want["scores"]) and all(
        (g is None and w is None) or (g is not None and w is not None and math.isclose(g, w, rel_tol=1e-12))
        for g, w in zip(got["scores"], want["scores"]))
    assert same, f"installed zscorelib {got['zscorelib']}: the scores differ from the recorded ones"


def test_build_script_installs_the_lock_with_hash_checking(target):
    text = (target / "build.sh").read_text()
    installs = [ln for ln in re.sub(r"\\\s*\n", " ", text).splitlines() if re.search(r"pip\s+install", ln)]
    assert installs, "build.sh no longer installs anything"
    for line in installs:
        assert "requirements.lock" in line and "requirements.in" not in line, \
            "build.sh must install service/requirements.lock, not resolve requirements.in"
        assert "--require-hashes" in line, "build.sh must install with --require-hashes"


@pytest.mark.parametrize("section", ["What changed", "Why the build drifted", "Fix", "Prevention"])
def test_drift_report_section(target, section):
    path = target / "DRIFT_REPORT.md"
    assert path.is_file(), "missing DRIFT_REPORT.md"
    match = re.search(rf"^## {re.escape(section)}\s*$(.*?)(?=^## |\Z)", path.read_text(), flags=re.M | re.S)
    assert match, f"no '## {section}' section"
    assert len(re.findall(r"\w+", match.group(1))) >= 40, f"section '{section}' has fewer than 40 words"
