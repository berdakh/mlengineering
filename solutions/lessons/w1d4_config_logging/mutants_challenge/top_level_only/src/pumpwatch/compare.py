"""Compare two run directories: what was configured differently, and what changed."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_FILES = ("config.json", "metrics.json", "environment.json")


class RunDirError(ValueError):
    """The path is not a complete run directory."""


def load_run(run_dir: str | Path) -> dict[str, dict[str, Any]]:
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise RunDirError(f"not a run directory: {run_dir}")
    loaded = {}
    for name in REQUIRED_FILES:
        path = run_dir / name
        if not path.is_file():
            raise RunDirError(f"{run_dir} is missing {name}")
        loaded[name.removesuffix(".json")] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def flatten(nested: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """``{"split": {"seed": 7}}`` -> ``{"split.seed": 7}`` (any depth)."""
    flat: dict[str, Any] = {}
    for key, value in nested.items():
        dotted = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(flatten(value, prefix=f"{dotted}."))
        else:
            flat[dotted] = value
    return flat


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def compare_runs(run_a: str | Path, run_b: str | Path) -> dict[str, Any]:
    a, b = load_run(run_a), load_run(run_b)
    cfg_a, cfg_b = a["config"], b["config"]
    config_diff = {
        key: {"a": cfg_a.get(key), "b": cfg_b.get(key)}
        for key in sorted(set(cfg_a) | set(cfg_b))
        if cfg_a.get(key) != cfg_b.get(key)
    }
    metric_diff = {
        key: {"a": a["metrics"][key], "b": b["metrics"][key], "delta": b["metrics"][key] - a["metrics"][key]}
        for key in sorted(set(a["metrics"]) & set(b["metrics"]))
        if _is_number(a["metrics"][key]) and _is_number(b["metrics"][key])
    }
    return {
        "config_diff": config_diff,
        "metric_diff": metric_diff,
        # Same bytes, not same path: a file can be edited in place or copied elsewhere.
        "same_data": a["environment"]["data_sha256"] == b["environment"]["data_sha256"],
    }
