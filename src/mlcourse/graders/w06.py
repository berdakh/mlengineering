"""Week 6 graders: validation and leakage (notebooks 21-24).

What the tests check, in plain words:
* splitters (notebook 21): on several generated inputs, every row is tested exactly once (or held out once), no
  group is on both sides, time only flows forward, sizes are right, the same seed gives the same split;
* leakage tools (notebook 22): single-feature probes, availability checks, duplicates across splits and target
  encoding, on small hand-made frames with edge cases (missing values, unseen categories, ties);
* search setups (notebook 23): the model's preprocessing is inside the search, the CV object matches the data
  (grouped or time-ordered), and the numbers match an independent reference;
* the lab (notebook 24): cleaning, splits and pipeline on freshly generated tables; the identified issues as a set;
  the honest score within a tolerance of the score on brand-new future companies (the generator's ground truth).

Reference implementations are written differently from the notebook solutions on purpose, so tests check
behaviour, not one way of writing it. All data is synthetic (mlcourse.validation_data).
"""
from __future__ import annotations

import warnings
from functools import lru_cache

import numpy as np
import pandas as pd

from mlcourse.grader import exercise, register_quiz
from mlcourse import validation_data as vd


# ============================================================================== small helpers
def _pairs(splits, what="your function"):
    """Turn the student's splits into a list of (train, test) integer arrays, with clear messages."""
    try:
        splits = list(splits)
    except TypeError:
        raise AssertionError(f"{what} should return a list of (train_indices, test_indices) pairs")
    out = []
    for s in splits:
        try:
            tr, te = s
        except (TypeError, ValueError):
            raise AssertionError("each split should be a pair: (train_indices, test_indices)")
        tr, te = np.asarray(tr), np.asarray(te)
        if tr.dtype == bool or te.dtype == bool:
            raise AssertionError("return row positions (integers), not True/False masks: np.flatnonzero(mask) "
                                 "turns a mask into positions")
        if (tr.size and not np.issubdtype(tr.dtype, np.integer)) or (te.size and not np.issubdtype(te.dtype, np.integer)):
            raise AssertionError("indices should be integers (row positions 0, 1, 2, ...)")
        out.append((tr.astype(int), te.astype(int)))
    return out


def _pair(result, what="your function"):
    try:
        tr, te = result
    except (TypeError, ValueError):
        raise AssertionError(f"{what} should return two arrays: (train_indices, test_indices)")
    return _pairs([(tr, te)], what)[0]


def _check_partition(tr, te, n, label=""):
    if np.intersect1d(tr, te).size:
        raise AssertionError(f"{label}some rows are in both train and test")
    if len(np.unique(te)) != len(te) or len(np.unique(tr)) != len(tr):
        raise AssertionError(f"{label}a row appears twice in the same side")
    if tr.size + te.size != n or (np.union1d(tr, te) != np.arange(n)).any():
        raise AssertionError(f"{label}train and test together should contain every row 0..{n - 1} exactly once")


def _grouped_frame(seed, n_groups=24, per=(4, 12)):
    """Rows that belong together: each group has its own feature offset and its own label rate."""
    rng = np.random.default_rng(seed)
    rows, labels, groups = [], [], []
    for g in range(n_groups):
        size = int(rng.integers(*per))
        centre = rng.normal(0, 3, size=3)
        rate = rng.uniform(0.05, 0.95)
        signal = rng.normal(size=size)
        x = centre + rng.normal(0, 0.3, size=(size, 3))
        x[:, 0] += signal
        y = (rng.random(size) < 0.7 * rate + 0.3 * (signal > 0)).astype(int)
        rows.append(x)
        labels.append(y)
        groups += [f"g{g:02d}"] * size
    return np.vstack(rows), np.concatenate(labels), np.array(groups)


def _time_frame(seed, n_days=90, per_day=6):
    """Rows over time with a slowly changing label rate and a drifting 'clock-like' feature."""
    rng = np.random.default_rng(seed)
    days = np.repeat(np.arange(n_days), per_day)
    regime = np.cumsum(rng.normal(0, 0.35, size=n_days))
    clock = np.cumsum(rng.normal(0, 1.0, size=n_days))[days] + rng.normal(0, 0.1, size=days.size)
    x1 = rng.normal(size=days.size)
    y = (rng.random(days.size) < 1 / (1 + np.exp(-(0.8 * x1 + 1.5 * (regime[days] - regime.mean()))))).astype(int)
    order = rng.permutation(days.size)   # rows arrive in a shuffled order: the dates tell the time
    dates = pd.Timestamp("2025-01-01") + pd.to_timedelta(days[order], unit="D")
    return np.c_[x1, clock][order], y[order], pd.Series(dates)


def _knn():
    from sklearn.neighbors import KNeighborsClassifier
    return KNeighborsClassifier(n_neighbors=5)


def _num(x, what):
    try:
        return float(x)
    except (TypeError, ValueError):
        raise AssertionError(f"{what} should be a single number, got {type(x).__name__}")


# ============================================================================== notebook 21: validation
@exercise("w06.holdout_split", hint="Shuffle np.arange(n) with np.random.default_rng(seed), then cut it in two.")
def _(fn):
    for n, frac in ((100, 0.2), (10, 0.3), (57, 0.25), (5, 0.2)):
        tr, te = _pair(fn(n, frac, 0), "holdout_split")
        _check_partition(tr, te, n, f"n={n}: ")
        want = n * frac
        if abs(len(te) - want) > 1:
            raise AssertionError(f"n={n}, test_fraction={frac}: expected about {want:g} test rows, got {len(te)}")
    a, b = _pair(fn(100, 0.2, 7)), _pair(fn(100, 0.2, 7))
    if set(a[1]) != set(b[1]):
        raise AssertionError("the same seed gave two different splits: use the seed for all randomness")
    c = _pair(fn(100, 0.2, 8))
    if set(a[1]) == set(c[1]):
        raise AssertionError("different seeds gave the same split: is the seed used?")
    te = np.sort(a[1])
    if (te == np.arange(te[0], te[0] + len(te))).all():
        raise AssertionError("the test rows are one consecutive block: shuffle the rows before cutting")


@exercise("w06.kfold_indices", hint="Shuffle the positions once, then np.array_split them into k parts.")
def _(fn):
    for n, k in ((50, 5), (7, 3), (23, 4), (10, 10)):
        splits = _pairs(fn(n, k, 0), "kfold_indices")
        if len(splits) != k:
            raise AssertionError(f"n={n}, k={k}: expected {k} splits, got {len(splits)}")
        tested = np.concatenate([te for _, te in splits])
        for i, (tr, te) in enumerate(splits):
            _check_partition(tr, te, n, f"n={n}, k={k}, split {i + 1}: ")
        if sorted(tested.tolist()) != list(range(n)):
            raise AssertionError(f"n={n}, k={k}: every row must be in exactly one test fold")
        sizes = [len(te) for _, te in splits]
        if max(sizes) - min(sizes) > 1:
            raise AssertionError(f"n={n}, k={k}: test folds should differ in size by at most one row, got {sizes}")
    a, b = _pairs(fn(30, 3, 1)), _pairs(fn(30, 3, 1))
    if [set(t) for _, t in a] != [set(t) for _, t in b]:
        raise AssertionError("the same seed gave different folds")
    first = np.sort(_pairs(fn(60, 3, 2))[0][1])
    if (first == np.arange(first[0], first[0] + len(first))).all():
        raise AssertionError("the first test fold is a consecutive block of rows: shuffle the positions first")


