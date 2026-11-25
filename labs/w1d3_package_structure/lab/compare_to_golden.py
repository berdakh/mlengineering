"""Compare the JSON printed by `pumpwatch train` with the script's golden output.

    pumpwatch train --data data/synthetic/pump_vibration.csv > /tmp/metrics.json
    python labs/w1d3_package_structure/lab/compare_to_golden.py \
        labs/w1d3_package_structure/lab/golden.txt /tmp/metrics.json

Exit code 0 if every metric the script printed matches to 1e-9, 1 otherwise.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def parse_golden(text: str) -> dict[str, float]:
    """Pick out lines of the form '<name> <float>' from the script's stdout."""
    values = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2:
            try:
                values[parts[0]] = float(parts[1])
            except ValueError:
                pass
    return values


def main(golden_path: str, json_path: str) -> int:
    golden = parse_golden(Path(golden_path).read_text())
    if not golden:
        print(f"no '<name> <number>' lines found in {golden_path}")
        return 1
    metrics = json.loads(Path(json_path).read_text())
    ok = True
    for name, expected in golden.items():
        got = metrics.get(name)
        same = got is not None and abs(got - expected) <= 1e-9
        ok &= same
        print(f"{'ok  ' if same else 'DIFF'} {name:>5}  golden={expected!r}  package={got!r}")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
