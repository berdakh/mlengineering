"""Week 5 graders: from theory to practice - framing, baselines, metrics (notebooks 17-20).

Three kinds of exercise:
* framing answers (small dicts of choices or numbers), checked key by key with a message that names the key and
  the idea that is off, never the answer;
* functions (splits, metrics, thresholds, curves), run on several random inputs and edge cases and compared with an
  independent reference (often scikit-learn);
* model builders (functions returning an unfitted scikit-learn pipeline), fitted here on the course churn table
  and checked for behaviour: quality, robustness to unseen or missing categories, scale invariance.
"""
from __future__ import annotations

import math
import re
from functools import lru_cache

import numpy as np
import pandas as pd

from mlcourse.grader import exercise, register_quiz

_REFERENCES: dict = {}
_NOTED: set = set()


def _ref(fn):
    _REFERENCES[fn.__name__.lstrip("_")] = fn
    return fn


def use(fn, *args, **kwargs):
    """Call your function `fn`; if it is not written yet, use the course's reference version (and say so)."""
    try:
        return fn(*args, **kwargs)
    except NotImplementedError:
        name = getattr(fn, "__name__", "")
        if name not in _REFERENCES:
            raise
        if name not in _NOTED:  # say it once per function, not once per call in a loop
            _NOTED.add(name)
            print(f"(note: `{name}` is not finished yet, so the course's reference version was used here. "
                  "Come back to that exercise.)")
        return _REFERENCES[name](*args, **kwargs)


def _close(a, b, tol=1e-9) -> bool:
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return False
    if math.isinf(a) or math.isinf(b):
        return a == b
    return abs(a - b) <= tol * max(1.0, abs(b))


def _number(x, what: str) -> float:
    if isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, float, np.integer, np.floating)):
        raise AssertionError(f"{what} should be a number, got {type(x).__name__}")
    return float(x)


def _choices(answer, expected: dict, messages: dict, what: str = "answer") -> None:
    """Compare a dict of choices key by key; report the first wrong key with its message."""
    if not isinstance(answer, dict):
        raise AssertionError(f"the {what} should be a dict with keys {sorted(expected, key=str)}")
    missing = [k for k in expected if k not in answer]
    if missing:
        raise AssertionError(f"the {what} is missing the key(s) {missing}")
    for k, v in expected.items():
        got = answer[k]
        if isinstance(got, str):
            got = got.strip().lower()
        if isinstance(v, float):
            ok = isinstance(got, (int, float, np.integer, np.floating)) and not isinstance(got, bool) and _close(got, v, 1e-6)
        elif isinstance(v, (set, frozenset)):
            ok = isinstance(got, (set, frozenset, list, tuple)) and {str(g).strip().lower() for g in got} == v
        else:
            ok = got == v
        if not ok:
            if got in ("?", "", None):
                raise AssertionError(f"`{k}` is not filled in yet")
            raise AssertionError(f"`{k}` is not right: {messages[k]}")


def _bool_dict(answer, expected: dict[int, bool], hints: dict[int, str]) -> None:
    if not isinstance(answer, dict):
        raise AssertionError("the answer should be a dict {statement number: True or False}")
    if set(answer) != set(expected):
        raise AssertionError(f"use exactly the statement numbers {sorted(expected)} as keys")
    if any(not isinstance(v, (bool, np.bool_)) for v in answer.values()):
        raise AssertionError("every value should be True or False (no quotes)")
    wrong = [k for k in expected if bool(answer[k]) != expected[k]]
    if wrong:
        theme = hints.get(wrong[0], "")
        raise AssertionError(f"{len(wrong)} of {len(expected)} statements are judged wrongly. {theme}")


# --------------------------------------------------------------------------- data
@lru_cache(maxsize=None)
def _churn() -> pd.DataFrame:
    from mlcourse.churn import build_churn_table
    return build_churn_table()


def _xy(df=None):
    from mlcourse.churn import FEATURES
    df = _churn() if df is None else df
    return df[FEATURES], df["churned"]


@lru_cache(maxsize=None)
def _split(seed: int = 0):
    from sklearn.model_selection import train_test_split
    X, y = _xy()
    return train_test_split(X, y, test_size=0.25, random_state=seed, stratify=y)


def _preprocessor():
    from sklearn.compose import make_column_transformer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from mlcourse.churn import CATEGORICAL, NUMERIC
    return make_column_transformer((StandardScaler(), NUMERIC),
                                   (OneHotEncoder(handle_unknown="ignore"), CATEGORICAL))


def _builder(fn, *args, what="the function"):
    from sklearn.base import clone
    model = fn(*args)
    if model is None or not hasattr(model, "fit") or not hasattr(model, "predict_proba"):
        raise AssertionError(f"{what} should return a scikit-learn model or pipeline with fit and predict_proba")
    try:
        return clone(model)
    except Exception as err:  # noqa: BLE001
        raise AssertionError(f"{what} should return a scikit-learn estimator ({err})") from None


def _toy_frame(n: int, seed: int) -> tuple[pd.DataFrame, pd.Series]:
    """A small frame with the churn columns, for testing functions that take X and y."""
    from mlcourse.churn import FEATURES
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({
        "tenure_days": rng.integers(10, 600, n), "n_orders": rng.integers(1, 10, n),
        "total_spent": rng.gamma(2, 80, n).round(2), "avg_order_value": rng.gamma(2, 30, n).round(2),
        "days_since_last_order": rng.integers(0, 400, n), "n_tickets": rng.integers(0, 4, n),
        "n_open_tickets": rng.integers(0, 2, n), "share_mobile": rng.random(n).round(2),
        "segment": rng.choice(["consumer", "student", "small_business"], n),
        "city": rng.choice(["Almaty", "Astana", "Taraz", None], n),
    })[FEATURES]
    logit = (X["days_since_last_order"] - 150) / 80 - 0.3 * X["n_orders"] + rng.normal(0, 1, n)
    y = pd.Series((logit > 0).astype(int), name="churned")
    X.index = rng.permutation(np.arange(1000, 1000 + n))
    y.index = X.index
    return X, y


# =========================================================================== 17 · framing
JOB_STATEMENTS = {1: True, 2: False, 3: True, 4: False, 5: True, 6: False}


@exercise("w05.job_vs_textbook", hint="Reread section 1: who assembles the data, what the test set is for, and "
                                      "what happens after a prediction.")
def _t_job(answer):
    _bool_dict(answer, JOB_STATEMENTS, {
        1: "Think about who decides which rows, which label and which dates go into the table.",
        2: "Is a good test score a promise about the future, when customers and data change?",
        3: "What happens to an estimate when you pick the best of many results on the same data?",
        4: "Do a wasted phone call and a lost customer cost the same?",
        5: "Can you judge a model without knowing what action follows its prediction?",
        6: "Ask whether each column would exist at the moment the model is used.",
    })


@_ref
def _simulate_selection_bias(n_test, k, seed):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, n_test)
    preds = rng.integers(0, 2, (k, n_test))
    return float((preds == y).mean(axis=1).max())


@exercise("w05.selection_bias", hint="Draw the labels once, then k independent random prediction vectors of the same "
                                     "length; score each one and keep the largest accuracy.")
def _t_selection_bias(fn):
    a = fn(200, 5, 1)
    _number(a, "the result")
    if not 0 <= a <= 1:
        raise AssertionError(f"an accuracy must be between 0 and 1, got {a}")
    if fn(200, 5, 1) != a:
        raise AssertionError("the same seed should give the same result: create the generator from `seed`")
    if len({fn(200, 5, s) for s in range(6)}) < 2:
        raise AssertionError("different seeds should usually give different results")
    one = np.mean([fn(200, 1, s) for s in range(40)])
    if not 0.46 <= one <= 0.54:
        raise AssertionError(f"with k=1 a coin-flip classifier should average about 0.5 accuracy, got {one:.3f}")
    many = np.mean([fn(200, 50, s) for s in range(40)])
    if many < one + 0.04:
        raise AssertionError(f"the best of 50 coin-flip classifiers should look clearly better than one "
                             f"(got {many:.3f} vs {one:.3f}): are you keeping the maximum over the k classifiers?")
    big = np.mean([fn(5000, 50, s) for s in range(10)])
    if big > 0.53:
        raise AssertionError(f"with 5,000 test rows the best of 50 should be close to 0.5, got {big:.3f}")
    if fn(1, 1, 0) not in (0.0, 1.0):
        raise AssertionError("with a single test row the accuracy must be 0 or 1")


@_ref
def _split_three_ways(df, seed):
    n = len(df)
    n_test = n_val = int(0.2 * n)
    order = np.random.default_rng(seed).permutation(n)
    test = df.iloc[order[:n_test]]
    val = df.iloc[order[n_test:n_test + n_val]]
    train = df.iloc[order[n_test + n_val:]]
    return train, val, test


@exercise("w05.split_three_ways", hint="Shuffle the row positions with a generator made from `seed`, then cut the "
                                       "shuffled positions into three pieces and use .iloc.")
