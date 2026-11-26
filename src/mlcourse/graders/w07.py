"""Week 7 graders: trees and ensembles (25), uncertainty (26), error analysis (27), project milestone 1 (28).

Functions are run on small hand-made inputs and on freshly generated synthetic data (a different seed from the
notebook), and compared with reference results computed here. Model configurations are cloned and re-trained on
new data. The project graders use small synthetic sensor frames, so grading never needs the SKAB download; the
final project numbers are checked against loose ranges measured on the real data.
"""
from __future__ import annotations

import math
import time
from functools import lru_cache

import numpy as np
import pandas as pd

from mlcourse.grader import exercise, register_quiz

# ----------------------------------------------------------------------------- shared helpers


def _auc(y, s) -> float:
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, s))


@lru_cache(maxsize=None)
def _fresh_deliveries():
    """A delivery dataset the student has not seen (different seed and size), split by courier."""
    from mlcourse.datasets_w07 import make_deliveries, split_by_courier, to_matrix
    df = make_deliveries(n=4000, n_couriers=70, seed=11)
    tr, va, te = split_by_courier(df, seed=11)
    return to_matrix(tr), tr["late"], to_matrix(va), va["late"], to_matrix(te), te["late"]


def _is_fitted(model) -> bool:
    return any(k.endswith("_") and not k.startswith("_") for k in vars(model))


def _close(a, b, tol=1e-9) -> bool:
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


# ============================================================================= 25: trees and ensembles


def _ref_gini(y):
    y = np.asarray(y)
    if len(y) == 0:
        return 0.0
    p = y.mean()
    return 2 * p * (1 - p)


@exercise("w07.gini", hint="p is the fraction of 1s; Gini = 2p(1-p). Handle the empty array first.")
def _(fn):
    cases = [([0, 0, 1, 1], 0.5), ([1, 1, 1], 0.0), ([0, 0, 0, 0, 0], 0.0), ([0, 1, 1, 1], 0.375),
             (np.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0]), 0.18)]
    for y, want in cases:
        got = fn(y)
        assert isinstance(got, (float, np.floating)), f"gini should return a float, got {type(got).__name__}"
        assert _close(got, want), f"gini({list(np.asarray(y))}) should be {want}, got {round(float(got), 4)}"
    got = fn(np.array([], dtype=int))
    assert got is not None and _close(got, 0.0), "gini of an empty array should be 0.0"


def _ref_best_split(x, y):
    x, y = np.asarray(x, dtype=float), np.asarray(y)
    best_t, best = None, _ref_gini(y)
    n = len(y)
    for t in np.unique(x)[:-1]:
        left = x <= t
        s = left.sum() / n * _ref_gini(y[left]) + (~left).sum() / n * _ref_gini(y[~left])
        if best_t is None or s < best - 1e-12:
            best_t, best = float(t), float(s)
    return best_t, best


@exercise("w07.best_split", hint="Loop over np.unique(x); skip thresholds that leave a side empty; weight each "
                                 "child's Gini by its share of rows.")
def _(fn):
    rng = np.random.default_rng(7)
    cases = [([1, 2, 3, 10, 11, 12], [0, 0, 0, 1, 1, 1]),
             ([5, 5, 5, 5], [0, 1, 0, 1]),                       # no split possible
             ([1, 2, 3, 4], [0, 1, 0, 1]),                       # ties between thresholds
             ([3, 1, 2, 2, 7, 7, 9], [1, 0, 0, 1, 1, 1, 0])]     # unsorted, repeated values
    for _ in range(6):
        n = int(rng.integers(5, 40))
        cases.append((rng.integers(0, 8, n).astype(float), rng.integers(0, 2, n)))
    for x, y in cases:
        want_t, want_s = _ref_best_split(x, y)
        got = fn(x, y)
        assert isinstance(got, tuple) and len(got) == 2, "best_split should return a tuple (threshold, score)"
        t, s = got
        if want_t is None:
            assert t is None, f"for x={list(x)} every value is equal, so no split is possible: expected (None, ...)"
        else:
            assert t is not None and _close(t, want_t), (
                f"for x={list(np.asarray(x))}, y={list(np.asarray(y))} the best threshold is not {t} "
                "(are you keeping the smallest threshold on ties, and using x <= t for the left side?)")
        assert _close(s, want_s), f"for x={list(np.asarray(x))} the weighted Gini should be {round(want_s, 4)}, got {s}"


