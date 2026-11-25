"""Write a /predict request body for one real SKAB experiment (given; you do not need to edit it).

    python labs/w5d4_fastapi_validation/lab/make_request.py --experiment valve1/13 --out /tmp/req.json

Uses the canonical column names of flowguard.data; the API's field for the time is ``timestamp``.
Default experiment: valve1/13, a test experiment of splits/v2.json. Serving a request is not a model
decision, so using a test experiment here does not spend the test set.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = next(p for p in HERE.parents if (p / "project" / "get_skab.py").is_file())
sys.path.insert(0, str(HERE / "src"))

from flowguard.data import SENSOR_COLUMNS, load_raw  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw-dir", default=str(REPO_ROOT / "data" / "raw" / "skab"))
    ap.add_argument("--experiment", default="valve1/13")
    ap.add_argument("--machine-id", default=None, help="defaults to the experiment id")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    run = tidy[tidy["experiment_id"] == args.experiment].sort_values("t")
    if run.empty:
        print(f"error: no experiment {args.experiment!r}", file=sys.stderr)
        return 2
    samples = [{"timestamp": row["datetime"].isoformat(), **{c: float(row[c]) for c in SENSOR_COLUMNS}}
               for row in run.to_dict("records")]
    body = {"machine_id": args.machine_id or args.experiment, "samples": samples}
    Path(args.out).write_text(json.dumps(body))
    print(f"wrote {args.out}: {len(samples)} samples of {args.experiment}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