@exercise("w06.stratified_folds", hint="StratifiedKFold(n_splits=k, shuffle=True, random_state=seed).split(X, y)")
def _(fn):
    rng = np.random.default_rng(3)
    cases = [np.array([0] * 80 + [1] * 20), rng.permutation(np.array(["a"] * 30 + ["b"] * 12 + ["c"] * 9)),
             np.array([1, 0] * 15)]
    for y in cases:
        for k in (3, 5):
            splits = _pairs(fn(y, k, 0), "stratified_folds")
            if len(splits) != k:
                raise AssertionError(f"expected {k} folds, got {len(splits)}")
            for i, (tr, te) in enumerate(splits):
                _check_partition(tr, te, len(y), f"fold {i + 1}: ")
            if sorted(np.concatenate([te for _, te in splits]).tolist()) != list(range(len(y))):
                raise AssertionError("every row must be in exactly one test fold")
            for cls in np.unique(y):
                total = (y == cls).sum()
                counts = [(y[te] == cls).sum() for _, te in splits]
                if min(counts) < np.floor(total / k) - 0.01 or max(counts) > np.ceil(total / k) + 0.01:
                    raise AssertionError(f"class {cls!r} ({total} rows) is spread {counts} over the folds: each fold "
                                         "should get its fair share of every class")
    a, b = _pairs(fn(cases[0], 5, 4)), _pairs(fn(cases[0], 5, 4))
    if [set(t) for _, t in a] != [set(t) for _, t in b]:
        raise AssertionError("the same seed gave different folds")


@exercise("w06.groups_on_both_sides", hint="Look up the groups of the train rows and of the test rows; intersect.")
def _(fn):
    g = np.array(["a", "a", "b", "b", "c", "c", "d"])
    cases = [
        (np.array([0, 2, 4]), np.array([1, 3, 6]), {"a", "b"}),
        (np.array([0, 1, 2, 3]), np.array([4, 5, 6]), set()),
        (np.array([0, 1, 2, 3, 4]), np.array([5]), {"c"}),
    ]
    for tr, te, want in cases:
        got = fn(tr, te, g)
        try:
            got = set(got)
        except TypeError:
            raise AssertionError("return a set of group names")
        if got != want:
            if not want:
                raise AssertionError("when no group is shared the answer should be an empty set")
            raise AssertionError(f"train rows {tr.tolist()}, test rows {te.tolist()}: expected {len(want)} shared "
                                 f"group(s), got {sorted(map(str, got))}")
    s = pd.Series([10, 10, 20, 30, 30], index=[100, 101, 102, 103, 104])
    got = set(fn(np.array([0, 2]), np.array([1, 3]), s))
    if got != {10}:
        raise AssertionError("with a pandas Series of groups whose index is not 0..n-1, use positions "
                             "(np.asarray(groups) or .iloc), not index labels")


@exercise("w06.group_kfold_indices", hint="GroupKFold(n_splits=k).split(X, y, groups) needs only the groups.")
def _(fn):
    rng = np.random.default_rng(5)
    cases = [np.repeat(np.arange(10), 3),
             rng.permutation(np.repeat(["m1", "m2", "m3", "m4", "m5", "m6", "m7"], [9, 2, 5, 5, 1, 7, 3])),
             np.array(["x"] * 4 + ["y"] * 4 + ["z"] * 4)]
    for groups in cases:
        for k in (2, 3):
            splits = _pairs(fn(groups, k), "group_kfold_indices")
            if len(splits) != k:
                raise AssertionError(f"expected {k} splits, got {len(splits)}")
            for i, (tr, te) in enumerate(splits):
                _check_partition(tr, te, len(groups), f"split {i + 1}: ")
                shared = set(groups[tr]) & set(groups[te])
                if shared:
                    raise AssertionError(f"split {i + 1}: {len(shared)} group(s) have rows in both train and test")
            if sorted(np.concatenate([te for _, te in splits]).tolist()) != list(range(len(groups))):
                raise AssertionError("every row must be in exactly one test fold")


@exercise("w06.grouped_cv_auc", hint="cross_val_score(model, X, y, groups=groups, cv=GroupKFold(k), scoring='roc_auc')")
def _(fn):
    from sklearn.model_selection import GroupKFold, KFold, cross_val_score

    for seed, k in ((0, 4), (1, 3)):
        X, y, g = _grouped_frame(seed)
        got = _num(fn(_knn(), X, y, g, k), "grouped_cv_auc")
        ref = cross_val_score(_knn(), X, y, groups=g, cv=GroupKFold(k), scoring="roc_auc").mean()
        rnd = cross_val_score(_knn(), X, y, cv=KFold(k, shuffle=True, random_state=0), scoring="roc_auc").mean()
        if abs(got - rnd) < 0.01 and abs(got - ref) > 0.02:
            raise AssertionError("your score matches random (ungrouped) folds: rows of a group still end up on both "
                                 "sides. Pass the groups to a grouped splitter")
        if 0.5 < got <= 1 and got > ref + 0.04:
            raise AssertionError(f"your score {got:.3f} is optimistic compared with grouped folds: check the splitter")
        if abs(got - ref) > 0.04:
            raise AssertionError(f"expected the mean ROC AUC over {k} grouped folds; your number {got:.3f} is off. "
                                 "Is it the mean of the fold scores, with scoring='roc_auc'?")


def _ref_forward_days(dates, n_splits, gap_days):
    days = np.asarray(dates)
    uniq = np.unique(days)
    pos = np.searchsorted(uniq, days)
    n_days = len(uniq)
    test_size = n_days // (n_splits + 1)
    out = []
    for i in range(n_splits):
        start = n_days - (n_splits - i) * test_size
        out.append((np.flatnonzero(pos < start - gap_days), np.flatnonzero((pos >= start) & (pos < start + test_size))))
    return out


@exercise("w06.forward_day_splits",
          hint="Split the sorted UNIQUE days with TimeSeriesSplit(n_splits, gap=gap_days), then map rows to their day.")
def _(fn):
    rng = np.random.default_rng(11)
    day_list = pd.date_range("2025-03-01", periods=24, freq="D")
    cases = [
        (pd.Series(rng.permutation(np.repeat(day_list, rng.integers(1, 4, size=24)))), 3, 0),
        (pd.Series(rng.permutation(np.repeat(day_list, 2))), 4, 2),
        (pd.Series(rng.permutation(np.repeat(np.arange(30), 3))), 5, 1),
    ]
    for dates, n_splits, gap in cases:
        d = np.asarray(dates)
        uniq = np.sort(pd.unique(d))
        pos = np.searchsorted(uniq, d)
        splits = _pairs(fn(dates, n_splits, gap), "forward_day_splits")
        if len(splits) != n_splits:
            raise AssertionError(f"expected {n_splits} splits, got {len(splits)}")
        ref = _ref_forward_days(dates, n_splits, gap)
        prev_end = -1
        for i, ((tr, te), (rtr, rte)) in enumerate(zip(splits, ref)):
            if not len(te) or not len(tr):
                raise AssertionError(f"split {i + 1} has an empty train or test side")
            if np.intersect1d(tr, te).size:
                raise AssertionError(f"split {i + 1}: some rows are in both train and test")
            tr_days, te_days = set(pos[tr]), set(pos[te])
            if tr_days & te_days:
                raise AssertionError(f"split {i + 1}: the same day has rows in train and in test; split by day, "
                                     "not by row")
            if max(tr_days) >= min(te_days):
                raise AssertionError(f"split {i + 1}: some training days come after a test day; time must flow "
                                     "forward")
            if min(te_days) - max(tr_days) - 1 != gap:
                raise AssertionError(f"split {i + 1}: expected exactly {gap} unused day(s) between the last training "
                                     f"day and the first test day, got {min(te_days) - max(tr_days) - 1}")
            if set(te) != set(rte.tolist()):
                if min(te_days) <= prev_end:
                    raise AssertionError("test periods overlap or go backwards: each split should test a later period")
                raise AssertionError(f"split {i + 1}: the test period has the wrong days. Expected equal-sized test "
                                     "periods (in days) ending on the last day, like TimeSeriesSplit on the unique days")
            if set(tr) != set(rtr.tolist()):
                raise AssertionError(f"split {i + 1}: training should use every day before the gap (an expanding "
                                     "window), all rows of those days")
            prev_end = max(te_days)


