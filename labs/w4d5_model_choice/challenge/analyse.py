"""Evidence for the Larkspur churn-model decision (w4d5 challenge). YOUR implementation goes here.

    python labs/w4d5_model_choice/challenge/analyse.py                    # the committed case
    python labs/w4d5_model_choice/challenge/analyse.py --case /tmp/case2  # another variant

Contract (the checks rely on it): ``analyse(case_dir, n_boot=2000, seed=0)`` returns a dict with
auc_a, auc_b, diff (= auc_b - auc_a), diff_lo, diff_hi (95 % paired bootstrap interval of the
difference, resampling the right unit), vs_reference ("better" | "worse" | "equivalent" |
"inconclusive", same rule as flowguard.decision.classify_difference), p95_ms_a, p95_ms_b (numpy
default percentile of the logged latencies), meets_latency_a, meets_latency_b, choice ("A" or "B")
and reason. Every decision parameter must come from case.json, not from constants in this file.

Decision rule, fixed before looking: switch to B only if B is shown to be practically better
(the whole interval above +MPID) AND B meets the p95 budget. Otherwise keep A.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def analyse(case_dir: str | Path, n_boot: int = 2000, seed: int = 0) -> dict:
    raise NotImplementedError("TODO: implement analyse (see the docstring and challenge/README.md)")


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
