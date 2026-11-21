"""Worked example for w2d4: the unit of splitting decides what your estimate means.

SYNTHETIC data (generated below). It demonstrates mechanisms; the sizes of the effects are
properties of this simulation, not of any real equipment.

    python lessons/w2d4_problem_framing_splits/example/split_unit_demo.py

Part 1  row-level vs machine-level split vs the truth (brand-new machines)
Part 2  "the seed is the split" breaks when the list of machines changes
Part 3  a manifest is data: it can be hashed, diffed and validated
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split

N_FEATURES = 6


def simulate(n_machines: int, windows: int, rng: np.random.Generator, first_id: int = 0):
    """Each machine has a sensor 'fingerprint' (visible in X) and its own fault propensity (not in X)."""
    X, y, g = [], [], []
    for m in range(n_machines):
        fingerprint = rng.normal(0, 2.0, N_FEATURES)        # identifies the machine
        propensity = rng.normal(0, 2.0)                      # machine-level effect on the label
        x_signal = rng.normal(0, 1.0, windows)               # the genuinely transferable signal
        noise = rng.normal(0, 1.0, (windows, N_FEATURES))
        feats = fingerprint + noise
        feats[:, 0] += x_signal
        p = 1 / (1 + np.exp(-(1.0 * x_signal + propensity)))
        X.append(feats); y.append(rng.random(windows) < p); g.append(np.full(windows, first_id + m))
    return np.vstack(X), np.concatenate(y).astype(int), np.concatenate(g)


def fit_auc(X_tr, y_tr, X_te, y_te) -> float:
    model = RandomForestClassifier(n_estimators=200, min_samples_leaf=5, random_state=0, n_jobs=1)
    return roc_auc_score(y_te, model.fit(X_tr, y_tr).predict_proba(X_te)[:, 1])


def part1() -> None:
    rng = np.random.default_rng(0)
    X, y, g = simulate(24, 200, rng)
    X_new, y_new, _ = simulate(200, 50, rng, first_id=1000)   # the deployment population

    row_aucs, grp_aucs = [], []
    for seed in range(5):
        tr, te = train_test_split(np.arange(len(y)), test_size=0.25, random_state=seed)
        row_aucs.append(fit_auc(X[tr], y[tr], X[te], y[te]))
        tr, te = next(GroupShuffleSplit(1, test_size=0.25, random_state=seed).split(X, y, g))
        grp_aucs.append(fit_auc(X[tr], y[tr], X[te], y[te]))
    truth = fit_auc(X, y, X_new, y_new)
    print("Part 1: what does each split estimate?  (ROC AUC, 5 split seeds)")
    print(f"  row-level split      mean {np.mean(row_aucs):.3f}   range {min(row_aucs):.3f}-{max(row_aucs):.3f}")
    print(f"  machine-level split  mean {np.mean(grp_aucs):.3f}   range {min(grp_aucs):.3f}-{max(grp_aucs):.3f}")
    print(f"  truth: 200 new machines   {truth:.3f}")


def part2() -> None:
    def test_ids(ids):
        ids = np.array(ids)
        _, te = next(GroupShuffleSplit(1, test_size=0.25, random_state=0).split(ids, groups=ids))
        return set(ids[te].tolist())

    before = test_ids([f"M{i:02d}" for i in range(24)])
    after = test_ids([f"M{i:02d}" for i in range(25)])        # one machine was commissioned
    moved_out = sorted(before - after)
    print("\nPart 2: same code, same random_state=0, one extra machine in the list")
    print(f"  test set before: {len(before)} machines; after: {len(after)} machines")
    print(f"  machines that were test and are now training data: {len(moved_out)} -> {moved_out}")


def part3() -> None:
    manifest = {"version": "v1", "unit": "machine_id", "test": [f"M{i:02d}" for i in (3, 8, 11, 17, 20, 22)]}
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    print("\nPart 3: a manifest is data")
    print(f"  sha256 of the manifest text: {hashlib.sha256(text.encode()).hexdigest()[:16]}")
    print("  adding machine M24 to the fleet changes this file by: nothing (M24 is simply unassigned,")
    print("  and validation fails loudly until someone decides where it goes)")


if __name__ == "__main__":
    part1()
    part2()
    part3()