@exercise("w06.time_cv_auc", hint="Loop over forward_day_splits(...), fit on train rows, score ROC AUC on test rows.")
def _(fn):
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import KFold, cross_val_score

    for seed, n_splits, gap in ((0, 4, 0), (1, 3, 5)):
        X, y, dates = _time_frame(seed)
        got = _num(fn(_knn(), X, y, dates, n_splits, gap), "time_cv_auc")
        scores = []
        for tr, te in _ref_forward_days(dates, n_splits, gap):
            m = _knn().fit(X[tr], y[tr])
            scores.append(roc_auc_score(y[te], m.predict_proba(X[te])[:, 1]))
        ref = float(np.mean(scores))
        rnd = cross_val_score(_knn(), X, y, cv=KFold(n_splits, shuffle=True, random_state=0), scoring="roc_auc").mean()
        if abs(got - rnd) < 0.01 and abs(got - ref) > 0.02:
            raise AssertionError("your score matches shuffled folds: the model is trained on days after the test days")
        if abs(got - ref) > 0.02:
            raise AssertionError(f"n_splits={n_splits}, gap={gap}: expected the mean ROC AUC over the forward splits, "
                                 f"your number {got:.3f} is off. Fit a fresh model in each split?")


@exercise("w06.group_holdout", hint="GroupShuffleSplit(n_splits=1, test_size=test_fraction, random_state=seed)")
def _(fn):
    rng = np.random.default_rng(2)
    cases = [np.repeat(np.arange(20), 5), rng.permutation(np.repeat([f"s{i}" for i in range(12)], rng.integers(1, 9, 12)))]
    for groups in cases:
        for frac in (0.2, 0.25):
            tr, te = _pair(fn(groups, frac, 0), "group_holdout")
            _check_partition(tr, te, len(groups))
            if set(groups[tr]) & set(groups[te]):
                raise AssertionError("some groups are in both train and test: hold out whole groups")
            n_g = len(set(groups))
            want = n_g * frac
            if abs(len(set(groups[te])) - want) > 1:
                raise AssertionError(f"with {n_g} groups and test_fraction={frac}, expected about {want:g} test "
                                     f"groups, got {len(set(groups[te]))}")
    g = cases[0]
    if set(_pair(fn(g, 0.2, 1))[1]) != set(_pair(fn(g, 0.2, 1))[1]):
        raise AssertionError("the same seed gave different splits")
    if set(_pair(fn(g, 0.2, 1))[1]) == set(_pair(fn(g, 0.2, 2))[1]):
        raise AssertionError("different seeds gave the same split: is the seed used?")


register_quiz(
    "w06.21_q1", "b",
    "One split gives one noisy number: which rows land in the test set moves it. k-fold averages several held-out "
    "estimates and shows their spread, so you can tell a real difference from luck.",
    {"a": "The two models are the same procedure; only the luck of the split changed.",
     "c": "Different seeds giving different numbers is expected, not a bug.",
     "d": "Picking the higher of several estimates is how optimism creeps in."})
register_quiz(
    "w06.21_q2", "c",
    "Validate the way the model will be used. It will meet new patients, so only folds where every test patient is "
    "new (GroupKFold) estimate that.",
    {"a": "More training rows do not help when the test rows are near-copies of training rows (same patient).",
     "b": "Averaging an honest number with a biased one gives a biased number.",
     "d": "The grouped estimate is exactly the one that matches how the model will be used."})
register_quiz(
    "w06.21_q3", "a",
    "Rows of one group are not independent: a flexible model recognises the group and recalls its labels. The "
    "validation rows are then not 'fresh' points, so their error underestimates E_out on new groups.",
    {"b": "Imbalance between groups is not the reason; correlation within groups is.",
     "c": "GroupKFold trains on about the same number of rows; it is the choice of rows that differs.",
     "d": "Random k-fold works exactly as designed; it just answers a different question (new rows of known groups)."})
register_quiz(
    "w06.21_q4", "d",
    "The model will predict the future from the past, so validation must too: train on earlier days, test on later "
    "days, with TimeSeriesSplit.",
    {"a": "Shuffled folds train on days after the test days, which production never can.",
     "b": "Stratifying keeps class balance but still mixes past and future.",
     "c": "Grouping by weekday puts the same weeks on both sides and still mixes past and future."})
register_quiz(
    "w06.21_q5", "b",
    "On the day you train, orders from the last 14 days have no final label yet. A gap of 14 days makes validation "
    "leave out exactly the information production will not have.",
    {"a": "A gap removes rows; it does not make anything noticeably faster.",
     "c": "A gap does not change the class balance in any planned way.",
     "d": "A gap uses fewer rows, not more."})