def _t_split3(fn):
    for n, seed in [(100, 0), (37, 3), (5, 1)]:
        df = pd.DataFrame({"a": np.arange(n), "b": np.arange(n) * 2.0}, index=np.arange(n) * 7 + 3)
        out = fn(df.copy(), seed)
        if not isinstance(out, tuple) or len(out) != 3:
            raise AssertionError("return three DataFrames: train, val, test")
        tr, va, te = out
        if not all(isinstance(p, pd.DataFrame) for p in out):
            raise AssertionError("each part should be a DataFrame")
        want = (n - 2 * int(0.2 * n), int(0.2 * n), int(0.2 * n))
        if (len(tr), len(va), len(te)) != want:
            raise AssertionError(f"for {n} rows the sizes should be {want} (train, val, test), "
                                 f"got {(len(tr), len(va), len(te))}")
        idx = list(tr.index) + list(va.index) + list(te.index)
        if len(set(idx)) != len(idx):
            raise AssertionError("a row appears in more than one part: the parts must not overlap")
        if set(idx) != set(df.index):
            raise AssertionError("some rows are missing or invented: together the parts must be the whole table")
        if list(tr.columns) != list(df.columns):
            raise AssertionError("keep all the columns in each part")
        again = fn(df.copy(), seed)
        if list(again[2].index) != list(te.index):
            raise AssertionError("the same seed must give the same split (reproducibility)")
    df = pd.DataFrame({"a": np.arange(100)})
    if list(fn(df, 0)[2].index) == list(fn(df, 1)[2].index):
        raise AssertionError("different seeds should give different test sets")
    if list(fn(df, 0)[2].index) == list(range(80, 100)) or list(fn(df, 0)[2].index) == list(range(20)):
        raise AssertionError("the rows are not shuffled: the test set is just the first or last rows")


@_ref
def _snapshot(orders, cutoff, horizon_days):
    end = cutoff + pd.Timedelta(days=horizon_days)
    history = orders[orders["order_date"] <= cutoff]
    future = orders[(orders["order_date"] > cutoff) & (orders["order_date"] <= end)]
    return history, future


@exercise("w05.snapshot", hint="Two boolean masks on `order_date`: on or before the cutoff; strictly after the "
                               "cutoff and on or before cutoff + horizon.")
def _t_snapshot(fn):
    cut = pd.Timestamp("2025-06-30")
    dates = pd.to_datetime(["2025-01-01", "2025-06-29", "2025-06-30", "2025-07-01", "2025-09-28",
                            "2025-09-29", "2025-10-15", "2024-12-31"])
    orders = pd.DataFrame({"order_id": range(1, 9), "customer_id": [1, 1, 2, 2, 3, 3, 4, 5],
                           "order_date": dates, "status": ["delivered"] * 7 + ["cancelled"]})
    before = orders.copy()
    out = fn(orders, cut, 90)
    if not isinstance(out, tuple) or len(out) != 2:
        raise AssertionError("return two DataFrames: history, future")
    h, f = out
    if not orders.equals(before):
        raise AssertionError("do not modify the orders table you were given")
    if 3 not in set(h["order_id"]):
        raise AssertionError("an order placed ON the cutoff day is history (it happened before the prediction)")
    if set(h["order_id"]) != {1, 2, 3, 8}:
        raise AssertionError("history should be every order on or before the cutoff (any status)")
    if 5 not in set(f["order_id"]):
        raise AssertionError("an order exactly `horizon_days` after the cutoff is still inside the label window")
    if {6, 7} & set(f["order_id"]):
        raise AssertionError("an order after cutoff + horizon is outside the label window")
    if set(f["order_id"]) != {4, 5}:
        raise AssertionError("future should be orders strictly after the cutoff and up to cutoff + horizon_days")
    h2, f2 = fn(orders, pd.Timestamp("2025-07-01"), 30)
    if set(h2["order_id"]) != {1, 2, 3, 4, 8} or set(f2["order_id"]) != set():
        raise AssertionError("the result should follow the `cutoff` and `horizon_days` arguments, not fixed dates")


CANDIDATE_FEATURES = {
    "days_since_last_order": True, "orders_in_next_90_days": False, "segment": True,
    "tickets_opened_last_30_days": True, "refund_issued_after_cutoff": False,
    "answered_retention_call": False, "tenure_days": True, "lifetime_spend_including_next_quarter": False,
}


@exercise("w05.available_features", hint="For each name ask: on the morning we score customers, could we compute "
                                         "this from the database as it is then?")
def _t_available(answer):
    if isinstance(answer, str) or not isinstance(answer, (set, list, tuple, frozenset)):
        raise AssertionError("the answer should be a set of feature names, e.g. {\"segment\", ...}")
    got = {str(a).strip() for a in answer}
    unknown = got - set(CANDIDATE_FEATURES)
    if unknown:
        raise AssertionError(f"{sorted(unknown)} is not one of the candidate names: copy names exactly")
    future = {k for k in got if not CANDIDATE_FEATURES[k]}
    if future:
        raise AssertionError(f"{len(future)} of your choices is only known AFTER the prediction time")
    missed = {k for k, v in CANDIDATE_FEATURES.items() if v} - got
    if missed:
        raise AssertionError(f"you left out {len(missed)} feature(s) that are known at prediction time")


@_ref
def _policy_value(y_true, contact, value_saved, contact_cost, success_rate):
    y = np.asarray(y_true, dtype=float)
    c = np.asarray(contact, dtype=bool)
    return float((success_rate * value_saved * y[c] - contact_cost).sum())


@exercise("w05.policy_value", hint="Only contacted customers count. Each contact costs `contact_cost`; a contacted "
                                   "churner also brings back `success_rate * value_saved` on average.")
def _t_policy(fn):
    rng = np.random.default_rng(5)
    cases = [([1, 0, 1, 0], [1, 1, 0, 0], 60, 5, 0.25), ([0, 0, 0], [1, 1, 1], 60, 5, 0.25),
             ([1, 1], [0, 0], 60, 5, 0.25), ([1], [1], 100, 10, 1.0)]
    for _ in range(5):
        n = int(rng.integers(5, 40))
        cases.append((rng.integers(0, 2, n), rng.integers(0, 2, n).astype(bool), float(rng.uniform(10, 200)),
                      float(rng.uniform(1, 20)), float(rng.uniform(0.1, 0.9))))
    for y, c, v, k, s in cases:
        got = _number(fn(y, c, v, k, s), "the value")
        want = _policy_value(y, c, v, k, s)
        if not _close(got, want, 1e-6):
            if _close(got, float(np.sum(np.asarray(y)) * s * v - np.sum(c) * k), 1e-6) and not _close(want, got):
                raise AssertionError("you count churners who were NOT contacted: only a contact can save a customer")
            raise AssertionError(f"wrong value for y={list(np.asarray(y))[:6]}..., contact={list(np.asarray(c, int))[:6]}..., "
                                 f"value_saved={v:.0f}, contact_cost={k:.0f}, success_rate={s:.2f}")
    got = fn(pd.Series([1, 0, 1]), pd.Series([True, False, True]), 60, 5, 0.25)
    if not _close(got, 20.0):
        raise AssertionError("the function should also work with pandas Series inputs")


@_ref
def _break_even_precision(contact_cost, value_saved, success_rate):
    gain = value_saved * success_rate
    return float("inf") if gain <= 0 else contact_cost / gain


@exercise("w05.break_even_precision", hint="At the break-even point, the average gain per contact equals its cost: "
                                           "precision × success_rate × value_saved = contact_cost.")
def _t_break_even(fn):
    for c, v, s in [(5, 60, 0.25), (12, 60, 0.3), (1, 10, 0.5), (30, 50, 0.4), (0, 60, 0.3)]:
        got = _number(fn(c, v, s), "the precision")
        want = _break_even_precision(c, v, s)
        if not _close(got, want, 1e-9):
            raise AssertionError(f"wrong break-even precision for contact_cost={c}, value_saved={v}, success_rate={s}")
    got = fn(5, 60, 0.0)
    if not (isinstance(got, float) and math.isinf(got)):
        raise AssertionError("when a contact can never save anyone (success_rate 0) return float('inf'): no precision "
                             "is enough")


FRAMING_CHURN = {"unit": "customer", "label": "b", "prediction_time": "a", "decision": "c",
                 "cost_fp": 5.0, "cost_fn": 10.0, "budget": 100.0}
FRAMING_CHURN_MSG = {
    "unit": "the model scores one thing per row: what does the team call?",
    "label": "the label must be observable a fixed time after the prediction, and match what the team cares about",
    "prediction_time": "a prediction is useful only if it is made before the decision, from data that exists then",
    "decision": "what does the team do with the scores, given that it cannot call everyone?",
    "cost_fp": "a false positive is a call to someone who was not going to leave: what does that call cost?",
    "cost_fn": "a false negative is a churner you did not call: what net value did you give up? Remember the call "
               "only works some of the time and would itself have cost money",
    "budget": "how many customers can the team contact per quarter?",
}


@exercise("w05.churn_framing", hint="Fill in the worksheet from the retention team's message, one key at a time.")
def _t_churn_framing(answer):
    _choices(answer, FRAMING_CHURN, FRAMING_CHURN_MSG, "framing")


FRAMING_TICKET = {"unit": "ticket", "label": "a", "prediction_time": "b",
                  "allowed_features": {"topic", "segment", "past_tickets"}}
FRAMING_TICKET_MSG = {
    "unit": "what is routed, one at a time?",
    "label": "the label should say whether this ticket ends up slow, measured the same way for every ticket",
    "prediction_time": "routing happens once; what do we know at that moment?",
    "allowed_features": "keep exactly the facts that exist when the ticket is opened",
}


