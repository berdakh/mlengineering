"""Command line: ``flowguard features --data <tidy.csv> --out-dir <dir>``."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from flowguard import __version__
from flowguard.data import SENSOR_COLUMNS, read_tidy
from flowguard.features import FEATURE_VERSION, cache_key, causal_rolling_features


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flowguard")
    parser.add_argument("--version", action="version", version=f"flowguard {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    feat = sub.add_parser("features", help="build the causal feature table (content-addressed)")
    feat.add_argument("--data", required=True, help="tidy CSV, e.g. data/interim/skab.csv")
    feat.add_argument("--out-dir", required=True, help="parent directory of the feature cache")
    feat.add_argument("--windows", type=int, nargs="+", default=[10, 30, 60])
    feat.add_argument("--max-gap-s", type=float, default=5.0)
    return parser


def run_features(args: argparse.Namespace) -> dict:
    data_path = Path(args.data)
    data_sha = hashlib.sha256(data_path.read_bytes()).hexdigest()
    params = {"windows": sorted(set(args.windows)), "max_gap_s": float(args.max_gap_s),
              "columns": list(SENSOR_COLUMNS)}
    key = cache_key(data_sha, {})
    out = Path(args.out_dir) / key[:16]
    table, meta = out / "features.csv", out / "meta.json"
    if table.is_file() and meta.is_file():
        return {"key": key, "path": str(table), "cache_hit": True}
    features = causal_rolling_features(read_tidy(data_path), params["windows"], max_gap_s=params["max_gap_s"])
    out.mkdir(parents=True, exist_ok=True)
    features.to_csv(table, index=False, lineterminator="\n")
    meta.write_text(json.dumps({
        "key": key, "data_sha256": data_sha, "feature_version": FEATURE_VERSION, "params": params,
        "n_rows": int(len(features)), "columns": list(features.columns),
        "features_sha256": hashlib.sha256(table.read_bytes()).hexdigest(),
    }, indent=2, sort_keys=True) + "\n")  # written last: its presence marks a complete entry
    return {"key": key, "path": str(table), "cache_hit": False}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_features(args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
