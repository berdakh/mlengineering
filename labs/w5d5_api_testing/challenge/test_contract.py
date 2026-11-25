"""Your contract tests. Run from the repository root:

    python -m pytest labs/w5d5_api_testing/challenge/test_contract.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apps import v1, v2  # noqa: E402
from compat import breaking_changes  # noqa: E402


def test_v1_is_compatible_with_itself():
    schema = v1.create_app().openapi()
    assert breaking_changes(schema, schema) == []


# TODO: a test that would block the release of apps/v2.py, and asserts the specific changes found.
