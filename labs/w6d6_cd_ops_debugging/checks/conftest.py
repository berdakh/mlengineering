"""Fixtures for the w6d6 lab checks. Grades <target>/ops/rollback.py, <target>/service/src/flowguard/
settings.py and <target>/DEBUG_LOG.md. No Docker is needed; the optional live test runs only with
WB_DOCKER=1 (it builds images, starts containers on 127.0.0.1 and removes them afterwards).
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

UNIT = "labs/w6d6_cd_ops_debugging"


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "lab")


def _load(path: Path, name: str):
    assert path.is_file(), f"missing {path}"
    spec = importlib.util.spec_from_file_location(f"{name}_{abs(hash(str(path)))}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import {path}: {exc!r}", pytrace=False)
    return mod


@pytest.fixture(scope="session")
def rb(target):
    return _load(target / "ops" / "rollback.py", "rollback")


@pytest.fixture(scope="session")
def settings_mod(target):
    return _load(target / "service" / "src" / "flowguard" / "settings.py", "settings")


IMAGE = "127.0.0.1:5005/flowguard"


def entry(env, release, digest_char, at, status="good"):
    return {"env": env, "release": release, "image": IMAGE, "digest": "sha256:" + digest_char * 64,
            "deployed_at": f"2026-11-22T10:{at:02d}:00.000+00:00", "status": status, "note": ""}
