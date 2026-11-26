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
    from threadpoolctl import threadpool_limits
    with threadpool_limits(1):          # small data: one thread is much faster than OpenMP start-up costs
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


# ============================================================================= 27: error analysis and model choice


@exercise("w07.add_bands", hint="out = df.copy(); out[f'{column}_band'] = pd.cut(out[column], bins=edges, "
                                "labels=labels, right=False).")
def _(fn):
    df = pd.DataFrame({"distance_km": [0.0, 4.9, 5.0, 11.99, 12.0, 19.5, 20.0, 55.0], "x": range(8)})
    before = df.copy()
    got = fn(df, "distance_km", [0, 5, 12, 20, np.inf], ["0-5", "5-12", "12-20", "20+"])
    assert df.equals(before), "add_bands changed its input: work on a copy"
    assert "distance_km_band" in got.columns, "the new column should be called 'distance_km_band'"
    want = ["0-5", "0-5", "5-12", "5-12", "12-20", "12-20", "20+", "20+"]
    assert [str(v) for v in got["distance_km_band"]] == want, (
        "some values fall in the wrong band: each band includes its left edge and excludes its right edge (right=False)")
    got2 = fn(pd.DataFrame({"hour": [7, 8, 12, 17, 18, 21, 22]}), "hour", [8, 12, 18, 22], ["m", "a", "e"])
    vals = [None if pd.isna(v) else str(v) for v in got2["hour_band"]]
    assert vals == [None, "m", "a", "a", "e", "e", None], "values outside the edges should become missing (NaN)"
    assert len(got) == len(df) and list(got["x"]) == list(df["x"]), "keep every row and every original column"


def _ref_slice(df, by, threshold):
    pred = (df["score"] >= threshold).astype(int)
    rows = {}
    for v, part in df.assign(_p=pred).groupby(by, observed=True, sort=True):
        late, p = part["late"], part["_p"]
        rows[v] = {"n": len(part), "late_rate": late.mean(),
                   "recall": p[late == 1].mean() if (late == 1).any() else np.nan,
                   "precision": late[p == 1].mean() if (p == 1).any() else np.nan,
                   "error_rate": (p != late).mean()}
    return pd.DataFrame.from_dict(rows, orient="index")


def _toy_slices():
    return pd.DataFrame({
        "region": ["n", "n", "n", "n", "s", "s", "s", "e", "e", "w", "w", "w"],
        "late":   [1, 1, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0],
        "score":  [0.9, 0.2, 0.5, 0.1, 0.34, 0.2, 0.1, 0.6, 0.1, 0.35, 0.8, 0.36],
    })


@exercise("w07.slice_metrics", hint="Group by `by`; per group: n = size, late_rate = mean of late, recall among "
                                    "late rows, precision among predicted rows (NaN when there are none).")
def _(fn):
    df = _toy_slices()
    for threshold in (0.35, 0.5):
        got = fn(df.copy(), "region", threshold=threshold) if threshold != 0.35 else fn(df.copy(), "region")
        want = _ref_slice(df, "region", threshold)
        assert isinstance(got, pd.DataFrame), "return a DataFrame"
        for col in ["n", "late_rate", "recall", "precision", "error_rate"]:
            assert col in got.columns, f"the table needs a column '{col}'"
        assert list(got.index) == list(want.index), (f"the index should be the slice values, sorted: {list(want.index)}"
                                                    f" (got {list(got.index)})")
        for col in ["n", "late_rate", "recall", "precision", "error_rate"]:
            a, b = got[col].astype(float).to_numpy(), want[col].astype(float).to_numpy()
            ok = np.isclose(a, b, equal_nan=True)
            if not ok.all():
                i = int(np.argmin(ok))
                hint = ""
                if col == "recall" and np.isnan(b[i]):
                    hint = " (a slice with no late rows has no recall: NaN)"
                elif col == "precision" and np.isnan(b[i]):
                    hint = " (a slice where nothing is predicted late has no precision: NaN)"
                elif threshold == 0.35:
                    hint = " (a score exactly at the threshold counts as predicted late)"
                raise AssertionError(f"with threshold {threshold}, column '{col}' is wrong for slice "
                                     f"'{want.index[i]}'{hint}")


