"""Contract tests: block a release whose OpenAPI schema breaks v1 clients."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apps import v1, v2  # noqa: E402
from compat import breaking_changes  # noqa: E402


@pytest.fixture(scope="module")
def schemas():
    return v1.create_app().openapi(), v2.create_app().openapi()


def test_v1_is_compatible_with_itself(schemas):
    old, _ = schemas
    assert breaking_changes(old, old) == []


def test_v2_breaks_v1_clients(schemas):
    old, new = schemas
    changes = breaking_changes(old, new)
    text = "\n".join(changes)
    assert "site_id" in text                       # newly required request field
    assert "'scores'" in text                      # response field renamed = removed
    assert "burn_in" in text and "maxItems" in text  # 3600 -> 600
    assert all(c.startswith("POST /predict") for c in changes)


def test_additions_alone_are_not_breaking(schemas):
    _, new = schemas
    assert not any("/sites" in c or "latency_ms" in c or "explain" in c for c in breaking_changes(*schemas))
    assert breaking_changes(new, new) == []