# ============================================================================== notebook 22: leakage
def _ref_auc(x, y):
    from scipy.stats import rankdata

    x, y = np.asarray(x, float), np.asarray(y)
    keep = ~np.isnan(x)
    x, y = x[keep], y[keep]
    pos = y == 1
    n1, n0 = pos.sum(), (~pos).sum()
    if n1 == 0 or n0 == 0:
        return 0.5
    r = rankdata(x)
    auc = (r[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
    return float(max(auc, 1 - auc))


@exercise("w06.single_feature_auc",
          hint="Drop rows where x is missing; if both classes remain, roc_auc_score(y, x); report max(auc, 1 - auc).")
def _(fn):
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 200)
    cases = [
        (y + rng.normal(0, 0.5, 200), y, "a feature that rises with the label"),
        (-y + rng.normal(0, 0.5, 200), y, "a feature that FALLS as the label rises"),
        (rng.normal(size=200), y, "a pure-noise feature"),
        (np.ones(200), y, "a constant feature"),
        (np.where(rng.random(200) < 0.3, np.nan, y + rng.normal(0, 1, 200)), y, "a feature with missing values"),
        (np.array([1.0, 2.0, np.nan, np.nan]), np.array([0, 0, 1, 1]), "a feature whose non-missing rows are one class"),
        (np.array([1, 2, 2, 3]), np.array([0, 0, 1, 1]), "a feature with ties"),
    ]
    for x, yy, label in cases:
        try:
            got = _num(fn(pd.Series(x), pd.Series(yy)), "single_feature_auc")
        except ValueError as err:
            raise AssertionError(f"your function crashed on {label}: {err}")
        want = _ref_auc(x, yy)
        if np.isnan(got) or abs(got - want) > 1e-6:
            raise AssertionError(f"wrong value for {label}: expected {want:.3f}, got {got:.3f}")


def _probe_frame(seed):
    rng = np.random.default_rng(seed)
    n = 300
    y = rng.integers(0, 2, n)
    return pd.DataFrame({"noise": rng.normal(size=n), "weak": y * 0.4 + rng.normal(size=n),
                         "leak": y * 3 + rng.normal(0, 0.5, n), "neg": -y + rng.normal(0, 1, n),
                         "city": rng.choice(["a", "b"], n), "label": y,
                         "gaps": np.where(rng.random(n) < 0.2, np.nan, rng.normal(size=n))})


@exercise("w06.probe_features", hint="For each numeric column except the target, single_feature_auc; sort descending.")
def _(fn):
    for seed, target in ((0, "label"), (1, "label")):
        df = _probe_frame(seed)
        got = fn(df.copy(), target)
        if not isinstance(got, pd.Series):
            raise AssertionError("return a pandas Series: index = column name, value = AUC")
        want = pd.Series({c: _ref_auc(df[c], df[target]) for c in ["noise", "weak", "leak", "neg", "gaps"]})
        if target in got.index:
            raise AssertionError("the target itself should not be probed (it would always score 1.0)")
        if "city" in got.index:
            raise AssertionError("only numeric columns: text columns like 'city' have no order to rank")
        if set(got.index) != set(want.index):
            raise AssertionError(f"expected one value per numeric feature column ({len(want)}), got {len(got)}")
        if not np.allclose(got.astype(float).reindex(want.index).values, want.values, atol=1e-6):
            raise AssertionError("some AUC values differ: are you using max(auc, 1 - auc) and ignoring missing values?")
        if list(got.index) != list(want.sort_values(ascending=False).index):
            raise AssertionError("sort the Series from the highest AUC to the lowest")
    other = _probe_frame(2).rename(columns={"label": "y"})
    if "y" in fn(other, "y").index:
        raise AssertionError("use the `target` argument, not a fixed column name")


@exercise("w06.suspicious_features", hint="probe_features(...), keep values >= threshold, return the names as a list.")
def _(fn):
    df = _probe_frame(3)
    for thr, want in ((0.9, ["leak"]), (0.7, ["leak", "neg"]), (0.53, ["leak", "neg", "noise", "gaps", "weak"]), (1.0, [])):
        got = fn(df.copy(), "label", thr)
        try:
            got = list(got)
        except TypeError:
            raise AssertionError("return a list of column names")
        if got != want:
            if set(got) == set(want):
                raise AssertionError("right columns, wrong order: most suspicious (highest AUC) first")
            raise AssertionError(f"threshold {thr}: expected {len(want)} suspicious column(s), got {len(got)}")


@exercise("w06.available_features", hint="Keep rows of the data dictionary whose known_at date is <= prediction_date.")
def _(fn):
    dd = pd.DataFrame({
        "feature": ["tenure", "orders_90d", "refund_amount", "plan", "survey_score", "last_login"],
        "known_at": ["2025-01-01", "2025-06-30", "2025-08-15", "2024-12-01", None, "2025-07-01"],
    })
    for date, want in (("2025-06-30", ["tenure", "orders_90d", "plan"]),
                       ("2025-07-01", ["tenure", "orders_90d", "plan", "last_login"]),
                       ("2024-06-01", [])):
        got = fn(dd.copy(), date)
        try:
            got = list(got)
        except TypeError:
            raise AssertionError("return a list of feature names")
        if "survey_score" in got:
            raise AssertionError("a feature with no known_at date should be treated as NOT available: if you cannot "
                                 "say when it is known, do not use it")
        if set(got) != set(want):
            if set(want) - set(got) and date == "2025-07-01":
                raise AssertionError("a feature known ON the prediction date is available (use <=)")
            raise AssertionError(f"prediction date {date}: expected {len(want)} available feature(s), got {len(got)}")
        if got != want:
            raise AssertionError("keep the features in the order of the data dictionary")


@exercise("w06.selection_pipeline", hint="Pipeline([('select', SelectKBest(f_classif, k=k)), ('model', LogisticRegression(max_iter=1000))])")
def _(fn):
    from sklearn.base import is_classifier
    from sklearn.feature_selection import SelectKBest
    from sklearn.model_selection import StratifiedKFold, cross_val_score
    from sklearn.pipeline import Pipeline

    pipe = fn(15)
    if not isinstance(pipe, Pipeline):
        raise AssertionError("return a scikit-learn Pipeline, so selection is refitted inside every fold")
    sel = [s for _, s in pipe.steps if isinstance(s, SelectKBest)]
    if not sel:
        raise AssertionError("the pipeline should contain a SelectKBest step")
    if sel[0].k != 15:
        raise AssertionError("use the k you are given")
    if not is_classifier(pipe.steps[-1][1]):
        raise AssertionError("the last step should be a classifier")
    if hasattr(sel[0], "scores_"):
        raise AssertionError("return the pipeline unfitted: cross-validation fits it")
    X, y = vd.make_noise(150, 1000, seed=5)
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        noise = cross_val_score(fn(15), X, y, cv=cv).mean()
        rng = np.random.default_rng(1)
        Xs = rng.normal(size=(150, 200))
        ys = (Xs[:, :3].sum(axis=1) > 0).astype(int)
        signal = cross_val_score(fn(3), Xs, ys, cv=cv).mean()
    if noise > 0.65:
        raise AssertionError(f"on pure noise your pipeline scores {noise:.2f}: selection is still seeing the test rows")
    if signal < 0.75:
        raise AssertionError(f"on data with 3 real signals your pipeline only scores {signal:.2f}: is the selection "
                             "scoring features against the label (f_classif)?")


@exercise("w06.count_shared_rows", hint="Merge test with the de-duplicated train on all columns, or use isin on row tuples.")
def _(fn):
    train = pd.DataFrame({"a": [1, 2, 3, 3], "b": ["x", "y", "z", "z"], "c": [0.5, 1.5, 2.5, 2.5]})
    cases = [
        (pd.DataFrame({"a": [1, 9, 3], "b": ["x", "y", "z"], "c": [0.5, 1.5, 2.5]}), 2, "two test rows copy train rows"),
        (pd.DataFrame({"a": [1, 1], "b": ["x", "x"], "c": [0.5, 0.5]}), 2, "a test row that appears twice counts twice"),
        (pd.DataFrame({"a": [2], "b": ["y"], "c": [1.6]}), 0, "rows that differ in one column are not copies"),
        (pd.DataFrame({"a": [3], "b": ["z"], "c": [2.5]}), 1, "a test row whose copy is in train twice counts once"),
        (train.iloc[:0], 0, "an empty test set"),
    ]
    for test, want, label in cases:
        got = _num(fn(train.copy(), test.copy()), "count_shared_rows")
        if got != want:
            raise AssertionError(f"{label}: expected {want}, got {got:g}")


@exercise("w06.dedupe_then_split", hint="df.drop_duplicates() first, then train_test_split(..., test_size=, random_state=seed).")
def _(fn):
    rng = np.random.default_rng(4)
    base = pd.DataFrame({"x": rng.integers(0, 1000, 120), "y": rng.integers(0, 2, 120)}).drop_duplicates()
    df = pd.concat([base, base.sample(40, random_state=1)]).sample(frac=1, random_state=2).reset_index(drop=True)
    tr, te = fn(df.copy(), 0.25, 0)
    if not isinstance(tr, pd.DataFrame) or not isinstance(te, pd.DataFrame):
        raise AssertionError("return two DataFrames: (train, test)")
    if tr.duplicated().any() or te.duplicated().any():
        raise AssertionError("duplicates remain inside train or test: remove them before splitting")
    shared = tr.merge(te, how="inner")
    if len(shared):
        raise AssertionError(f"{len(shared)} row(s) appear in both train and test")
    if len(tr) + len(te) != len(base):
        raise AssertionError(f"expected {len(base)} unique rows in total, got {len(tr) + len(te)}")
    if abs(len(te) - 0.25 * len(base)) > 1:
        raise AssertionError(f"expected about 25% of the unique rows in test, got {len(te)} of {len(base)}")
    tr2, te2 = fn(df.copy(), 0.25, 0)
    if set(map(tuple, te.values)) != set(map(tuple, te2.values)):
        raise AssertionError("the same seed gave different splits")


@exercise("w06.target_encode", hint="means = y.groupby(train_cat).mean() on TRAIN only; map; fill unknown with y.mean().")
def _(fn):
    train_cat = pd.Series(["a", "a", "b", "b", "b", None, "c"])
    train_y = pd.Series([1, 0, 1, 1, 0, 1, 0])
    test_cat = pd.Series(["b", "c", "z", None, "a"])
    got = fn(train_cat.copy(), train_y.copy(), test_cat.copy())
    try:
        tr, te = (np.asarray(v, float) for v in got)
    except (TypeError, ValueError):
        raise AssertionError("return two arrays (or Series): the encoded train values and the encoded test values")
    overall = train_y.mean()
    want_tr = np.array([0.5, 0.5, 2 / 3, 2 / 3, 2 / 3, overall, 0.0])
    want_te = np.array([2 / 3, 0.0, overall, overall, 0.5])
    if tr.shape != (7,) or te.shape != (5,):
        raise AssertionError("one encoded value per row: train and test should keep their lengths")
    if np.isnan(te).any() or np.isnan(tr).any():
        raise AssertionError("some values are NaN: categories unseen in training (and missing ones) should get the "
                             "overall training mean")
    if not np.allclose(te[[2, 3]], overall):
        raise AssertionError("an unseen or missing category should get the overall mean of the TRAINING labels")
    if not np.allclose(te, want_te):
        raise AssertionError("some test values differ: each category's value is the mean label of that category in "
                             "the training rows only")
    if not np.allclose(tr, want_tr):
        raise AssertionError("some training values differ: encode training rows with the same training means")


@exercise("w06.leakage_report", hint="Three counts: shared groups, train rows dated after the first test date, test rows copied in train.")
def _(fn):
    df = pd.DataFrame({
        "store": ["s1", "s1", "s2", "s2", "s3", "s3", "s4", "s4"],
        "date": pd.to_datetime(["2025-01-01", "2025-02-01", "2025-01-15", "2025-03-01",
                                "2025-01-10", "2025-01-20", "2025-02-10", "2025-02-20"]),
        "x": [1, 2, 3, 4, 5, 6, 5, 7],
        "y": [0, 1, 0, 1, 1, 0, 1, 1],
    })
    df.loc[6, ["store", "date", "x", "y"]] = df.loc[4, ["store", "date", "x", "y"]].values   # row 6 copies row 4
    cases = [
        ([0, 2, 4, 5], [1, 3, 6, 7], {"shared_groups": 3, "train_rows_after_test_start": 2, "duplicated_rows": 1}),
        ([0, 1, 2, 3], [4, 5, 6, 7], {"shared_groups": 0, "train_rows_after_test_start": 3, "duplicated_rows": 0}),
        ([0, 5], [4, 7], {"shared_groups": 1, "train_rows_after_test_start": 1, "duplicated_rows": 0}),
    ]
    for tr, te, want in cases:
        got = fn(df.copy(), np.array(tr), np.array(te), "store", "date")
        if not isinstance(got, dict):
            raise AssertionError("return a dict with the three counts")
        if set(got) != set(want):
            raise AssertionError(f"the dict should have exactly these keys: {sorted(want)}")
        for key, value in want.items():
            if _num(got[key], key) != value:
                raise AssertionError(f"train rows {tr}, test rows {te}: {key} should be {value}, got {got[key]}")


register_quiz(
    "w06.22_q1", "b",
    "A score far above anything seen before is a reason to look for leakage first: probe single features, then check "
    "when each top feature becomes known.",
    {"a": "Shipping an unexplained jump is how teams get surprised in production.",
     "c": "Tuning cannot explain a jump this large and may hide the cause.",
     "d": "Adding features before understanding the jump adds more places for a leak to hide."})
register_quiz(
    "w06.22_q2", "c",
    "A refund is issued after the fraud is confirmed, so the column is a consequence of the label: target leakage.",
    {"a": "Age is known when the account exists, before any transaction.",
     "b": "Counts from a backward window ending before the prediction are safe by construction.",
     "d": "The country is known at the time of the transaction."})
register_quiz(
    "w06.22_q3", "a",
    "Selection used the labels of all rows, so it picked features that happen to fit the noise in the validation rows "
    "too. The validation rows were no longer unseen.",
    {"b": "Overfitting alone would show up as a LOW validation score; here validation itself is contaminated.",
     "c": "More folds do not help when every fold's validation rows were seen during selection.",
     "d": "The data is pure noise by construction; the 'signal' was created by the leak."})
register_quiz(
    "w06.22_q4", "d",
    "Scaling uses no labels, so the effect is usually tiny, but it still lets test-row statistics into training. Inside "
    "a pipeline it costs nothing and the question disappears.",
    {"a": "No labels does not mean no information: means and spreads of test rows still flow into training.",
     "b": "It does not make results meaningless; it is a small leak, usually.",
     "c": "Scaling on all rows does not make the estimate pessimistic."})
register_quiz(
    "w06.22_q5", "b",
    "Copies land on both sides, so the model is scored on rows it has memorised: the estimate is optimistic, most of "
    "all for flexible models such as forests or nearest neighbours.",
    {"a": "Duplicates change what the test set measures, so they matter.",
     "c": "Scoring on memorised rows makes the estimate better than reality, not worse.",
     "d": "The main damage is to the estimate, not to training time."})


# ============================================================================== notebook 23: search
def _ref_pipe():
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    return Pipeline([("prep", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])),
                     ("model", LogisticRegression(max_iter=1000))])