@exercise("w07.worst_slice", hint="Filter n >= min_n and metric not NaN; sort by the metric (direction from "
                                  "higher_is_worse) and by n descending for ties.")
def _(fn):
    t = pd.DataFrame({"n": [325, 579, 231, 74, 12], "recall": [0.35, 0.25, 0.97, 0.95, 0.0],
                      "error_rate": [0.16, 0.21, 0.46, 0.46, 0.5]}, index=["0-5", "5-12", "12-20", "20+", "tiny"])
    assert fn(t) == "5-12", "the lowest recall among slices with at least 50 rows is not that one"
    assert fn(t, min_n=10) == "tiny", "with min_n=10 the tiny slice qualifies"
    assert fn(t, metric="error_rate", higher_is_worse=True) == "12-20", (
        "for error_rate (higher is worse) with a tie between 12-20 and 20+, the larger slice should win")
    assert fn(t, min_n=1000) is None, "when no slice is big enough, return None"
    t2 = t.copy()
    t2.loc["5-12", "recall"] = np.nan
    assert fn(t2) == "0-5", "slices with a missing metric (NaN) should be skipped"


@exercise("w07.top_mistakes", hint="Keep wrong predictions only; error label from the prediction; margin = "
                                   "|score - threshold|; sort by margin descending; head(k).")
def _(fn):
    df = pd.DataFrame({"id": range(8), "late": [1, 0, 1, 0, 1, 0, 1, 0],
                       "score": [0.05, 0.95, 0.30, 0.40, 0.90, 0.10, 0.36, 0.70]})
    before = df.copy()
    got = fn(df, k=3, threshold=0.35)
    assert df.equals(before), "top_mistakes changed its input: work on a copy"
    assert isinstance(got, pd.DataFrame) and len(got) == 3, "return a DataFrame with k=3 rows"
    assert list(got["id"]) == [1, 7, 0], "wrong rows or wrong order: the largest margins first, only wrong predictions"
    assert list(got["error"]) == ["false positive", "false positive", "false negative"], "the `error` labels are wrong"
    assert np.allclose(got["margin"], [0.60, 0.35, 0.30]), "margin should be |score - threshold|"
    allm = fn(df, k=100, threshold=0.35)
    assert sorted(allm["id"]) == [0, 1, 2, 3, 7], "with a large k, return every wrong prediction (and only those)"
    got5 = fn(df, k=2, threshold=0.5)
    assert sorted(got5["id"]) == [0, 1], "the threshold argument must be used"


@exercise("w07.group_residuals", hint="groupby(group): mean of late minus mean of score; sort descending; "
                                      ".rename('residual').")
def _(fn):
    df = pd.DataFrame({"courier_id": [1, 1, 2, 2, 2, 3, 3, 4],
                       "late": [1, 1, 0, 0, 1, 0, 1, 0],
                       "score": [0.2, 0.4, 0.3, 0.3, 0.3, 0.5, 0.5, 0.1]})
    got = fn(df)
    assert isinstance(got, pd.Series), "return a Series"
    assert got.name == "residual", "name the Series 'residual'"
    want = (df.groupby("courier_id")["late"].mean() - df.groupby("courier_id")["score"].mean()).sort_values(ascending=False)
    assert list(got.index) == list(want.index), "sort from the most positive residual to the most negative"
    assert np.allclose(got.to_numpy(), want.to_numpy()), "residual = mean(late) - mean(score) per group"
    got2 = fn(df.rename(columns={"courier_id": "region"}), group="region")
    assert np.allclose(got2.sort_index().to_numpy(), want.sort_index().to_numpy()), "use the `group` argument"


@exercise("w07.measure_latency", hint="Time n_repeats calls with time.perf_counter() for X.iloc[:1] and for X; "
                                      "medians in ms; divide the batch median by len(X).")
