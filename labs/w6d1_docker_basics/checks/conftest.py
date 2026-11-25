"""Fixtures for the w6d1 lab checks. Static: they read the Dockerfile, .dockerignore and
run_container.sh of the graded directory and never need a Docker daemon (see test_live_docker.py
for the optional live build). No network; no downloaded data."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from tools.wbcheck import resolve_target  # noqa: E402

import w6d1_dockerlint as dl  # noqa: E402

UNIT = "labs/w6d1_docker_basics"


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
        pytest.fail("the Dockerfile has no FROM instruction yet", pytrace=False)
    return parsed


@pytest.fixture(scope="session")
def final(dockerfile) -> dl.Stage:
    return dockerfile.final


@pytest.fixture(scope="session")
def ignore(target) -> dl.DockerIgnore:
    return dl.DockerIgnore.from_file(target / ".dockerignore")
