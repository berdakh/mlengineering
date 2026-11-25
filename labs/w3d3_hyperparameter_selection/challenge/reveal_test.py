"""Reveal the held-out TEST score of ONE recorded trial - and write down that you looked.

    python labs/w3d3_hyperparameter_selection/challenge/reveal_test.py --trial 17

Every call appends to ``test_looks.json`` next to this file. The log is part of your submission:
the challenge allows exactly one look, at the trial your procedure chose. The scores are stored
obfuscated in ``sealed_test_scores.b64``; decoding them by hand defeats the exercise.
"""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser(description="Reveal one test score and log the look.")
    ap.add_argument("--trial", type=int, required=True)
    args = ap.parse_args()
    scores = json.loads(base64.b64decode((HERE / "sealed_test_scores.b64").read_text()))
    if not 0 <= args.trial < len(scores):
        raise SystemExit(f"trial must be between 0 and {len(scores) - 1}")
    log_path = HERE / "test_looks.json"
    looks = json.loads(log_path.read_text()) if log_path.is_file() else []
    looks.append({"look": len(looks) + 1, "trial": args.trial, "test_score": scores[args.trial]})
    log_path.write_text(json.dumps(looks, indent=2) + "\n")
    print(f"trial {args.trial}: test score {scores[args.trial]:.4f}   (look number {len(looks)}, logged)")


if __name__ == "__main__":
    main()