def _search_data(seed, n_groups=30, nan=False):
    X, y, g = _grouped_frame(seed, n_groups=n_groups)
    X = X.copy()
    if nan:
        rng = np.random.default_rng(seed)
        X[rng.random(X.shape) < 0.05] = np.nan
    return X, y, g


@exercise("w06.grid_size", hint="Multiply the lengths of the value lists; for a list of grids, add the products.")
def _(fn):
    cases = [({"a": [1, 2, 3]}, 3), ({"a": [1, 2, 3], "b": ["x", "y"]}, 6),
             ({"a": [1, 2], "b": [1, 2], "c": [1, 2, 3, 4]}, 16),
             ([{"a": [1, 2]}, {"b": [1, 2, 3], "c": [0, 1]}], 8), ({}, 1), ({"a": [5]}, 1)]
    for grid, want in cases:
        got = _num(fn(grid), "grid_size")
        if got != want:
            kind = "a list of grids" if isinstance(grid, list) else "a grid"
            raise AssertionError(f"{kind} with {grid}: expected {want} combinations, got {got:g}")


@exercise("w06.make_search", hint="GridSearchCV(Pipeline([('prep', ...), ('model', LogisticRegression(max_iter=1000))]), param_grid, cv=cv, scoring='roc_auc')")
def _(fn):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GridSearchCV, GroupKFold
    from sklearn.pipeline import Pipeline

    cv = GroupKFold(3)
    grid = {"model__C": [0.1, 1.0]}
    s = fn(grid, cv)
    if not isinstance(s, GridSearchCV):
        raise AssertionError("return a GridSearchCV object")
    if not isinstance(s.estimator, Pipeline):
        raise AssertionError("the search should tune a Pipeline, so preprocessing is refitted in every fold")
    names = [n for n, _ in s.estimator.steps]
    if names[-1] != "model" or not isinstance(s.estimator.steps[-1][1], LogisticRegression):
        raise AssertionError("the last step should be named 'model' and be a LogisticRegression")
    if len(names) < 2:
        raise AssertionError("put the preprocessing (imputer and scaler) in the pipeline before the model")
    if s.cv is not cv:
        raise AssertionError("pass the cv object you are given to the search")
    if s.scoring != "roc_auc":
        raise AssertionError("use scoring='roc_auc'")
    if s.param_grid != grid:
        raise AssertionError("pass the param_grid you are given")
    X, y, g = _search_data(0, nan=True)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fn(grid, GroupKFold(3)).fit(X, y, groups=g)
    except ValueError as err:
        raise AssertionError(f"fitting on data with missing values failed ({str(err)[:80]}...): does the pipeline "
                             "impute missing values before the model?")


@exercise("w06.grouped_search", hint="search = make_search({'model__C': Cs}, GroupKFold(k)); search.fit(X, y, groups=groups)")
def _(fn):
    from sklearn.model_selection import GridSearchCV, GroupKFold

    for seed, k in ((1, 3), (2, 4)):
        X, y, g = _search_data(seed)
        Cs = [0.01, 0.1, 1.0, 10.0]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            s = fn(X, y, g, Cs, k)
            ref = GridSearchCV(_ref_pipe(), {"model__C": Cs}, cv=GroupKFold(k), scoring="roc_auc").fit(X, y, groups=g)
        if not hasattr(s, "cv_results_"):
            raise AssertionError("return the search after calling .fit(...)")
        if not isinstance(s.cv, GroupKFold):
            raise AssertionError("the search's cv should be a GroupKFold, because rows of one group belong together")
        if s.cv.get_n_splits() != k:
            raise AssertionError(f"use k={k} folds")
        got = np.asarray(s.cv_results_["mean_test_score"], float)
        if got.shape != (len(Cs),):
            raise AssertionError(f"search exactly the {len(Cs)} values of C you are given")
        if not np.allclose(got, ref.cv_results_["mean_test_score"], atol=1e-4):
            raise AssertionError("the cross-validated scores differ from a grouped search with scaling inside the "
                                 "pipeline and scoring='roc_auc'")


@exercise("w06.time_search", hint="RandomizedSearchCV(pipeline, dists, n_iter=n_iter, cv=TimeSeriesSplit(n_splits), scoring='roc_auc', random_state=seed)")
def _(fn):
    from scipy.stats import loguniform
    from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit

    for seed, n_iter, n_splits in ((0, 5, 3), (3, 4, 4)):
        X, y, dates = _time_frame(seed)
        order = np.argsort(dates.values, kind="stable")
        X, y = X[order], y[order]
        dists = {"model__C": loguniform(1e-3, 1e2)}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            s = fn(X, y, dists, n_iter, n_splits, seed)
            ref = RandomizedSearchCV(_ref_pipe(), dists, n_iter=n_iter, cv=TimeSeriesSplit(n_splits),
                                     scoring="roc_auc", random_state=seed).fit(X, y)
        if not isinstance(s, RandomizedSearchCV):
            raise AssertionError("return a fitted RandomizedSearchCV")
        if not hasattr(s, "cv_results_"):
            raise AssertionError("return the search after calling .fit(X, y)")
        if not isinstance(s.cv, TimeSeriesSplit):
            raise AssertionError("rows are in time order and the model predicts the future: use TimeSeriesSplit")
        if s.cv.get_n_splits() != n_splits:
            raise AssertionError(f"use n_splits={n_splits}")
        if len(s.cv_results_["params"]) != n_iter:
            raise AssertionError(f"try exactly n_iter={n_iter} candidates")
        got = [p["model__C"] for p in s.cv_results_["params"]]
        if not np.allclose(got, [p["model__C"] for p in ref.cv_results_["params"]]):
            raise AssertionError("the sampled values of C differ: pass random_state=seed to the search")
        if not np.allclose(s.cv_results_["mean_test_score"], ref.cv_results_["mean_test_score"], atol=1e-4):
            raise AssertionError("the scores differ from a search with scaling inside the pipeline and "
                                 "scoring='roc_auc'")


