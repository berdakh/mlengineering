"""Worked example (REAL data, SKAB): where should reference statistics come from, and how much
does a centred window flatter an offline evaluation?

    python project/get_skab.py                                            # once
    python lessons/w2d5_feature_pipeline/example/centred_vs_causal_skab.py

Score = largest absolute z-score, over the eight sensors, of a rolling mean. Two choices of the
reference used for the z-scores are compared:

  A  "anomaly-free":  the separate fault-free recording shipped with SKAB
  B  "other experiments": the normal-labelled rows of the OTHER 33 labelled experiments
     (leave-one-experiment-out, so no row of the scored experiment touches its own statistics)

The script is self-contained (plain pandas) so it runs before you have written the lab code.
It is a diagnostic comparison on all 34 labelled experiments, not a model evaluation: nothing is
tuned here, and these numbers must not be quoted as detector performance.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

RAW = Path(__file__).resolve().parents[3] / "data" / "raw" / "skab"
SENSORS = ["Accelerometer1RMS", "Accelerometer2RMS", "Current", "Pressure", "Temperature",
           "Thermocouple", "Voltage", "Volume Flow RateRMS"]


def rolling_mean(df: pd.DataFrame, w: int, center: bool) -> pd.DataFrame:
    return df[SENSORS].rolling(w, min_periods=w, center=center).mean()


def main() -> None:
    if not RAW.is_dir():
        sys.exit("data/raw/skab is missing. Run:  python project/get_skab.py")
    reference = pd.read_csv(RAW / "anomaly-free" / "anomaly-free.csv", sep=";")
    paths = sorted(p for p in RAW.glob("*/*.csv") if p.parent.name != "anomaly-free")
    experiments = [pd.read_csv(p, sep=";") for p in paths]
    print(f"{len(experiments)} labelled experiments; fault-free reference rows: {len(reference)}\n")

    print("1) How far is the NORMAL part of each labelled experiment from the fault-free recording?")
    print("   (mean of the experiment's normal rows, in reference standard deviations; median over experiments)")
    shift = pd.DataFrame([(e.loc[e["anomaly"] == 0, SENSORS].mean() - reference[SENSORS].mean())
                          / reference[SENSORS].std() for e in experiments])
    for sensor in SENSORS:
        print(f"   {sensor:<22} median {shift[sensor].median():>7.1f}   range {shift[sensor].min():>7.1f} .. {shift[sensor].max():>6.1f}")

    print("\n2) Pooled point-level average precision of the max-|z| score (prevalence "
          f"{np.mean(np.concatenate([e['anomaly'] for e in experiments])):.3f})")
    print(f"{'w':>4} {'window':>8} {'A anomaly-free':>15} {'B other experiments':>20}")
    for w in (10, 30, 60):
        for center in (False, True):
            rolled = [rolling_mean(e, w, center) for e in experiments]
            ref_rolled = rolling_mean(reference, w, center)
            result = {}
            for name in ("A", "B"):
                scores, labels = [], []
                for i, (e, m) in enumerate(zip(experiments, rolled)):
                    if name == "A":
                        basis = ref_rolled
                    else:
                        basis = pd.concat([r[x["anomaly"] == 0] for j, (x, r) in
                                           enumerate(zip(experiments, rolled)) if j != i])
                    score = ((m - basis.mean()) / basis.std()).abs().max(axis=1)
                    keep = score.notna().to_numpy()
                    scores.append(score[keep].to_numpy())
                    labels.append(e["anomaly"][keep].to_numpy())
                result[name] = average_precision_score(np.concatenate(labels), np.concatenate(scores))
            print(f"{w:>4} {'centred' if center else 'causal':>8} {result['A']:>15.3f} {result['B']:>20.3f}")


if __name__ == "__main__":
    main()
