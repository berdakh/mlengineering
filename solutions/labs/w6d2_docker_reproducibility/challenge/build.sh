#!/usr/bin/env bash
# Build the service environment from the LOCAL package index in wheelhouse/ (no internet needed).
# REFERENCE SOLUTION: installs the hash-checked lock instead of resolving requirements.in.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf build/site
python -m pip install --quiet --no-index --find-links wheelhouse --require-hashes --target build/site \
    -r service/requirements.lock
echo "installed: $(ls build/site | grep -E '^zscorelib-.*dist-info$')"
PYTHONPATH=build/site python service/driftsvc.py expected/input.json > build/scores.json
python - <<'PY'
import json, math, sys
got = json.load(open("build/scores.json"))
want = json.load(open("expected/scores.json"))
ok = len(got["scores"]) == len(want["scores"]) and all(
    (g is None and w is None) or (g is not None and w is not None and math.isclose(g, w, rel_tol=1e-12))
    for g, w in zip(got["scores"], want["scores"]))
print(f"zscorelib {got['zscorelib']}: smoke test {'PASS' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
PY