@exercise("w07.depth_curve", hint="One DecisionTreeClassifier(max_depth=d, random_state=0) per depth; "
                                  "roc_auc_score on predict_proba(...)[:, 1].")
def _(fn):
    from sklearn.tree import DecisionTreeClassifier
    Xtr, ytr, Xva, yva, _, _ = _fresh_deliveries()
    depths = [3, 1, None, 6]
    got = fn(Xtr, ytr, Xva, yva, depths)
    assert isinstance(got, pd.DataFrame), "depth_curve should return a DataFrame"
    for col in ["depth", "train_auc", "valid_auc"]:
        assert col in got.columns, f"the table needs a column '{col}'"
    assert len(got) == len(depths), f"expected one row per depth ({len(depths)} rows), got {len(got)}"
    for i, d in enumerate(depths):
        tree = DecisionTreeClassifier(max_depth=d, random_state=0).fit(Xtr, ytr)
        tr, va = _auc(ytr, tree.predict_proba(Xtr)[:, 1]), _auc(yva, tree.predict_proba(Xva)[:, 1])
        row = got.iloc[i]
        same_depth = (row["depth"] is None or (isinstance(row["depth"], float) and math.isnan(row["depth"]))) \
            if d is None else row["depth"] == d
        assert same_depth, f"row {i} should be depth {d} (keep the order of `depths`)"
        assert abs(row["train_auc"] - tr) < 1e-6, f"train_auc for depth {d} is wrong (is it measured on the training rows?)"
        assert abs(row["valid_auc"] - va) < 1e-6, f"valid_auc for depth {d} is wrong (is it measured on the validation rows?)"


@exercise("w07.pick_depth", hint="Find the best valid_auc, keep the rows within 0.005 of it, return the smallest "
                                 "real depth among them (None only if it is the only one).")
def _(fn):
    def t(depths, aucs):
        return pd.DataFrame({"depth": pd.Series(depths, dtype=object), "train_auc": 0.9, "valid_auc": aucs})
    cases = [
        (t([1, 2, 4, 8], [0.70, 0.76, 0.78, 0.72]), 4),
        (t([1, 2, 4, 8], [0.70, 0.778, 0.78, 0.72]), 2),          # within tolerance: smaller wins
        (t([8, 4, 2, 1], [0.72, 0.78, 0.778, 0.70]), 2),          # unsorted input
        (t([2, 6, None], [0.70, 0.70, 0.80]), None),               # unlimited really is best
        (t([2, 6, None], [0.70, 0.797, 0.80]), 6),                 # a real depth is as good
        (t([3], [0.5]), 3),
    ]
    for curve, want in cases:
        got = fn(curve.copy())
        assert got == want, (f"for depths {list(curve.depth)} with valid_auc {list(curve.valid_auc)} the answer "
                             f"should not be {got}")


@exercise("w07.forest_proba", hint="np.mean over [tree.predict_proba(np.asarray(X))[:, 1] for tree in "
                                   "forest.estimators_], axis=0.")
def _(fn):
    from sklearn.ensemble import RandomForestClassifier
    Xtr, ytr, Xva, _, _, _ = _fresh_deliveries()
    for n, leaf in [(15, 1), (7, 30)]:
        forest = RandomForestClassifier(n_estimators=n, min_samples_leaf=leaf, random_state=3).fit(Xtr, ytr)
        got = np.asarray(fn(forest, Xva.iloc[:200]))
        assert got.shape == (200,), f"expected a 1-D array with one probability per row, got shape {got.shape}"
        assert np.allclose(got, forest.predict_proba(Xva.iloc[:200])[:, 1]), (
            "your average differs from the forest's own predict_proba: average the class-1 probability of every tree")


