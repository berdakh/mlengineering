"""Reference for the w4d4 interview rep, plus tests you can run against your own file.

    python solutions/lessons/w4d4_experiment_tracking/interview_rep/config_diff.py            # test this reference
    python solutions/lessons/w4d4_experiment_tracking/interview_rep/config_diff.py mine.py    # test your file
"""
from __future__ import annotations

import importlib.util
import sys
from typing import Any


def _flatten(d: dict, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in d.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict) and value:
            out.update(_flatten(value, name + "."))
        else:
            out[name] = value
    return out


def diff_configs(a: dict, b: dict) -> dict:
    fa, fb = _flatten(a), _flatten(b)
    return {"changed": {k: (fa[k], fb[k]) for k in sorted(fa.keys() & fb.keys()) if fa[k] != fb[k]},
            "only_a": {k: fa[k] for k in sorted(fa.keys() - fb.keys())},
            "only_b": {k: fb[k] for k in sorted(fb.keys() - fa.keys())}}


def _get(d: dict, dotted: str) -> Any:
    for part in dotted.split("."):
        d = d[part]
    return d


def best_per_group(records: list[dict], group_by: list[str], metric: str) -> dict:
    best: dict[tuple, dict] = {}
    for record in records:
        if record.get("status") != "complete":
            continue
        key = tuple(_get(record["config"], k) for k in group_by)
        if key not in best or record["metrics"][metric] > best[key]["metrics"][metric]:
            best[key] = record
    return best


def run_tests(m) -> None:
    out = m.diff_configs({"model": {"alpha": 1.0, "kind": "ridge"}, "seed": 0},
                         {"model": {"alpha": 2.0}, "seed": 0, "data": {"n": 5}})
    assert out == {"changed": {"model.alpha": (1.0, 2.0)}, "only_a": {"model.kind": "ridge"},
                   "only_b": {"data.n": 5}}, out
    assert m.diff_configs({"a": [1, 2]}, {"a": [1, 2]}) == {"changed": {}, "only_a": {}, "only_b": {}}
    assert m.diff_configs({"a": {"b": 1}}, {"a": 1})["only_a"] == {"a.b": 1}, "a table replaced by a scalar"
    runs = [
        {"config": {"m": {"k": "x"}, "seed": 0}, "metrics": {"ap": 0.5}, "status": "complete"},
        {"config": {"m": {"k": "x"}, "seed": 1}, "metrics": {"ap": 0.7}, "status": "complete"},
        {"config": {"m": {"k": "x"}, "seed": 2}, "metrics": {"ap": 0.9}, "status": "partial"},
        {"config": {"m": {"k": "y"}, "seed": 0}, "metrics": {"ap": 0.6}, "status": "complete"},
        {"config": {"m": {"k": "y"}, "seed": 1}, "metrics": {"ap": 0.6}, "status": "complete"},
    ]
    best = m.best_per_group(runs, ["m.k"], "ap")
    assert set(best) == {("x",), ("y",)}
    assert best[("x",)]["config"]["seed"] == 1, "the partial run (0.9) must be ignored"
    assert best[("y",)]["config"]["seed"] == 0, "ties keep the first record"
    print("all interview-rep tests passed")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        spec = importlib.util.spec_from_file_location("candidate", sys.argv[1])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        module = sys.modules[__name__]
    run_tests(module)
