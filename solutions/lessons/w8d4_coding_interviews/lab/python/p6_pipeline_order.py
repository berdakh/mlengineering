"""P6 (medium-hard, graphs): order pipeline steps by their dependencies. Reference solution."""
from __future__ import annotations

import heapq


def pipeline_order(steps: list[str], deps: list[tuple[str, str]]) -> list[str]:
    """A run order of all steps in which every (before, after) dependency is respected.

    At each point, among the steps whose dependencies are all done, the alphabetically smallest runs
    next, so the answer is unique. Raises ValueError if a dependency names an unknown step, or if the
    dependencies contain a cycle (the message names at least one step on it).
    Kahn's algorithm with a heap: O((V + E) log V), iterative (no recursion limit).
    """
    known = set(steps)
    if len(known) != len(steps):
        raise ValueError("duplicate step names")
    succ: dict[str, list[str]] = {s: [] for s in steps}
    indeg = {s: 0 for s in steps}
    for before, after in deps:
        if before not in known or after not in known:
            raise ValueError(f"dependency ({before!r}, {after!r}) names an unknown step")
        succ[before].append(after)
        indeg[after] += 1
    ready = [s for s in steps if indeg[s] == 0]
    heapq.heapify(ready)
    order: list[str] = []
    while ready:
        s = heapq.heappop(ready)
        order.append(s)
        for nxt in succ[s]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                heapq.heappush(ready, nxt)
    if len(order) != len(steps):
        stuck = sorted(s for s in steps if indeg[s] > 0)
        raise ValueError(f"dependency cycle involving {stuck[0]!r} ({len(stuck)} steps cannot run)")
    return order