def _check_config(model, cls_name: str):
    from sklearn.base import clone
    assert model is not None, "create the model first"
    assert type(model).__name__ == cls_name, f"expected a {cls_name}, got {type(model).__name__}"
    assert not _is_fitted(model), "give the grader an unfitted model (do not call .fit on it)"
    assert model.get_params().get("random_state") == 0, "set random_state=0 so results are reproducible"
    m = clone(model)
    if "n_jobs" in m.get_params():
        m.set_params(n_jobs=-1)
    Xtr, ytr, Xva, yva, _, _ = _fresh_deliveries()
    m.fit(Xtr, ytr)
    tr, va = _auc(ytr, m.predict_proba(Xtr)[:, 1]), _auc(yva, m.predict_proba(Xva)[:, 1])
    return m, tr, va


@exercise("w07.rf_model", hint="RandomForestClassifier(n_estimators=300, min_samples_leaf=..., random_state=0); "
                               "try a few leaf sizes on the validation couriers.")
def _(model):
    if model is None:
        raise NotImplementedError
    assert getattr(model, "n_estimators", 0) >= 100, "use at least 100 trees"
    _, tr, va = _check_config(model, "RandomForestClassifier")
    assert va >= 0.78, f"on new data your forest reaches validation AUC {va:.3f}; at least 0.78 is needed"
    assert tr - va < 0.12, (f"training AUC {tr:.3f} vs validation {va:.3f}: a gap of {tr - va:.2f} means the trees "
                            "still memorise the training rows")


@exercise("w07.boost_stumps", hint="pred starts at y.mean(); each round fits DecisionTreeRegressor(max_depth=1) to "
                                   "y - pred and adds learning_rate * its predictions.")
def _(fn):
    from sklearn.tree import DecisionTreeRegressor

    def ref(x, y, n, lr):
        x, y = np.asarray(x, float), np.asarray(y, float)
        pred = np.full(len(y), y.mean())
        for _ in range(n):
            pred = pred + lr * DecisionTreeRegressor(max_depth=1).fit(x.reshape(-1, 1), y - pred).predict(x.reshape(-1, 1))
        return pred
    rng = np.random.default_rng(5)
    x = np.sort(rng.uniform(0, 10, 80))
    y = np.where(x > 4, 3.0, 0.0) + np.sin(x) + rng.normal(0, 0.2, 80)
    got0 = np.asarray(fn(x, y, 0, 0.1), float)
    assert got0.shape == y.shape and np.allclose(got0, y.mean()), "with 0 rounds every prediction should be the mean of y"
    for n, lr in [(1, 1.0), (5, 0.3), (40, 0.1)]:
        got = np.asarray(fn(x, y, n, lr), float)
        assert got.shape == y.shape, f"expected {len(y)} predictions, got shape {got.shape}"
        assert np.allclose(got, ref(x, y, n, lr), atol=1e-8), (
            f"with {n} rounds and learning rate {lr} your predictions differ from boosting on the residuals")
    mse = [np.mean((y - np.asarray(fn(x, y, n, 0.3))) ** 2) for n in (0, 5, 50)]
    assert mse[0] > mse[1] > mse[2], "training error should go down as rounds are added"


@exercise("w07.hgb_model", hint="HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=1000, "
                                "early_stopping=True, n_iter_no_change=20, random_state=0).")
def _(model):
    if model is None:
        raise NotImplementedError
    assert model.get_params().get("early_stopping") is True, "switch early stopping on with early_stopping=True"
    m, tr, va = _check_config(model, "HistGradientBoostingClassifier")
    assert m.n_iter_ < m.max_iter, (f"the model used all {m.max_iter} trees, so early stopping never stopped it: "
                                    "raise max_iter or lower the patience")
    assert va >= 0.78, f"on new data your model reaches validation AUC {va:.3f}; at least 0.78 is needed"
    assert tr - va < 0.12, f"training AUC {tr:.3f} vs validation {va:.3f}: the model overfits (smaller trees?)"


