"""Worked example (SYNTHETIC): two ways slice tables mislead.

    python lessons/w3d6_error_analysis_transfer/example/slice_traps.py

Part 1 - Simpson's paradox. Detector B has higher recall than A within every operating regime and
lower recall overall, because the two were evaluated on different mixes of easy and hard machines.
Part 2 - slice hunting. A detector with the SAME true recall on each of 24 machines is sliced 40 ways.
The worst slice looks alarming; it is the minimum of 80 noisy numbers.

The numbers are simulated. They show the arithmetic of the traps, nothing about real equipment.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)

# ---------------------------------------------------------------- Part 1: Simpson's paradox
print("Part 1: recall of two detectors, by regime and overall")
counts = pd.DataFrame({
    "detector": ["A", "A", "B", "B"],
    "regime": ["steady load", "variable load", "steady load", "variable load"],
    "events": [400, 100, 100, 400],
    "true_recall": [0.90, 0.50, 0.94, 0.56],
})
counts["detected"] = rng.binomial(counts["events"], counts["true_recall"])
counts["recall"] = counts["detected"] / counts["events"]
print(counts[["detector", "regime", "events", "detected", "recall"]].to_string(index=False,
      float_format=lambda v: f"{v:.3f}"))
overall = counts.groupby("detector")[["events", "detected"]].sum()
overall["recall"] = overall["detected"] / overall["events"]
print("\npooled over regimes:")
print(overall.to_string(float_format=lambda v: f"{v:.3f}"))
weights = counts.groupby("regime")["events"].sum() / counts["events"].sum()
standardised = (counts.assign(w=counts["regime"].map(weights))
                .assign(part=lambda d: d["w"] * d["recall"]).groupby("detector")["part"].sum())
print("\nstandardised to the same regime mix (50/50):")
print(standardised.to_string(float_format=lambda v: f"{v:.3f}"))

# ---------------------------------------------------------------- Part 2: slice hunting
print("\nPart 2: 24 machines, identical true recall 0.80, 10 events each, 40 arbitrary binary attributes")
n_machines, n_events, n_attributes = 24, 10, 40
recall = rng.binomial(n_events, 0.80, size=n_machines) / n_events
attributes = rng.integers(0, 2, size=(n_machines, n_attributes)).astype(bool)
rows = []
for j in range(n_attributes):
    for level in (False, True):
        member = attributes[:, j] == level
        rows.append({"slice": f"attr{j:02d}={int(level)}", "n_machines": int(member.sum()),
                     "recall": recall[member].mean()})
slices = pd.DataFrame(rows).sort_values("recall")
print(f"overall mean recall {recall.mean():.3f}")
print("three 'worst' slices found by searching:")
print(slices.head(3).to_string(index=False, float_format=lambda v: f"{v:.3f}"))

# How unusual is that minimum if nothing is going on? Re-draw the whole search many times.
minima = []
for _ in range(2000):
    r = rng.binomial(n_events, 0.80, size=n_machines) / n_events
    a = rng.integers(0, 2, size=(n_machines, n_attributes)).astype(bool)
    best = min(min(r[a[:, j]].mean(), r[~a[:, j]].mean()) for j in range(n_attributes))
    minima.append(best)
minima = np.array(minima)
observed = slices["recall"].iloc[0]
print(f"\nminimum slice recall under 'no real slice effect': median {np.median(minima):.3f}, "
      f"5th percentile {np.quantile(minima, 0.05):.3f}")
print(f"observed minimum {observed:.3f} -> fraction of null searches at least this low: "
      f"{(minima <= observed).mean():.2f}")

# The honest follow-up: test the hunted slice on machines that were not used to find it.
fresh = rng.binomial(n_events, 0.80, size=n_machines) / n_events
fresh_attr = rng.integers(0, 2, size=n_machines).astype(bool)
print(f"same slice definition on 24 fresh machines: recall {fresh[fresh_attr].mean():.3f} "
      f"vs rest {fresh[~fresh_attr].mean():.3f}")
