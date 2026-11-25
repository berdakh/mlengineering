"""Detect breaking changes between two OpenAPI documents. Implement breaking_changes().

Specification: challenge/README.md, "What counts as breaking".
"""
from __future__ import annotations


def breaking_changes(old: dict, new: dict) -> list[str]:
    """Return one human-readable message per breaking change from ``old`` to ``new``.

    Each message must contain the HTTP method and path it concerns, e.g. "POST /predict: ...".
    An empty list means: a client written against ``old`` keeps working against ``new``.
    """
    raise NotImplementedError
