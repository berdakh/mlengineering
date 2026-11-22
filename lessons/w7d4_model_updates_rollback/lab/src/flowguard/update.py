"""Replacing a model safely: offline gate, shadow scoring, promotion and rollback with an audit log.

YOU IMPLEMENT THIS MODULE in lesson w7d4 (section 4). The contract, in short:

* ``offline_gate(current, candidate, *, policy="superiority", margin=0.05,
  max_false_alarms_per_hour=None, slices=None, slice_margin=0.0, n_boot=2000, seed=0, level=0.95)``
  -> dict with at least ``decision`` ("promote" / "reject"), ``diff`` (paired bootstrap result),
  ``checks`` (``superior``, ``non_inferior``, ``guardrail``, ``slices``), ``reasons`` (list of str).
* ``ShadowRunner(current, candidate, log=None).score(run_id, run)`` -> the CURRENT model's response,
  exactly ``flowguard.serving.respond(current, run)``; appends a record with both outcomes to ``log``.
* ``disagreements(log)`` -> dict with ``runs``, ``runs_differ``, ``only_current``, ``only_candidate``,
  ``candidate_errors``.
* ``promote(root, name, version, *, serving_columns, actor="", reason="")``
* ``rollback(root, name, *, serving_columns, actor="", reason="")`` -> the version now current.
* ``audit_log(root, name)`` -> list of entries (dicts with ``action``, ``from``, ``to``, ``ts``,
  ``actor``, ``reason``), oldest first, read from ``<root>/<name>/audit.jsonl``.

Use ``flowguard.registry.write_pointer`` (atomic) to move the pointer, and
``flowguard.uncertainty.paired_bootstrap_diff`` for the gate.
"""
from __future__ import annotations

AUDIT_FILE = "audit.jsonl"
POLICIES = ("superiority", "non_inferiority")


def pooled_recall(results) -> float:
    """Sum of n_detected / sum of n_events over the given per-experiment results (NaN if no events)."""
    raise NotImplementedError("task 1")


def pooled_far(results) -> float:
    """Sum of n_false_alarms / sum of normal_hours (NaN if no hours)."""
    raise NotImplementedError("task 1")


def offline_gate(current: dict, candidate: dict, *, policy: str = "superiority", margin: float = 0.05,
                 max_false_alarms_per_hour: float | None = None, slices: dict | None = None,
                 slice_margin: float = 0.0, n_boot: int = 2000, seed: int = 0, level: float = 0.95) -> dict:
    raise NotImplementedError("task 2")


class ShadowRunner:
    def __init__(self, current, candidate, log: list | None = None):
        raise NotImplementedError("task 3")

    def score(self, run_id: str, run) -> dict:
        raise NotImplementedError("task 3")


def disagreements(log: list) -> dict:
    raise NotImplementedError("task 3")


def audit_log(root, name) -> list[dict]:
    raise NotImplementedError("task 4")


def promote(root, name, version: str, *, serving_columns, actor: str = "", reason: str = "") -> None:
    raise NotImplementedError("task 4")


def rollback(root, name, *, serving_columns, actor: str = "", reason: str = "") -> str:
    raise NotImplementedError("task 5")
