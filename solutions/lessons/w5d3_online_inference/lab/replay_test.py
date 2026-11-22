"""Replay the frozen test experiments sample by sample and compare with batch scoring (given).

    python lessons/w5d3_online_inference/lab/replay_test.py        # about 5 s; needs project/get_skab.py

For each of the 7 test experiments of splits/v2.json this script
1. scores the whole run with ``Detector.score_batch`` (the reference),
2. feeds the same rows one at a time to YOUR ``StreamScorer`` and times every ``update`` call,
3. reports parity (largest absolute difference; None/NaN agreement), gaps flagged, and latency.

No model is chosen or tuned here, so replaying test experiments does not spend the test set: the
question is "does the streaming code compute the same function?", not "is the model good?".
Writes ``results/replay.json`` (git-ignored).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = next(p for p in HERE.parents if (p / "project" / "get_skab.py").is_file())
sys.path.insert(0, str(HERE / "src"))

from flowguard.bundle import load_bundle  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.splits import load_splits, validate_splits  # noqa: E402
from flowguard.streaming import StreamScorer  # noqa: E402


def replay(detector, run, machine_id: str) -> dict:
    batch = detector.score_batch(run)
    scorer = StreamScorer(detector, machine_id=machine_id, max_gap_s=5.0, gap_policy="flag")
    rows = run.to_dict("records")
    streamed = np.full(len(rows), np.nan)
    latency_ns = np.empty(len(rows), dtype=np.int64)
    gaps = 0
    for i, row in enumerate(rows):
        t0 = time.perf_counter_ns()
        result = scorer.update(row)
        latency_ns[i] = time.perf_counter_ns() - t0
        gaps += result.after_gap
        if result.score is not None:
            streamed[i] = result.score
    same_missing = bool((np.isnan(batch) == np.isnan(streamed)).all())
    ok = ~np.isnan(batch)
    max_abs = float(np.max(np.abs(batch[ok] - streamed[ok]))) if ok.any() else 0.0
    return {"experiment_id": machine_id, "rows": len(rows), "same_warm_up": same_missing,
            "max_abs_diff": max_abs, "gaps_flagged": int(gaps),
            "exceedances": int(np.sum(batch[ok] >= detector.threshold)), "latency_ns": latency_ns.tolist()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw-dir", default=str(REPO_ROOT / "data" / "raw" / "skab"))
    ap.add_argument("--model-dir", default=str(HERE / "models" / "flowguard-z" / "1.0.0"))
    ap.add_argument("--out", default=str(HERE / "results"))
    args = ap.parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    detector, _ = load_bundle(args.model_dir)
    manifest = load_splits(HERE / "splits" / "v2.json")
    validate_splits(manifest, tidy)
    reports = []
    for eid in sorted(manifest["test"]):
        run = tidy[tidy["experiment_id"] == eid].sort_values("t").reset_index(drop=True)
        reports.append(replay(detector, run, eid))

    print(f"model {detector.version}: n_burn {detector.n_burn}, threshold {detector.threshold:.4f}")
    print(f"{'experiment':<12}{'rows':>6}{'warm-up same':>14}{'max |diff|':>13}{'gaps':>6}{'exceed':>8}")
    for r in reports:
        print(f"{r['experiment_id']:<12}{r['rows']:>6}{str(r['same_warm_up']):>14}"
              f"{r['max_abs_diff']:>13.2e}{r['gaps_flagged']:>6}{r['exceedances']:>8}")
    lat = np.concatenate([np.array(r["latency_ns"]) for r in reports]) / 1e3
    p50, p95, p99 = np.percentile(lat, [50, 95, 99])
    print(f"update() latency over {lat.size} samples: p50 {p50:.1f} us, p95 {p95:.1f} us, "
          f"p99 {p99:.1f} us, max {lat.max():.1f} us")
    parity = all(r["same_warm_up"] for r in reports) and max(r["max_abs_diff"] for r in reports) <= 1e-9
    print("PARITY OK" if parity else "PARITY FAILED")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "replay.json").write_text(json.dumps({"model": detector.version, "experiments": reports}) + "\n")
    return 0 if parity else 1


if __name__ == "__main__":
    sys.exit(main())
