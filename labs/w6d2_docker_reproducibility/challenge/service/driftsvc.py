"""A tiny scoring service used in the w6d2 drift challenge (SYNTHETIC; given, do not edit).

    python service/driftsvc.py expected/input.json      # prints the scores as JSON

The first ``n_burn`` values calibrate a z-score with ``zscorelib.calibrate``; every later value
gets |x - mean| / sd, the same rule as the flowguard detector. Which zscorelib gets imported
depends on how the environment was built: that is the point of the challenge.
"""
from __future__ import annotations

import json
import sys

import zscorelib


def score(values: list[float], n_burn: int) -> list[float | None]:
    mean, sd = zscorelib.calibrate(values[:n_burn])
    return [None] * n_burn + [abs(v - mean) / sd for v in values[n_burn:]]


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: driftsvc.py INPUT.json", file=sys.stderr)
        return 2
    payload = json.loads(open(argv[0]).read())
    scores = score(payload["values"], payload["n_burn"])
    print(json.dumps({"zscorelib": zscorelib.__version__, "scores": scores}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
