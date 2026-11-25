"""P6 (medium-hard, graphs): order pipeline steps by their dependencies. Starter: implement the function; the docstring is the specification."""
from __future__ import annotations



def pipeline_order(steps: list[str], deps: list[tuple[str, str]]) -> list[str]:
    """A run order of all steps in which every (before, after) dependency is respected.

    At each point, among the steps whose dependencies are all done, the alphabetically smallest runs
    next, so the answer is unique. Raises ValueError if a dependency names an unknown step, or if the
    dependencies contain a cycle (the message names at least one step on it).
    Required: about O((V + E) log V) for graphs of 30,000 steps, including a single chain of 30,000.
    """
    raise NotImplementedError("w8d4: implement this")