@exercise("w07.permutation_drop", hint="Copy X, shuffle one column with np.random.default_rng(seed).permutation, "
                                       "and subtract the shuffled AUC from the original AUC.")
def _(fn):
    from sklearn.linear_model import LogisticRegression
    Xtr, ytr, Xva, yva, _, _ = _fresh_deliveries()
    model = LogisticRegression(max_iter=2000).fit(Xtr, ytr)
    X = Xva.copy()
    before = X.copy()
    base = _auc(yva, model.predict_proba(X)[:, 1])
    for col, seed in [("distance_km", 0), ("distance_km", 4), ("tracking_noise", 1), ("hour", 2)]:
        got = fn(model, X, yva, col, seed=seed)
        Xs = X.copy()
        Xs[col] = np.random.default_rng(seed).permutation(Xs[col].to_numpy())
        want = base - _auc(yva, model.predict_proba(Xs)[:, 1])
        assert X.equals(before), "your function changed X: shuffle a copy"
        assert isinstance(got, (float, np.floating)), "return the drop as a float"
        assert abs(got - want) < 1e-9, (f"for column '{col}' (seed {seed}) the drop should be {want:.4f}, got "
                                        f"{float(got):.4f} (baseline AUC minus shuffled AUC, same seed?)")


@exercise("w07.misleading_features", hint="Boolean mask (impurity >= high) & (permutation <= useless); "
                                          "return sorted(table.index[mask]).")
def _(fn):
    table = pd.DataFrame({"impurity": [0.30, 0.18, 0.12, 0.04, 0.06, 0.05],
                          "permutation": [0.16, 0.001, 0.04, -0.01, 0.005, 0.0051]},
                         index=["distance", "noise", "hour", "region", "id_like", "edge"])
    got = fn(table)
    assert isinstance(got, list), "return a list of feature names"
    assert got == ["id_like", "noise"], f"expected exactly the features that look important but are useless; got {got}"
    assert fn(table, high=0.2) == [], "with high=0.2 no feature qualifies (distance is useful)"
    assert fn(table, useless=0.05) == ["edge", "hour", "id_like", "noise"], "the thresholds `high` and `useless` must be used"
    assert fn(table.iloc[:0]) == [], "an empty table should give an empty list"


@exercise("w07.simplest_good_enough", hint="best = max(scores.values()); walk through `order` and return the first "
                                           "name with score >= best - tolerance.")
def _(fn):
    order = ["logistic", "forest", "boosting"]
    cases = [({"logistic": 0.746, "forest": 0.793, "boosting": 0.792}, order, 0.01, "forest"),
             ({"logistic": 0.801, "forest": 0.806, "boosting": 0.805}, order, 0.01, "logistic"),
             ({"logistic": 0.801, "forest": 0.806, "boosting": 0.805}, order, 0.001, "forest"),
             ({"logistic": 0.70, "forest": 0.70, "boosting": 0.80}, order, 0.05, "boosting"),
             ({"b": 0.5, "a": 0.9}, ["a", "b"], 0.0, "a"),
             ({"logistic": 0.801, "forest": 0.806, "boosting": 0.805}, list(reversed(order)), 0.01, "boosting")]
    for scores, o, tol, want in cases:
        got = fn(dict(scores), list(o), tolerance=tol)
        assert got == want, f"scores {scores}, order {o}, tolerance {tol}: expected a different model than {got!r}"


register_quiz("w07.25_q1", "b",
              "The tree memorises training rows; limiting depth or leaf size and choosing the limit on validation "
              "data is the fix, and the test set stays untouched.",
              {"a": "A forest helps, but the question is what to do with this tree; and forests of unlimited trees "
                    "still need sensible leaf sizes on small data.",
               "c": "Training AUC says nothing about new data; a 0.37 gap is overfitting, not bad luck.",
               "d": "Tuning on the test set turns it into a validation set: your final number becomes optimistic."})
