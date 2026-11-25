"""Download the SKAB v0.9 files used by the portfolio project (not redistributed here).

Source:   https://github.com/waico/SKAB  (Skoltech Anomaly Benchmark)
Licence:  GPL-3.0 (see the upstream LICENSE). The data stays out of this repository;
          this script fetches it to data/raw/skab/ (git-ignored) at a pinned commit.
Citation: Katser, I. D. & Kozitsin, V. O. (2020). Skoltech Anomaly Benchmark (SKAB).
          Kaggle. DOI 10.34740/KAGGLE/DSV/1693952

    python scripts/fetch_skab.py            # download + write MANIFEST.json (sha256 per file)
    python scripts/fetch_skab.py --verify   # re-hash local files against MANIFEST.json

Only the standard library is used. File names are probed because the upstream folder
listing and the actual file numbering differ; a 404 for a probed name is expected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

COMMIT = "b2c0d46c2971dcbfe71e26087b6d231998bb91c2"  # upstream HEAD on 2026-11-21
BASE = f"https://raw.githubusercontent.com/waico/SKAB/{COMMIT}/data"
CANDIDATES = (["anomaly-free/anomaly-free.csv"]
              + [f"valve1/{i}.csv" for i in range(0, 17)]
              + [f"valve2/{i}.csv" for i in range(0, 5)]
              + [f"other/{i}.csv" for i in range(0, 15)])
DEST = Path(__file__).resolve().parents[1] / "data" / "raw" / "skab"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download() -> int:
    manifest = {"source": "https://github.com/waico/SKAB", "commit": COMMIT, "licence": "GPL-3.0", "files": {}}
    for rel in CANDIDATES:
        target = DEST / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with urllib.request.urlopen(f"{BASE}/{rel}", timeout=60) as response:
                target.write_bytes(response.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                continue
            raise
        manifest["files"][rel] = {"sha256": sha256(target), "bytes": target.stat().st_size}
        print(f"ok  {rel}")
    (DEST / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"{len(manifest['files'])} files in {DEST}")
    return 0


def verify() -> int:
    manifest = json.loads((DEST / "MANIFEST.json").read_text())
    bad = [rel for rel, meta in manifest["files"].items()
           if not (DEST / rel).is_file() or sha256(DEST / rel) != meta["sha256"]]
    print("all files match MANIFEST.json" if not bad else f"MISMATCH: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Fetch SKAB at a pinned commit.")
    ap.add_argument("--verify", action="store_true")
    sys.exit(verify() if ap.parse_args().verify else download())
