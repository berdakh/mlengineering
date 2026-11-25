"""Step 2 of the worked example: format the stored numbers. Computes nothing.

    python render.py <summary.json> <report.md>
"""
import json
import sys
from pathlib import Path

s = json.loads(Path(sys.argv[1]).read_text())
lines = [
    "# Churn models A and B: summary (SYNTHETIC case)", "",
    "| Quantity | Value |", "|---|---|",
    f"| Customers | {s['customers']} |", f"| Regions | {s['regions']} |",
    f"| AUC, model A | {s['auc_a']:.3f} |", f"| AUC, model B | {s['auc_b']:.3f} |",
    f"| Regions where B has the higher AUC | {s['regions_where_b_wins']} |", "",
    "Regions where B does worst relative to A:", "",
    "| Region | Customers | AUC A | AUC B |", "|---|---|---|---|",
]
lines += [f"| {r['region']} | {r['customers']} | {r['auc_a']:.3f} | {r['auc_b']:.3f} |" for r in s["worst_regions_for_b"]]
lines += ["", f"Input sha256: `{s['input_sha256']}`. Rebuild: `make`."]
Path(sys.argv[2]).write_text("\n".join(lines) + "\n")
print(f"wrote {sys.argv[2]}")
