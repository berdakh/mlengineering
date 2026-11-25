"""Worked example (w8d2): a results paragraph generated from the results file, never typed.

    python labs/w8d2_report_limitations/example/write_results_paragraph.py

Reads the committed milestone-1 results (real SKAB, w4d6 reference) and prints two versions of the same
paragraph: the one people write by hand, and the one a sceptical reviewer accepts. Every number in the
second comes from the file, with its interval and how the interval was obtained.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
res = json.loads((ROOT / "solutions/labs/w4d6_project_milestone_1/example_report/results.json").read_text())
test = {t["name"]: t for t in res["test"]}
dev = {d["name"]: d for d in res["development"]}
p = res["protocol"]
chosen, logit = test["flow-rate |z|"], test["logistic (supervised)"]
d = dev["logistic (supervised)"]

print("== Written by hand (what reviewers reject)")
print(f"The supervised model is better ({logit['pr_auc']:.2f} vs {chosen['pr_auc']:.2f} PR-AUC), and our detector "
      f"is highly reliable ({chosen['events_detected']}/{chosen['events_total']} faults detected).\n")

print("== Generated from the results file")
reading = ("inconclusive: the interval excludes zero but not differences below"
           if d["diff_lo"] < p["mpid"] < d["diff_hi"] or 0 < d["diff_lo"] < p["mpid"]
           else "decided by")
print(f"On the {p['dev_experiments']} development recordings the supervised model's PR-AUC was "
      f"{d['diff']:+.3f} [{d['diff_lo']:.3f}, {d['diff_hi']:.3f}] higher than the flow-rate z-score "
      f"(paired cluster bootstrap over {p['dev_clusters']} overlap groups, {p['n_boot']} replicates); "
      f"{reading} the {p['mpid']} we fixed in advance. On the single test look ({len(p['test_experiments'])} "
      f"recordings) the chosen detector found {chosen['events_detected']} of {chosen['events_total']} faults "
      f"(Wilson 95 % interval [{chosen['recall_lo']:.2f}, {chosen['recall_hi']:.2f}]) with a median delay of "
      f"{chosen['median_delay_s']:.0f} s and no false alarm in {chosen['normal_hours']:.1f} hours of normal operation, "
      f"too little time to confirm the budget of one per {p['alert_budget_hours']} hours.")
