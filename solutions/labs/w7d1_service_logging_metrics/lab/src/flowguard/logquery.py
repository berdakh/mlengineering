"""Answer "what happened to request X?" from JSON-lines logs. REFERENCE SOLUTION (w7d1).

    python -m flowguard.cli logs --file service.log --request-id 3f9c...

Lines that are not JSON objects (a crash dump, uvicorn's own text logs) are skipped and counted, not
fatal: a debugging tool must work on the messy file you actually have.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class QueryResult:
    request_id: str
    events: list[dict] = field(default_factory=list)
    skipped_lines: int = 0

    @property
    def found(self) -> bool:
        return bool(self.events)


def parse_lines(lines: Iterable[str]) -> tuple[list[dict], int]:
    """JSON objects in file order, and the number of lines that were not JSON objects."""
    events, skipped = [], 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue
        if isinstance(obj, dict):
            events.append(obj)
        else:
            skipped += 1
    return events, skipped


def find_request(lines: Iterable[str], request_id: str) -> QueryResult:
    """All events carrying ``request_id``, in the order they were written."""
    events, skipped = parse_lines(lines)
    return QueryResult(request_id, [e for e in events if e.get("request_id") == request_id], skipped)


def describe(result: QueryResult) -> str:
    """A short human-readable timeline of one request."""
    if not result.found:
        return f"no events for request {result.request_id} ({result.skipped_lines} non-JSON lines skipped)"
    out = [f"request {result.request_id}: {len(result.events)} event(s)"]
    for e in result.events:
        keys = [k for k in ("method", "route", "status", "duration_ms", "machine_id", "model_version",
                            "n_samples", "n_exceeding", "max_score", "error_type") if k in e]
        detail = ", ".join(f"{k}={e[k]}" for k in keys)
        out.append(f"  {e.get('ts', '?')}  {e.get('level', '?'):7s} {e.get('event', '?'):12s} {detail}")
    if result.skipped_lines:
        out.append(f"  ({result.skipped_lines} non-JSON lines skipped)")
    return "\n".join(out)
