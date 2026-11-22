"""Fixtures for the w6d2 lab checks. No Docker daemon and no network are needed: the Dockerfile and
lockfile are read statically, and your smoke test is run against real uvicorn servers that these
fixtures start in-process on 127.0.0.1 (see servers.py). test_live_docker.py is optional."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from tools.wbcheck import resolve_target  # noqa: E402

import w6d2_dockerlint as dl  # noqa: E402

UNIT = "lessons/w6d2_docker_reproducibility"


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "lab")


@pytest.fixture(scope="session")
def dockerfile(target) -> dl.Dockerfile:
    path = target / "Dockerfile"
    if not path.is_file():
        pytest.fail(f"no Dockerfile in {target}", pytrace=False)
    parsed = dl.load_dockerfile(path)
    if not parsed.stages:
        pytest.fail("the Dockerfile has no FROM", pytrace=False)
    return parsed


@pytest.fixture(scope="session")
def ignore(target) -> dl.DockerIgnore:
    return dl.DockerIgnore.from_file(target / ".dockerignore")
