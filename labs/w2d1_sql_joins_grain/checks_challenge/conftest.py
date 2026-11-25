"""Fixtures for the w2d1 challenge checks (shares the harness and oracle with checks/)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "checks"))
import w2d1_harness as H  # noqa: E402
import w2d1_oracle as O  # noqa: E402


@pytest.fixture(scope="session")
def target() -> Path:
    return H.resolve_target(H.UNIT, "challenge")


@pytest.fixture(scope="session")
def databases(tmp_path_factory) -> dict[str, Path]:
    reseeded = tmp_path_factory.mktemp("w2d1c") / "reseeded.db"
    H.load_make_db().build(reseeded, seed=H.RESEED)
    return {"committed": H.COMMITTED_DB, "reseeded": reseeded}


@pytest.fixture(scope="session")
def tables(databases) -> dict[str, dict]:
    return {name: O.load_tables(path) for name, path in databases.items()}