@exercise("w05.ticket_framing", hint="Ask of every choice: is it known at the moment the ticket is routed?")
def _t_ticket(answer):
    _choices(answer, FRAMING_TICKET, FRAMING_TICKET_MSG, "framing")


ML_OR_NOT = {1: "rule", 2: "ml", 3: "no_prediction", 4: "rule", 5: "ml"}


@exercise("w05.ml_or_not", hint="ML earns its cost when the pattern is unknown and must be learned from examples; a "
                                "known rule is cheaper and easier to trust; a report predicts nothing.")
def _t_ml_or_not(answer):
    if not isinstance(answer, dict) or set(answer) != set(ML_OR_NOT):
        raise AssertionError(f"the answer should be a dict with keys {sorted(ML_OR_NOT)}")
    allowed = {"ml", "rule", "no_prediction"}
    bad = [k for k, v in answer.items() if str(v).strip().lower() not in allowed]
    if bad:
        raise AssertionError(f"use only the values {sorted(allowed)} (check scenario {bad[0]})")
    wrong = [k for k in ML_OR_NOT if str(answer[k]).strip().lower() != ML_OR_NOT[k]]
    if wrong:
        raise AssertionError(f"{len(wrong)} of 5 scenarios are classified wrongly")


# =========================================================================== 18 · baselines
@_ref
def _majority_accuracy(y_train, y_test):
    vals, counts = np.unique(np.asarray(y_train), return_counts=True)
    majority = vals[np.argmax(counts)]
    return float(np.mean(np.asarray(y_test) == majority))


@exercise("w05.majority_accuracy", hint="Find the most common class in y_train (not y_test!), then the share of "
                                        "y_test equal to it.")
def _t_majority(fn):
    from sklearn.dummy import DummyClassifier
    rng = np.random.default_rng(2)
    cases = [([0, 0, 1], [1, 1, 1, 0]), ([1, 1, 0], [1, 0, 0, 0]), ([0, 1], [0, 1, 1])]
    for _ in range(6):
        p = rng.uniform(0.1, 0.9)
        cases.append((rng.random(int(rng.integers(5, 60))) < p, rng.random(int(rng.integers(5, 60))) < 1 - p))
    for ytr, yte in cases:
        ytr, yte = np.asarray(ytr).astype(int), np.asarray(yte).astype(int)
        want = DummyClassifier(strategy="most_frequent").fit(np.zeros((len(ytr), 1)), ytr).score(
            np.zeros((len(yte), 1)), yte)
        got = _number(fn(ytr, yte), "the accuracy")
        if not _close(got, want, 1e-9):
            if _close(got, max(yte.mean(), 1 - yte.mean())):
                raise AssertionError("you picked the majority class of y_test: the baseline may only learn from y_train")
            raise AssertionError(f"wrong accuracy for y_train={list(ytr)[:8]}..., y_test={list(yte)[:8]}...")
    got = fn(pd.Series([1, 1, 0]), pd.Series([1, 0]))
    if not _close(got, 0.5):
        raise AssertionError("the function should also work with pandas Series")


@_ref
def _recency_rule(X, threshold):
    return (np.asarray(X["days_since_last_order"]) > threshold).astype(int)


@exercise("w05.recency_rule", hint="Compare the `days_since_last_order` column with the threshold (strictly greater) "
                                   "and convert True/False to 1/0.")
def _t_recency(fn):
    X, _ = _toy_frame(30, 1)
    for t in [0, 90, 150, 1000]:
        got = np.asarray(fn(X, t))
        want = _recency_rule(X, t)
        if got.shape != want.shape:
            raise AssertionError(f"expected one prediction per row ({len(X)}), got shape {got.shape}")
        if not set(np.unique(got)) <= {0, 1}:
            raise AssertionError("predictions should be 0 or 1")
        if not np.array_equal(got.astype(int), want):
            raise AssertionError(f"wrong predictions for threshold={t}: predict 1 when the customer has not ordered "
                                 "for MORE than threshold days")
    X2 = pd.DataFrame({"days_since_last_order": [90, 91, 89]}, index=[5, 2, 9])
    if list(np.asarray(fn(X2, 90)).astype(int)) != [0, 1, 0]:
        raise AssertionError("a customer exactly `threshold` days since the last order should get 0 (strictly greater)")


@_ref
def _best_rule_threshold(X, y, candidates):
    y = np.asarray(y)
    accs = [np.mean(_recency_rule(X, t) == y) for t in candidates]
    best = max(accs)
    return min(t for t, a in zip(candidates, accs) if a == best)


@exercise("w05.best_rule_threshold", hint="Loop over the candidates, compute the rule's accuracy on (X, y) for each, "
                                          "keep the best; on a tie keep the smallest threshold.")
def _t_best_rule(fn):
    for seed in range(4):
        X, y = _toy_frame(80, seed)
        cands = list(range(0, 400, 25))
        got = fn(X, y, cands)
        want = _best_rule_threshold(X, y, cands)
        if got not in cands:
            raise AssertionError("return one of the candidate thresholds")
        acc = lambda t: np.mean(_recency_rule(X, t) == np.asarray(y))  # noqa: E731
        if acc(got) < acc(want) - 1e-12:
            raise AssertionError(f"threshold {got} is not the most accurate candidate on the data you were given")
        if got != want:
            raise AssertionError("several thresholds tie for the best accuracy: return the smallest of them")
    X = pd.DataFrame({"days_since_last_order": [10, 20, 300, 400]})
    if fn(X, [0, 0, 1, 1], [500, 100, 50, 200]) != 50:
        raise AssertionError("candidates may come in any order; ties go to the smallest threshold")


def _check_pipeline_basics(fn, what):
    from mlcourse.churn import CATEGORICAL
    Xtr, Xte, ytr, yte = _split(0)
    model = _builder(fn, what=what)
    try:
        model.fit(Xtr, ytr)
    except Exception as err:  # noqa: BLE001
        raise AssertionError(f"fitting {what}'s model on the churn training set failed: "
                             f"{type(err).__name__}: {err}") from None
    odd = Xte.head(5).copy()
    odd["city"] = ["Atyrau", None, "Almaty", "Kokshetau", None]
    odd["segment"] = ["enterprise", "consumer", "student", "consumer", "student"]
    try:
        p = model.predict_proba(odd)
    except Exception as err:  # noqa: BLE001
        raise AssertionError(f"the model cannot score customers with a city or segment it never saw (or a missing "
                             f"city): {type(err).__name__}. Production data will contain those. "
                             f"Look at OneHotEncoder's handle_unknown.") from None
    if p.shape != (5, 2):
        raise AssertionError("predict_proba should give two columns (P(0), P(1)) per row")
    assert CATEGORICAL
    return model, Xtr, Xte, ytr, yte


@exercise("w05.make_logreg", hint="Copy the preprocessor from section 3 (scale numeric columns, one-hot the "
                                  "categorical ones with handle_unknown='ignore') and end with LogisticRegression.")
def _t_make_logreg(fn):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    model, Xtr, Xte, ytr, yte = _check_pipeline_basics(fn, "make_logreg()")
    last = model.steps[-1][1] if hasattr(model, "steps") else model
    if not isinstance(last, LogisticRegression):
        raise AssertionError("the last step should be a LogisticRegression")
    auc = roc_auc_score(yte, model.predict_proba(Xte)[:, 1])
    if auc < 0.70:
        raise AssertionError(f"test ROC-AUC is {auc:.3f}; a scaled logistic regression on all features reaches about "
                             f"0.74: are all FEATURES used and the numeric ones standardised?")
    big = Xtr.copy()
    big["total_spent"] = big["total_spent"] * 1000
    big_te = Xte.copy()
    big_te["total_spent"] = big_te["total_spent"] * 1000
    p1 = model.predict_proba(Xte)[:, 1]
    p2 = _builder(fn, what="make_logreg()").fit(big, ytr).predict_proba(big_te)[:, 1]
    if np.max(np.abs(p1 - p2)) > 1e-4:
        raise AssertionError("measuring total_spent in a different unit changes the predictions: the numeric "
                             "columns are not standardised before the regularised logistic regression")
    m2 = fn()
    if hasattr(m2, "steps") and hasattr(m2.steps[-1][1], "coef_"):
        raise AssertionError("return a NEW, unfitted pipeline each time; fit it outside the function")


@exercise("w05.make_tree", hint="Same preprocessor, then DecisionTreeClassifier(max_depth=max_depth, random_state=0).")
def _t_make_tree(fn):
    from sklearn.tree import DecisionTreeClassifier
    for depth in [1, 3]:
        model, Xtr, Xte, ytr, yte = _check_pipeline_basics(lambda: fn(depth), f"make_tree({depth})")
        tree = model.steps[-1][1] if hasattr(model, "steps") else model
        if not isinstance(tree, DecisionTreeClassifier):
            raise AssertionError("the last step should be a DecisionTreeClassifier")
        if tree.get_depth() > depth:
            raise AssertionError(f"make_tree({depth}) grew a tree of depth {tree.get_depth()}: pass max_depth through")
    a = _builder(fn, None, what="make_tree(None)").fit(Xtr, ytr)
    b = _builder(fn, None, what="make_tree(None)").fit(Xtr, ytr)
    if not np.array_equal(a.predict(Xte), b.predict(Xte)):
        raise AssertionError("two fits on the same data give different predictions: fix the tree's random_state")
    if a.score(Xtr, ytr) < 0.99:
        raise AssertionError("make_tree(None) should grow an unlimited tree that fits the training set almost "
                             "perfectly")


