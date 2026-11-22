"""Command line for flowguard (this lesson's subset). Given complete; you do not need to edit it.

    flowguard predict-batch --model-dir lab/model --input rows.csv --out results/predictions

Exit codes: 0 every run scored; 3 some runs could not be scored (see manifest.json);
2 the input or the output directory was refused (nothing written); 1 anything unexpected.
"""
from __future__ import annotations

import argparse
import sys

from flowguard import __version__
from flowguard.batch import OutputExistsError, predict_batch
from flowguard.inference import SchemaError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flowguard", description="Fault detection on SKAB (educational).")
    parser.add_argument("--version", action="version", version=f"flowguard {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("predict-batch", help="score a CSV of serving rows with a saved model")
    p.add_argument("--model-dir", required=True, help="directory holding model.json")
    p.add_argument("--input", required=True, help="CSV with columns run_id, datetime and the 8 sensors")
    p.add_argument("--out", required=True, help="output directory (predictions.csv, manifest.json)")
    p.add_argument("--chunk-runs", type=int, default=50, help="runs scored per chunk (memory bound)")
    p.add_argument("--force", action="store_true", help="overwrite predictions for another input/model")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = predict_batch(args.model_dir, args.input, args.out, chunk_runs=args.chunk_runs, force=args.force)
    except (SchemaError, OutputExistsError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"scored {manifest['runs_scored']}/{manifest['runs']} runs, {manifest['input_rows']} rows "
          f"with {manifest['model_name']} {manifest['model_version']} -> {args.out}")
    for run_id, reason in manifest["runs_failed"].items():
        print(f"  not scored: {run_id}: {reason}", file=sys.stderr)
    return 3 if manifest["runs_failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