def _exact_expected_max(n_configs, n_val, p):
    from scipy.stats import binom

    k = np.arange(n_val + 1)
    cdf = binom.cdf(k, n_val, p)
    prev = np.r_[0.0, cdf[:-1]]
    return float(((cdf ** n_configs - prev ** n_configs) * k / n_val).sum())


@exercise("w06.best_of_noise", hint="rng.binomial(n_val, true_acc, size=n_configs) / n_val, then the max.")
def _(fn):
    vals = [_num(fn(1, 200, 0.7, s), "best_of_noise") for s in range(300)]
    if any(v < 0 or v > 1 for v in vals):
        raise AssertionError("an accuracy must be between 0 and 1")
    if any(abs(v * 200 - round(v * 200)) > 1e-9 for v in vals[:20]):
        raise AssertionError("with n_val=200 every accuracy is a whole number of correct rows divided by 200")
    if abs(np.mean(vals) - 0.7) > 0.01:
        raise AssertionError(f"with ONE configuration the average over many seeds should be about the true accuracy "
                             f"0.7, got {np.mean(vals):.3f}")
    if len(set(vals)) < 5:
        raise AssertionError("the result should change with the seed")
    if fn(20, 200, 0.7, 5) != fn(20, 200, 0.7, 5):
        raise AssertionError("the same seed should give the same result")
    many = np.mean([_num(fn(50, 200, 0.7, s), "best_of_noise") for s in range(200)])
    want = _exact_expected_max(50, 200, 0.7)
    if abs(many - want) > 0.008:
        raise AssertionError(f"with 50 configurations the best score should average about {want:.3f}, got {many:.3f}:"
                             " return the MAXIMUM of the simulated scores")


@exercise("w06.expected_optimism", hint="Average best_of_noise over n_sims seeds (a different seed each time), minus true_acc.")
def _(fn):
    for m, n_val, p in ((1, 200, 0.7), (10, 200, 0.7), (100, 100, 0.6), (30, 1000, 0.8)):
        got = _num(fn(m, n_val, p, 2000, 0), "expected_optimism")
        want = _exact_expected_max(m, n_val, p) - p
        if abs(got - want) > 0.006:
            raise AssertionError(f"{m} configuration(s), {n_val} validation rows, true accuracy {p}: expected an "
                                 f"optimism of about {want:+.3f}, got {got:+.3f}")


def _ref_final(X, y, groups, Cs, seed):
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GridSearchCV, GroupKFold, GroupShuffleSplit

    tr, te = next(GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=seed).split(X, y, groups))
    s = GridSearchCV(_ref_pipe(), {"model__C": Cs}, cv=GroupKFold(5), scoring="roc_auc").fit(X[tr], y[tr], groups=groups[tr])
    test = roc_auc_score(y[te], s.predict_proba(X[te])[:, 1])
    return {"cv_best": s.best_score_, "test": test, "best_C": s.best_params_["model__C"]}


@exercise("w06.final_protocol", hint="Hold out 25% of the groups first; search on the rest only; score the refitted best model once on the held-out rows.")
def _(fn):
    Cs = [0.001, 0.01, 0.1, 1.0, 10.0]
    for seed in (0, 1):
        X, y, g = _search_data(seed + 10, n_groups=40)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            got = fn(X, y, g, Cs, seed)
            ref = _ref_final(X, y, g, Cs, seed)
        if not isinstance(got, dict) or set(got) != set(ref):
            raise AssertionError(f"return a dict with the keys {sorted(ref)}")
        if not np.isclose(_num(got["best_C"], "best_C"), ref["best_C"]):
            raise AssertionError("best_C differs: is the search run on the training groups only, with GroupKFold(5)?")
        if abs(_num(got["cv_best"], "cv_best") - ref["cv_best"]) > 1e-4:
            raise AssertionError("cv_best should be the search's best_score_ on the training part")
        if abs(_num(got["test"], "test") - ref["test"]) > 1e-4:
            raise AssertionError("test should be the ROC AUC of the refitted best model on the held-out groups")


def _ref_nested(X, y, groups, Cs, outer_k, inner_k):
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GridSearchCV, GroupKFold

    scores = []
    for tr, te in GroupKFold(outer_k).split(X, y, groups):
        s = GridSearchCV(_ref_pipe(), {"model__C": Cs}, cv=GroupKFold(inner_k), scoring="roc_auc")
        s.fit(X[tr], y[tr], groups=groups[tr])
        scores.append(roc_auc_score(y[te], s.predict_proba(X[te])[:, 1]))
    return float(np.mean(scores))


@exercise("w06.nested_cv_auc", hint="Outer GroupKFold loop; inside it, grouped_search on the outer-train rows; score on the outer-test rows.")
def _(fn):
    Cs = [0.01, 1.0, 100.0]
    for seed, ok, ik in ((3, 3, 3), (4, 4, 2)):
        X, y, g = _search_data(seed, n_groups=24)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            got = _num(fn(X, y, g, Cs, ok, ik), "nested_cv_auc")
            ref = _ref_nested(X, y, g, Cs, ok, ik)
        if abs(got - ref) > 1e-4:
            raise AssertionError(f"outer_k={ok}, inner_k={ik}: expected the mean outer-fold ROC AUC; your number "
                                 f"{got:.4f} is off. Are the inner folds grouped, and only built from outer-train rows?")


@exercise("w06.one_se_choice", hint="best = max mean; se = its std / sqrt(n_splits); among candidates with mean >= best - se, the smallest C.")
def _(fn):
    cases = [
        ({"param_model__C": [0.01, 0.1, 1.0, 10.0], "mean_test_score": [0.70, 0.78, 0.80, 0.79],
          "std_test_score": [0.02, 0.03, 0.05, 0.04]}, 5, 0.1),
        ({"param_model__C": [10.0, 1.0, 0.1, 0.01], "mean_test_score": [0.81, 0.80, 0.74, 0.60],
          "std_test_score": [0.01, 0.02, 0.02, 0.03]}, 4, 10.0),
        ({"param_model__C": [0.001, 0.01, 0.1], "mean_test_score": [0.74, 0.76, 0.77],
          "std_test_score": [0.04, 0.04, 0.06]}, 9, 0.01),
        ({"param_model__C": [1.0, 0.5], "mean_test_score": [0.9, 0.9], "std_test_score": [0.0, 0.0]}, 3, 0.5),
    ]
    for res, k, want in cases:
        res = {key: np.ma.masked_array(v) if key.startswith("param_") else np.array(v) for key, v in res.items()}
        got = _num(fn(res, k), "one_se_choice")
        if not np.isclose(got, want):
            raise AssertionError(f"means {list(res['mean_test_score'])}, stds {list(res['std_test_score'])}, "
                                 f"{k} folds: expected C = {want}, got {got:g}")


register_quiz(
    "w06.23_q1", "a",
    "Parameters (like logistic-regression weights) are learned by fit; hyperparameters (like C or tree depth) are set "
    "before fit and chosen by comparing validation scores.",
    {"b": "It is the other way round.",
     "c": "Hyperparameters do change the fitted model; that is why they are tuned.",
     "d": "Both kinds exist for every model that has settings."})
register_quiz(
    "w06.23_q2", "c",
    "The best of many noisy validation scores is biased upward (the winner was partly lucky). Expect somewhat less on "
    "new data, and measure it on a test set the search never saw.",
    {"a": "0.83 was chosen as the maximum of 200 noisy numbers, so it is optimistic.",
     "b": "Nothing makes new data easier than the validation folds.",
     "d": "The model is not useless; its score is just a bit lower than the best validation score."})