@_ref
def _train_val_gap(model, X_tr, y_tr, X_val, y_val):
    model.fit(X_tr, y_tr)
    tr = float(model.score(X_tr, y_tr))
    va = float(model.score(X_val, y_val))
    return {"train": tr, "val": va, "gap": tr - va}


@exercise("w05.train_val_gap", hint="Fit on the training part only, then .score on each part; gap = train - val.")
def _t_gap(fn):
    from sklearn.dummy import DummyClassifier
    from sklearn.tree import DecisionTreeClassifier
    X, y = _toy_frame(200, 4)
    X = X.drop(columns=["segment", "city"])
    Xtr, ytr, Xva, yva = X.iloc[:150], y.iloc[:150], X.iloc[150:], y.iloc[150:]
    for model in [DummyClassifier(), DecisionTreeClassifier(random_state=0),
                  DecisionTreeClassifier(max_depth=2, random_state=0)]:
        from sklearn.base import clone
        got = fn(clone(model), Xtr, ytr, Xva, yva)
        want = _train_val_gap(clone(model), Xtr, ytr, Xva, yva)
        if not isinstance(got, dict) or set(got) != {"train", "val", "gap"}:
            raise AssertionError("return a dict with keys 'train', 'val', 'gap'")
        for k in want:
            if not _close(got[k], want[k], 1e-9):
                if k == "gap" and _close(got[k], -want[k]):
                    raise AssertionError("the gap has the wrong sign: it is train accuracy minus validation accuracy")
                if k == "val" and _close(got["val"], got["train"]) and not _close(want["val"], want["train"]):
                    raise AssertionError("val equals train: are you scoring the validation rows?")
                raise AssertionError(f"`{k}` is wrong for {type(model).__name__}: fit on the training rows only, "
                                     "then score each part")


@_ref
def _depth_curve(make_model, depths, X_tr, y_tr, X_val, y_val):
    rows = []
    for d in depths:
        m = make_model(d).fit(X_tr, y_tr)
        rows.append({"depth": d, "train_acc": m.score(X_tr, y_tr), "val_acc": m.score(X_val, y_val)})
    return pd.DataFrame(rows)


def _ref_make_tree(depth):
    from sklearn.pipeline import make_pipeline
    from sklearn.tree import DecisionTreeClassifier
    return make_pipeline(_preprocessor(), DecisionTreeClassifier(max_depth=depth, random_state=0))


def _ref_make_logreg():
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    return make_pipeline(_preprocessor(), LogisticRegression(max_iter=1000))


_REFERENCES["make_tree"] = _ref_make_tree
_REFERENCES["make_logreg"] = _ref_make_logreg
_REFERENCES["make_model"] = _ref_make_logreg


def _check_curve(got, want, key, what):
    if not isinstance(got, pd.DataFrame):
        raise AssertionError("return a DataFrame")
    cols = list(want.columns)
    if list(got.columns) != cols:
        raise AssertionError(f"the columns should be {cols}, in that order")
    if len(got) != len(want):
        raise AssertionError(f"expected one row per {what} ({len(want)}), got {len(got)}")
    norm = lambda col: [None if pd.isna(v) else v for v in col]  # noqa: E731
    if norm(got[key]) != norm(want[key]):
        raise AssertionError(f"the `{key}` column should list the {what}s in the order given")
    for c in cols[1:]:
        if not np.allclose(got[c].astype(float), want[c].astype(float), atol=1e-9):
            raise AssertionError(f"`{c}` is wrong in at least one row: fit a fresh model for each {what} on the "
                                 "training rows only")


@exercise("w05.depth_curve", hint="For each depth: model = make_model(depth), fit on the training rows, then score "
                                  "both parts. Build the DataFrame from a list of dicts.")
def _t_depth_curve(fn):
    X, y = _toy_frame(240, 6)
    Xtr, ytr, Xva, yva = X.iloc[:160], y.iloc[:160], X.iloc[160:], y.iloc[160:]
    for depths in ([1, 2, 4, None], [3]):
        got = fn(_ref_make_tree, depths, Xtr, ytr, Xva, yva)
        _check_curve(got, _depth_curve(_ref_make_tree, depths, Xtr, ytr, Xva, yva), "depth", "depth")


@_ref
def _learning_curve_points(make_model, sizes, X_tr, y_tr, X_val, y_val):
    rows = []
    for n in sizes:
        Xn, yn = X_tr.iloc[:n], y_tr.iloc[:n]
        m = make_model().fit(Xn, yn)
        rows.append({"n_train": n, "train_acc": m.score(Xn, yn), "val_acc": m.score(X_val, y_val)})
    return pd.DataFrame(rows)


@exercise("w05.learning_curve_points", hint="For each size n, fit a fresh model on the FIRST n training rows; the "
                                            "training accuracy is measured on those same n rows.")
def _t_learning_curve(fn):
    X, y = _toy_frame(300, 7)
    Xtr, ytr, Xva, yva = X.iloc[:220], y.iloc[:220], X.iloc[220:], y.iloc[220:]
    for sizes in ([20, 60, 120, 220], [50]):
        got = fn(_ref_make_logreg, sizes, Xtr, ytr, Xva, yva)
        want = _learning_curve_points(_ref_make_logreg, sizes, Xtr, ytr, Xva, yva)
        if isinstance(got, pd.DataFrame) and list(got.columns) == list(want.columns) and len(got) == len(want):
            full = _ref_make_logreg().fit(Xtr, ytr).score(Xtr, ytr)
            if np.allclose(got["train_acc"].astype(float), full) and not np.allclose(want["train_acc"], full):
                raise AssertionError("train_acc should be measured on the n rows the model was fitted on, "
                                     "not on the whole training set")
        _check_curve(got, want, "n_train", "size")


DIAGNOSIS = {"dummy": "underfit", "full_tree": "overfit", "logreg": "good_fit"}


@exercise("w05.diagnosis", hint="Underfit: training and validation both poor, close together. Overfit: training "
                                "much better than validation. Good fit: validation clearly above the baselines, modest gap.")
def _t_diagnosis(answer):
    _choices(answer, DIAGNOSIS, {
        "dummy": "compare its training score with the baseline and with the other models",
        "full_tree": "look at the distance between its training and validation scores",
        "logreg": "look at both its validation score and its gap",
    }, "diagnosis")


@_ref
def _coef_table(pipeline):
    names = pipeline[:-1].get_feature_names_out()
    coef = pipeline[-1].coef_[0]
    t = pd.DataFrame({"feature": names, "coef": coef})
    return t.reindex(t["coef"].abs().sort_values(ascending=False).index).reset_index(drop=True)


@exercise("w05.coef_table", hint="pipeline[:-1].get_feature_names_out() gives the names; pipeline[-1].coef_[0] the "
                                 "coefficients; sort by their absolute value, largest first.")
def _t_coef_table(fn):
    from sklearn.compose import make_column_transformer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    Xtr, _, ytr, _ = _split(0)
    pipes = [_ref_make_logreg().fit(Xtr, ytr),
             make_pipeline(make_column_transformer((StandardScaler(), ["n_orders", "days_since_last_order"]),
                                                   (OneHotEncoder(handle_unknown="ignore"), ["segment"])),
                           LogisticRegression(C=0.1)).fit(Xtr, ytr)]
    for p in pipes:
        got = fn(p)
        want = _coef_table(p)
        if not isinstance(got, pd.DataFrame) or list(got.columns) != ["feature", "coef"]:
            raise AssertionError("return a DataFrame with columns 'feature' and 'coef'")
        if len(got) != len(want):
            raise AssertionError(f"expected one row per model input ({len(want)}), got {len(got)}: use the names "
                                 "AFTER preprocessing (one-hot columns included)")
        if set(got["feature"]) != set(want["feature"]):
            raise AssertionError("the feature names do not match the pipeline's inputs after preprocessing")
        merged = want.merge(got, on="feature", suffixes=("_w", "_g"))
        if not np.allclose(merged["coef_w"], merged["coef_g"]):
            raise AssertionError("some coefficients are attached to the wrong feature, or changed")
        if not np.allclose(got["coef"].abs().to_numpy(), want["coef"].abs().to_numpy()):
            raise AssertionError("sort by the absolute size of the coefficient, largest first (negative ones count)")
        if list(got.index) != list(range(len(got))):
            raise AssertionError("reset the index after sorting (0, 1, 2, ...)")


COEF_STATEMENTS = {1: False, 2: True, 3: False, 4: True, 5: False}


@exercise("w05.coef_statements", hint="Reread section 5: scaling, correlated features, and what a coefficient does "
                                      "and does not say about causes.")
def _t_coef_statements(answer):
    _bool_dict(answer, COEF_STATEMENTS, {
        1: "Without scaling, what does the size of a coefficient depend on?",
        2: "Each coefficient is read holding the other inputs fixed.",
        3: "Does a model that predicts churn tell you what CAUSES churn?",
        4: "What happens to two coefficients when two inputs carry the same information?",
        5: "What is the baseline category of a one-hot encoding, and what does a single sign mean?",
    })


