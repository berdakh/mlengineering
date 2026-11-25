"""Worked example (w6d5): the cost *structure* of a small always-on container service.

    python labs/w6d5_cloud_deployment/example/task_hours.py
    python labs/w6d5_cloud_deployment/example/task_hours.py --vcpu-hour 0.04 --gb-hour 0.004 --ipv4-hour 0.005

No prices are built in. AWS prices differ by region and change; this course could not verify them when
it was written. Without rates the script reports billed *units* (vCPU-hours, GB-hours, address-hours);
with the rates you looked up on the official pricing pages today, it multiplies them out. The numbers
in the example call above are placeholders to show the arithmetic, not prices.

The point the units make on their own: the cost of a demo is set by how long it runs, and a forgotten
service runs for every hour of the month.
"""
from __future__ import annotations

import argparse

HOURS_PER_MONTH = 730  # 365 * 24 / 12

SCENARIOS = [  # name, tasks, hours
    ("lab: deploy, verify, tear down the same day", 1, 2),
    ("demo left running over a weekend", 1, 64),
    ("forgotten until the next bill", 1, HOURS_PER_MONTH),
    ("forgotten, two tasks 'for availability'", 2, HOURS_PER_MONTH),
]


def units(tasks: int, hours: float, vcpu: float, gb: float) -> dict[str, float]:
    return {"vcpu_h": tasks * hours * vcpu, "gb_h": tasks * hours * gb, "ipv4_h": tasks * hours}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vcpu", type=float, default=0.25, help="vCPU per task (task definition cpu / 1024)")
    ap.add_argument("--gb", type=float, default=0.5, help="GB per task (task definition memory / 1024)")
    ap.add_argument("--vcpu-hour", type=float, help="price per vCPU-hour you looked up")
    ap.add_argument("--gb-hour", type=float, help="price per GB-hour you looked up")
    ap.add_argument("--ipv4-hour", type=float, help="price per public IPv4 address-hour you looked up")
    a = ap.parse_args()
    priced = None not in (a.vcpu_hour, a.gb_hour, a.ipv4_hour)
    print(f"task size {a.vcpu} vCPU, {a.gb} GB; one public IPv4 address per task")
    print(f"{'scenario':<46}{'vCPU-h':>9}{'GB-h':>9}{'IPv4-h':>9}" + (f"{'cost':>10}" if priced else ""))
    for name, tasks, hours in SCENARIOS:
        u = units(tasks, hours, a.vcpu, a.gb)
        line = f"{name:<46}{u['vcpu_h']:>9.1f}{u['gb_h']:>9.1f}{u['ipv4_h']:>9.0f}"
        if priced:
            line += f"{u['vcpu_h'] * a.vcpu_hour + u['gb_h'] * a.gb_hour + u['ipv4_h'] * a.ipv4_hour:>10.2f}"
        print(line)
    print("not included: ECR storage, CloudWatch Logs ingestion and storage, data transfer out, tax")
    if not priced:
        print("add --vcpu-hour, --gb-hour and --ipv4-hour (from the pricing pages, today) to see amounts")


if __name__ == "__main__":
    main()
