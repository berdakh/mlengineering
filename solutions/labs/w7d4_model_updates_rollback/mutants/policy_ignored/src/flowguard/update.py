"""Replacing a model safely: offline gate, shadow scoring, promotion and rollback with an audit log.

REFERENCE SOLUTION for lesson w7d4. Contract (lesson section 4):

* ``offline_gate(current, candidate, *, policy, margin, max_false_alarms_per_hour, slices,
  slice_margin, n_boot, seed, level)`` -> decision dict
* ``ShadowRunner(current, candidate, log=None).score(run_id, run)`` -> the CURRENT model's response
* ``disagreements(log)`` -> summary dict
* ``promote(root, name, version, *, serving_columns, actor, reason)``
* ``rollback(root, name, *, serving_columns, actor, reason)`` -> the version now current
* ``audit_log(root, name)`` -> list of entries, oldest first

``current`` / ``candidate`` for the gate map experiment id -> per-experiment event counts
(``n_events``, ``n_detected``, ``n_false_alarms``, ``normal_hours``) on the SAME experiments.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

from flowguard.registry import RegistryError, current_version, list_versions, load_bundle, write_pointer
from flowguard.serving import respond
from flowguard.uncertainty import paired_bootstrap_diff

AUDIT_FILE = "audit.jsonl"
POLICIES = ("superiority", "non_inferiority")


# --------------------------------------------------------------------------- offline gate
def pooled_recall(results) -> float:
    results = list(results)
    events = sum(r["n_events"] for r in results)
    return sum(r["n_detected"] for r in results) / events if events else math.nan


def pooled_far(results) -> float:
    results = list(results)
    hours = sum(r["normal_hours"] for r in results)
    return sum(r["n_false_alarms"] for r in results) / hours if hours > 0 else math.nan


def offline_gate(current: dict, candidate: dict, *, policy: str = "superiority", margin: float = 0.05,
                 max_false_alarms_per_hour: float | None = None, slices: dict | None = None,
                 slice_margin: float = 0.0, n_boot: int = 2000, seed: int = 0, level: float = 0.95) -> dict:
    """Decide "promote" or "reject" for ``candidate`` against ``current``.

    Primary metric: pooled event recall, compared with a paired cluster bootstrap of
    ``recall(candidate) - recall(current)`` (experiments resampled together for both models).
    * ``superiority``: the interval's lower end must be > 0.
    * ``non_inferiority``: the interval's lower end must be > ``-margin``.
    Guardrail: the candidate's pooled false alarms per hour must not exceed
    ``max_false_alarms_per_hour`` (if given). Slices (experiment id -> slice name): in every slice the
    candidate's pooled recall must be >= the current model's minus ``slice_margin``.
    Promote only if the primary rule, the guardrail and every slice pass.
    """
    if policy not in POLICIES:
        raise ValueError(f"policy must be one of {POLICIES}")
    if set(current) != set(candidate):
        raise ValueError("current and candidate must be evaluated on the same experiments")
    diff = paired_bootstrap_diff(pooled_recall, candidate, current, n_boot=n_boot, seed=seed, level=level)
    checks = {"superior": bool(diff["low"] > 0), "non_inferior": bool(diff["low"] > -margin)}
    primary = checks["non_inferior"]
    far_c = pooled_far(candidate.values())
    checks["guardrail"] = bool(max_false_alarms_per_hour is None or far_c <= max_false_alarms_per_hour)
    slice_rows = {}
    for name in sorted(set((slices or {}).values())):
        ids = [e for e, s in slices.items() if s == name and e in current]
        rc, rk = pooled_recall(current[e] for e in ids), pooled_recall(candidate[e] for e in ids)
        slice_rows[name] = {"current": rc, "candidate": rk, "n_experiments": len(ids),
                            "ok": bool(math.isnan(rc) or rk >= rc - slice_margin)}
    checks["slices"] = all(r["ok"] for r in slice_rows.values())
    reasons = []
    if not primary:
        need = "> 0" if policy == "superiority" else f"> {-margin:g}"
        reasons.append(f"{policy}: lower end of the recall difference is {diff['low']:+.3f}, needs {need}")
    if not checks["guardrail"]:
        reasons.append(f"guardrail: {far_c:.2f} false alarms/hour > {max_false_alarms_per_hour}")
    for name, r in slice_rows.items():
        if not r["ok"]:
            reasons.append(f"slice {name}: recall {r['candidate']:.2f} < {r['current']:.2f} - {slice_margin}")
    decision = "promote" if primary and checks["guardrail"] and checks["slices"] else "reject"
    return {"decision": decision, "policy": policy, "margin": margin, "diff": diff, "checks": checks,
            "current": {"recall": pooled_recall(current.values()), "false_alarms_per_hour": pooled_far(current.values())},
            "candidate": {"recall": pooled_recall(candidate.values()), "false_alarms_per_hour": far_c},
            "slices": slice_rows, "reasons": reasons or ["all checks passed"]}


# --------------------------------------------------------------------------- shadow mode
class ShadowRunner:
    """Serve ``current``; score ``candidate`` on the same input for comparison only.

    The returned response is computed from the current model before the candidate sees anything, and
    the candidate receives a copy, so neither a mutation nor an exception in the candidate can change
    what is served. Both outcomes are appended to ``log``.
    """

    def __init__(self, current, candidate, log: list | None = None):
        self.current, self.candidate = current, candidate
        self.log = [] if log is None else log

    def score(self, run_id: str, run) -> dict:
        response = respond(self.current, run)
        record = {"run_id": run_id, "current_version": self.current.label,
                  "candidate_version": getattr(self.candidate, "label", repr(self.candidate)),
                  "current_alarms": response["alarm_events"], "candidate_alarms": None, "candidate_error": None}
        try:
            record["candidate_alarms"] = respond(self.candidate, run.copy(deep=True))["alarm_events"]
        except Exception as exc:  # noqa: BLE001  (the candidate must never break serving)
            record["candidate_error"] = f"{type(exc).__name__}: {exc}"
        self.log.append(record)
        return response


def _overlaps(a, events) -> bool:
    return any(a[0] < e[1] and e[0] < a[1] for e in events)


def disagreements(log: list) -> dict:
    """Runs where the two alarm sets differ, alarms only one model raised, and candidate errors."""
    out = {"runs": len(log), "runs_differ": 0, "only_current": 0, "only_candidate": 0, "candidate_errors": 0}
    for r in log:
        if r["candidate_error"] is not None:
            out["candidate_errors"] += 1
            continue
        cur, cand = r["current_alarms"], r["candidate_alarms"]
        if cur != cand:
            out["runs_differ"] += 1
        out["only_current"] += sum(not _overlaps(a, cand) for a in cur)
        out["only_candidate"] += sum(not _overlaps(a, cur) for a in cand)
    return out


# --------------------------------------------------------------------------- registry pointer moves
def audit_log(root, name) -> list[dict]:
    path = Path(root) / name / AUDIT_FILE
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _append_audit(root, name, entry: dict) -> None:
    with open(Path(root) / name / AUDIT_FILE, "a") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


def _check_deployable(root, name, version, serving_columns) -> None:
    if version not in list_versions(root, name):
        raise RegistryError(f"{name} {version} is not registered")
    model, doc = load_bundle(Path(root) / name / version)  # verifies checksums and format
    missing = set(doc["input_schema"]["required"]) - set(serving_columns)
    if missing:
        raise RegistryError(f"{name} {version} needs columns the serving contract lacks: {sorted(missing)}")


def _move(root, name, action, version, actor, reason) -> None:
    previous = current_version(root, name)
    write_pointer(root, name, version)  # atomic; if it raises, nothing below runs
    _append_audit(root, name, {"ts": datetime.now(timezone.utc).isoformat(), "action": action,
                               "from": previous, "to": version, "actor": actor, "reason": reason})


def promote(root, name, version: str, *, serving_columns, actor: str = "", reason: str = "") -> None:
    """Point ``current`` at ``version`` after checking that it is registered, intact and servable."""
    _check_deployable(root, name, version, serving_columns)
    if current_version(root, name) == version:
        raise RegistryError(f"{name} {version} is already current")
    _move(root, name, "promote", version, actor, reason)


def rollback(root, name, *, serving_columns, actor: str = "", reason: str = "") -> str:
    """Undo the most recent promotion that has not been undone yet; returns the restored version."""
    stack = []
    for entry in audit_log(root, name):
        if entry["action"] == "promote":
            stack.append(entry)
        elif entry["action"] == "rollback" and stack:
            stack.pop()
    if not stack or stack[-1]["from"] is None:
        raise RegistryError(f"{name}: nothing to roll back to")
    target = stack[-1]["from"]
    _check_deployable(root, name, target, serving_columns)
    _move(root, name, "rollback", target, actor, reason)
    return target
