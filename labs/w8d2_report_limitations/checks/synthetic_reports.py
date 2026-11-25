"""SYNTHETIC results and reports for the w8d2 checks (a churn model for a fictional subscription service).

`good_report()` follows every rule and deliberately contains the number formats a checker must handle:
thousands separators, percentages, negative values, a value at the end of a sentence, code spans,
dates, version strings and identifiers. Each variant breaks exactly one rule.
"""
from __future__ import annotations

RESULTS = {
    "data": {"call_budget": 300, "customers": 12408, "churn_rate": 0.0731, "regions": 4, "months": 18},
    "protocol": {"n_boot": 2000, "level": 0.95, "test_customers": 2481, "mpid": 0.01},
    "test": {"auc": 0.8137, "auc_lo": 0.7902, "auc_hi": 0.8361, "baseline_auc": 0.7712,
             "diff": 0.0421, "diff_lo": 0.0213, "diff_hi": 0.0644, "recall_at_budget": 0.412,
             "precision_at_budget": 0.338, "calibration_slope": 0.94},
    "comparison": {"gbt_minus_logistic": -0.0061, "p_value": 0.21},
    "slices": {"new_region_auc": 0.7411, "new_region_customers": 611},
}

SECTIONS = {
    "Problem": """The retention team can call 300 customers a month and wants the ones most likely to cancel.
We rank customers by predicted churn probability over the next month.""",
    "Data": """The table covers 12,408 customers in 4 regions over 18 months; 7.3 % churned in a given month.
Extract dated 2026-10-01 from `warehouse.churn_v3`, schema in `docs/schema.md`.""",
    "Protocol": """Customers are split by customer id, and the test months come after the training months.
Thresholds were chosen on validation months only. Run with `make evaluate N_BOOT=200` for a quick check.""",
    "Results": """| Model | AUC [95 % CI] |
|---|---|
| gradient-boosted trees | 0.814 [0.790, 0.836] |
| logistic baseline | 0.771 |
*Interval: bootstrap over customers, 2000 replicates.*

The difference to the baseline was 0.042 [0.021, 0.064] (paired bootstrap over customers). At the call
budget, recall was 41 % and precision 34 %. Trees and a regularised logistic model with interactions were
not significantly different (paired permutation test, p = 0.21; difference -0.006). In the newest region
the AUC was 0.741.""",
    "Error analysis": """Most misses are customers in their first two months, where the history is short. Customer
`C-1042` in region `R2` illustrates it; see `notebooks/errors_2026-10-03.ipynb` (version `1.4.2`).""",
    "Decision": """We ship the gradient-boosted trees because the gain over the baseline is larger than the 0.01
AUC we fixed in advance, and the calibration slope is 0.94.""",
    "Serving and monitoring": """Scores are produced in a nightly batch for 12,408 customers and monitored for drift
in tenure and plan mix; recall is re-estimated when cancellations are confirmed a month later.""",
    "Limitations": """* **One extract.** Impact: seasonality beyond 18 months is unseen. Mitigation: re-evaluate quarterly.
* **New regions.** Impact: AUC was lower in the newest region (611 customers). Mitigation: report it
  separately and monitor.
* **Calls change behaviour.** Impact: customers who were called churn less, which biases later labels.
  Mitigation: keep a small random holdout that is never called.
* **Short histories.** Impact: most misses. Mitigation: a tenure-aware feature set is planned.
* **Proxy outcome.** Impact: cancellation is recorded with a delay. Mitigation: evaluate one month late.""",
    "Reproducibility": """`make report` regenerates every number from the extract and `splits.json`; environment pinned
in `requirements.lock`.""",
}


def render(sections: dict[str, str]) -> str:
    parts = ["# Churn model report (SYNTHETIC)", ""]
    for i, (title, body) in enumerate(sections.items(), 1):
        parts += [f"## {i}. {title}", "", body, ""]
    return "\n".join(parts)


def good_report() -> str:
    return render(SECTIONS)


def variants() -> dict[str, tuple[str, str]]:
    """name -> (report text, the one finding code expected)."""
    s = dict(SECTIONS)
    out = {}
    v = dict(s)
    v["Results"] = s["Results"].replace("In the newest region\nthe AUC was 0.741.",
                                        "In the newest region\nthe AUC was 0.774.")
    out["untraced_number"] = (render(v), "untraced_number")
    v = dict(s)
    v["Results"] = s["Results"].replace(" (paired bootstrap over customers)", "")
    out["interval_without_unit"] = (render(v), "interval_without_unit")
    v = dict(s)
    v["Decision"] = s["Decision"].replace("We ship the gradient-boosted trees because",
                                          "The trees are significantly better, and")
    out["significance_without_test"] = (render(v), "significance_without_test")
    v = dict(s)
    del v["Reproducibility"]
    out["missing_section"] = (render(v), "missing_section")
    v = dict(s)
    v["Limitations"] = s["Limitations"].replace(" Mitigation: keep a small random holdout that is never called.", "")
    out["limitation_without_mitigation"] = (render(v), "limitations_incomplete")
    v = dict(s)
    v["Limitations"] = "\n".join(s["Limitations"].splitlines()[:4])
    out["too_few_limitations"] = (render(v), "limitations_incomplete")
    return out
