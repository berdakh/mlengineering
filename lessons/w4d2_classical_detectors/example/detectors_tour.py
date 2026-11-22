"""Worked example (SYNTHETIC): what T2, Q and an isolation forest each see, and why an isolation
forest's `contamination` is a threshold in disguise.

    python lessons/w4d2_classical_detectors/example/detectors_tour.py

Uses the REFERENCE flowguard.detectors from solutions/ (set DETECTORS_SRC to your lab/src to run it
on your implementation).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "project" / "get_skab.py").is_file())
sys.path.insert(0, os.environ.get("DETECTORS_SRC",
                                  str(ROOT / "solutions" / "lessons" / "w4d2_classical_detectors" / "lab" / "src")))

from flowguard.detectors import GBTDetector, IForestDetector, PCADetector  # noqa: E402


def normal_plant(n, rng):
    """Six sensors driven by two hidden factors (load, temperature) plus small sensor noise."""
    load, temp = rng.standard_normal(n), rng.standard_normal(n)
    mix = np.array([[1.0, 0.0], [0.9, 0.2], [0.8, -0.1], [0.0, 1.0], [0.1, 0.9], [0.5, 0.5]])
    x = np.column_stack([load, temp]) @ mix.T + 0.15 * rng.standard_normal((n, 6))
    return pd.DataFrame(x, columns=[f"s{i}" for i in range(1, 7)])


def main() -> None:
    rng = np.random.default_rng(0)
    train = normal_plant(5000, rng)
    normal_test = normal_plant(1000, rng)

    # fault A: an extreme but CONSISTENT operating point (high load): every sensor follows the factors
    a = normal_plant(200, rng)
    a[["s1", "s2", "s3"]] += 3.0 * np.array([1.0, 0.9, 0.8])
    a["s6"] += 1.5
    # fault B: one sensor drifts away from what the factors predict (a broken relationship), small size
    b = normal_plant(200, rng)
    b["s2"] += 1.0

    pca = PCADetector(variance=0.9).fit(train)
    print(f"1. PCA on 6 sensors driven by 2 factors: k = {pca.k_} components keep "
          f">= 90% of the variance; 99% limits: T2 {pca.t2_limit_:.1f}, Q {pca.q_limit_:.2f}")
    for name, fault in (("A (extreme but consistent)", a), ("B (broken relationship)", b)):
        t2_rate = np.mean(pca.score_t2(fault) > pca.t2_limit_)
        q_rate = np.mean(pca.score_q(fault) > pca.q_limit_)
        print(f"   fault {name:<28} rows above the T2 limit {t2_rate:5.1%}   above the Q limit {q_rate:5.1%}")
    print(f"   normal test rows above the limits: T2 {np.mean(pca.score_t2(normal_test) > pca.t2_limit_):.1%}, "
          f"Q {np.mean(pca.score_q(normal_test) > pca.q_limit_):.1%}")

    probe = pd.concat([normal_test, a, b], ignore_index=True)
    y = np.r_[np.zeros(len(normal_test)), np.ones(len(a) + len(b))]
    kinds = np.r_[np.zeros(len(normal_test)), np.ones(len(a)), 2 * np.ones(len(b))]
    print("\n2. ROC AUC against the normal test rows, per fault type")
    scorers = {"PCA T2": pca.score_t2, "PCA Q": pca.score_q,
               "isolation forest": IForestDetector(seed=0).fit(train).score}
    for name, fn in scorers.items():
        s = fn(probe)
        aucs = [roc_auc_score(np.r_[np.zeros(1000), np.ones(200)], np.r_[s[kinds == 0], s[kinds == k]]) for k in (1, 2)]
        print(f"   {name:<17} fault A {aucs[0]:.3f}   fault B {aucs[1]:.3f}")

    print("\n3. `contamination` only moves the threshold of predict(); the scores do not change")
    for c in (0.01, 0.05, 0.2):
        m = IsolationForest(n_estimators=200, contamination=c, random_state=0).fit(train)
        flagged = np.mean(m.predict(probe) == -1)
        print(f"   contamination {c:<4}: share of probe rows flagged {flagged:.1%}; "
              f"first three scores {np.round(m.score_samples(probe.iloc[:3]), 4)}")

    print("\n4. A supervised model trained on fault A only, tested on fault B (a mechanism it never saw)")
    xa = pd.concat([train.iloc[:1000], normal_plant(200, rng).assign(s1=lambda d: d.s1 + 3.0,
                                                                         s2=lambda d: d.s2 + 2.7,
                                                                         s3=lambda d: d.s3 + 2.4,
                                                                         s6=lambda d: d.s6 + 1.5)])
    ya = np.r_[np.zeros(1000), np.ones(200)]
    gbt = GBTDetector(seed=0).fit(xa, ya)
    s = gbt.score(probe)
    for k, name in ((1, "A (seen in training)"), (2, "B (unseen)")):
        auc = roc_auc_score(np.r_[np.zeros(1000), np.ones(200)], np.r_[s[kinds == 0], s[kinds == k]])
        print(f"   GBT on fault {name:<22} ROC AUC {auc:.3f}")


if __name__ == "__main__":
    main()