def _(fn):
    calls = {"single": 0, "batch": 0}

    def fake_predict(X):
        if len(X) == 1:
            calls["single"] += 1
        else:
            calls["batch"] += 1
        time.sleep(0.004 + 0.0002 * len(X))
    X = pd.DataFrame({"a": range(50)})
    got = fn(fake_predict, X, n_repeats=5)
    assert isinstance(got, dict) and {"single_ms", "batch_ms_per_row"} <= set(got), \
        "return a dict with the keys 'single_ms' and 'batch_ms_per_row'"
    assert calls == {"single": 5, "batch": 5}, f"expected 5 single-row and 5 batch calls, got {calls}"
    assert 3.5 <= got["single_ms"] <= 15, (f"a single call takes about 4.2 ms here, you report {got['single_ms']:.3f}"
                                           " (milliseconds = seconds * 1000)")
    assert 0.25 <= got["batch_ms_per_row"] <= 0.6, (
        f"the batch call takes about 14 ms for 50 rows (0.28 ms per row); you report {got['batch_ms_per_row']:.4f}")


def _cand():
    return pd.DataFrame({"model": ["logistic", "forest", "boosting"], "auc": [0.730, 0.801, 0.798],
                         "diff_low": [-0.088, 0.0, -0.014], "diff_high": [-0.054, 0.0, 0.010],
                         "single_ms": [0.8, 14.0, 2.0], "complexity": [1, 3, 2]})


@exercise("w07.choose_model", hint="ok = table[table.diff_high >= 0]; sort by complexity, then single_ms; "
                                   "take the first model.")
def _(fn):
    t = _cand()
    assert fn(t.copy()) == "boosting", "logistic is detectably worse; of the rest, the simpler one should win"
    t2 = t.copy()
    t2.loc[0, ["diff_low", "diff_high"]] = [-0.03, 0.002]
    assert fn(t2) == "logistic", "if logistic is not detectably worse, the simplest model should win"
    t3 = t.copy()
    t3["complexity"] = [1, 2, 2]
    assert fn(t3) == "boosting", "on a complexity tie, the faster model should win"
    t4 = t.copy()
    t4.loc[2, ["diff_low", "diff_high"]] = [-0.03, -0.001]
    assert fn(t4) == "forest", "when every other model is detectably worse, the best one remains"


@exercise("w07.write_memo", hint="Build a list of lines with the four headings in order; format numbers with "
                                 "f'{x:.3f}'; join with newlines.")
def _(fn):
    import re
    t = _cand()
    worst = "5-12 km trips, recall about 0.25"
    memo = fn(t.copy(), "boosting", worst)
    assert isinstance(memo, str), "return the memo as a string"
    heads = ["## Decision", "## Evidence", "## Alternatives", "## Risks"]
    lines = memo.splitlines()
    pos = []
    for h in heads:
        hits = [i for i, line in enumerate(lines) if line.strip() == h]
        assert hits, f"the heading '{h}' is missing (it must be on its own line)"
        pos.append(hits[0])
    assert pos == sorted(pos), "the four headings must appear in the order Decision, Evidence, Alternatives, Risks"
    part = {h: "\n".join(lines[pos[i] + 1:(pos[i + 1] if i + 1 < 4 else len(lines))]) for i, h in enumerate(heads)}
    assert "boosting" in part["## Decision"], "the Decision section should name the chosen model"
    nums = [float(x) for x in re.findall(r"[-+]?\d+\.\d+", part["## Evidence"])]

    def has(v, tol):
        return any(abs(x - v) <= tol for x in nums)
    assert has(0.798, 0.0005), "the Evidence section should give the chosen model's AUC with 3 decimals (0.798)"
    assert has(-0.014, 0.0005) and has(0.010, 0.0005), "the Evidence section should give the difference interval"
    assert has(2.0, 0.05), "the Evidence section should give the chosen model's single-row latency in ms"
    for other in ["logistic", "forest"]:
        assert other in part["## Alternatives"], f"the Alternatives section should mention '{other}'"
    assert worst in part["## Risks"], "the Risks section should include the description of the weakest slice"
    memo2 = fn(t.copy(), "forest", "north region")
    assert "forest" in memo2.split("## Evidence")[0] and "0.801" in memo2, "the memo must follow the `choice` argument"


