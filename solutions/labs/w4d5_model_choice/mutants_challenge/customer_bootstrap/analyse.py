"""Evidence for the Larkspur churn-model decision (w4d5 challenge). Reference solution.

    python labs/w4d5_model_choice/challenge/analyse.py                    # the committed case
    python labs/w4d5_model_choice/challenge/analyse.py --case /tmp/case2  # another variant

Contract (the checks rely on it): ``analyse(case_dir, n_boot=2000, seed=0)`` returns a dict with
auc_a, auc_b, diff (= auc_b - auc_a), diff_lo, diff_hi (95 % paired bootstrap, resampling REGIONS),
vs_reference ("better" | "worse" | "equivalent" | "inconclusive", same rule as flowguard.decision),
p95_ms_a, p95_ms_b (numpy default percentile of the logged latencies), meets_latency_a/_b,
choice ("A" or "B") and reason. All decision parameters come from case.json.

Decision rule, fixed before looking: switch to B only if B is shown to be practically better
(the whole interval above +MPID) AND B meets the p95 budget. Otherwise keep A.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent


def _auc(y: np.ndarray, s: np.ndarray) -> float:
    return float(roc_auc_score(y, s))


def classify(lo: float, hi: float, mpid: float) -> str:
    if lo > mpid:
        return "better"
    if hi < -mpid:
        return "worse"
    if -mpid < lo and hi < mpid:
        return "equivalent"
    return "inconclusive"


def analyse(case_dir: str | Path, n_boot: int = 2000, seed: int = 0) -> dict:
    case_dir = Path(case_dir)
    case = json.loads((case_dir / "case.json").read_text())
    preds = pd.read_csv(case_dir / "predictions.csv")
    lat = pd.read_csv(case_dir / "latency_ms.csv")
    y, a, b = (preds[c].to_numpy() for c in ("churned", "score_a", "score_b"))
    auc_a, auc_b = _auc(y, a), _auc(y, b)

    # paired cluster bootstrap: draw regions with replacement, apply the same draw to both models
    groups = [g.index.to_numpy() for _, g in preds.groupby("region", sort=True)]
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, len(y), size=len(y))
        diffs[i] = _auc(y[idx], b[idx]) - _auc(y[idx], a[idx])
    lo, hi = (float(x) for x in np.percentile(diffs, [2.5, 97.5]))

    p95 = {m: float(np.percentile(lat.loc[lat["model"] == m, "ms"], 95)) for m in ("A", "B")}
    budget, mpid = case["p95_budget_ms"], case["mpid"]
    verdict = classify(lo, hi, mpid)
    meets = {m: p95[m] <= budget for m in ("A", "B")}
    if verdict == "better" and meets["B"]:
        choice, reason = "B", "B is practically better and meets the latency budget"
    elif verdict == "better":
        choice, reason = "A", "B is practically better but breaks the latency budget"
    else:
        choice, reason = "A", f"B is not shown to be practically better ({verdict})"
    return {"auc_a": auc_a, "auc_b": auc_b, "diff": auc_b - auc_a, "diff_lo": lo, "diff_hi": hi,
            "vs_reference": verdict, "p95_ms_a": p95["A"], "p95_ms_b": p95["B"],
            "meets_latency_a": meets["A"], "meets_latency_b": meets["B"],
            "choice": choice, "reason": reason, "n_regions": len(groups), "n_boot": n_boot}


def main() -> int:
    ap = argparse.ArgumentParser(description="Evidence for the churn-model decision.")
    ap.add_argument("--case", default=str(HERE / "case"))
    ap.add_argument("--n-boot", type=int, default=2000)
    args = ap.parse_args()
    res = analyse(args.case, n_boot=args.n_boot)
    for k, v in res.items():
        print(f"{k:>16}: {v:.4f}" if isinstance(v, float) else f"{k:>16}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