# =========================================================================== 19 · metrics
def _binary_cases(seed=0, n_cases=8):
    rng = np.random.default_rng(seed)
    cases = [(np.array([1, 0, 1, 1, 0]), np.array([1, 1, 0, 1, 0])), (np.array([0, 0, 0]), np.array([0, 0, 0])),
             (np.array([1, 1]), np.array([0, 0])), (np.array([0, 1]), np.array([1, 1]))]
    for _ in range(n_cases):
        n = int(rng.integers(3, 80))
        cases.append((rng.integers(0, 2, n), rng.integers(0, 2, n)))
    return cases


@_ref
def _confusion_counts(y_true, y_pred):
    t, p = np.asarray(y_true).astype(int), np.asarray(y_pred).astype(int)
    return {"tp": int(((t == 1) & (p == 1)).sum()), "fp": int(((t == 0) & (p == 1)).sum()),
            "fn": int(((t == 1) & (p == 0)).sum()), "tn": int(((t == 0) & (p == 0)).sum())}


@exercise("w05.confusion_counts", hint="Each count is the number of positions where y_true and y_pred take a given "
                                       "pair of values, e.g. tp: true 1 AND predicted 1.")
def _t_confusion(fn):
    from sklearn.metrics import confusion_matrix
    for t, p in _binary_cases(1):
        got = fn(t, p)
        if not isinstance(got, dict) or set(got) != {"tp", "fp", "fn", "tn"}:
            raise AssertionError("return a dict with keys 'tp', 'fp', 'fn', 'tn'")
        tn, fp, fn_, tp = confusion_matrix(t, p, labels=[0, 1]).ravel()
        want = {"tp": tp, "fp": fp, "fn": fn_, "tn": tn}
        for k in want:
            if int(got[k]) != int(want[k]):
                if k in ("fp", "fn") and int(got["fp"]) == int(want["fn"]) and int(got["fn"]) == int(want["fp"]):
                    raise AssertionError("fp and fn are swapped: a false POSITIVE is a predicted 1 whose truth is 0")
                raise AssertionError(f"`{k}` is wrong for y_true={list(t)[:8]}, y_pred={list(p)[:8]}")
    got = fn([1, 0], [True, False])
    if int(got["tp"]) != 1 or int(got["tn"]) != 1:
        raise AssertionError("also accept lists and booleans (True counts as 1)")


@_ref
def _precision_recall_f1(y_true, y_pred):
    c = _confusion_counts(y_true, y_pred)
    p = c["tp"] / (c["tp"] + c["fp"]) if c["tp"] + c["fp"] else 0.0
    r = c["tp"] / (c["tp"] + c["fn"]) if c["tp"] + c["fn"] else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return float(p), float(r), float(f)


@exercise("w05.precision_recall_f1", hint="Use your confusion counts. When a denominator is 0, the metric is 0.0.")
def _t_prf(fn):
    from sklearn.metrics import f1_score, precision_score, recall_score
    for t, p in _binary_cases(2):
        got = fn(t, p)
        if not isinstance(got, tuple) or len(got) != 3:
            raise AssertionError("return a tuple (precision, recall, f1)")
        want = (precision_score(t, p, zero_division=0), recall_score(t, p, zero_division=0),
                f1_score(t, p, zero_division=0))
        for name, g, w in zip(("precision", "recall", "f1"), got, want):
            _number(g, name)
            if not _close(g, w, 1e-9):
                if name in ("precision", "recall") and _close(got[0], want[1]) and _close(got[1], want[0]):
                    raise AssertionError("precision and recall are swapped: precision is about the predicted "
                                         "positives, recall about the actual positives")
                if name == "f1" and _close(g, (want[0] + want[1]) / 2):
                    raise AssertionError("F1 is the harmonic mean of precision and recall, not their average")
                raise AssertionError(f"{name} is wrong for y_true={list(t)[:8]}, y_pred={list(p)[:8]} "
                                     "(when nothing is predicted positive, or there are no positives, return 0.0)")


@_ref
def _roc_auc_by_ranks(y_true, scores):
    y = np.asarray(y_true).astype(int)
    s = np.asarray(scores, dtype=float)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        raise ValueError("ROC-AUC needs at least one positive and one negative")
    diff = pos[:, None] - neg[None, :]
    return float(((diff > 0).sum() + 0.5 * (diff == 0).sum()) / diff.size)


@exercise("w05.roc_auc_by_ranks", hint="Compare every (positive, negative) pair: count 1 when the positive scores "
                                       "higher, 0.5 for a tie; divide by the number of pairs.")
def _t_auc(fn):
    from sklearn.metrics import roc_auc_score
    rng = np.random.default_rng(3)
    cases = [([0, 0, 1, 1], [0.1, 0.4, 0.35, 0.8]), ([1, 0], [0.5, 0.5]), ([1, 1, 0], [0.2, 0.9, 0.9])]
    for _ in range(6):
        n = int(rng.integers(6, 60))
        y = rng.integers(0, 2, n)
        y[0], y[1] = 0, 1
        s = rng.integers(0, 5, n) / 4 if rng.random() < 0.5 else rng.random(n)
        cases.append((y, s))
    for y, s in cases:
        got = _number(fn(y, s), "the AUC")
        want = roc_auc_score(y, s)
        if not _close(got, want, 1e-9):
            if _close(got, ((np.asarray(s)[np.asarray(y) == 1][:, None] > np.asarray(s)[np.asarray(y) == 0][None, :]).mean())):
                raise AssertionError("ties between a positive and a negative score should count as one half")
            raise AssertionError(f"wrong AUC for y_true={list(y)[:8]}, scores={list(np.round(s, 2))[:8]}")
    try:
        fn([1, 1, 1], [0.1, 0.2, 0.3])
    except ValueError:
        pass
    except Exception as err:  # noqa: BLE001
        raise AssertionError(f"with only one class raise ValueError, not {type(err).__name__}") from None
    else:
        raise AssertionError("with only one class in y_true the AUC is undefined: raise ValueError")


def _top_k(scores, k):
    s = np.asarray(scores, dtype=float)
    return np.argsort(-s, kind="stable")[:k]


@_ref
def _precision_at_k(y_true, scores, k):
    y = np.asarray(y_true).astype(int)
    if k <= 0:
        return 0.0
    return float(y[_top_k(scores, k)].mean())


@_ref
def _recall_at_k(y_true, scores, k):
    y = np.asarray(y_true).astype(int)
    if y.sum() == 0 or k <= 0:
        return 0.0
    return float(y[_top_k(scores, k)].sum() / y.sum())


def _check_at_k(fn, ref, name):
    rng = np.random.default_rng(4)
    cases = [([1, 0, 1, 0, 0], [0.9, 0.8, 0.7, 0.2, 0.1], 2), ([0, 0, 1], [0.3, 0.2, 0.1], 1),
             ([1, 0, 1], [0.5, 0.1, 0.9], 3), ([1, 0, 1], [0.5, 0.1, 0.9], 10), ([0, 0, 0], [0.5, 0.2, 0.1], 2)]
    for _ in range(6):
        n = int(rng.integers(5, 50))
        cases.append((rng.integers(0, 2, n), rng.random(n), int(rng.integers(1, n + 3))))
    for y, s, k in cases:
        got = _number(fn(y, s, k), name)
        want = ref(y, s, k)
        if not _close(got, want, 1e-9):
            raise AssertionError(f"wrong {name} for y_true={list(y)[:8]}, scores={list(np.round(s, 2))[:8]}, k={k} "
                                 "(take the k HIGHEST scores; if k is larger than the number of rows, take them all)")
    if not _close(fn([1, 0], [0.9, 0.1], 0), 0.0):
        raise AssertionError(f"with k=0 nobody is contacted: return 0.0")


@exercise("w05.precision_at_k", hint="Sort the rows by score, highest first; take k of them; precision = share of "
                                     "those that are positive.")
def _t_prec_k(fn):
    _check_at_k(fn, _precision_at_k, "precision@k")


@exercise("w05.recall_at_k", hint="Same top-k rows; recall = positives among them divided by ALL positives (0.0 if "
                                  "there are none).")
def _t_rec_k(fn):
    _check_at_k(fn, _recall_at_k, "recall@k")


@_ref
def _expected_cost(y_true, scores, threshold, cost_fp, cost_fn):
    y = np.asarray(y_true).astype(int)
    pred = np.asarray(scores, dtype=float) >= threshold
    return float(cost_fp * ((y == 0) & pred).sum() + cost_fn * ((y == 1) & ~pred).sum())