register_quiz("w07.27_q1", "b",
              "Nine rows cannot support a recall estimate (one more caught delivery changes it by a lot). Note it, "
              "set a minimum slice size, and watch it as data grows.",
              {"a": "Reacting to a 9-row slice is fitting noise, and it may hurt the other slices.",
               "c": "Removing inconvenient data hides the problem from evaluation instead of solving it.",
               "d": "The slice is far too small to support a claim about the whole region."})
register_quiz("w07.27_q2", "d",
              "Every change made after studying errors is a modelling decision; the test set must stay untouched "
              "until the final, one-time evaluation.",
              {"a": "Size is not the reason; even a big test set must not be used for tuning.",
               "b": "Both should be representative; the point is which data you are allowed to learn from.",
               "c": "Speed has nothing to do with it."})
register_quiz("w07.27_q3", "c",
              "The pattern points to a missing feature (courier skill). A courier-history feature computed only from "
              "earlier deliveries can capture it without leakage.",
              {"a": "No algorithm can use information that is not in its inputs.",
               "b": "A global threshold change trades precision for recall everywhere; it does not fix the cause.",
               "d": "Those couriers will still deliver parcels; hiding them from training makes the model worse for them."})
register_quiz("w07.27_q4", "a",
              "Timings have outliers from warm-up and background activity; the median of many repeats is a stable "
              "summary.",
              {"b": "The median is chosen for robustness, not to flatter the model.",
               "c": "The mean can be computed; it is just pulled up by one slow call.",
               "d": "One timing is the least reliable measurement of all."})
register_quiz("w07.27_q5", "b",
              "B's interval contains 0, so it is not detectably worse than A; it is simpler and faster, so the rule "
              "picks B.",
              {"a": "The rule deliberately does not chase a point estimate that is inside the noise.",
               "c": "Overlap is not the criterion; the paired interval of B's difference contains 0, which makes B "
                    "acceptable.",
               "d": "Part of the interval being negative is expected; only an interval entirely below 0 excludes B."})


# ============================================================================= 28: project milestone 1 (SKAB)

_SKAB_RAW = ["Accelerometer1RMS", "Accelerometer2RMS", "Current", "Pressure", "Temperature", "Thermocouple",
             "Voltage", "Volume Flow RateRMS"]
_SENSORS = ["accel1", "accel2", "current", "pressure", "temperature", "thermocouple", "voltage", "flow_rate"]


def _synthetic_runs(n_exp=6, seed=0, n_rows=(160, 260)):
    """Synthetic sensor experiments shaped like SKAB: one anomalous segment each, sensor levels differ per run."""
    rng = np.random.default_rng(seed)
    parts = []
    for e in range(n_exp):
        n = int(rng.integers(*n_rows))
        start = int(rng.integers(110, n - 40))
        stop = int(rng.integers(start + 10, n - 5))
        anomaly = np.zeros(n, int)
        anomaly[start:stop] = 1
        level = rng.normal(0, 5, len(_SENSORS))
        X = level + rng.normal(0, 1, (n, len(_SENSORS)))
        X[:, 7] += anomaly * rng.uniform(1.5, 4)          # flow rate reacts to the fault
        X[:, 1] = np.round(X[:, 1])                        # a quantised sensor
        df = pd.DataFrame(X, columns=_SENSORS)
        df.insert(0, "t", np.arange(n))
        df.insert(0, "experiment", f"fam{e % 2}/{e}")
        df["anomaly"] = anomaly
        df["changepoint"] = 0
        df.loc[[start, stop], "changepoint"] = 1
        parts.append(df)
    return pd.concat(parts, ignore_index=True)


@exercise("w07.p_load_experiment", hint="pd.read_csv(path, sep=';'), rename with SKAB_COLUMNS, parse datetime, "
                                        "cast anomaly/changepoint to int, insert experiment and t at the front.")
