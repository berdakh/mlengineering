"""Part B data and scoring harness: intermittent short network outages. SYNTHETIC. Complete.

    python labs/w3d4_point_vs_event_evaluation/challenge/outages.py

One link is monitored for 24 hours at one sample per second. Forty short outages (3-20 s) occur.
The LABELS are not the truth: they come from a ticket log, so each logged outage starts 0-8 s
after the outage really began and ends 0-8 s after it really ended.
Two detectors are simulated from the true (unlogged) outage times:
  A "fast":   alarm 2 s after the true start, cleared 2 s after the true end; misses 2 outages;
              6 spurious alarms per day.
  B "steady": alarm 12 s after the true start, held for 10 s; misses nothing; 1 spurious alarm per day.
Because the data is simulated, nothing here says which detector design is better in a real network.
The exercise is the matching rule: the table printed under the SKAB rule is misleading, and you
have to say why and replace it (outage_rule.py, OUTAGE_RULE.md).
"""
from __future__ import annotations

import numpy as np

import _paths  # noqa: F401
from flowguard.evaluation import delay_summary, detection_delay, false_alarms_per_hour, match_events
from outage_rule import score_outages

N = 24 * 3600


def simulate(seed: int = 7):
    rng = np.random.default_rng(seed)
    starts = np.sort(rng.choice(np.arange(600, N - 600, 300), size=40, replace=False)) + rng.integers(0, 200, 40)
    durations = rng.integers(3, 21, 40)
    truth = [(int(s), int(s + d)) for s, d in zip(starts, durations)]
    logged = [(s + int(rng.integers(0, 9)), e + int(rng.integers(0, 9))) for s, e in truth]
    logged = [(s, max(e, s + 1)) for s, e in logged]
    missed_by_a = set(rng.choice(40, size=2, replace=False).tolist())
    alarms_a = [(s + 2, e + 2) for k, (s, e) in enumerate(truth) if k not in missed_by_a]
    alarms_b = [(s + 12, s + 22) for s, e in truth]
    quiet = np.setdiff1d(np.arange(1000, N - 1000, 500), np.concatenate([np.arange(s - 600, e + 600) for s, e in truth]))
    spurious = rng.choice(quiet, size=7, replace=False)
    alarms_a += [(int(s), int(s) + 4) for s in spurious[:6]]
    alarms_b += [(int(spurious[6]), int(spurious[6]) + 10)]
    return truth, logged, sorted(alarms_a), sorted(alarms_b), np.arange(N, dtype=float)


def skab_rule(logged, alarms, times) -> dict:
    """The rule used for SKAB in the lab: alarm must start inside the logged event, no tolerance."""
    labels = match_events(logged, alarms)["pred_label"]
    delays = detection_delay(logged, alarms, times)
    return {"events found": f"{int(np.isfinite(delays).sum())}/{len(logged)}", "alarms": len(alarms),
            "false alarms": labels.count("false_alarm"),
            "false alarms/day": round(24 * false_alarms_per_hour(logged, alarms, times), 1),
            "median delay s": delay_summary(delays)["median"]}


def main() -> None:
    truth, logged, alarms_a, alarms_b, times = simulate()
    print(f"SYNTHETIC: {len(truth)} outages in 24 h, true length {min(e - s for s, e in truth)}-"
          f"{max(e - s for s, e in truth)} s; logged onset lags the true onset by 0-8 s\n")
    for rule_name, rule in (("SKAB rule (start inside logged event, tolerance 0)", skab_rule),
                            ("your rule (outage_rule.score_outages)", score_outages)):
        print(rule_name)
        for name, alarms in (("A fast", alarms_a), ("B steady", alarms_b)):
            try:
                print(f"  {name:<9} {rule(logged, alarms, times)}")
            except NotImplementedError as exc:
                print(f"  {name:<9} not implemented yet ({exc})")
        print()


if __name__ == "__main__":
    main()