@exercise("w05.expected_cost", hint="Predict 1 where score >= threshold, then cost = cost_fp × (#FP) + cost_fn × (#FN).")
def _t_cost(fn):
    rng = np.random.default_rng(6)
    cases = [([1, 0, 1, 0], [0.9, 0.6, 0.4, 0.1], 0.5, 12, 6), ([1, 0], [0.5, 0.5], 0.5, 1, 1),
             ([1, 1], [0.2, 0.3], float("inf"), 5, 10)]
    for _ in range(6):
        n = int(rng.integers(5, 60))
        cases.append((rng.integers(0, 2, n), rng.random(n), float(rng.random()), float(rng.uniform(1, 20)),
                      float(rng.uniform(1, 20))))
    for y, s, t, cfp, cfn in cases:
        got = _number(fn(y, s, t, cfp, cfn), "the cost")
        want = _expected_cost(y, s, t, cfp, cfn)
        if not _close(got, want, 1e-9):
            if _close(got, _expected_cost(y, s, t, cfn, cfp)):
                raise AssertionError("cost_fp and cost_fn are applied to the wrong errors")
            pred_gt = np.asarray(s) > t
            yy = np.asarray(y)
            if _close(got, cfp * ((yy == 0) & pred_gt).sum() + cfn * ((yy == 1) & ~pred_gt).sum()):
                raise AssertionError("a score exactly equal to the threshold should count as a positive prediction (>=)")
            raise AssertionError(f"wrong cost for threshold={t}, cost_fp={cfp:.1f}, cost_fn={cfn:.1f}")


@_ref
def _best_threshold(y_true, scores, cost_fp, cost_fn):
    cands = sorted(set(np.asarray(scores, dtype=float).tolist())) + [float("inf")]
    costs = [_expected_cost(y_true, scores, t, cost_fp, cost_fn) for t in cands]
    best = min(costs)
    return max(t for t, c in zip(cands, costs) if c == best)


@exercise("w05.best_threshold", hint="Try every distinct score as a threshold, plus float('inf') (contact nobody); "
                                     "keep the cheapest; on a tie keep the highest threshold.")
def _t_best_threshold(fn):
    rng = np.random.default_rng(7)
    cases = [([1, 0, 1, 0], [0.9, 0.6, 0.4, 0.1], 12, 6), ([0, 0, 0], [0.9, 0.5, 0.2], 1, 1),
             ([1, 1, 1], [0.9, 0.5, 0.2], 1, 1), ([1, 0, 1, 0], [0.9, 0.9, 0.4, 0.4], 1, 1)]
    for _ in range(6):
        n = int(rng.integers(5, 60))
        cases.append((rng.integers(0, 2, n), rng.integers(0, 20, n) / 20, float(rng.uniform(1, 20)),
                      float(rng.uniform(1, 20))))
    for y, s, cfp, cfn in cases:
        got = fn(y, s, cfp, cfn)
        _number(got, "the threshold")
        want = _best_threshold(y, s, cfp, cfn)
        gc, wc = _expected_cost(y, s, got, cfp, cfn), _expected_cost(y, s, want, cfp, cfn)
        if gc > wc + 1e-9:
            raise AssertionError(f"threshold {got} costs {gc:.1f}, but a cheaper one exists ({wc:.1f}) for "
                                 f"cost_fp={cfp:.1f}, cost_fn={cfn:.1f}. Did you include 'contact nobody' (inf)?")
        n_got = int((np.asarray(s) >= got).sum())
        n_want = int((np.asarray(s) >= want).sum())
        if n_got != n_want:
            raise AssertionError("several thresholds are equally cheap: return the highest (contact fewer people)")


@_ref
def _budget_threshold(scores, budget):
    s = np.sort(np.asarray(scores, dtype=float))[::-1]
    if budget <= 0 or len(s) == 0:
        return float("inf")
    if budget >= len(s):
        return float(s[-1])
    best = float("inf")
    for t in sorted(set(s.tolist()), reverse=True):
        if (s >= t).sum() <= budget:
            best = t
        else:
            break
    return float(best)


@exercise("w05.budget_threshold", hint="Go through the distinct scores from highest to lowest and keep the lowest one "
                                       "that still contacts at most `budget` people (score >= threshold).")
def _t_budget(fn):
    rng = np.random.default_rng(8)
    cases = [([0.9, 0.8, 0.7, 0.1], 2), ([0.9, 0.8, 0.8, 0.1], 2), ([0.5, 0.5, 0.5], 2), ([0.3, 0.2], 0),
             ([0.3, 0.2], 5), ([0.3, 0.2, 0.1], 3)]
    for _ in range(6):
        n = int(rng.integers(5, 80))
        cases.append((rng.integers(0, 30, n) / 30, int(rng.integers(0, n + 2))))
    for s, b in cases:
        got = fn(s, b)
        _number(got, "the threshold")
        n_got = int((np.asarray(s) >= got).sum())
        n_want = int((np.asarray(s) >= _budget_threshold(s, b)).sum())
        if n_got > b:
            raise AssertionError(f"threshold {got} contacts {n_got} people but the budget is {b} "
                                 "(watch out for tied scores)")
        if n_got < n_want:
            raise AssertionError(f"with budget {b} you contact only {n_got}; a lower threshold could contact "
                                 f"{n_want} without breaking the budget")


@_ref
def _cost_threshold(cost_fp, cost_fn):
    return cost_fp / (cost_fp + cost_fn)


@exercise("w05.cost_threshold", hint="Contact when the expected cost of not contacting, p × cost_fn, is at least "
                                     "the expected cost of contacting, (1 - p) × cost_fp. Solve for p.")
def _t_cost_threshold(fn):
    for a, b in [(12, 6), (5, 10), (1, 1), (1, 99), (3.5, 0.5)]:
        got = _number(fn(a, b), "the threshold")
        if not _close(got, _cost_threshold(a, b), 1e-9):
            if _close(got, b / (a + b)):
                raise AssertionError("upside down: when false positives are EXPENSIVE the threshold should be HIGH")
            raise AssertionError(f"wrong threshold for cost_fp={a}, cost_fn={b}")


@_ref
def _calibration_table(y_true, probs, n_bins):
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(probs, dtype=float)
    edges = np.linspace(0, 1, n_bins + 1)
    b = np.clip(np.searchsorted(edges[1:-1], p, side="right"), 0, n_bins - 1)
    df = pd.DataFrame({"bin": b, "p": p, "y": y})
    g = df.groupby("bin").agg(mean_predicted=("p", "mean"), observed_rate=("y", "mean"), n=("y", "size"))
    return g.reset_index(drop=True)


@exercise("w05.calibration_table", hint="Cut [0, 1] into n_bins equal-width bins (a probability of exactly 1.0 goes "
                                        "into the last bin); per non-empty bin: mean probability, share of 1s, count.")
def _t_calibration(fn):
    from sklearn.calibration import calibration_curve
    rng = np.random.default_rng(9)
    cases = [([0, 1, 1, 0], [0.05, 0.95, 1.0, 0.0], 2), ([0, 1, 0, 1, 1], [0.1, 0.12, 0.5, 0.55, 0.9], 5)]
    for _ in range(5):
        n = int(rng.integers(20, 200))
        p = rng.random(n) ** 2
        cases.append(((rng.random(n) < p).astype(int), p, int(rng.integers(3, 11))))
    for y, p, nb in cases:
        got = fn(y, p, nb)
        if not isinstance(got, pd.DataFrame) or list(got.columns) != ["mean_predicted", "observed_rate", "n"]:
            raise AssertionError("return a DataFrame with columns 'mean_predicted', 'observed_rate', 'n'")
        want = _calibration_table(y, p, nb)
        prob_true, prob_pred = calibration_curve(y, p, n_bins=nb, strategy="uniform")
        if len(got) != len(want):
            raise AssertionError(f"expected {len(want)} non-empty bins for n_bins={nb}, got {len(got)} "
                                 "(drop empty bins; put a probability of exactly 1.0 into the last bin)")
        if int(got["n"].sum()) != len(np.asarray(y)):
            raise AssertionError("every row should land in exactly one bin: the counts do not add up")
        if not (np.allclose(got["mean_predicted"].astype(float), prob_pred)
                and np.allclose(got["observed_rate"].astype(float), prob_true)):
            raise AssertionError(f"the bin averages do not match for n_bins={nb}: are the bins equal-width on [0, 1] "
                                 "and listed from low to high?")


@_ref
def _brier_score(y_true, probs):
    return float(np.mean((np.asarray(probs, dtype=float) - np.asarray(y_true, dtype=float)) ** 2))


@exercise("w05.brier_score", hint="The mean of (probability - outcome) squared, over all rows.")
def _t_brier(fn):
    from sklearn.metrics import brier_score_loss
    rng = np.random.default_rng(10)
    for _ in range(6):
        n = int(rng.integers(3, 60))
        y, p = rng.integers(0, 2, n), rng.random(n)
        if not _close(_number(fn(y, p), "the Brier score"), brier_score_loss(y, p), 1e-9):
            raise AssertionError("the Brier score does not match: average the squared differences between the "
                                 "probability and the 0/1 outcome")
    if not _close(fn([1, 0], [1.0, 0.0]), 0.0) or not _close(fn([1, 0], [0.0, 1.0]), 1.0):
        raise AssertionError("perfect confident predictions should score 0 and perfectly wrong ones 1")


# =========================================================================== 20 · lab
LAB_FRAMING = {"unit": "customer", "horizon_days": 90.0, "cost_fp": 12.0, "cost_fn": 6.0,
               "budget_share": 0.15, "decision": "b"}