register_quiz(
    "w06.23_q3", "b",
    "With the pipeline inside the search, every candidate in every fold refits the preprocessing on that fold's "
    "training part only. Preprocessed X would have seen the validation rows.",
    {"a": "Speed is not the reason; it is usually a little slower.",
     "c": "The search works with any estimator, but the estimate is honest only if all fitting happens inside it.",
     "d": "Scaling is not optional for tuning; it is a question of WHERE it is fitted."})
register_quiz(
    "w06.23_q4", "d",
    "cv=5 means plain (stratified) k-fold: groups are ignored. The search then rewards settings that memorise groups, "
    "and best_score_ is optimistic. Pass cv=GroupKFold(5) and groups=... to fit.",
    {"a": "GridSearchCV does not know about groups unless you give it a grouped splitter and the groups.",
     "b": "It does not fail; it silently answers the wrong question.",
     "c": "Shuffling does not keep groups together."})
register_quiz(
    "w06.23_q5", "a",
    "Nested CV estimates how well the whole procedure (search, then refit) works on new data: the inner loop chooses, "
    "the outer loop judges what the choice is worth.",
    {"b": "Nested CV gives one hyperparameter choice per outer fold; the final model still comes from one search on "
          "all training data.",
     "c": "It costs more computation, not less.",
     "d": "It does not replace a final test set when you have enough data to keep one."})


# ============================================================================== notebook 24: the lab
def _lab_clean_ref(df):
    return df.drop_duplicates().drop(columns=[c for c in vd.LAB_LEAKY_COLUMNS if c in df.columns])


def _lab_features(df):
    return [c for c in df.columns if c not in (*vd.LAB_ID_COLUMNS, vd.LAB_TARGET, *vd.LAB_LEAKY_COLUMNS)]


@exercise("w06.lab_probe", hint="Same as notebook 22: single-feature AUC of every numeric column except the target, sorted.")
def _(fn):
    df, _ = vd.make_saas_churn(seed=3, n_companies=80)
    got = fn(df.copy(), "churned")
    if not isinstance(got, pd.Series):
        raise AssertionError("return a pandas Series: index = column name, value = AUC")
    num = [c for c in df.select_dtypes("number").columns if c != "churned"]
    want = pd.Series({c: _ref_auc(df[c], df["churned"]) for c in num}).sort_values(ascending=False)
    if "churned" in got.index:
        raise AssertionError("do not probe the target itself")
    if set(got.index) != set(want.index):
        raise AssertionError(f"expected one value for each of the {len(want)} numeric columns")
    if not np.allclose(got.astype(float).reindex(want.index).values, want.values, atol=1e-6):
        raise AssertionError("some AUC values differ: max(auc, 1 - auc), ignoring missing values")
    if list(got.index[:3]) != list(want.index[:3]):
        raise AssertionError("sort from the highest AUC to the lowest")


@exercise("w06.lab_duplicates", hint="df.duplicated() marks every copy after the first one.")
def _(fn):
    for seed, n in ((4, 60), (5, 90)):
        df, _ = vd.make_saas_churn(seed=seed, n_companies=n)
        got = fn(df.copy())
        if not isinstance(got, dict) or set(got) != {"duplicate_rows", "companies_affected"}:
            raise AssertionError("return a dict with the keys 'duplicate_rows' and 'companies_affected'")
        dup = df[df.duplicated(keep="first")]
        if _num(got["duplicate_rows"], "duplicate_rows") != len(dup):
            raise AssertionError("duplicate_rows should count the extra copies (a row that appears twice adds 1)")
        if _num(got["companies_affected"], "companies_affected") != dup["company_id"].nunique():
            raise AssertionError("companies_affected should count the distinct companies that have at least one copy")


@exercise("w06.lab_clean", hint="Drop exact duplicate rows and the columns that are not known at prediction time; keep everything else.")
def _(fn):
    for seed in (6, 7):
        df, _ = vd.make_saas_churn(seed=seed, n_companies=70)
        got = fn(df.copy())
        if not isinstance(got, pd.DataFrame):
            raise AssertionError("return a DataFrame")
        want = _lab_clean_ref(df)
        bad = [c for c in vd.LAB_LEAKY_COLUMNS if c in got.columns]
        if bad:
            raise AssertionError(f"{len(bad)} column(s) that are only known after the prediction date are still there")
        if got.duplicated().any():
            raise AssertionError("some rows are still exact duplicates")
        missing = [c for c in want.columns if c not in got.columns]
        if missing:
            raise AssertionError(f"you removed column(s) that are fine to keep: {missing}. Keep the ids too: the "
                                 "evaluation needs company_id and month")
        extra = [c for c in got.columns if c not in want.columns]
        if extra:
            raise AssertionError(f"unexpected new column(s): {extra}")
        if len(got) != len(want):
            raise AssertionError(f"expected {len(want)} rows after removing copies, got {len(got)}: remove only exact "
                                 "copies, and keep one of each")


@exercise("w06.lab_pipeline", hint="ColumnTransformer (impute numeric; impute + one-hot categorical) then the given RandomForestClassifier, in one Pipeline.")
def _(fn):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.utils.validation import check_is_fitted
    from sklearn.exceptions import NotFittedError

    df, _ = vd.make_saas_churn(seed=8, n_companies=60)
    df = _lab_clean_ref(df)
    feats = _lab_features(df)
    cat = ["plan", "industry"]
    num = [c for c in feats if c not in cat]
    pipe = fn(num, cat)
    if not isinstance(pipe, Pipeline):
        raise AssertionError("return a scikit-learn Pipeline, so every preprocessing step is fitted inside each split")
    model = pipe.steps[-1][1]
    if not isinstance(model, RandomForestClassifier):
        raise AssertionError("keep the lab's model as the last step: RandomForestClassifier(...)")
    p = model.get_params()
    if (p["n_estimators"], p["min_samples_leaf"], p["random_state"]) != (200, 5, 0):
        raise AssertionError("keep the model settings unchanged (n_estimators=200, min_samples_leaf=5, random_state=0)"
                             ": this lab changes the evaluation, not the model")
    try:
        check_is_fitted(model)
        raise AssertionError("return the pipeline unfitted")
    except NotFittedError:
        pass
    train, test = df[df["month"] <= 8], df[df["month"] > 8].copy()
    test.loc[test.index[:3], "industry"] = ["mining", None, "space"]
    try:
        pipe.fit(train[feats], train["churned"])
        proba = pipe.predict_proba(test[feats])
    except Exception as err:   # noqa: BLE001 - report any failure in plain words
        raise AssertionError(f"the pipeline failed on rows with missing or new industries: {type(err).__name__}: "
                             f"{str(err)[:100]}")
    if proba.shape != (len(test), 2):
        raise AssertionError("predict_proba should give two columns, one row per test row")


def _ref_month_splits(months, first_test_month, block):
    months = np.asarray(months)
    out = []
    start = first_test_month
    while start <= months.max():
        test = np.flatnonzero((months >= start) & (months < start + block))
        out.append((np.flatnonzero(months < start), test))
        start += block
    return out


@exercise("w06.lab_splits", hint="For start = first_test_month, first_test_month + block, ...: train = months before start, test = the next `block` months.")
def _(fn):
    rng = np.random.default_rng(9)
    cases = [(rng.permutation(np.repeat(np.arange(1, 13), 5)), 4, 3), (rng.permutation(np.arange(1, 11).repeat(2)), 3, 4),
             (np.arange(1, 10), 5, 2)]
    for months, first, block in cases:
        got = _pairs(fn(pd.Series(months), first, block), "month_splits")
        ref = _ref_month_splits(months, first, block)
        if len(got) != len(ref):
            raise AssertionError(f"months {months.min()}-{months.max()}, first test month {first}, block {block}: "
                                 f"expected {len(ref)} splits, got {len(got)}")
        for i, ((tr, te), (rtr, rte)) in enumerate(zip(got, ref)):
            if len(tr) and len(te) and months[tr].max() >= months[te].min():
                raise AssertionError(f"split {i + 1}: training months must all come before the test months")
            if set(te) != set(rte.tolist()):
                raise AssertionError(f"split {i + 1}: the test rows should be exactly the rows of months "
                                     f"{rte.size and months[rte].min()}-{rte.size and months[rte].max()}")
            if set(tr) != set(rtr.tolist()):
                raise AssertionError(f"split {i + 1}: train on every row from the months before the test block")