register_quiz("w07.25_q2", "c",
              "Each deep tree has low bias but high variance; bootstrap samples and random feature subsets make their "
              "errors differ, and averaging cancels much of the variance.",
              {"a": "Forest trees are usually grown deep, not shallow; the gain comes from averaging.",
               "b": "A forest never sees the test set.",
               "d": "Forests can still split on noise features (section 5 shows one ranked second)."})
register_quiz("w07.25_q3", "a",
              "A smaller step means each tree corrects less, so more trees are needed; with early stopping that "
              "usually gives a slightly better and smoother fit.",
              {"b": "Tree size is set by max_depth / max_leaf_nodes, not by the learning rate.",
               "c": "Early stopping decides when to stop; the learning rate still decides how big each step is.",
               "d": "Boosting stays sequential; a forest averages independent trees."})
register_quiz("w07.25_q4", "b",
              "Impurity importance is measured on training data and favours columns with many distinct values. Check "
              "permutation importance on held-out data, and question whether an ID belongs in the model.",
              {"a": "That is the trap: the ranking may reflect memorised training noise, not a driver.",
               "c": "Nothing here suggests a broken model, and random_state does not cause this.",
               "d": "Permutation importance on validation data typically shows an ID near zero."})
register_quiz("w07.25_q5", "c",
              "The rule was fixed in advance: take the simplest model within the tolerance of the best. 0.801 is "
              "within 0.01 of 0.806.",
              {"a": "A 0.005 difference is inside the agreed tolerance; picking the larger number ignores the rule "
                    "(and, as notebook 26 shows, probably the noise).",
               "b": "Both models are usable; the rule tells you which one to ship.",
               "d": "Choosing on the test set makes the test score optimistic."})


# ============================================================================= 26: uncertainty and comparisons


@exercise("w07.binomial_se", hint="np.sqrt(p * (1 - p) / n).")
def _(fn):
    for p, n in [(0.805, 1217), (0.5, 100), (0.9, 10_000), (0.0, 50), (1.0, 3)]:
        got = fn(p, n)
        want = math.sqrt(p * (1 - p) / n)
        assert got is not None and _close(got, want), f"binomial_se({p}, {n}) should be {want:.5f}, got {got}"


@exercise("w07.normal_interval", hint="se = binomial_se(p, n); return (max(0, p - z*se), min(1, p + z*se)).")
def _(fn):
    for p, n, z in [(0.805, 1217, 1.96), (0.5, 100, 1.96), (0.7, 400, 2.576), (0.99, 10, 1.96), (0.02, 20, 1.96)]:
        se = math.sqrt(p * (1 - p) / n)
        want = (max(0.0, p - z * se), min(1.0, p + z * se))
        got = fn(p, n, z=z) if z != 1.96 else fn(p, n)
        assert isinstance(got, tuple) and len(got) == 2, "return a tuple (low, high)"
        assert _close(got[0], want[0]) and _close(got[1], want[1]), (
            f"normal_interval({p}, {n}, z={z}) should be ({want[0]:.4f}, {want[1]:.4f}), got "
            f"({float(got[0]):.4f}, {float(got[1]):.4f})" + (" - remember to clip to [0, 1]" if p in (0.99, 0.02) else ""))


def _spy_rows(n):
    """Labels and scores that encode the row position, and a metric that checks rows stay aligned."""
    y = np.arange(n) % 2
    s = np.arange(n) / n
    calls = []

    def metric(yy, ss):
        yy, ss = np.asarray(yy), np.asarray(ss)
        assert len(yy) == len(ss), "y and s were resampled to different lengths"
        pos = np.rint(ss * n).astype(int)
        assert np.array_equal(pos % 2, yy), "y and s must be resampled with the SAME positions (pairs broke apart)"
        calls.append(len(yy))
        return float(ss.mean())
    return y, s, metric, calls


