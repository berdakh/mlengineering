"""Generate the SYNTHETIC canary logs used by the w7d4 challenge (committed; rerun to check).

    python lessons/w7d4_model_updates_rollback/challenge/make_canary_logs.py           # rewrite
    python lessons/w7d4_model_updates_rollback/challenge/make_canary_logs.py --check   # compare

One CSV per scenario, one row per (hour, arm). 10 % of machines (and of requests) are routed to the
canary. Columns: hour, arm (control | canary), requests, errors (5xx), machine_hours (monitored
machine-hours), alerts. Rates per scenario are stated in SCENARIOS; nothing here is real traffic.
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent / "canary_logs"
# name: (hours, canary error rate, canary alerts per machine-hour, seed)
SCENARIOS = {
    "a_broken_release": (48, 0.035, 0.10, 1),
    "b_alarm_storm": (48, 0.01, 3.00, 2),
    "c_too_early": (6, 0.01, 0.10, 3),
    "d_healthy": (96, 0.01, 0.10, 4),
    "e_borderline_alerts": (96, 0.01, 1.00, 5),
}
CONTROL_ERROR, CONTROL_ALERTS = 0.01, 0.10


def generate(hours: int, canary_error: float, canary_alerts: float, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for h in range(hours):
        for arm, share, err, alert in (("control", 0.9, CONTROL_ERROR, CONTROL_ALERTS),
                                       ("canary", 0.1, canary_error, canary_alerts)):
            requests = int(rng.poisson(1000 * share))
            machine_hours = round(50 * share, 2)
            rows.append({"hour": h, "arm": arm, "requests": requests,
                         "errors": int(rng.binomial(requests, err)), "machine_hours": machine_hours,
                         "alerts": int(rng.poisson(alert * machine_hours))})
    return pd.DataFrame(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    HERE.mkdir(exist_ok=True)
    same = True
    for name, spec in SCENARIOS.items():
        buf = io.StringIO()
        generate(*spec).to_csv(buf, index=False, lineterminator="\n")
        path = HERE / f"{name}.csv"
        if args.check:
            same &= path.is_file() and path.read_text() == buf.getvalue()
        else:
            path.write_text(buf.getvalue())
    if args.check:
        print("canary logs reproduce" if same else "canary logs DIFFER")
        return 0 if same else 1
    print(f"wrote {len(SCENARIOS)} logs to {HERE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