@exercise("w05.lab_framing", hint="Reread the message from Aigerim and translate each sentence into one key.")
def _t_lab_framing(answer):
    _choices(answer, LAB_FRAMING, {
        "unit": "who gets the call?",
        "horizon_days": "how long after the scoring day do we wait to know whether the customer left?",
        "cost_fp": "a call to a customer who would have stayed anyway: what is lost?",
        "cost_fn": "a churner you did not call: the call would have saved them only some of the time, and it would "
                   "have cost money too. What net value is missed?",
        "budget_share": "what fraction of the customers can the team call at most (a number between 0 and 1)?",
        "decision": "the team calls a ranked list, within a limit",
    }, "framing")


@_ref
def _lab_split(table, seed):
    from sklearn.model_selection import train_test_split
    from mlcourse.churn import FEATURES
    return train_test_split(table[FEATURES], table["churned"], test_size=0.25, random_state=seed,
                            stratify=table["churned"])


@exercise("w05.lab_split", hint="train_test_split(table[FEATURES], table['churned'], test_size=0.25, "
                                "random_state=seed, stratify=...).")
def _t_lab_split(fn):
    from mlcourse.churn import FEATURES
    t = _churn()
    for seed in (0, 42):
        out = fn(t.copy(), seed)
        if not isinstance(out, (tuple, list)) or len(out) != 4:
            raise AssertionError("return X_train, X_test, y_train, y_test")
        Xtr, Xte, ytr, yte = out
        if list(Xtr.columns) != FEATURES:
            raise AssertionError("X should hold exactly the FEATURES columns (no customer_id, no label)")
        if len(Xte) != int(np.ceil(0.25 * len(t))):
            raise AssertionError(f"the test set should be 25% of the rows ({int(np.ceil(0.25 * len(t)))}), "
                                 f"got {len(Xte)}")
        if set(Xtr.index) & set(Xte.index):
            raise AssertionError("some rows are in both the training and the test set")
        if abs(float(np.mean(yte)) - float(np.mean(ytr))) > 0.01:
            raise AssertionError("the churn rate differs between train and test: stratify on the label")
        if list(fn(t.copy(), seed)[1].index) != list(Xte.index):
            raise AssertionError("the same seed should give the same split")
    if list(fn(t, 0)[1].index) == list(fn(t, 42)[1].index):
        raise AssertionError("the seed should change the split")


@_ref
def _lab_baselines(X_train, y_train, X_test, y_test):
    from sklearn.metrics import roc_auc_score
    return {"majority_accuracy": _majority_accuracy(y_train, y_test),
            "recency_auc": float(roc_auc_score(y_test, X_test["days_since_last_order"]))}


@exercise("w05.lab_baselines", hint="The majority baseline from notebook 18; for the recency AUC use "
                                    "days_since_last_order itself as the score.")
def _t_lab_baselines(fn):
    for seed in (0, 1, 2):
        X, y = _toy_frame(120, seed)
        Xtr, Xte, ytr, yte = X.iloc[:80], X.iloc[80:], y.iloc[:80], y.iloc[80:]
        got = fn(Xtr, ytr, Xte, yte)
        want = _lab_baselines(Xtr, ytr, Xte, yte)
        if not isinstance(got, dict) or set(got) != set(want):
            raise AssertionError(f"return a dict with keys {sorted(want)}")
        if not _close(got["majority_accuracy"], want["majority_accuracy"], 1e-9):
            raise AssertionError("majority_accuracy is wrong: learn the majority class on train, score on test")
        if not _close(got["recency_auc"], want["recency_auc"], 1e-9):
            if _close(got["recency_auc"], 1 - want["recency_auc"], 1e-9):
                raise AssertionError("recency_auc is upside down: MORE days since the last order means MORE risk")
            raise AssertionError("recency_auc is wrong: it is the ROC-AUC on the TEST rows of the raw "
                                 "days_since_last_order column")


@exercise("w05.lab_model", hint="Build on make_logreg from notebook 18. The grader fits it on its own split.")
def _t_lab_model(fn):
    from sklearn.metrics import roc_auc_score
    model, Xtr, Xte, ytr, yte = _check_pipeline_basics(fn, "make_model()")
    Xtr, Xte, ytr, yte = _split(42)
    model = _builder(fn, what="make_model()").fit(Xtr, ytr)
    auc = roc_auc_score(yte, model.predict_proba(Xte)[:, 1])
    rec = roc_auc_score(yte, Xte["days_since_last_order"])
    if auc < 0.70:
        raise AssertionError(f"on the grader's split your model's test ROC-AUC is {auc:.3f}; the logistic regression "
                             f"from notebook 18 reaches about 0.74")
    if auc <= rec:
        raise AssertionError(f"your model (AUC {auc:.3f}) does not beat the recency baseline ({rec:.3f})")


@_ref
def _lab_choose_threshold(y_val, scores, cost_fp, cost_fn, budget_share):
    s = np.asarray(scores, dtype=float)
    cap = int(np.floor(budget_share * len(s)))
    cands = sorted(set(s.tolist())) + [float("inf")]
    ok = [t for t in cands if (s >= t).sum() <= cap]
    costs = [_expected_cost(y_val, s, t, cost_fp, cost_fn) for t in ok]
    best = min(costs)
    return max(t for t, c in zip(ok, costs) if c == best)


@exercise("w05.lab_choose_threshold", hint="Like best_threshold from notebook 19, but only consider thresholds that "
                                           "contact at most floor(budget_share × number of rows) customers.")
def _t_lab_threshold(fn):
    rng = np.random.default_rng(11)
    cases = [([1, 0, 1, 0, 1], [0.9, 0.8, 0.7, 0.3, 0.2], 12, 6, 0.4), ([1, 1, 1, 1], [0.9, 0.8, 0.7, 0.6], 1, 10, 0.5),
             ([0, 0, 0], [0.9, 0.8, 0.7], 5, 5, 1.0), ([1, 0], [0.9, 0.1], 1, 1, 0.0)]
    for _ in range(6):
        n = int(rng.integers(10, 80))
        cases.append((rng.integers(0, 2, n), rng.integers(0, 25, n) / 25, float(rng.uniform(1, 20)),
                      float(rng.uniform(1, 20)), float(rng.uniform(0.05, 0.6))))
    for y, s, cfp, cfn, share in cases:
        got = fn(y, s, cfp, cfn, share)
        _number(got, "the threshold")
        s_arr = np.asarray(s)
        cap = int(np.floor(share * len(s_arr)))
        n_got = int((s_arr >= got).sum())
        if n_got > cap:
            raise AssertionError(f"threshold {got} contacts {n_got} customers but the budget allows {cap} "
                                 f"({share:.2f} of {len(s_arr)})")
        want = _lab_choose_threshold(y, s, cfp, cfn, share)
        gc, wc = _expected_cost(y, s, got, cfp, cfn), _expected_cost(y, s, want, cfp, cfn)
        if gc > wc + 1e-9:
            raise AssertionError(f"a cheaper threshold within the budget exists (cost {wc:.1f} instead of {gc:.1f})")
        if n_got != int((s_arr >= want).sum()):
            raise AssertionError("several thresholds tie: return the highest (contact fewer people)")


@_ref
def _lab_decision_summary(y_true, scores, threshold, value_saved, contact_cost, success_rate):
    y = np.asarray(y_true).astype(int)
    contact = np.asarray(scores, dtype=float) >= threshold
    tp = int((contact & (y == 1)).sum())
    return {"n_contacted": int(contact.sum()),
            "precision": float(tp / contact.sum()) if contact.sum() else 0.0,
            "recall": float(tp / y.sum()) if y.sum() else 0.0,
            "net_value": _policy_value(y, contact, value_saved, contact_cost, success_rate)}


@exercise("w05.lab_decision_summary", hint="Contact = score >= threshold. Reuse your precision/recall logic and "
                                           "policy_value from notebook 17.")
def _t_lab_summary(fn):
    rng = np.random.default_rng(12)
    cases = [([1, 0, 1, 0], [0.9, 0.8, 0.3, 0.1], 0.5, 60, 12, 0.3), ([1, 0], [0.2, 0.1], 0.5, 60, 12, 0.3)]
    for _ in range(5):
        n = int(rng.integers(10, 60))
        cases.append((rng.integers(0, 2, n), rng.random(n), float(rng.random()), 60.0, 12.0, 0.3))
    for args in cases:
        got = fn(*args)
        want = _lab_decision_summary(*args)
        if not isinstance(got, dict) or set(got) != set(want):
            raise AssertionError(f"return a dict with keys {sorted(want)}")
        for k in want:
            if not _close(got[k], want[k], 1e-9):
                raise AssertionError(f"`{k}` is wrong for threshold={args[2]:.2f} (contact everyone with "
                                     "score >= threshold; with nobody contacted precision is 0.0)")


_REC_PARTS = {
    "a comparison with a baseline (use the word 'baseline')": lambda t: "baseline" in t,
    "what the team should do: how many customers to contact/call": lambda t: re.search(r"\b(call|contact)", t),
    "the expected money result (a value or cost)": lambda t: re.search(r"\b(value|cost|profit|net)\b", t),
    "a risk or limitation": lambda t: re.search(r"\b(risk|limitation|caveat|uncertain|assum)", t),
    "a next step (monitor, test, re-check, A/B, pilot...)": lambda t: re.search(
        r"\b(next|monitor|pilot|a/b|experiment|re-?check|retrain|track)", t),
}


