"""The code from the interview rep, as given (buggy)."""
import json
from pathlib import Path

_CACHE = {}


def load_thresholds(path, overrides={}):
    """Per-sensor alert thresholds from a JSON file, with optional overrides."""
    if path not in _CACHE:
        _CACHE[path] = json.loads(Path(path).read_text())
    thresholds = _CACHE[path]
    thresholds.update(overrides)
    return thresholds
