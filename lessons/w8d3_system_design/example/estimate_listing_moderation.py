"""Worked example for w8d3: back-of-envelope numbers for a listing-moderation model.

Scenario (constructed for the lesson): an online marketplace receives new listings (an item for sale with
title, description and photos). A model must flag listings that break the rules (counterfeits, banned
items) before they go live. Human moderators review flagged listings; their decision is the label.

Every number below is a stated assumption. The script shows the arithmetic an interviewer wants to hear,
with units, and which assumption dominates. Run from the repository root:

    python lessons/w8d3_system_design/example/estimate_listing_moderation.py
"""
from __future__ import annotations

import math

A = {
    "listings_per_day": 3_000_000,
    "peak_to_mean": 4.0,               # evening peak
    "bytes_per_logged_prediction": 600,  # ids, model version, scores, top features; no images or text
    "log_retention_days": 180,
    "replication": 3,
    "flag_rate": 0.02,                 # share of listings the model sends to moderators
    "moderator_label_delay_days": 1.0,  # moderators clear the queue within a day
    "random_audit_rate": 0.001,         # unflagged listings sampled for review (finds misses)
    "budget_ms": 400,                   # listing must be accepted or held within 400 ms at p99
    "components_ms": {"api gateway + auth": 30, "image fetch from object store": 120,
                      "image embedding (GPU service)": 90, "text features": 15, "feature lookup": 25},
    "model_ms_per_request": 12,          # gradient-boosted trees on embeddings + tabular features, one core
    "cores_per_replica": 4,
    "target_utilisation": 0.6,
}


def main() -> None:
    peak = A["listings_per_day"] / 86_400 * A["peak_to_mean"]
    storage = A["listings_per_day"] * A["bytes_per_logged_prediction"] * A["log_retention_days"] * A["replication"]
    remaining = A["budget_ms"] - sum(A["components_ms"].values())
    busy_cores = peak * A["model_ms_per_request"] / 1000
    replicas = max(1, math.ceil(busy_cores / (A["cores_per_replica"] * A["target_utilisation"])))
    flagged_labels_week = A["listings_per_day"] * A["flag_rate"] * (7 - A["moderator_label_delay_days"])
    audit_labels_week = A["listings_per_day"] * A["random_audit_rate"] * (7 - A["moderator_label_delay_days"])
    # How precisely can we estimate the miss rate (violations among unflagged listings) from audits?
    base_violation_rate = 0.004  # assumption: among unflagged listings
    expected_misses_found = audit_labels_week * base_violation_rate
    n_for_half_width = math.ceil(1.96 ** 2 * base_violation_rate * (1 - base_violation_rate) / 0.001 ** 2)

    rows = [
        ("Peak requests per second", f"{A['listings_per_day']:,}/86,400 x {A['peak_to_mean']}", f"{peak:,.0f} req/s"),
        ("Prediction log storage", "per day x 600 B x 180 d x 3 copies", f"{storage / 1e12:,.2f} TB"),
        ("Latency left for the model", f"{A['budget_ms']} ms - {sum(A['components_ms'].values())} ms",
         f"{remaining} ms (model needs {A['model_ms_per_request']} ms)"),
        ("Busy cores at peak (Little's law)", f"{peak:,.0f} req/s x {A['model_ms_per_request']} ms", f"{busy_cores:,.2f}"),
        ("Model replicas", f"busy / ({A['cores_per_replica']} cores x {A['target_utilisation']})", f"{replicas}"),
        ("Moderator labels per week", "flagged x (7 - 1 day delay)", f"{flagged_labels_week:,.0f}"),
        ("Audit labels per week (unflagged)", "0.1 % audit x (7 - 1)", f"{audit_labels_week:,.0f}"),
        ("Misses found by audits per week", "audit labels x 0.4 % violation rate", f"{expected_misses_found:,.1f}"),
        ("Audits for +/-0.1 pt on the miss rate", "1.96^2 p(1-p) / 0.001^2", f"{n_for_half_width:,} (~{n_for_half_width / audit_labels_week:.1f} weeks)"),
    ]
    width = max(len(r[0]) for r in rows)
    print(f"{'Quantity':<{width}}  {'Arithmetic':<40}  Result")
    for name, how, result in rows:
        print(f"{name:<{width}}  {how:<40}  {result}")


if __name__ == "__main__":
    main()