@exercise("w07.bootstrap_rows", hint="rng = np.random.default_rng(seed); idx = rng.integers(0, n, n); "
                                     "out[b] = metric(y[idx], s[idx]).")
def _(fn):
    n = 400
    y, s, metric, calls = _spy_rows(n)
    out = np.asarray(fn(y, s, metric, n_boot=300, seed=0), float)
    assert out.shape == (300,), f"expected an array of n_boot=300 values, got shape {out.shape}"
    assert set(calls) == {n}, f"each resample must have the same size as the test set ({n} rows)"
    assert np.array_equal(out, np.asarray(fn(y, s, metric, n_boot=300, seed=0), float)), \
        "the same seed must give the same replicates (use np.random.default_rng(seed))"
    assert not np.array_equal(out, np.asarray(fn(y, s, metric, n_boot=300, seed=1), float)), \
        "different seeds should give different replicates"
    assert len(np.unique(out)) > 250, "the replicates barely vary: are you drawing WITH replacement?"
    se_true = s.std() / math.sqrt(n)            # standard error of a mean, known in closed form
    assert abs(out.mean() - s.mean()) < 3 * se_true, "the replicates should centre on the full-sample metric"
    assert 0.75 * se_true < out.std() < 1.3 * se_true, (
        f"the spread of your replicates ({out.std():.4f}) does not match a bootstrap of rows ({se_true:.4f})")


@exercise("w07.percentile_interval", hint="np.percentile(replicates, [(1-level)/2*100, (1+level)/2*100]).")
def _(fn):
    rng = np.random.default_rng(3)
    for reps, level in [(rng.normal(0.8, 0.02, 1000), 0.95), (rng.uniform(0, 1, 501), 0.9), (np.arange(101.0), 0.5)]:
        a = (1 - level) / 2 * 100
        want = np.percentile(reps, [a, 100 - a])
        got = fn(reps, level=level) if level != 0.95 else fn(reps)
        assert isinstance(got, tuple) and len(got) == 2, "return a tuple (low, high)"
        assert _close(got[0], want[0]) and _close(got[1], want[1]), (
            f"for level={level} the interval should be ({want[0]:.4f}, {want[1]:.4f}), got ({got[0]}, {got[1]})")


