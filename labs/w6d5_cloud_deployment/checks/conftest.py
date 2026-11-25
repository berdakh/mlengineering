"""Fixtures for the w6d5 lab checks. Grades <target>/deploy/aws_deploy.py, the task-definition template
and the files in <target>. Nothing here contacts AWS or runs Docker: the live path is exercised only with
a fake executor that records the script it would have run.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w6d5_cloud_deployment"
ACCOUNT = "000011112222"          # obviously fake; only ever written to pytest's tmp dirs
RELEASE = "1a2b3c4d5e6f"

CONFIG = """\
[aws]
region = "eu-central-1"
account_id = "{account}"
profile = "flowguard-sso"
[app]
name = "{name}"
release = "{release}"
container_port = 8000
cpu = "256"
memory = "512"
[network]
vpc_id = "vpc-0abc123"
subnet_id = "subnet-0def456"
allowed_cidr = "{cidr}"
allow_public = {public}
[budget]
limit_usd = 10
notify_email = "learner@example.org"
"""


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "lab")


@pytest.fixture(scope="session")
def dep(target):
    path = target / "deploy" / "aws_deploy.py"
    assert path.is_file(), f"missing {path}"
    spec = importlib.util.spec_from_file_location(f"aws_deploy_{abs(hash(str(path)))}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import {path}: {exc!r}", pytrace=False)
    return mod


@pytest.fixture()
def write_config(tmp_path):
    def _write(name="flowguard", account=ACCOUNT, release=RELEASE, cidr="", public="false") -> Path:
        p = tmp_path / f"config-{name}-{abs(hash((account, release, cidr, public)))}.toml"
        p.write_text(CONFIG.format(name=name, account=account, release=release, cidr=cidr, public=public))
        return p
    return _write


SIGNED = """\
# Sign-off
## Required
- [x] read the briefing
- [x] short-lived credentials
## Public access (only needed when network.allow_public = true)
- [{p}] reachable from more than my IP
- [{p}] tear down the same day
"""


@pytest.fixture()
def signoff(tmp_path):
    def _write(required=True, public=False) -> Path:
        text = SIGNED.format(p="x" if public else " ")
        if not required:
            text = text.replace("- [x] short-lived credentials", "- [ ] short-lived credentials")
        p = tmp_path / f"SIGNOFF-{required}-{public}.md"
        p.write_text(text)
        return p
    return _write


def commands(script: str) -> list[str]:
    """Executable lines of a bash script: no blanks, no comments."""
    return [ln.strip() for ln in script.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def first_index(cmds: list[str], needle: str) -> int:
    for i, c in enumerate(cmds):
        if needle in c:
            return i
    raise AssertionError(f"no command containing {needle!r} in:\n" + "\n".join(cmds))