@exercise("w05.lab_recommendation", hint="Five ingredients: baseline comparison, the action with a number, the "
                                         "expected value, a risk, a next step. Use the numbers you computed.")
def _t_lab_rec(text):
    if not isinstance(text, str):
        raise AssertionError("the recommendation should be a string")
    words = text.split()
    if len(words) < 60:
        raise AssertionError(f"{len(words)} words is too short for a recommendation someone can act on (60-250)")
    if len(words) > 250:
        raise AssertionError(f"{len(words)} words: a manager will not read past 250. Cut it down")
    low = text.lower()
    nums = re.findall(r"\d+(?:[.,]\d+)?", text)
    if len(nums) < 3:
        raise AssertionError("use at least three numbers from your results (AUC, people contacted, value...)")
    for part, check in _REC_PARTS.items():
        if not check(low):
            raise AssertionError(f"the recommendation is missing {part}")


# =========================================================================== quizzes
register_quiz(
    "w05.17_q1", "b",
    "The best of 30 was chosen partly for its luck on those test rows, so its score is biased upwards. Report a "
    "score from data that played no part in the choice (a fresh test set, after choosing on validation).",
    {"a": "That would hold for ONE model fixed in advance; picking the maximum of 30 makes the estimate optimistic.",
     "c": "A small test set makes the estimate noisy, not pessimistic; selection makes it optimistic.",
     "d": "Not training on the test set is not enough: using it to CHOOSE a model is also a form of fitting."})
register_quiz(
    "w05.17_q2", "b",
    "Inactivity after the cutoff is measured in the label window: on the scoring morning it does not exist yet. It "
    "looks predictive because it almost IS the label.",
    {"a": "It is excellent only in the notebook. In production the value is unknown, so the model cannot run.",
     "c": "Retraining does not help: on any scoring day the future window is still in the future.",
     "d": "Scaling changes units, not when the information becomes available."})
register_quiz(
    "w05.17_q3", "b",
    "Break-even precision = 8 / (0.2 × 40) = 1.0: even a list of pure churners would only break even, so random calls "
    "lose money. Fix the offer or its cost before building any model.",
    {"a": "A 30% churn rate means a random list has precision 0.3, far below the 1.0 needed to break even.",
     "c": "0.2 is the success rate of a call, not the break-even precision; divide the cost by the expected gain.",
     "d": "The break-even precision needs only the costs, and it already shows that no list can make money."})
register_quiz(
    "w05.17_q4", "b",
    "A label must be observable for every training row at the same distance after the cutoff. 'Never' is never "
    "observed: a recent customer looks like a churner just because time has not passed yet.",
    {"a": "Training speed does not depend on the label window.",
     "c": "scikit-learn knows nothing about how a label was defined.",
     "d": "The window is a business definition agreed with the team, not a law."})
register_quiz(
    "w05.17_q5", "c",
    "The deployment question fixes the unit, the cutoff, the label window, which features are allowed, and what "
    "errors cost. Model choice comes much later.",
    {"a": "Choosing a model before the problem is framed optimises the wrong thing.",
     "b": "How much data you have depends on how you define rows and labels, which comes from the framing.",
     "d": "A competition metric may have nothing to do with your team's costs."})

register_quiz(
    "w05.18_q1", "b",
    "With 0.8% fraud, the majority class alone scores 99.2%. Accuracy hides that the model may catch no fraud at "
    "all; compare with the baseline and look at precision/recall (notebook 19).",
    {"a": "99.2% is exactly what 'always say no fraud' gets: no evidence of skill.",
     "c": "Nothing here compares training and validation scores, so there is no sign of overfitting either way.",
     "d": "Leakage produces suspiciously high scores relative to a baseline; here the score equals the baseline."})
register_quiz(
    "w05.18_q2", "b",
    "A wide gap that stays wide is high variance: the model fits noise. Reduce flexibility (shallower tree, more "
    "regularisation) or get much more data.",
    {"a": "More flexibility widens the gap further.",
     "c": "The test set is for the final report, not for diagnosing and fixing.",
     "d": "Without a validation set you can no longer see the problem, which does not fix it."})
register_quiz(
    "w05.18_q3", "b",
    "Both scores low and close together is high bias: the model cannot express the pattern, so extra rows of the "
    "same features add little. Add better features or a more flexible model.",
    {"a": "A small gap means the model already generalises what it can learn; more rows mostly help when the gap is large.",
     "c": "Overfitting shows up as a large gap; adding rows does not create one.",
     "d": "More rows do not usually make validation worse."})
register_quiz(
    "w05.18_q4", "b",
    "A threshold picked to maximise accuracy on some rows has been fitted to those rows. Fit on train, so that the "
    "validation score stays an honest estimate.",
    {"a": "The size of the validation set is not the reason; any choice made on it biases its score.",
     "c": "This is a rule we wrote ourselves; scikit-learn is not involved.",
     "d": "It does: the selected threshold's score on the rows used to choose it is optimistic."})
register_quiz(
    "w05.18_q5", "b",
    "In production new categories appear. With handle_unknown='ignore' the encoder outputs zeros for them instead of "
    "raising an error, so the model still returns a score.",
    {"a": "It makes no real difference to speed.",
     "c": "Dropping rare categories is a different option (min_frequency).",
     "d": "Numeric missing values need an imputer; the encoder only handles categorical columns."})

register_quiz(
    "w05.19_q1", "b",
    "A lower threshold flags more customers: more of the churners are caught (recall up), but the list also takes in "
    "more stayers, so precision usually falls.",
    {"a": "Both rarely rise together: lowering the threshold trades precision for recall.",
     "c": "That is what RAISING the threshold does.",
     "d": "The scores stay the same, but the threshold changes which customers are predicted positive."})
register_quiz(
    "w05.19_q2", "b",
    "With 99 negatives per positive, even a small false positive RATE means many false alarms. ROC-AUC divides by the "
    "huge number of negatives and barely notices; precision, and so PR-AUC, does.",
    {"a": "Both are useful, but under strong imbalance ROC-AUC alone can make a weak alerting system look excellent.",
     "c": "Both AUCs depend only on the ranking of the scores, not on whether they are calibrated.",
     "d": "Nothing here compares training and validation, so there is no evidence of overfitting."})
register_quiz(
    "w05.19_q3", "c",
    "Act when p × 18 ≥ (1 − p) × 2, i.e. p ≥ 2 / (2 + 18) = 0.1. Missing a positive is so expensive that acting on "
    "fairly unlikely cases pays.",
    {"a": "0.5 assumes both errors cost the same.",
     "b": "That is upside down: 0.9 would be right if false POSITIVES were the expensive ones.",
     "d": "0.18 mixes up the formula: divide cost_fp by the SUM of both costs."})
register_quiz(
    "w05.19_q4", "c",
    "The team's decision is 'call the top 50', so the quality of exactly that list is what matters: precision@50 "
    "(and recall@50 for how much churn it reaches).",
    {"a": "No one acts at threshold 0.5; accuracy also mixes both errors together.",
     "b": "ROC-AUC averages over every possible threshold, including ones the team will never use.",
     "d": "F1 at 0.5 describes a policy the team does not follow."})
register_quiz(
    "w05.19_q5", "b",
    "A score of 0.8 should mean about 80% churn; 45% means the scores are over-confident there. Ranking (who is above "
    "whom) can still be good, which is all a budgeted top-k list needs.",
    {"a": "Calibration and ranking are different: you cannot judge ranking from one bin.",
     "c": "The threshold comes from costs and budget, not from one bin's observed rate.",
     "d": "Calibrated would mean about 80% of them churn."})

register_quiz(
    "w05.20_q1", "b",
    "The budget is a limit, not a target. Each extra call goes to a lower-scored customer; once the chance that they "
    "churn falls below the break-even precision, the call costs more than it is expected to bring back.",
    {"a": "Using the whole budget can lose money when the last calls go to customers who are unlikely to leave.",
     "c": "The size of the validation set affects how sure we are, not whether a budget should be filled.",
     "d": "The threshold comes from costs; nothing here suggests overfitting."})
register_quiz(
    "w05.20_q2", "b",
    "Tuning on the test set turns it into a second validation set and its numbers become optimistic (notebook 17). "
    "Report the validation choice; if you want to explore, use validation data or cross-validation.",
    {"a": "That is choosing on the test set: the reported value would be biased upwards.",
     "c": "Averaging still uses the test results to choose.",
     "d": "Training on the test set destroys your only honest estimate."})
register_quiz(
    "w05.20_q3", "b",
    "The team acts on one list of a given size, so compare lists of that size: their precision and expected value. "
    "AUC is a good overall ranking summary, but it is not the decision.",
    {"a": "It can: use days_since_last_order as the score, as in Exercise 3.",
     "c": "They can, but a fair comparison holds the size (and so the cost) fixed.",
     "d": "scikit-learn has no opinion about this comparison."})
register_quiz(
    "w05.20_q4", "b",
    "A few dozen calls on a small test set, under assumed costs and success rate, give a rough estimate with wide "
    "uncertainty. A pilot with a random control group measures what actually happens.",
    {"a": "A small test set gives an estimate, not a proof, and the costs themselves are assumptions.",
     "c": "Too pessimistic: there is evidence the model ranks better than the baseline, just with uncertainty.",
     "d": "Nothing in this setup retrains the model from call outcomes."})