@lru_cache(maxsize=None)
def lab_ground_truth(seed: int = 0) -> float:
    """Accuracy of the lab's model, trained honestly on the whole lab table, on brand-new companies of months 13-15."""
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    df, _ = vd.make_saas_churn(seed)
    df = _lab_clean_ref(df)
    feats = _lab_features(df)
    cat = ["plan", "industry"]
    num = [c for c in feats if c not in cat]
    prep = ColumnTransformer([("num", SimpleImputer(strategy="median"), num),
                              ("cat", Pipeline([("i", SimpleImputer(strategy="most_frequent")),
                                                ("o", OneHotEncoder(handle_unknown="ignore"))]), cat)])
    pipe = Pipeline([("prep", prep), ("model", RandomForestClassifier(n_estimators=200, min_samples_leaf=5,
                                                                      random_state=0, n_jobs=-1))])
    pipe.fit(df[feats], df[vd.LAB_TARGET])
    future = vd.make_saas_future(seed, n_companies=1500)
    return float((pipe.predict(future[feats]) == future[vd.LAB_TARGET]).mean())


@exercise("w06.lab_honest_score", hint="Mean accuracy over month_splits(clean['month'], 4, 3) of the honest pipeline on the clean table.")
def _(score):
    got = _num(score, "honest_score")
    if not 0 <= got <= 1:
        raise AssertionError("report the accuracy as a number between 0 and 1")
    truth = lab_ground_truth(0)
    if got > truth + 0.05:
        raise AssertionError(f"your estimate {got:.3f} is still optimistic: something still lets the model see test "
                             "information (a column, a copy, a company, or a later month)")
    if got < truth - 0.05:
        raise AssertionError(f"your estimate {got:.3f} is more pessimistic than it should be: check that you train on "
                             "every earlier month and keep all the legitimate features")


@exercise("w06.lab_issues", hint="Every planted issue makes the 0.98 too high; the distractors are real facts that do not inflate the score.")
def _(answer):
    if isinstance(answer, str) or not hasattr(answer, "__iter__"):
        raise AssertionError("give a set of codes, like {'code_one', 'code_two'}")
    got = {str(a).strip() for a in answer}
    unknown = got - set(vd.LAB_ISSUES)
    if unknown:
        raise AssertionError(f"not codes from the table: {sorted(unknown)}")
    why_not = {
        "class_imbalance": "imbalance makes accuracy a weak metric, but it does not make the cross-validated score "
                           "optimistic",
        "missing_values_in_industry": "missing values are a cleaning task; they do not carry test information into "
                                      "training",
        "unscaled_features": "a random forest does not care about scale, and scale cannot leak labels",
        "too_many_trees": "more trees make a forest slower, not optimistic",
        "plan_price_is_too_predictive": "the price is known at the prediction date; a strong honest feature is not a "
                                        "leak",
    }
    wrong = sorted(got & set(why_not))
    if wrong:
        raise AssertionError(f"'{wrong[0]}' is not a leak: {why_not[wrong[0]]}")
    missing = vd.PLANTED - got
    if missing:
        areas = []
        if missing & {"retention_offer_after_cancel", "last_login_measured_at_export"}:
            areas.append("the data dictionary's known_at column")
        if missing & {"duplicate_rows", "selection_fitted_on_all_rows"}:
            areas.append("the leaky code, line by line")
        if missing & {"same_company_in_train_and_test", "training_on_future_months"}:
            areas.append("which rows end up on both sides of the split")
        raise AssertionError(f"you found {len(vd.PLANTED) - len(missing)} of the {len(vd.PLANTED)} planted issues. "
                             f"Look again at {' and '.join(areas)}")


register_quiz(
    "w06.24_q1", "b",
    "Without the two columns, copies of rows and seats of the same company still sit on both sides of random folds; the "
    "forest recognises the company and recalls its label.",
    {"a": "The forest's settings were never the cause; the evaluation was.",
     "c": "Imbalance does not make cross-validation optimistic.",
     "d": "Removing the leaky columns was right; the remaining gap comes from the split."})
register_quiz(
    "w06.24_q2", "c",
    "An honest report gives the number, what it is compared with (the baseline), and how it was measured (forward in "
    "time, whole companies, no duplicates), so others can trust and reproduce it.",
    {"a": "0.98 was measured with leaks; reporting it would mislead every decision built on it.",
     "b": "A number without the baseline hides how much the model really adds.",
     "d": "A modest honest score is still useful information; hiding it helps nobody."})
register_quiz(
    "w06.24_q3", "a",
    "Churn drifts over the year (prices rose after month 8), and the model will be used on months after its training "
    "data. Testing on later months is the only way to include that change in the estimate.",
    {"b": "Each company appears in only one month, so grouping alone is already satisfied by any month split.",
     "c": "Time order does not change the class balance.",
     "d": "Forward splits train on fewer rows, which is the honest price of predicting the future."})
register_quiz(
    "w06.24_q4", "d",
    "At prediction time the retention offer has not been sent and the export-date login gap does not exist. A model "
    "trained to rely on them meets missing or meaningless values in production and its accuracy collapses.",
    {"a": "Strong predictors that are not available at prediction time are not predictors at all.",
     "b": "Accuracy on leaky columns says nothing about the model's value in production.",
     "c": "Removing a column the model depends on changes its predictions; it is not harmless."})


# ============================================================================== fallbacks for later cells
def _ref_probe(df, target):
    num = [c for c in df.select_dtypes("number").columns if c != target]
    return pd.Series({c: _ref_auc(df[c], df[target]) for c in num}).sort_values(ascending=False)


def _ref_lab_pipeline(numeric, categorical):
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    prep = ColumnTransformer([("num", SimpleImputer(strategy="median"), numeric),
                              ("cat", Pipeline([("i", SimpleImputer(strategy="most_frequent")),
                                                ("o", OneHotEncoder(handle_unknown="ignore"))]), categorical)])
    return Pipeline([("prep", prep), ("model", RandomForestClassifier(n_estimators=200, min_samples_leaf=5,
                                                                      random_state=0))])


def _ref_group_kfold(groups, k):
    from sklearn.model_selection import GroupKFold
    groups = np.asarray(groups)
    return list(GroupKFold(k).split(np.zeros(len(groups)), groups=groups))


def _ref_grouped_search(X, y, groups, Cs, k):
    from sklearn.model_selection import GridSearchCV, GroupKFold
    return GridSearchCV(_ref_pipe(), {"model__C": list(Cs)}, cv=GroupKFold(k), scoring="roc_auc").fit(X, y, groups=groups)


def _ref_best_of_noise(n_configs, n_val, true_acc, seed):
    return float((np.random.default_rng(seed).binomial(n_val, true_acc, size=n_configs) / n_val).max())


_REFERENCES = {
    "kfold_indices": lambda n, k, seed: [(np.setdiff1d(np.arange(n), t), np.sort(t))
                                         for t in np.array_split(np.random.default_rng(seed).permutation(n), k)],
    "group_kfold_indices": _ref_group_kfold,
    "forward_day_splits": _ref_forward_days,
    "probe_features": _ref_probe,
    "probe_columns": _ref_probe,
    "grouped_search": _ref_grouped_search,
    "best_of_noise": _ref_best_of_noise,
    "clean_table": _lab_clean_ref,
    "make_honest_pipeline": _ref_lab_pipeline,
    "month_splits": _ref_month_splits,
}


def use(fn, *args, **kwargs):
    """Call your function `fn`; if it is not written yet, use the course's reference version (and say so)."""
    try:
        return fn(*args, **kwargs)
    except NotImplementedError:
        name = getattr(fn, "__name__", "")
        if name not in _REFERENCES:
            raise
        print(f"(note: `{name}` is not finished yet, so the course's reference version was used here. "
              "Come back to that exercise.)")
        return _REFERENCES[name](*args, **kwargs)
