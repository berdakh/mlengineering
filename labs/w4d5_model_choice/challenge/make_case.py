"""Generate the SYNTHETIC churn-model decision case for the w4d5 challenge.

    python labs/w4d5_model_choice/challenge/make_case.py                 # writes challenge/case/
    python labs/w4d5_model_choice/challenge/make_case.py --check         # regenerate and compare
    python labs/w4d5_model_choice/challenge/make_case.py --variant clear_win --out /tmp/case2

SYNTHETIC. The business ("Larkspur", a meal-kit subscription), the customers and both models are
invented. The case is built so that the arithmetic has a defensible answer; it says nothing about
real churn models, real latency or real costs.

Files written to the case directory:
  predictions.csv  customer_id, region, churned (0/1), score_a, score_b   (held-out month)
  latency_ms.csv   model (A/B), ms      (per-request latency logged in a staging load test)
  case.json        the decision parameters fixed before the comparison (MPID, latency budget, ...)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SEED = 20261122

VARIANTS = {
    # B gains a little on average, very unevenly across regions; B is 20x slower.
    "default": dict(gain_mean=0.42, gain_sd=0.55, b_latency_factor=20.0),
    # B gains clearly everywhere and is only 1.5x slower: the evidence should change the decision.
    "clear_win": dict(gain_mean=0.70, gain_sd=0.10, b_latency_factor=1.5),
}

CASE = {
    "business": "Larkspur meal-kit subscriptions (SYNTHETIC)",
    "decision": "which churn model scores customers on the account page to choose a retention offer",
    "reference": "A",
    "metric": "ROC AUC on the held-out month, pooled over customers",
    "unit_of_resampling": "region (customers in a region share pricing, couriers and promotions)",
    "mpid": 0.02,
    "p95_budget_ms": 50.0,
    "models": {
        "A": {"kind": "gradient-boosted trees, 120 features, in the current Python service",
              "new_dependencies": []},
        "B": {"kind": "transformer over the order-event sequence, needs a GPU-backed inference server",
              "new_dependencies": ["onnxruntime-gpu", "a model-server container", "a GPU node pool"]},
    },
}


def generate(variant: str = "default", seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    v = VARIANTS[variant]
    rng = np.random.default_rng(seed)
    n_regions = 40
    sizes = rng.integers(150, 600, size=n_regions)
    region_base = rng.normal(0.0, 0.6, size=n_regions)        # regions differ in churn rate
    region_gain = rng.normal(v["gain_mean"], v["gain_sd"], size=n_regions)   # B's extra signal per region
    rows = []
    cid = 0
    for r in range(n_regions):
        n = int(sizes[r])
        risk = rng.normal(0.0, 1.0, size=n)                    # true latent churn risk
        logit = -2.2 + region_base[r] + 1.3 * risk
        churned = rng.random(n) < 1 / (1 + np.exp(-logit))
        score_a = risk + rng.normal(0.0, 0.9, size=n)
        noise_b = rng.normal(0.0, 0.9, size=n)
        score_b = risk * (1.0 + region_gain[r]) + noise_b
        for i in range(n):
            rows.append((f"C{cid:06d}", f"R{r:02d}", int(churned[i]), round(float(score_a[i]), 5),
                         round(float(score_b[i]), 5)))
            cid += 1
    preds = pd.DataFrame(rows, columns=["customer_id", "region", "churned", "score_a", "score_b"])
    lat_a = rng.lognormal(mean=np.log(3.0), sigma=0.35, size=2000)
    lat_b = rng.lognormal(mean=np.log(3.0 * v["b_latency_factor"]), sigma=0.35, size=2000)
    lat = pd.DataFrame({"model": ["A"] * 2000 + ["B"] * 2000,
                        "ms": np.round(np.concatenate([lat_a, lat_b]), 4)})
    return preds, lat


def write(out: Path, variant: str = "default") -> None:
    out.mkdir(parents=True, exist_ok=True)
    preds, lat = generate(variant)
    preds.to_csv(out / "predictions.csv", index=False, lineterminator="\n")
    lat.to_csv(out / "latency_ms.csv", index=False, lineterminator="\n")
    (out / "case.json").write_text(json.dumps(dict(CASE, variant=variant), indent=2) + "\n")


def digest(folder: Path) -> str:
    h = hashlib.sha256()
    for name in ("predictions.csv", "latency_ms.csv", "case.json"):
        h.update((folder / name).read_bytes())
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--variant", default="default", choices=sorted(VARIANTS))
    ap.add_argument("--out", default=str(HERE / "case"))
    ap.add_argument("--check", action="store_true", help="regenerate into a temp dir and compare with --out")
    args = ap.parse_args()
    if args.check:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp), args.variant)
            same = digest(Path(tmp)) == digest(Path(args.out))
        print("identical" if same else "DIFFERENT")
        return 0 if same else 1
    write(Path(args.out), args.variant)
    print(f"wrote {args.out} (variant {args.variant})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
