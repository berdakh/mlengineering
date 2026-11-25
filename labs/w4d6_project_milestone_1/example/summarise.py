"""Step 1 of the worked example: compute every number once and store it (SYNTHETIC churn case).

    python summarise.py <predictions.csv> <summary.json>
"""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import roc_auc_score

src, out = Path(sys.argv[1]), Path(sys.argv[2])
d = pd.read_csv(src)
rows = []
for region, g in d.groupby("region", sort=True):
    rows.append({"region": region, "customers": int(len(g)), "churn_rate": float(g["churned"].mean()),
                 "auc_a": float(roc_auc_score(g["churned"], g["score_a"])),
                 "auc_b": float(roc_auc_score(g["churned"], g["score_b"]))})
summary = {
    "input_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
    "customers": int(len(d)), "regions": int(d["region"].nunique()),
    "auc_a": float(roc_auc_score(d["churned"], d["score_a"])),
    "auc_b": float(roc_auc_score(d["churned"], d["score_b"])),
    "regions_where_b_wins": int(sum(r["auc_b"] > r["auc_a"] for r in rows)),
    "worst_regions_for_b": sorted(rows, key=lambda r: r["auc_b"] - r["auc_a"])[:3],
}
out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
print(f"wrote {out}")
