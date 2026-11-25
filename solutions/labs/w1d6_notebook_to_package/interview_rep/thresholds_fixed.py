"""Reference fix for the interview rep."""
import json
from pathlib import Path

_CACHE: dict[str, dict] = {}


def load_thresholds(path, overrides=None):
    """Per-sensor alert thresholds from a JSON file, with optional overrides.

    The file is parsed once per path. Every call returns a NEW dict, so neither
    the caller nor the overrides can alter what later calls see.
    """
    key = str(path)
    if key not in _CACHE:
        _CACHE[key] = json.loads(Path(path).read_text())
    return {**_CACHE[key], **(overrides or {})}