def _(fn):
    import tempfile
    from pathlib import Path
    want_cols = ["experiment", "t", "datetime", *_SENSORS, "anomaly", "changepoint"]
    with tempfile.TemporaryDirectory() as tmp:
        for i, n in enumerate([5, 12]):
            rng = np.random.default_rng(i)
            raw = pd.DataFrame(rng.normal(size=(n, 8)).round(5), columns=_SKAB_RAW)
            raw.insert(0, "datetime", pd.date_range("2020-03-09 10:14:33", periods=n, freq="s").astype(str))
            raw["anomaly"] = (np.arange(n) >= n // 2).astype(float)
            raw["changepoint"] = (np.arange(n) == n // 2).astype(float)
            path = Path(tmp) / f"{i}.csv"
            raw.to_csv(path, sep=";", index=False)
            exp = f"valve{i + 1}/{i}"
            got = fn(path, exp)
            assert isinstance(got, pd.DataFrame), "return a DataFrame"
            assert list(got.columns) == want_cols, f"the columns should be, in order: {want_cols}; got {list(got.columns)}"
            assert len(got) == n, f"expected {n} rows, got {len(got)}"
            assert (got["experiment"] == exp).all(), "every row should carry the experiment id passed in"
            assert list(got["t"]) == list(range(n)), "t should be 0, 1, 2, ... (the row number in the file)"
            assert pd.api.types.is_datetime64_any_dtype(got["datetime"]), "parse `datetime` into a pandas datetime"
            for c in ["anomaly", "changepoint"]:
                assert pd.api.types.is_integer_dtype(got[c]), f"`{c}` should be an integer column (0/1)"
            assert np.allclose(got["flow_rate"], raw["Volume Flow RateRMS"]), "sensor values changed while loading"
            assert np.allclose(got[_SENSORS].to_numpy(), raw[_SKAB_RAW].to_numpy()), "sensors were renamed in the wrong order"


@exercise("w07.p_split_violations", hint="For each group: does it intersect dev AND intersect test? Return those "
                                         "groups, sorted.")
def _(fn):
    groups = [["anomaly-free/anomaly-free", "other/5"], ["other/10", "other/11"], ["other/12", "other/13"],
              ["other/2", "other/3", "other/4"]]
    ok = {"dev": ["other/5", "other/10", "other/11", "other/12", "other/13", "other/2", "other/3", "other/4"],
          "test": ["other/1", "valve1/8"]}
    assert fn(ok, groups) == [], "this split keeps every group together (anomaly-free is in neither list)"
    bad = {"dev": ["other/5", "other/10", "other/12", "other/13", "other/2", "other/3"],
           "test": ["other/4", "other/11", "other/1"]}
    got = fn(bad, groups)
    assert got == [["other/10", "other/11"], ["other/2", "other/3", "other/4"]], (
        f"expected exactly the two broken groups, in the given order, each sorted; got {got}")
    assert fn({"dev": [], "test": ["other/4"]}, groups) == [], "a group with members only in test is not a violation"
    assert fn({"dev": ["b"], "test": ["a"]}, [["b", "a"]]) == [["a", "b"]], "return each violated group sorted"


def _ref_burn(df, columns, burn_in):
    calib = df[df["t"] < burn_in].groupby("experiment")[columns]
    mean = calib.mean().reindex(df["experiment"]).to_numpy()
    std = calib.std().reindex(df["experiment"]).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.abs(df[columns].to_numpy(float) - mean) / std
    z[~np.isfinite(z)] = 0.0
    return pd.DataFrame(z, index=df.index, columns=columns)


@exercise("w07.p_burn_in_abs_z", hint="Per experiment, mean and std of the rows with t < burn_in; "
                                      "|x - mean| / std; 0 where the std is 0.")
def _(fn):
    df = _synthetic_runs(5, seed=3)
    df["constant"] = 7.0
    df.index = df.index * 3 + 10                           # a non-default index must be kept
    cols = ["flow_rate", "accel2", "constant", "pressure"]
    before = df.copy()
    for b in (100, 40):
        got = fn(df, cols, burn_in=b) if b != 100 else fn(df, cols)
        assert df.equals(before), "burn_in_abs_z changed its input"
        assert isinstance(got, pd.DataFrame), "return a DataFrame"
        assert list(got.columns) == cols, f"one column per requested sensor, named as given: {cols}"
        assert got.index.equals(df.index), "keep the same index as the input"
        want = _ref_burn(df, cols, b)
        assert np.allclose(got["constant"], 0), "a sensor that is constant during burn-in should get |z| = 0"
        ok = np.isclose(got.to_numpy(float), want.to_numpy(), atol=1e-9)
        if not ok.all():
            r, c = np.argwhere(~ok)[0]
            raise AssertionError(f"with burn_in={b}, |z| of '{cols[c]}' is wrong (first at experiment "
                                 f"{df['experiment'].iloc[r]}, t={df['t'].iloc[r]}): use only rows with t < burn_in of "
                                 "the SAME experiment, and the pandas default std")
    later = df.copy()
    later.loc[later["t"] >= 150, "flow_rate"] += 1000.0
    z1, z2 = fn(df, ["flow_rate"]), fn(later, ["flow_rate"])
    early = df["t"] < 150
    assert np.allclose(z1.loc[early, "flow_rate"], z2.loc[early, "flow_rate"]), \
        "changing later rows changed earlier scores: the calibration must use only the burn-in rows"


@exercise("w07.p_pr_auc_usable", hint="keep = (split == split) & (t >= burn_in); average_precision_score on the "
                                      "kept rows.")
def _(fn):
    from sklearn.metrics import average_precision_score
    df = _synthetic_runs(6, seed=4)
    rng = np.random.default_rng(1)
    df["split"] = np.where(df["experiment"].str.endswith(("/4", "/5")), "test", "dev")
    df["score"] = df["anomaly"] * 0.8 + rng.normal(0, 0.6, len(df))
    df.loc[df["t"] < 100, "score"] = 5.0                   # burn-in rows look alarming: they must be excluded
    for split, b in [("dev", 100), ("test", 100), ("dev", 120)]:
        keep = (df["split"] == split) & (df["t"] >= b)
        want = average_precision_score(df.loc[keep, "anomaly"], df.loc[keep, "score"])
        got = fn(df, "score", split, burn_in=b) if b != 100 else fn(df, "score", split)
        assert isinstance(got, (float, np.floating)), "return a float"
        assert abs(got - want) < 1e-9, (f"PR-AUC on {split} rows with burn_in={b} should be {want:.4f}, got {got:.4f} "
                                        "(only rows of that split with t >= burn_in)")


@exercise("w07.p_event_table", hint="Group by experiment; detected = any(alert & anomaly); false_alarm = "
                                    "any(alert & not anomaly); delay from the first alert on an anomalous row.")
def _(fn):
    rows = []

    def exp(name, anomaly, alert, t0=100):
        for i, (a, al) in enumerate(zip(anomaly, alert)):
            rows.append({"experiment": name, "t": t0 + i, "anomaly": a, "alert": al})
    exp("b/1", [0, 0, 1, 1, 1, 1, 0], [0, 0, 0, 1, 1, 0, 0])       # detected, delay 1, no false alarm
    exp("a/2", [0, 0, 0, 1, 1, 0, 0], [1, 0, 0, 0, 0, 0, 0])       # missed, false alarm
    exp("c/3", [0, 1, 1, 1, 0], [0, 1, 0, 0, 1], t0=250)           # detected at once, false alarm after
    df = pd.DataFrame(rows)
    df["alert"] = df["alert"].astype(bool)
    got = fn(df.copy(), "alert")
    assert isinstance(got, pd.DataFrame), "return a DataFrame"
    assert list(got.index) == ["a/2", "b/1", "c/3"], "index by experiment, sorted"
    for col in ["detected", "false_alarm", "delay"]:
        assert col in got.columns, f"missing column '{col}'"
    assert [bool(v) for v in got["detected"]] == [False, True, True], "`detected` is wrong for some experiment"
    assert [bool(v) for v in got["false_alarm"]] == [True, False, True], "`false_alarm` is wrong for some experiment"
    d = got["delay"].astype(float).to_numpy()
    assert np.isnan(d[0]), "a missed fault has no delay: NaN"
    assert d[1] == 1 and d[2] == 0, "delay = t of the first alert on an anomalous row - t of the first anomalous row"
    got2 = fn(df.assign(other=df["alert"].astype(int)), "other")
    assert [bool(v) for v in got2["detected"]] == [False, True, True], "use the column named by `alert_col` (0/1 works too)"


@exercise("w07.p_persistent_alerts", hint="Group the alert column by experiment and take a rolling sum over k rows; "
                                          "True where the sum equals k.")
def _(fn):
    df = pd.DataFrame({"experiment": ["x"] * 6 + ["y"] * 5,
                       "t": list(range(6)) + list(range(5)),
                       "alert": [1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1]}, index=range(100, 111))
    df["alert"] = df["alert"].astype(bool)
    for k, want in [(1, df["alert"].tolist()),
                    (2, [False, True, True, False, False, True, False, True, False, False, True]),
                    (3, [False, False, True, False, False, False, False, False, False, False, False])]:
        got = fn(df.copy(), "alert", k)
        assert isinstance(got, pd.Series), "return a boolean Series"
        assert got.index.equals(df.index), "keep the index of the input"
        assert [bool(v) for v in got] == want, (f"with k={k} the result is wrong (a run must not continue across two "
                                                "experiments, and the first k-1 rows of an experiment cannot qualify)")


@exercise("w07.p_experiment_bootstrap", hint="rng.choice(unique experiments, size=n, replace=True); concatenate all "
                                            "rows of the drawn experiments; average_precision_score per replicate.")
def _(fn):
    from sklearn.metrics import average_precision_score
    df = _synthetic_runs(8, seed=9)
    rng = np.random.default_rng(2)
    strength = {e: rng.uniform(0.0, 3.0) for e in df["experiment"].unique()}   # experiments differ a lot
    df["score"] = df["anomaly"] * df["experiment"].map(strength) + rng.normal(0, 1, len(df))
    got = np.asarray(fn(df, "score", n_boot=200, seed=0), float)
    assert got.shape == (200,), f"expected n_boot=200 values, got shape {got.shape}"
    assert np.array_equal(got, np.asarray(fn(df, "score", n_boot=200, seed=0), float)), \
        "the same seed must give the same replicates"
    y, s, g = df["anomaly"].to_numpy(), df["score"].to_numpy(), df["experiment"].to_numpy()
    ref = _ref_group_boot(y, s, g, average_precision_score, 400, 1)
    rows_r = np.random.default_rng(1)
    row_sd = np.std([average_precision_score(y[i], s[i]) for i in
                     (rows_r.integers(0, len(y), len(y)) for _ in range(200))])
    assert abs(got.mean() - ref.mean()) < 0.03, "the replicates do not centre where an experiment bootstrap would"
    assert got.std() > 2 * row_sd and abs(got.std() - ref.std()) < 0.4 * ref.std(), (
        f"the spread of your replicates ({got.std():.3f}) looks like a row bootstrap ({row_sd:.3f}), not an "
        f"experiment bootstrap ({ref.std():.3f}): draw whole experiments")


# Ranges measured on the real data (7 test experiments of split v2; see the solved notebook). They are loose on
# purpose: a student's own interval code or bootstrap draws may differ slightly.
_RANGES = {"ap_constant": (0.36, 0.39), "ap_detector": (0.86, 0.91), "ap_model": (0.86, 0.92)}


@exercise("w07.p_findings", hint="Build the dict key by key from the functions of steps 4-7; the summary is your "
                                 "own text with the numbers in it.")
def _(f):
    if f is None:
        raise NotImplementedError
    assert isinstance(f, dict), "findings should be a dict"
    keys = ["n_dev_experiments", "n_test_experiments", "ap_constant", "ap_detector", "ap_model", "ap_detector_ci",
            "ap_model_ci", "diff_ci", "events_detected", "false_alarm_experiments_k1", "false_alarm_experiments_k5",
            "summary"]
    missing = [k for k in keys if k not in f]
    assert not missing, f"missing keys: {missing}"
    assert (f["n_dev_experiments"], f["n_test_experiments"]) == (27, 7), \
        "split v2 has 27 dev and 7 test experiments: are you counting experiments, not rows?"
    for k, (lo, hi) in _RANGES.items():
        assert lo <= f[k] <= hi, (f"{k} = {f[k]:.3f} is outside the range measured on the real data ({lo}-{hi}): "
                                  "test split only, rows with t >= burn-in only?")
    for k, point in [("ap_detector_ci", f["ap_detector"]), ("ap_model_ci", f["ap_model"])]:
        lo, hi = f[k]
        assert lo < point < hi, f"{k} should be an interval (low, high) around the point estimate"
        assert 0.03 < hi - lo < 0.25, f"{k} has width {hi - lo:.3f}; an experiment bootstrap on 7 experiments gives about 0.1"
    lo, hi = f["diff_ci"]
    diff = f["ap_model"] - f["ap_detector"]
    assert lo < hi and lo - 0.01 <= diff <= hi + 0.01, "diff_ci should be an interval around ap_model - ap_detector"
    assert hi - lo < 0.2, "diff_ci is too wide for a PAIRED interval: resample both scores on the same experiments"
    assert 6 <= f["events_detected"] <= 7, "events_detected: count of test experiments whose fault was detected (k=1)"
    assert f["false_alarm_experiments_k5"] <= f["false_alarm_experiments_k1"] <= 7, \
        "a persistence rule can only remove false alarms, never add them"
    assert f["false_alarm_experiments_k1"] >= 5, "with k=1 the detector raises false alarms in most test experiments"
    s = f["summary"]
    assert isinstance(s, str) and len(s.split()) >= 60, "write a summary of 4-8 sentences (at least 60 words)"
    assert str(f["n_test_experiments"]) in s, "the summary should say how many test experiments the numbers rest on"
    assert f"{f['ap_detector']:.2f}" in s or f"{f['ap_detector']:.3f}" in s, \
        "the summary should quote the detector's PR-AUC"
    assert "interval" in s.lower(), "the summary should mention the intervals"


register_quiz("w07.28_q1", "a",
              "Statistics over the whole recording include the anomalous segment and the future; at prediction time "
              "only the past exists. The burn-in uses the past only.",
              {"b": "Speed is not the reason; correctness is.",
               "c": "It is the opposite: the start of each experiment is normal operation, which is why it calibrates.",
               "d": "It changes the meaning of the feature: whole-recording statistics leak the future."})
register_quiz("w07.28_q2", "b",
              "The fault onset is set by the experimental protocol (rows 550-600 in 31 of 34 runs); `t` lets the model "
              "learn the protocol, which a real plant does not follow.",
              {"a": "Pump wear over a 20-minute run is not what the labels describe; the jump comes from the protocol.",
               "c": "More features can add leakage or noise; here it adds a leak.",
               "d": "Being known at prediction time is necessary, not sufficient: the feature must also generalise."})
register_quiz("w07.28_q3", "d",
              "The interval contains 0, so the model is not detectably better; the rule picks the simpler, "
              "explainable detector and keeps the comparison for later.",
              {"a": "That chases a point estimate inside the noise (notebook 26).",
               "b": "More data would help, but you can still make a defensible decision now.",
               "c": "An ensemble adds complexity without evidence that it helps."})
register_quiz("w07.28_q4", "b",
              "A handful of isolated rows hardly moves a point-level metric, but each becomes an alarm. Event-level "
              "metrics count them; persistence rules reduce them.",
              {"a": "The metric can be correct and still not measure what the engineer experiences.",
               "c": "The complaint is about alarms in operation; the dev/test split is not the issue.",
               "d": "Choosing the threshold on test would make every reported test number optimistic."})
