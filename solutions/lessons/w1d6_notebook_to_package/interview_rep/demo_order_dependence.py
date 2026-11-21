"""Shows the symptom from the prompt: the same assertion passes or fails depending on what ran before.

    python solutions/lessons/w1d6_notebook_to_package/interview_rep/demo_order_dependence.py
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thresholds_buggy import load_thresholds  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    path = str(Path(tmp) / "thresholds.json")
    Path(path).write_text(json.dumps({"pressure": 2.0, "current": 5.0}))
    print("fresh process, defaults:      ", load_thresholds(path))
    print("with override:                ", load_thresholds(path, {"pressure": 1.5}))
    print("defaults again (same process):", load_thresholds(path))
    print("default argument object:      ", load_thresholds.__defaults__)