def _spy_groups():
    """Groups of different sizes; the score encodes the group; the metric checks groups arrive whole."""
    sizes = {"g1": 3, "g2": 7, "g3": 1, "g4": 12, "g5": 5, "g6": 9}
    gid = {g: i for i, g in enumerate(sizes)}
    groups = np.array([g for g, k in sizes.items() for _ in range(k)])
    rng = np.random.default_rng(0)
    order = rng.permutation(len(groups))          # interleave the groups, as in real data
    groups = groups[order]
    s = np.array([gid[g] for g in groups], float)
    y = (s % 2 == 0).astype(int)
    level = {g: (i * 1.7) % 5 for g, i in gid.items()}   # between-group differences
    calls = []

    def metric(yy, ss):
        ss = np.asarray(ss)
        counts = pd.Series(ss).value_counts()
        for v, c in counts.items():
            size = list(sizes.values())[int(v)]
            assert c % size == 0, "a group was split apart: every drawn group must bring ALL of its rows"
        drawn = sum(c // list(sizes.values())[int(v)] for v, c in counts.items())
        calls.append(drawn)
        return float(np.mean([level[list(sizes)[int(v)]] for v in ss]))
    return y, s, groups, metric, calls


@exercise("w07.bootstrap_groups", hint="unique = np.unique(groups); positions per group; each replicate: "
                                       "rng.choice(unique, size=len(unique), replace=True), concatenate positions.")
def _(fn):
    y, s, groups, metric, calls = _spy_groups()
    out = np.asarray(fn(y, s, groups, metric, n_boot=400, seed=0), float)
    assert out.shape == (400,), f"expected n_boot=400 values, got shape {out.shape}"
    assert set(calls) == {6}, "each replicate should draw as many groups as there are distinct groups (6)"
    assert np.array_equal(out, np.asarray(fn(y, s, groups, metric, n_boot=400, seed=0), float)), \
        "the same seed must give the same replicates"
    assert len(np.unique(out)) > 50, "the replicates barely vary: draw groups WITH replacement"
    # string, integer and unsorted group labels must all work
    _, _, g2, _, _ = _spy_groups()
    out2 = np.asarray(fn(y, s, pd.Series(g2).str[1:].astype(int).to_numpy(), metric, n_boot=50, seed=2), float)
    assert out2.shape == (50,), "integer group labels should work too"


def _ref_group_boot(y, s, groups, metric, n_boot, seed):
    rng = np.random.default_rng(seed)
    unique = np.unique(groups)
    pos = {g: np.flatnonzero(groups == g) for g in unique}
    out = np.empty(n_boot)
    for b in range(n_boot):
        idx = np.concatenate([pos[g] for g in rng.choice(unique, size=len(unique), replace=True)])
        out[b] = metric(y[idx], s[idx])
    return out


@lru_cache(maxsize=None)
def _small_grouped_scores():
    rng = np.random.default_rng(21)
    groups = np.repeat(np.arange(14), rng.integers(20, 60, 14))
    effect = rng.normal(0, 0.8, 14)[groups]
    x = rng.normal(size=len(groups))
    y = (rng.random(len(groups)) < 1 / (1 + np.exp(-(x + effect)))).astype(int)
    return y, x + rng.normal(0, 0.8, len(x)), x + rng.normal(0, 1.2, len(x)), groups


@exercise("w07.results_table", hint="For each (name, s): auc on the full arrays, then percentile_interval of "
                                    "bootstrap_groups(y, s, groups, roc_auc_score, n_boot, seed).")
def _(fn):
    y, s1, s2, groups = _small_grouped_scores()
    got = fn(y, {"good": s1, "weaker": s2}, groups, n_boot=300, seed=0)
    assert isinstance(got, pd.DataFrame), "return a DataFrame"
    for col in ["model", "auc", "low", "high"]:
        assert col in got.columns, f"the table needs a column '{col}'"
    assert list(got["model"]) == ["good", "weaker"], "one row per model, in the order of the dict"
    for i, s in enumerate([s1, s2]):
        auc = _auc(y, s)
        assert abs(got["auc"].iloc[i] - auc) < 1e-9, "auc should be roc_auc_score on the full test arrays"
        lo, hi = np.percentile(_ref_group_boot(y, s, groups, _auc, 300, 0), [2.5, 97.5])
        assert got["low"].iloc[i] < auc < got["high"].iloc[i], "the interval should contain the full-sample AUC"
        assert abs(got["low"].iloc[i] - lo) < 0.03 and abs(got["high"].iloc[i] - hi) < 0.03, (
            f"the interval for '{got['model'].iloc[i]}' does not look like a GROUP bootstrap interval "
            f"(width {got['high'].iloc[i] - got['low'].iloc[i]:.3f}, expected about {hi - lo:.3f})")


@exercise("w07.paired_difference", hint="Same group resampling as bootstrap_groups; on each resample compute "
                                        "metric for b and for a on the SAME idx, and store b - a.")
def _(fn):
    y, s1, s2, groups = _small_grouped_scores()
    same = np.asarray(fn(y, s2, s2.copy(), groups, _auc, n_boot=100, seed=0), float)
    assert same.shape == (100,), f"expected n_boot=100 differences, got shape {same.shape}"
    assert np.allclose(same, 0), "two identical models must give a difference of exactly 0 on every resample: " \
                                 "use the same resampled rows for both models"
    diffs = np.asarray(fn(y, s2, s1, groups, _auc, n_boot=400, seed=0), float)
    observed = _auc(y, s1) - _auc(y, s2)
    assert abs(diffs.mean() - observed) < 0.02, "the differences should centre on metric(b) - metric(a) (order: b minus a)"
    ref = _ref_group_boot(y, s1, groups, _auc, 400, 1)
    assert diffs.std() < 0.9 * ref.std() + 0.02, "the differences vary too much: are both models scored on the same resample?"
    assert np.array_equal(diffs, np.asarray(fn(y, s2, s1, groups, _auc, n_boot=400, seed=0), float)), \
        "the same seed must give the same differences"
    yy, ss, gg, metric, calls = _spy_groups()
    fn(yy, ss, ss.copy(), gg, metric, n_boot=20, seed=0)
    assert set(calls) == {6}, "resample whole groups, as many as there are distinct groups"


@exercise("w07.verdict", hint="low > 0: B better; high < 0: A better; otherwise no detectable difference.")
def _(fn):
    cases = [((0.054, 0.088, "logistic", "forest"), "forest is better"),
             ((-0.010, 0.014, "boosting", "forest"), "no detectable difference"),
             ((-0.05, -0.001, "a", "b"), "a is better"),
             ((0.0, 0.03, "a", "b"), "no detectable difference"),
             ((-0.02, 0.0, "x", "y"), "no detectable difference")]
    for args, want in cases:
        got = fn(*args)
        assert got == want, f"verdict{args} should be {want!r}, got {got!r}"


@exercise("w07.groups_needed", hint="n_new = n_now * (width_now / target)**2, rounded up with math.ceil.")
def _(fn):
    cases = [((0.024, 16, 0.006), 256), ((0.08, 16, 0.04), 64), ((0.05, 10, 0.06), 10), ((0.1, 10, 0.07), 21),
             ((0.03, 7, 0.03), 7), ((0.09, 9, 0.06), 21)]
    for args, want in cases:
        got = fn(*args)
        assert isinstance(got, (int, np.integer)), "return a whole number (int)"
        assert got == want, f"groups_needed{args} should be {want}, got {got}"


register_quiz("w07.26_q1", "b",
              "The standard error of an accuracy near 0.81 on 1,000 rows is about 0.012; a 0.006 gap is half of that. "
              "Only a paired interval of the difference can say whether it is real.",
              {"a": "The larger number may be luck; one test set is one draw.",
               "c": "Neither number is more stable; they come from the same test set.",
               "d": "1,000 rows is plenty to compute an interval; it is just not enough to separate 0.006."})
register_quiz("w07.26_q2", "d",
              "The evidence about new customers comes from 40 customers, not 5,000 independent rows. Resample whole "
              "customers.",
              {"a": "The bootstrap works for any metric, AUC included.",
               "b": "It is the other way round: treating correlated rows as independent makes the interval too narrow.",
               "c": "There is no such rule; the bootstrap works on small test sets too (with wide intervals)."})
register_quiz("w07.26_q3", "b",
              "Separate intervals ignore that both models saw the same rows. The paired difference cancels the shared "
              "noise and is the correct comparison.",
              {"a": "Overlapping intervals can still hide a consistent, detectable difference.",
               "c": "That is exactly the mistake this notebook is about.",
               "d": "A wider level makes intervals overlap more, and changing it after looking is cherry-picking."})
register_quiz("w07.26_q4", "c",
              "The interval contains 0, so the data cannot tell the models apart; report the interval and decide on "
              "other grounds.",
              {"a": "The point estimate alone hides that the difference could just as well be negative.",
               "b": "Most of the interval is above 0; nothing says A is better either.",
               "d": "No detectable difference is not the same as identical; a small difference may exist."})
register_quiz("w07.26_q5", "c",
              "Width scales like 1/sqrt(n): halving the width needs four times the groups, 16 x 4 = 64.",
              {"a": "Doubling the groups shrinks the width only by a factor of sqrt(2), to about 0.057.",
               "b": "That is less than double the groups; the width would barely change.",
               "d": "That would shrink the width to about 0.025, more than needed."})
