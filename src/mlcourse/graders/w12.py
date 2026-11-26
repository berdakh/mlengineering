"""Week 12 graders: capstone and career (notebooks 45-48).

45 assembles the SKAB project end to end (split, detector, evaluation with a bootstrap over experiments, a saved
detector with metadata, the scoring function the API calls, a monitoring summary); 46 checks written documents
structurally; 47 is interview practice (SQL, Python, system design, STAR); 48 is the final assessment.

Everything is graded offline on small synthetic inputs (and on data/course/shop.db plus a regenerated variant for
SQL). Reference versions here are written independently of the notebook solutions; tests check behaviour.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import math
import re
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from mlcourse.grader import exercise, register_quiz

_REFERENCES: dict = {}
_NOTED: set = set()


def use(fn, *args, **kwargs):
    """Call your function `fn`; if it is not written yet, use the course's reference version (and say so)."""
    try:
        return fn(*args, **kwargs)
    except NotImplementedError:
        name = getattr(fn, "__name__", "")
        if name not in _REFERENCES:
            raise
        if name not in _NOTED:
            _NOTED.add(name)
            print(f"(note: `{name}` is not finished yet, so the course's reference version was used here. "
                  "Come back to that exercise.)")
        return _REFERENCES[name](*args, **kwargs)


def _reference(fn):
    _REFERENCES[fn.__name__] = fn
    return fn


def _callable(fn, what="your answer"):
    if fn is None:
        raise NotImplementedError
    if not callable(fn):
        raise AssertionError(f"{what} should be a function (pass its name without parentheses)")


def _close(a, b, tol=1e-9) -> bool:
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return False
    return abs(a - b) <= tol * max(1.0, abs(b))


def _raises(fn, exc, *args, **kwargs) -> bool:
    try:
        fn(*args, **kwargs)
    except NotImplementedError:
        raise
    except exc:
        return True
    except Exception:
        return False
    return False


# ============================================================================ 45 · capstone references
@_reference
def split_ids(all_ids, manifest):
    test = sorted(manifest["test"])
    missing = [i for i in test if i not in set(all_ids)]
    if missing:
        raise ValueError(f"test experiments not found: {missing}")
    exclude = set(test) | set(manifest.get("reference_normal", []))
    return {"dev": sorted(i for i in all_ids if i not in exclude), "test": test}


@_reference
def group_violations(split, overlap_groups):
    dev, test = set(split["dev"]), set(split["test"])
    return [sorted(g) for g in overlap_groups if set(g) & dev and set(g) & test]


@_reference
def causal_scores(values, burn_in=100):
    v = np.asarray(values, dtype=float)
    if len(v) < burn_in:
        raise ValueError("fewer values than the burn-in")
    mu, sd = v[:burn_in].mean(), v[:burn_in].std()
    if sd == 0:
        raise ValueError("constant burn-in")
    z = np.abs((v - mu) / sd)
    z[:burn_in] = 0.0
    return z


@_reference
def pooled_pr_auc(frames):
    from sklearn.metrics import average_precision_score
    y = np.concatenate([np.asarray(a, dtype=int) for a, _ in frames])
    s = np.concatenate([np.asarray(b, dtype=float) for _, b in frames])
    if y.sum() == 0:
        raise ValueError("no positive labels")
    return float(average_precision_score(y, s))


@_reference
def event_outcome(labels, alarm_indices):
    y = np.asarray(labels)
    if not (y == 1).any():
        raise ValueError("no labelled anomaly")
    start = int(np.argmax(y == 1))
    if len(alarm_indices) == 0:
        return {"outcome": "missed", "delay": None}
    first = int(min(alarm_indices))
    return {"outcome": "early" if first < start else "detected", "delay": first - start}


@_reference
def bootstrap_over_experiments(items, metric, n_boot=1000, seed=0):
    rng = np.random.default_rng(seed)
    n = len(items)
    stats = [metric([items[k] for k in rng.integers(0, n, size=n)]) for _ in range(n_boot)]
    low, high = np.percentile(stats, [2.5, 97.5])
    return float(metric(list(items))), float(low), float(high)


REQUIRED_METADATA = ("created", "split_version", "metrics")


def _params_hash(params) -> str:
    return hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()


@_reference
def save_detector(params, metadata, folder):
    missing = [k for k in REQUIRED_METADATA if k not in metadata]
    if missing:
        raise ValueError(f"metadata is missing {missing}")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "detector.json"
    path.write_text(json.dumps({"params": params, "metadata": metadata, "sha256": _params_hash(params)}, indent=2))
    return path


@_reference
def load_detector(folder):
    blob = json.loads((Path(folder) / "detector.json").read_text())
    if _params_hash(blob["params"]) != blob["sha256"]:
        raise ValueError("checksum mismatch: the parameters changed since they were saved")
    return blob["params"], blob["metadata"]


def _ref_alarms(z, burn_in, threshold, min_run):
    out, run = [], 0
    for t, s in enumerate(z):
        run = run + 1 if (t >= burn_in and s > threshold) else 0
        if run >= min_run:
            out.append(t)
    return out


@_reference
def score_window(readings, params):
    b = params["burn_in"]
    v = np.asarray(readings, dtype=float)
    if len(v) <= b:
        raise ValueError("the window must be longer than the burn-in")
    if not np.all(np.isfinite(v)):
        raise ValueError("readings must be finite numbers")
    z = causal_scores(v, b)
    a = _ref_alarms(z, b, params["threshold"], params["min_run"])
    return {"n_alarms": len(a), "first_alarm": a[0] if a else None, "max_z": float(z[b:].max())}


@_reference
def monitoring_summary(log, reference_mean, reference_std):
    ok = log[log["status"] == 200]
    return {
        "n_requests": int(len(log)),
        "error_rate": float((log["status"] != 200).mean()),
        "latency_p95_ms": float(np.percentile(log["latency_ms"], 95)),
        "alarm_rate": float((ok["n_alarms"] > 0).mean()),
        "flow_shift": float(abs(ok["mean_flow"].mean() - reference_mean) / reference_std),
    }


# ============================================================================ 45 · tests
_MANIFEST = {"test": ["b/1", "a/3"], "reference_normal": ["free/free"], "version": "v9"}
_IDS = ["a/1", "a/2", "a/3", "b/0", "b/1", "c/7", "free/free"]


@exercise("w12.split_ids", hint="Start from the manifest's test list; everything else that is not reference data "
                                 "is development data. Sort both lists.")
def _(fn):
    _callable(fn)
    got = fn(list(_IDS), dict(_MANIFEST))
    exp = split_ids(_IDS, _MANIFEST)
    if not isinstance(got, dict) or set(got) != {"dev", "test"}:
        raise AssertionError("return a dict with exactly two keys, 'dev' and 'test'")
    if sorted(got["test"]) != exp["test"]:
        raise AssertionError("the test list should be exactly the manifest's test experiments")
    if "free/free" in got["dev"]:
        raise AssertionError("the fault-free reference recording ended up in 'dev': leave reference data out")
    if set(got["dev"]) & set(got["test"]):
        raise AssertionError("an experiment is in both dev and test")
    if sorted(got["dev"]) != exp["dev"]:
        raise AssertionError("'dev' should hold every other experiment")
    if list(got["dev"]) != exp["dev"] or list(got["test"]) != exp["test"]:
        raise AssertionError("sort both lists, so the split prints the same way every time")
    shuffled = list(reversed(_IDS))
    if fn(shuffled, dict(_MANIFEST)) != exp:
        raise AssertionError("the result changes when the input ids come in another order")
    m2 = {"test": ["x/1"], "version": "v1"}
    got2 = fn(["x/0", "x/1", "x/2"], m2)
    if got2 != {"dev": ["x/0", "x/2"], "test": ["x/1"]}:
        raise AssertionError("a manifest without 'reference_normal' should work too (nothing to exclude)")
    if not _raises(fn, ValueError, ["a/1", "a/2"], {"test": ["a/9"]}):
        raise AssertionError("a test experiment that does not exist should raise ValueError, not be ignored")


@exercise("w12.group_violations", hint="A group is a problem when some of its members are in dev AND some in test.")
def _(fn):
    _callable(fn)
    split = {"dev": ["a/1", "a/2", "b/0"], "test": ["a/3", "b/1"]}
    groups = [["a/1", "a/3"], ["b/0", "c/9"], ["b/1", "a/2", "x/1"], ["a/3", "b/1"]]
    got = fn(split, groups)
    exp = group_violations(split, groups)
    if not isinstance(got, list):
        raise AssertionError("return a list of groups")
    if any(g == ["a/3", "b/1"] or sorted(g) == ["a/3", "b/1"] for g in got):
        raise AssertionError("a group entirely inside the test set is fine; only groups split across dev and test "
                             "are violations")
    if any(sorted(g) == ["b/0", "c/9"] for g in got):
        raise AssertionError("a group whose other members are in neither list is not split across dev and test")
    if [sorted(g) for g in got] != exp:
        raise AssertionError(f"expected {len(exp)} violating group(s), got {len(got)}")
    if fn(split, []) != []:
        raise AssertionError("no groups should give an empty list")


@exercise("w12.causal_scores", hint="Mean and np.std of the first burn_in values only; |x - mean| / std; then set "
                                     "the burn-in positions to 0.")
def _(fn):
    _callable(fn)
    rng = np.random.default_rng(3)
    v = rng.normal(10, 2, 300)
    got = np.asarray(fn(v, 100), dtype=float)
    exp = causal_scores(v, 100)
    if got.shape != exp.shape:
        raise AssertionError(f"expected one score per reading ({len(exp)}), got shape {got.shape}")
    if np.any(got[:100] != 0):
        raise AssertionError("scores inside the burn-in should be 0: the detector does not judge its own baseline")
    sd1 = np.abs((v - v[:100].mean()) / v[:100].std(ddof=1))
    if np.allclose(got[100:], sd1[100:]) and not np.allclose(got[100:], exp[100:]):
        raise AssertionError("use np.std (divides by n), as the served detector does; you used the n-1 version")
    full = np.abs((v - v.mean()) / v.std())
    if np.allclose(got[100:], full[100:]):
        raise AssertionError("the mean and std must come from the burn-in only; using all readings looks into the "
                             "future")
    if not np.allclose(got, exp):
        raise AssertionError("the scores after the burn-in are not |x - mean| / std")
    w = v.copy()
    w[250:] += 50
    if not np.allclose(np.asarray(fn(w, 100))[:250], got[:250]):
        raise AssertionError("changing readings after t changed the score at t: scores must use the past only")
    if not np.allclose(np.asarray(fn(list(v[:150]), 50), dtype=float), causal_scores(v[:150], 50)):
        raise AssertionError("it should also work on a plain list and another burn_in")
    if not _raises(fn, ValueError, v[:20], 100):
        raise AssertionError("fewer readings than the burn-in should raise ValueError")
    if not _raises(fn, ValueError, [5.0] * 120 + [6.0] * 10, 100):
        raise AssertionError("a constant burn-in (std 0) should raise ValueError, not divide by zero")


def _frames(seed, n=4):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        y = (rng.random(80) < 0.3).astype(int)
        y[0] = 1
        s = rng.random(80) + 0.6 * y
        out.append((y, s))
    return out


@exercise("w12.pooled_pr_auc", hint="Concatenate all labels and all scores, then average_precision_score.")
def _(fn):
    _callable(fn)
    from sklearn.metrics import average_precision_score
    for seed in (0, 1, 2):
        fr = _frames(seed)
        got = fn(fr)
        exp = pooled_pr_auc(fr)
        mean_per = float(np.mean([average_precision_score(a, b) for a, b in fr]))
        if _close(got, mean_per, 1e-9) and not _close(got, exp, 1e-9):
            raise AssertionError("you averaged one PR-AUC per experiment; the task asks for one PR-AUC on all "
                                 "readings pooled together")
        if not _close(got, exp, 1e-9):
            raise AssertionError("the pooled PR-AUC differs from the expected value")
    lists = [(list(a), list(b)) for a, b in _frames(4)]
    if not _close(fn(lists), pooled_pr_auc(lists)):
        raise AssertionError("it should accept plain lists too")
    if not _raises(fn, ValueError, [(np.zeros(10, int), np.random.default_rng(0).random(10))]):
        raise AssertionError("frames with no positive labels at all should raise ValueError: PR-AUC is undefined")


@exercise("w12.event_outcome", hint="start = first index where the label is 1; compare the FIRST alarm with it.")
def _(fn):
    _callable(fn)
    y = np.array([0] * 50 + [1] * 30 + [0] * 20)
    cases = [([], "missed", None), ([60, 61, 62], "detected", 10), ([50], "detected", 0),
             ([20, 70], "early", -30), ([90, 55], "detected", 5)]
    for alarms, outcome, delay in cases:
        got = fn(y, alarms)
        if not isinstance(got, dict) or set(got) != {"outcome", "delay"}:
            raise AssertionError("return a dict with keys 'outcome' and 'delay'")
        if got["outcome"] != outcome:
            raise AssertionError(f"alarms at {alarms} with the anomaly starting at 50: outcome should not be "
                                 f"{got['outcome']!r}")
        if (got["delay"] is None) != (delay is None) or (delay is not None and int(got["delay"]) != delay):
            raise AssertionError(f"alarms at {alarms}, anomaly starting at 50: the delay is wrong (first alarm "
                                 "minus start, None when missed)")
    if fn(list(y), np.array([75]))["delay"] != 25:
        raise AssertionError("it should accept lists and arrays")
    if not _raises(fn, ValueError, np.zeros(30, int), [3]):
        raise AssertionError("labels with no anomaly should raise ValueError")


@exercise("w12.bootstrap_over_experiments", hint="Each round: rng.integers(0, n, size=n) picks n experiments "
                                                  "with replacement; compute the metric on them; then take the "
                                                  "2.5th and 97.5th percentiles.")
def _(fn):
    _callable(fn)
    items = list(np.random.default_rng(1).normal(0.7, 0.1, 9))
    mean = lambda xs: float(np.mean(xs))  # noqa: E731
    got = fn(items, mean, n_boot=2000, seed=0)
    if not isinstance(got, tuple) or len(got) != 3:
        raise AssertionError("return a tuple (point, low, high)")
    point, low, high = map(float, got)
    if not _close(point, mean(items)):
        raise AssertionError("the point estimate should be the metric on all experiments, not a bootstrap average")
    ref = bootstrap_over_experiments(items, mean, n_boot=2000, seed=0)
    if not (low <= point <= high):
        raise AssertionError("the interval should contain the point estimate for a mean")
    if abs(low - ref[1]) > 0.02 or abs(high - ref[2]) > 0.02:
        raise AssertionError("the interval is too far from a 95% percentile bootstrap: resample n experiments with "
                             "replacement each round and take the 2.5th and 97.5th percentiles")
    seen = []

    def spy(xs):
        seen.append(list(xs))
        return float(len(xs))
    objs = [object() for _ in range(5)]
    fn(objs, spy, n_boot=50, seed=1)
    rounds = [s for s in seen if s and all(any(x is o for o in objs) for x in s)]
    if len(rounds) < 50:
        raise AssertionError("the metric should be called on lists of the ORIGINAL experiments (resampled), once "
                             "per round")
    if any(len(s) != 5 for s in rounds):
        raise AssertionError("each bootstrap sample should have as many experiments as the original (n of n)")
    if all(len({id(x) for x in s}) == 5 for s in rounds):
        raise AssertionError("no sample ever repeated an experiment: resample WITH replacement")
    if fn(items, mean, n_boot=300, seed=5) != fn(items, mean, n_boot=300, seed=5):
        raise AssertionError("the same seed should give the same interval")
    c = fn(items, lambda xs: 1.0, n_boot=100, seed=0)
    if not (_close(c[1], 1.0) and _close(c[2], 1.0)):
        raise AssertionError("a metric that is always 1 should give the interval (1, 1)")


@exercise("w12.save_load", hint="Save params, metadata and a SHA-256 of json.dumps(params, sort_keys=True); on "
                                "load recompute the hash and compare.")
def _(pair):
    if pair is None:
        raise NotImplementedError
    if not (isinstance(pair, tuple) and len(pair) == 2 and all(callable(f) for f in pair)):
        raise AssertionError("pass the tuple (save_detector, load_detector)")
    save, load = pair
    params = {"burn_in": 100, "threshold": 3.0, "min_run": 5, "sensor": "Volume Flow RateRMS"}
    meta = {"created": "2026-11-26", "split_version": "v2", "metrics": {"pr_auc": 0.88}, "note": "x"}
    tmp = Path(tempfile.mkdtemp(prefix="mlcourse_w12_"))
    try:
        save(params, meta, tmp / "det")
        if not (tmp / "det" / "detector.json").is_file():
            raise AssertionError("save_detector should write <folder>/detector.json (creating the folder)")
        blob = json.loads((tmp / "det" / "detector.json").read_text())
        if not {"params", "metadata", "sha256"} <= set(blob):
            raise AssertionError("detector.json should hold 'params', 'metadata' and 'sha256'")
        if blob["sha256"] != _params_hash(params):
            raise AssertionError("'sha256' should be the hash of json.dumps(params, sort_keys=True)")
        got = load(tmp / "det")
        if not (isinstance(got, tuple) and len(got) == 2 and got[0] == params and got[1] == meta):
            raise AssertionError("load_detector should return (params, metadata) exactly as saved")
        blob["params"]["threshold"] = 1.0
        (tmp / "det" / "detector.json").write_text(json.dumps(blob))
        if not _raises(load, ValueError, tmp / "det"):
            raise AssertionError("a detector.json whose params were edited after saving should raise ValueError")
        if not _raises(save, ValueError, params, {"created": "x", "metrics": {}}, tmp / "d2"):
            raise AssertionError("metadata without 'split_version' should be refused with ValueError")
        if (tmp / "d2" / "detector.json").exists():
            raise AssertionError("refused metadata should not leave a detector.json behind")
        save(params, meta, str(tmp / "d3"))
        if load(str(tmp / "d3"))[0] != params:
            raise AssertionError("folders given as strings should work too")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


_PARAMS = {"burn_in": 100, "threshold": 3.0, "min_run": 5}


def _signal(seed, fault_at=None, n=260, size=6.0):
    rng = np.random.default_rng(seed)
    v = rng.normal(30.0, 0.5, n)
    if fault_at is not None:
        v[fault_at:] -= size
    return v


@exercise("w12.score_window", hint="Reuse causal_scores, then the persistence rule from notebook 36; max_z is over "
                                   "readings after the burn-in.")
def _(fn):
    _callable(fn)
    for seed, fault in [(0, 180), (1, None), (2, 120), (3, 255)]:
        v = _signal(seed, fault)
        got = fn(list(v), dict(_PARAMS))
        exp = score_window(v, _PARAMS)
        if not isinstance(got, dict) or set(got) != {"n_alarms", "first_alarm", "max_z"}:
            raise AssertionError("return a dict with keys 'n_alarms', 'first_alarm', 'max_z'")
        if got["n_alarms"] != exp["n_alarms"] or got["first_alarm"] != exp["first_alarm"]:
            where = "no fault" if fault is None else f"a fault from reading {fault}"
            raise AssertionError(f"wrong alarms on a signal with {where}: expected {exp['n_alarms']} alarm(s)")
        if not _close(got["max_z"], exp["max_z"], 1e-6):
            raise AssertionError("max_z should be the largest |z| after the burn-in")
    spike = _signal(4)
    spike[150] = 60
    if fn(spike, dict(_PARAMS))["n_alarms"] != 0:
        raise AssertionError("a single spike raised an alarm: apply the min_run persistence rule")
    p2 = {"burn_in": 50, "threshold": 4.0, "min_run": 2}
    v = _signal(5, 100)
    if fn(v, p2) != score_window(v, p2):
        raise AssertionError("use the burn_in, threshold and min_run from params, not fixed values")
    if not _raises(fn, ValueError, list(_signal(6)[:100]), dict(_PARAMS)):
        raise AssertionError("a window no longer than the burn-in should raise ValueError")
    bad = _signal(7)
    bad[200] = float("nan")
    if not _raises(fn, ValueError, bad, dict(_PARAMS)):
        raise AssertionError("a NaN reading should raise ValueError (the API turns it into a 422)")


def _log(seed, n=200):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "request_id": [f"r{i}" for i in range(n)],
        "latency_ms": rng.gamma(2.0, 4.0, n),
        "status": rng.choice([200, 200, 200, 200, 200, 200, 200, 422, 500], n),
        "n_alarms": rng.choice([0, 0, 0, 3, 12], n),
        "mean_flow": rng.normal(31.0 + seed * 0.3, 0.4, n),
    })


@exercise("w12.monitoring_summary", hint="Error rate over all requests; alarm rate and flow shift over the "
                                         "successful (status 200) ones only.")
def _(fn):
    _callable(fn)
    for seed in (0, 1, 2):
        log = _log(seed)
        got = fn(log.copy(), 31.0, 0.5)
        exp = monitoring_summary(log, 31.0, 0.5)
        if not isinstance(got, dict) or set(got) != set(exp):
            raise AssertionError(f"return a dict with exactly these keys: {sorted(exp)}")
        for k in exp:
            if _close(got[k], exp[k], 1e-6):
                continue
            if k == "alarm_rate" and _close(got[k], float((log["n_alarms"] > 0).mean()), 1e-6):
                raise AssertionError("alarm_rate counted failed requests too: use status 200 requests only")
            if k == "flow_shift" and _close(got[k], abs(log["mean_flow"].mean() - 31.0) / 0.5, 1e-6):
                raise AssertionError("flow_shift used failed requests too: use status 200 requests only")
            if k == "latency_p95_ms" and _close(got[k], float(log["latency_ms"].mean()), 1e-6):
                raise AssertionError("latency_p95_ms should be the 95th percentile, not the mean")
            raise AssertionError(f"{k!r} is wrong")
    flat = _log(9)
    flat["mean_flow"] = 29.0
    if not _close(fn(flat, 31.0, 0.5)["flow_shift"], 4.0, 1e-6):
        raise AssertionError("flow_shift should be a distance, never negative (use the absolute value)")


register_quiz("w12.45_q1", "c",
              "Seven test experiments are a small sample: 7/7 detected is compatible with a true detection rate well "
              "below 100%. The bootstrap cannot show uncertainty it never sees, so report the count and an exact "
              "binomial bound instead.",
              {"a": "7 of 7 is the observed rate, not proof that every future fault will be caught.",
               "b": "The interval [1, 1] reflects that every resample is 7/7, not that there is no uncertainty.",
               "d": "Resampling readings would ignore that readings within an experiment are dependent; it would "
                    "make the interval even more falsely narrow."})
register_quiz("w12.45_q2", "b",
              "Experiments that share rows must sit on the same side of the split, otherwise the test set contains "
              "data the model has (partly) seen.",
              {"a": "The overlap groups are about duplicated rows, not file size.",
               "c": "Shuffling does not stop shared rows from being on both sides.",
               "d": "Discarding the test set throws away the only unbiased estimate you have."})
register_quiz("w12.45_q3", "a",
              "The checksum shows the parameters are the ones that were evaluated; the metadata says which split "
              "and which numbers they belong to.",
              {"b": "A checksum does not make a detector more accurate.",
               "c": "JSON is not encrypted; the checksum detects changes, it does not hide anything.",
               "d": "Parameters still need to be loaded; the checksum only verifies them."})
register_quiz("w12.45_q4", "d",
              "The burn-in z-score adapts to each experiment's own baseline, so if the window starts mid-fault the "
              "baseline is already faulty: a limitation to write down.",
              {"a": "Latency has nothing to do with this failure mode.",
               "b": "More features would not fix a baseline computed on faulty data.",
               "c": "The detector has no training step on other experiments."})
register_quiz("w12.45_q5", "b",
              "Monitoring summarises what the service saw (inputs, errors, latency, alarm rate); labels arrive late "
              "or never, so accuracy cannot be computed live.",
              {"a": "Without labels you cannot compute PR-AUC in production.",
               "c": "A dashboard does not retrain anything.",
               "d": "Logging every reading of every request is costly and not what the summary is for."})


# ============================================================================ 46 · communicating results
OVERCLAIMS = ("production-ready", "production ready", "guarantee", "100% accurate", "never misses",
              "always detects", "state-of-the-art")


def _ref_format(point, low, high, digits=2):
    if not (low <= point <= high):
        raise ValueError("expected low <= point <= high")
    return f"{point:.{digits}f} (95% CI {low:.{digits}f} to {high:.{digits}f})"


@exercise("w12.format_result", hint="An f-string with :.{digits}f for each of the three numbers.")
def _(fn):
    _callable(fn)
    cases = [((0.884, 0.811, 0.927), {}), ((0.5, 0.5, 0.5), {}), ((12.3456, 10.0, 15.25), {"digits": 1}),
             ((0.83, 0.7, 0.9), {"digits": 3})]
    for args, kw in cases:
        got = fn(*args, **kw)
        exp = _ref_format(*args, **kw)
        if got != exp:
            raise AssertionError(f"for {args} {kw or ''} expected the text {exp!r}, got {got!r}")
    if not _raises(fn, ValueError, 0.9, 0.5, 0.8):
        raise AssertionError("a point outside its own interval is a mistake upstream: raise ValueError")


def _ref_headings(md):
    out, fenced = [], False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        m = re.match(r"^(#{1,6})\s+(.*\S)\s*$", line)
        if m and not fenced:
            out.append((len(m.group(1)), m.group(2).strip()))
    return out


_MD = """# flowguard

Some text with a # hash in the middle.

## Quickstart

```bash
# this is a shell comment, not a heading
python -m flowguard
```

### Details
#not-a-heading
## Results
"""


@exercise("w12.headings", hint="A heading line starts with 1-6 '#' and then a space; toggle a flag on lines that "
                               "start with ``` so code blocks are skipped.")
def _(fn):
    _callable(fn)
    got = fn(_MD)
    exp = _ref_headings(_MD)
    if not isinstance(got, list) or not all(isinstance(h, tuple) and len(h) == 2 for h in got):
        raise AssertionError("return a list of (level, text) tuples")
    got = [(int(a), str(b)) for a, b in got]
    if any("shell comment" in t for _, t in got):
        raise AssertionError("a '#' line inside a ``` code block is a comment, not a heading")
    if any("not-a-heading" in t for _, t in got):
        raise AssertionError("'#not-a-heading' has no space after the '#', so it is not a heading")
    if any("hash in the middle" in t for _, t in got):
        raise AssertionError("only lines that START with '#' are headings")
    if got != exp:
        raise AssertionError(f"expected {exp}, got {got}")
    if fn("") != [] or fn("no headings here\njust text") != []:
        raise AssertionError("text without headings should give []")


def _ref_missing(md, required):
    heads = [t.lower() for _, t in _ref_headings(md)]
    return [r for r in required if not any(r.lower() in h for h in heads)]


@exercise("w12.missing_sections", hint="Lower-case both sides; a section is present if its name appears inside "
                                       "any heading's text.")
def _(fn):
    _callable(fn)
    md = "# Flowguard\n## Overview\ntext\n## How to run it\n## RESULTS (test set)\n```\n## Limitations\n```\n"
    req = ["Overview", "Results", "Limitations", "How to run"]
    got = fn(md, req)
    exp = _ref_missing(md, req)
    if not isinstance(got, list):
        raise AssertionError("return a list of the missing section names")
    if "Results" in got:
        raise AssertionError("'## RESULTS (test set)' contains 'Results' when you ignore case: it counts")
    if "Limitations" not in got:
        raise AssertionError("'## Limitations' inside a code block is not a real heading: it should count as "
                             "missing (use your headings function)")
    if got != exp:
        raise AssertionError(f"expected {exp}, got {got} (keep the order of `required`)")
    if fn(md, []) != []:
        raise AssertionError("no required sections means nothing is missing")


def _section_lines(md, name):
    lines, inside, level, fenced = [], False, 0, False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            if inside:
                lines.append(line)
            continue
        m = None if fenced else re.match(r"^(#{1,6})\s+(.*\S)\s*$", line)
        if m:
            if inside and len(m.group(1)) <= level:
                break
            if not inside and name.lower() in m.group(2).lower():
                inside, level = True, len(m.group(1))
                continue
        if inside:
            lines.append(line)
    return lines


def _ref_unqualified(md, section="Results"):
    out, fenced = [], False
    for line in _section_lines(md, section):
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if re.search(r"\d+\.\d+", line) and "±" not in line and "CI" not in line \
                and "interval" not in line.lower():
            out.append(line.strip())
    return out


_RES = """# Report
## Results
- PR-AUC 0.88 (95% CI 0.81 to 0.93)
- Event recall 7/7 test experiments; lower bound 0.59 from an exact interval
- Median delay 56 readings
- Precision 0.91 at the chosen threshold
| metric | value |
|---|---|
| F1 | 0.84 ± 0.05 |
| recall | 0.80 |
### Notes
- latency 3.2 ms
## Limitations
- 0.5 litres per minute resolution
"""


@exercise("w12.unqualified_numbers", hint="Collect the lines between the section's heading and the next heading of "
                                          "the same or higher level; keep those with a decimal number and no "
                                          "'±', 'CI' or 'interval'.")
def _(fn):
    _callable(fn)
    got = fn(_RES, "Results")
    exp = _ref_unqualified(_RES, "Results")
    if not isinstance(got, list):
        raise AssertionError("return a list of lines")
    got = [str(x).strip() for x in got]
    if any("PR-AUC 0.88" in g for g in got):
        raise AssertionError("a line with 'CI' already has an interval")
    if any("Median delay" in g for g in got):
        raise AssertionError("'56' has no decimal point: the rule only looks at numbers like 0.84")
    if not any("latency 3.2" in g for g in got):
        raise AssertionError("a '### Notes' subsection is still inside '## Results' (a lower level heading does not "
                             "end it)")
    if any("litres" in g for g in got):
        raise AssertionError("'## Limitations' ends the Results section")
    if got != exp:
        raise AssertionError(f"expected {len(exp)} line(s), got {len(got)}: check '±' and the word 'interval'")
    if fn(_RES, "Discussion") != []:
        raise AssertionError("a section that does not exist has no lines, so the answer is []")


def _ref_overclaims(md):
    low = md.lower()
    return sorted({p for p in OVERCLAIMS if p in low})


@exercise("w12.overclaims", hint="Lower-case the text and test each phrase with `in`; return sorted, no duplicates.")
def _(fn):
    _callable(fn)
    cases = ["A production-ready detector that GUARANTEES early alarms.",
             "Guaranteed results; production-ready; production-ready again.",
             "An educational prototype evaluated on 7 laboratory experiments.",
             "It never misses a fault and is State-of-the-Art."]
    for md in cases:
        got = fn(md)
        exp = _ref_overclaims(md)
        if not isinstance(got, list):
            raise AssertionError("return a list of phrases")
        if got != exp:
            raise AssertionError(f"for the text {md!r} expected {exp}, got {got}")


def _bullets(lines):
    return [l for l in lines if re.match(r"^\s*([-*]|\d+\.)\s+\S", l)]


def _words(text):
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'.%-]*", text))


def _doc_checks(md, what, sections, *, results="Results", min_limits=2, words=None, extra=()):
    if md is None or (isinstance(md, str) and "YOUR" in md and "HERE" in md):
        raise NotImplementedError
    if not isinstance(md, str):
        raise AssertionError(f"{what} should be a string of Markdown")
    missing = _ref_missing(md, sections)
    if missing:
        raise AssertionError(f"{what} is missing these section headings: {missing}")
    found = _ref_overclaims(md)
    if found:
        raise AssertionError(f"{what} contains claims the evidence cannot support: {found}")
    if results:
        res = [l for l in _section_lines(md, results) if l.strip()]
        if not res:
            raise AssertionError(f"the '{results}' section of {what} is empty")
        bad = _ref_unqualified(md, results)
        if bad:
            raise AssertionError(f"in '{results}', these lines give a number without an interval: {bad[:2]}")
        if not any(("CI" in l or "interval" in l.lower() or "±" in l) for l in res):
            raise AssertionError(f"the '{results}' section of {what} should give at least one interval")
    lim = _bullets(_section_lines(md, "Limitations"))
    if len(lim) < min_limits:
        raise AssertionError(f"'Limitations' in {what} should list at least {min_limits} limitations as bullets")
    if words:
        n = _words(md)
        if not (words[0] <= n <= words[1]):
            raise AssertionError(f"{what} has about {n} words; aim for {words[0]}-{words[1]}")
    for check, message in extra:
        if not check(md):
            raise AssertionError(message)


README_SECTIONS = ["Overview", "Quickstart", "Results", "Limitations", "Data and licence"]
REPORT_SECTIONS = ["Question", "Data", "Method", "Results", "Limitations", "Next steps"]
CARD_SECTIONS = ["Intended use", "Out of scope", "Evaluation data", "Metrics", "Limitations",
                 "Ethical considerations"]


@exercise("w12.project_readme", hint="Use the five headings, put the commands in a ``` block, give every decimal "
                                     "number in Results an interval, and describe the project as an educational "
                                     "prototype.")
def _(md):
    _doc_checks(md, "the README", README_SECTIONS, extra=[
        (lambda m: "```" in "\n".join(_section_lines(m, "Quickstart")),
         "the Quickstart section should show the commands in a ``` code block"),
        (lambda m: "educational" in m.lower(),
         "say plainly that this is an educational prototype (the word 'educational' is missing)"),
        (lambda m: re.search(r"gpl", "\n".join(_section_lines(m, "Data and licence")), re.I),
         "'Data and licence' should name the dataset's licence (SKAB is GPL-3.0)"),
    ])


@exercise("w12.technical_report", hint="Six headings, 250-1,500 words, intervals in Results, at least two "
                                       "limitation bullets.")
def _(md):
    _doc_checks(md, "the report", REPORT_SECTIONS, words=(250, 1500), extra=[
        (lambda m: _bullets(_section_lines(m, "Next steps")),
         "'Next steps' should list at least one concrete next step as a bullet"),
    ])


@exercise("w12.model_card", hint="Six headings; 'Intended use' says educational; 'Metrics' gives an interval; "
                                 "every section has at least a couple of sentences.")
def _(md):
    _doc_checks(md, "the model card", CARD_SECTIONS, results="Metrics", extra=[
        (lambda m: "educational" in "\n".join(_section_lines(m, "Intended use")).lower(),
         "'Intended use' should say this is for educational use"),
        (lambda m: all(_words("\n".join(_section_lines(m, s))) >= 15 for s in CARD_SECTIONS),
         "every section of the model card needs at least about 15 words; one or more is too short"),
    ])


register_quiz("w12.46_q1", "b",
              "A reader decides in the first screen whether to keep reading: what it is, whether it works, and how "
              "to run it.",
              {"a": "History is for the report, if anywhere; it comes long after the overview.",
               "c": "Code belongs in the repository; the README points to it.",
               "d": "Acknowledgements are fine, but they are not what a reader needs first."})
register_quiz("w12.46_q2", "c",
              "With 7 test experiments the interval is wide; saying so tells the reader how much weight the number "
              "can bear.",
              {"a": "Rounding does not fix a small sample.",
               "b": "Hiding the interval makes the number look more certain than it is.",
               "d": "Reporting the best of several runs is a form of cherry-picking."})
register_quiz("w12.46_q3", "a",
              "A model card is written for people deciding whether to use the model: intended use, limits, data, "
              "metrics and risks.",
              {"b": "Hyperparameters may appear, but they are not the card's purpose.",
               "c": "The card is not marketing; it is about limits as much as strengths.",
               "d": "Licensing is one line, not the purpose."})
register_quiz("w12.46_q4", "d",
              "A limitation is specific and testable: what was not evaluated or where the method fails.",
              {"a": "'More data would help' is true of everything and tells the reader nothing.",
               "b": "Modesty is not a limitation.",
               "c": "Blaming the dataset without saying how it limits the conclusions is not useful."})
register_quiz("w12.46_q5", "b",
              "The evidence is 34 laboratory experiments; nothing was evaluated on a real plant, so the claim must "
              "stay inside that.",
              {"a": "'Production-ready' claims something the project never tested.",
               "c": "Accuracy is not even the metric used, and there is no guarantee.",
               "d": "Saying nothing about scope leaves readers to assume too much."})


# ============================================================================ 47 · interview practice
def _sql():
    from mlcourse.graders.w02 import REVENUE_STATUSES, _check, _line_totals
    return _check, _line_totals, REVENUE_STATUSES


def _revenue_by_customer(T):
    _, line_totals, statuses = _sql()
    it = line_totals(T)
    o = T["orders"]
    keep = o.loc[o["status"].isin(statuses), ["order_id", "customer_id"]]
    per = it.merge(keep, on="order_id").groupby("customer_id")["line_total"].sum()
    return per


@exercise("w12.sql_top_customers", hint="Join customers, orders and order_items; keep delivered and shipped orders; "
                                        "GROUP BY the customer; ORDER BY revenue DESC LIMIT 5.")
def _(q):
    check, line_totals, statuses = _sql()

    def exp(T):
        per = _revenue_by_customer(T).sort_values(ascending=False).head(5)
        c = T["customers"].set_index("customer_id")
        return pd.DataFrame({"customer_id": per.index, "name": c.loc[per.index, "name"].to_numpy(),
                             "revenue": per.round(2).to_numpy()})

    def all_status(T):
        it = line_totals(T).merge(T["orders"][["order_id", "customer_id"]], on="order_id")
        per = it.groupby("customer_id")["line_total"].sum().sort_values(ascending=False).head(5)
        c = T["customers"].set_index("customer_id")
        return pd.DataFrame({"customer_id": per.index, "name": c.loc[per.index, "name"].to_numpy(),
                             "revenue": per.round(2).to_numpy()})

    def no_discount(T):
        it = T["order_items"].copy()
        it["line_total"] = it["quantity"] * it["unit_price"]
        o = T["orders"]
        keep = o.loc[o["status"].isin(statuses), ["order_id", "customer_id"]]
        per = it.merge(keep, on="order_id").groupby("customer_id")["line_total"].sum()
        per = per.sort_values(ascending=False).head(5)
        c = T["customers"].set_index("customer_id")
        return pd.DataFrame({"customer_id": per.index, "name": c.loc[per.index, "name"].to_numpy(),
                             "revenue": per.round(2).to_numpy()})

    check(q, exp, ordered=True, mistakes=[
        (all_status, "you counted every order; revenue only comes from delivered and shipped orders"),
        (no_discount, "revenue per line is quantity * unit_price * (1 - discount): the discount is missing")])


@exercise("w12.sql_monthly_change", hint="A CTE with one row per month, then LAG(n_orders) OVER (ORDER BY month).")
def _(q):
    check, _, _ = _sql()

    def exp(T):
        o = T["orders"].copy()
        o["month"] = o["order_date"].str[:7]
        m = o.groupby("month").size().rename("n_orders").reset_index().sort_values("month")
        m["change"] = m["n_orders"].diff()
        return m.reset_index(drop=True)

    def reversed_(T):
        e = exp(T)
        e["change"] = -e["change"]
        return e

    check(q, exp, ordered=True, mistakes=[
        (reversed_, "the sign is flipped: change = this month minus the previous month")])


@exercise("w12.sql_repeat_rate", hint="Count non-cancelled orders per customer in a CTE; then the share of those "
                                      "customers with 2 or more. Multiply by 1.0 to avoid integer division.")
def _(q):
    check, _, _ = _sql()

    def exp(T):
        o = T["orders"]
        n = o.loc[o["status"] != "cancelled"].groupby("customer_id").size()
        return pd.DataFrame({"repeat_rate": [float((n >= 2).mean())]})

    def with_cancelled(T):
        n = T["orders"].groupby("customer_id").size()
        return pd.DataFrame({"repeat_rate": [float((n >= 2).mean())]})

    def all_customers(T):
        o = T["orders"]
        n = o.loc[o["status"] != "cancelled"].groupby("customer_id").size()
        return pd.DataFrame({"repeat_rate": [float((n >= 2).sum() / len(T["customers"]))]})

    check(q, exp, decimals=3, mistakes=[
        (with_cancelled, "cancelled orders should not count"),
        (all_customers, "the denominator should be customers who have at least one (non-cancelled) order, not every "
                        "customer"),
        (lambda T: pd.DataFrame({"repeat_rate": [0.0]}), "0: integer division? multiply by 1.0 first")])


def _ref_dedupe(records, key, ts):
    best = {}
    for r in records:
        k = r[key]
        if k not in best or r[ts] >= best[k][ts]:
            best[k] = r
    return [best[k] for k in sorted(best)]


@exercise("w12.py_dedupe_latest", hint="One pass with a dict from key to the best record so far; use >= so a later "
                                       "record wins a tie; sort the keys at the end.")
def _(fn):
    _callable(fn)
    recs = [{"id": 2, "t": 5, "v": "a"}, {"id": 1, "t": 3, "v": "b"}, {"id": 2, "t": 9, "v": "c"},
            {"id": 1, "t": 1, "v": "d"}, {"id": 3, "t": 4, "v": "e"}, {"id": 3, "t": 4, "v": "f"}]
    snapshot = [dict(r) for r in recs]
    got = fn(recs, "id", "t")
    exp = _ref_dedupe(recs, "id", "t")
    if recs != snapshot:
        raise AssertionError("your function changed the input records; return new results instead")
    if not isinstance(got, list) or [r.get("id") for r in got] != [1, 2, 3]:
        raise AssertionError("return one record per key, sorted by key")
    if got[1]["v"] != "c" or got[0]["v"] != "b":
        raise AssertionError("keep the record with the LATEST timestamp for each key")
    if got != exp:
        raise AssertionError("on a tie in the timestamp, keep the record that comes later in the input")
    if fn([], "id", "t") != []:
        raise AssertionError("an empty input should give []")
    words = [{"k": "b", "ts": "2025-01-02"}, {"k": "a", "ts": "2025-03-01"}, {"k": "b", "ts": "2025-02-01"}]
    if fn(words, "k", "ts") != _ref_dedupe(words, "k", "ts"):
        raise AssertionError("it should work for any key and timestamp field names (here 'k' and ISO date strings)")


def _ref_ma(xs, k):
    if k < 1:
        raise ValueError
    return [float(np.mean(xs[max(0, i - k + 1): i + 1])) for i in range(len(xs))]


@exercise("w12.py_moving_average", hint="Element i is the mean of xs[max(0, i-k+1) : i+1].")
def _(fn):
    _callable(fn)
    for xs, k in [([1, 2, 3, 4, 5], 2), ([4.0, 8.0, 6.0], 5), ([3, 1, 4, 1, 5, 9, 2, 6], 3), ([7], 1)]:
        got = fn(list(xs), k)
        exp = _ref_ma(xs, k)
        if not isinstance(got, list) or len(got) != len(exp):
            raise AssertionError(f"return a list of {len(exp)} values for an input of length {len(xs)}")
        if not np.allclose(got, exp):
            if np.allclose(got[k - 1:], exp[k - 1:]) if len(xs) >= k else False:
                raise AssertionError("the first k-1 values are wrong: average whatever values are available so far")
            raise AssertionError(f"for xs={xs}, k={k} expected {exp}")
    if fn([], 3) != []:
        raise AssertionError("an empty input should give []")
    if not _raises(fn, ValueError, [1, 2], 0):
        raise AssertionError("k = 0 makes no sense: raise ValueError")


def _ref_topk(text, k):
    from collections import Counter
    c = Counter(re.findall(r"[a-z]+", text.lower()))
    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:k]


@exercise("w12.py_top_k_words", hint="re.findall(r'[a-z]+', text.lower()), a Counter, then sort by (-count, word).")
def _(fn):
    _callable(fn)
    cases = [("the cat and the hat. The END", 2), ("b a c b a", 3), ("Data, data; DATA! model", 5), ("", 3),
             ("zeta alpha beta", 2)]
    for text, k in cases:
        got = fn(text, k)
        exp = _ref_topk(text, k)
        if not isinstance(got, list):
            raise AssertionError("return a list of (word, count) tuples")
        got = [tuple(x) for x in got]
        if got != exp:
            raise AssertionError(f"for {text!r}, k={k}: expected {exp}, got {got} (ties go alphabetically)")


DESIGN_KEYS = ["goal", "data", "baseline", "model", "offline_evaluation", "serving", "monitoring", "rollback"]
_METRIC_WORDS = ("precision", "recall", "auc", "f1", "mae", "rmse", "accuracy", "cost", "delay", "brier")
_SPLIT_WORDS = ("split", "validation", "test", "cross-validation", "holdout", "hold-out", "time")


@exercise("w12.system_design", hint="Fill every key with at least two sentences; name a metric and how you split "
                                    "the data; say what you watch in production and how you roll back.")
def _(d):
    if d is None:
        raise NotImplementedError
    if not isinstance(d, dict):
        raise AssertionError("the answer should be a dict of strings")
    missing = [k for k in DESIGN_KEYS if k not in d]
    if missing:
        raise AssertionError(f"these parts of the design are missing: {missing}")
    if any(not isinstance(d[k], str) or "YOUR" in d[k] for k in DESIGN_KEYS):
        raise NotImplementedError
    short = [k for k in DESIGN_KEYS if _words(d[k]) < 12]
    if short:
        raise AssertionError(f"these parts are too short to show your reasoning (aim for 2+ sentences): {short}")
    ev = d["offline_evaluation"].lower()
    if not any(w in ev for w in _METRIC_WORDS):
        raise AssertionError("offline_evaluation should name the metric you would use (and why)")
    if not any(w in ev for w in _SPLIT_WORDS):
        raise AssertionError("offline_evaluation should say how you would split the data")
    mon = d["monitoring"].lower()
    if not any(w in mon for w in ("drift", "latency", "alert", "error rate", "distribution")):
        raise AssertionError("monitoring should say what you watch (inputs/drift, latency, errors) and when to alert")
    if not any(w in d["baseline"].lower() for w in ("rule", "heuristic", "constant", "simple", "baseline", "majority",
                                                     "average", "last")):
        raise AssertionError("baseline should describe a simple non-ML or trivial approach to beat")
    found = _ref_overclaims(" ".join(d.values()))
    if found:
        raise AssertionError(f"the design makes claims no design can make: {found}")


STAR_KEYS = ["situation", "task", "action", "result"]


@exercise("w12.star_story", hint="Four parts of at least 15 words each; 'action' in the first person ('I ...'); "
                                 "'result' with something measurable.")
def _(d):
    if d is None:
        raise NotImplementedError
    if not isinstance(d, dict) or any(k not in d for k in STAR_KEYS):
        raise AssertionError(f"the answer should be a dict with keys {STAR_KEYS}")
    if any(not isinstance(d[k], str) or "YOUR" in d[k] for k in STAR_KEYS):
        raise NotImplementedError
    short = [k for k in STAR_KEYS if _words(d[k]) < 15]
    if short:
        raise AssertionError(f"too short to be convincing: {short} (aim for 2-3 sentences each)")
    if not re.search(r"\bI\b", d["action"]):
        raise AssertionError("'action' should say what YOU did ('I wrote...', 'I asked...'), not what 'we' did")
    if not re.search(r"\d", d["result"]):
        raise AssertionError("'result' should include something measurable (a number, a time saved, a count)")
    total = sum(_words(d[k]) for k in STAR_KEYS)
    if total > 350:
        raise AssertionError(f"about {total} words: a spoken answer should take about two minutes (under ~350 words)")


register_quiz("w12.47_q1", "c",
              "Scaling inside the pipeline means the scaler is fitted on the training folds only; fitting it on all "
              "data first leaks test-set statistics into training.",
              {"a": "Scaling does not change which rows are in which fold.",
               "b": "Scaling is not a source of label leakage by itself; doing it before the split is the problem.",
               "d": "Tree models do not need scaling, but that is not the question."})
register_quiz("w12.47_q2", "b",
              "With 1% positives, a model that flags nobody gets 99% accuracy; precision/recall or PR-AUC show "
              "whether positives are actually found.",
              {"a": "Accuracy is dominated by the majority class here.",
               "c": "ROC-AUC can look good with rare positives while precision is poor; it is not the best single "
                    "choice here.",
               "d": "MSE is a regression loss."})
register_quiz("w12.47_q3", "d",
              "Training error far below validation error is the classic overfitting (high-variance) signature; "
              "regularise, simplify or get more data.",
              {"a": "High bias shows as both errors being high and close together.",
               "b": "Leakage usually makes VALIDATION look too good, not worse.",
               "c": "A bug is possible, but the pattern described is the textbook variance gap."})
register_quiz("w12.47_q4", "a",
              "Rows from the same customer are dependent; a random split puts the same customer on both sides and "
              "the score measures memorisation of customers.",
              {"b": "More folds do not fix rows of one customer being on both sides.",
               "c": "Stratifying balances labels, not customers.",
               "d": "Shuffling is exactly what puts one customer in both train and test."})
register_quiz("w12.47_q5", "c",
              "Clarify the goal and constraints first: the right design depends on latency, data, labels and what a "
              "mistake costs.",
              {"a": "Naming a model first answers a question you have not asked yet.",
               "b": "Data collection comes after you know what you need.",
               "d": "Infrastructure follows from requirements."})
register_quiz("w12.47_q6", "b",
              "Interviews vary by company and interviewer; practice improves how clearly you show what you can do, "
              "and nothing guarantees an outcome.",
              {"a": "No amount of practice guarantees an offer.",
               "c": "Memorised answers break on the first follow-up question.",
               "d": "Many interviews still include SQL and coding exercises."})


# ============================================================================ 48 · final assessment
@exercise("w12.final_sql", hint="Revenue per category from delivered and shipped orders, then divide by the total "
                                "(a window SUM(...) OVER () or a subquery). Do not round.")
def _(q):
    check, line_totals, statuses = _sql()

    def per_cat(T, statuses_=statuses):
        it = line_totals(T).merge(T["orders"][["order_id", "status"]], on="order_id")
        if statuses_ is not None:
            it = it.loc[it["status"].isin(statuses_)]
        it = it.merge(T["products"][["product_id", "category"]], on="product_id")
        r = it.groupby("category")["line_total"].sum().sort_values(ascending=False)
        return pd.DataFrame({"category": r.index, "revenue": r.to_numpy(), "share": (r / r.sum()).to_numpy()})

    check(q, per_cat, ordered=True, decimals=3, mistakes=[
        (lambda T: per_cat(T, None), "you counted every order; revenue only comes from delivered and shipped orders"),
        (lambda T: per_cat(T).assign(share=lambda d: d["share"] * 100),
         "share should be a fraction between 0 and 1, not a percentage")])


def _ref_customer_summary(orders, cutoff):
    cutoff = pd.Timestamp(cutoff)
    o = orders.copy()
    o["order_date"] = pd.to_datetime(o["order_date"])
    o = o[(o["status"] != "cancelled") & (o["order_date"] <= cutoff)]
    g = o.groupby("customer_id")["order_date"]
    out = pd.DataFrame({"n_orders": g.size(), "days_since_last": (cutoff - g.max()).dt.days})
    return out.sort_index()


def _orders_frame(seed):
    rng = np.random.default_rng(seed)
    n = 60
    return pd.DataFrame({
        "order_id": range(1, n + 1),
        "customer_id": rng.integers(1, 12, n),
        "order_date": (pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 300, n), "D")).strftime("%Y-%m-%d"),
        "status": rng.choice(["delivered", "shipped", "cancelled", "pending"], n),
    })


@exercise("w12.final_pandas", hint="Filter (not cancelled, on or before the cutoff), then groupby customer_id: size "
                                   "and the latest date.")
def _(fn):
    _callable(fn)
    for seed, cutoff in [(0, "2025-08-01"), (1, "2025-10-27"), (2, "2025-03-15")]:
        df = _orders_frame(seed)
        before = df.copy()
        got = fn(df, cutoff)
        exp = _ref_customer_summary(before, cutoff)
        if not df.equals(before):
            raise AssertionError("your function changed the input DataFrame; work on a copy")
        if not isinstance(got, pd.DataFrame):
            raise AssertionError("return a DataFrame")
        if got.index.name != "customer_id" and "customer_id" in got.columns:
            got = got.set_index("customer_id")
        if set(got.columns) != {"n_orders", "days_since_last"}:
            raise AssertionError("columns should be exactly n_orders and days_since_last, indexed by customer_id")
        got = got.sort_index()[["n_orders", "days_since_last"]]
        if len(got) != len(exp):
            raise AssertionError(f"expected {len(exp)} customers, got {len(got)}: only customers with a "
                                 "non-cancelled order on or before the cutoff")
        if not np.array_equal(got["n_orders"].to_numpy(), exp["n_orders"].to_numpy()):
            raise AssertionError("n_orders is wrong: count non-cancelled orders on or before the cutoff")
        if not np.allclose(got["days_since_last"].to_numpy(dtype=float), exp["days_since_last"].to_numpy(dtype=float)):
            raise AssertionError("days_since_last is wrong: cutoff minus the latest counted order, in whole days")


def _leaky_groups(seed):
    rng = np.random.default_rng(seed)
    groups = np.repeat(np.arange(40), 10)
    gy = rng.integers(0, 2, 40)
    gid = rng.normal(0, 1, (40, 3))
    X = gid[groups] + rng.normal(0, 0.05, (400, 3))
    y = gy[groups]
    signal = rng.normal(0, 1, (400, 2))
    signal[:, 0] += 1.2 * (2 * y - 1)          # one genuinely predictive, row-level feature
    return np.hstack([X, signal]), y, groups


def _ref_group_cv(X, y, groups):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold, cross_val_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    pipe = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    return float(cross_val_score(pipe, X, y, groups=groups, cv=GroupKFold(n_splits=5)).mean())


@exercise("w12.final_grouped_cv", hint="make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)) and "
                                       "cross_val_score(..., groups=groups, cv=GroupKFold(n_splits=5)).")
def _(fn):
    _callable(fn)
    for seed in (0, 1):
        X, y, g = _leaky_groups(seed)
        got = fn(X, y, g)
        exp = _ref_group_cv(X, y, g)
        if not isinstance(got, (float, np.floating)):
            raise AssertionError("return the mean accuracy as a float")
        if abs(got - exp) > 0.03:
            if got > exp:
                raise AssertionError(f"your score ({got:.2f}) is far above an honest grouped estimate: rows of the "
                                     "same group are probably on both sides of a split")
            raise AssertionError(f"expected a grouped 5-fold accuracy near {exp:.2f}, got {got:.2f}")


def _ref_threshold(y, scores, cost_fp, cost_fn):
    y, s = np.asarray(y), np.asarray(scores, dtype=float)
    cands = sorted(set(s.tolist())) + [math.inf]
    best, best_cost = None, None
    for t in cands:
        pred = s >= t
        cost = cost_fp * int(((pred) & (y == 0)).sum()) + cost_fn * int(((~pred) & (y == 1)).sum())
        if best_cost is None or cost < best_cost or (cost == best_cost and t > best):
            best, best_cost = t, cost
    return best


@exercise("w12.final_threshold", hint="Try every distinct score and math.inf; cost = cost_fp*FP + cost_fn*FN with "
                                      "'positive' meaning score >= t; on a tie keep the larger threshold.")
def _(fn):
    _callable(fn)
    rng = np.random.default_rng(0)
    for trial in range(6):
        y = (rng.random(50) < 0.3).astype(int)
        s = np.round(rng.random(50) * 0.6 + 0.4 * y, 2)
        cfp, cfn = [(1, 5), (5, 1), (1, 1), (2, 30), (100, 1), (3, 3)][trial]
        got = fn(y, s, cfp, cfn)
        exp = _ref_threshold(y, s, cfp, cfn)
        if not _close(got, exp) and not (math.isinf(exp) and got == math.inf):
            raise AssertionError(f"with cost_fp={cfp}, cost_fn={cfn} the cheapest threshold is not {got}")
    y = np.array([0, 0, 0, 1])
    s = np.array([0.1, 0.2, 0.3, 0.9])
    if fn(y, s, 1, 1) != 0.9:
        raise AssertionError("with ties in cost, keep the LARGER threshold (fewer people flagged)")
    if fn(np.zeros(4, int), s, 1, 1) != math.inf:
        raise AssertionError("when flagging nobody is cheapest, return math.inf")


def _rolling_ok(xs, k):
    return [float(np.mean(xs[max(0, i - k + 1): i + 1])) for i in range(len(xs))]


def _rolling_centered(xs, k):
    h = k // 2
    return [float(np.mean(xs[max(0, i - h): i + h + 1])) for i in range(len(xs))]


def _rolling_excl(xs, k):
    return [float(np.mean(xs[max(0, i - k): i])) if i > 0 else float(xs[0]) for i in range(len(xs))]


def _rolling_div_k(xs, k):
    return [float(np.sum(xs[max(0, i - k + 1): i + 1]) / k) for i in range(len(xs))]


@exercise("w12.final_tests", hint="Write tests with values you can compute by hand: a short list where the future "
                                  "differs from the past, and check the first elements.")
def _(tests):
    if tests is None or (isinstance(tests, list) and not tests):
        raise NotImplementedError
    if not isinstance(tests, list) or not all(callable(t) for t in tests):
        raise AssertionError("TESTS should be a list of test functions (names without parentheses)")
    for t in tests:
        try:
            t(_rolling_ok)
        except AssertionError:
            raise AssertionError(f"{t.__name__} fails on the CORRECT rolling_mean: check its expected values") from None
        except Exception as err:
            raise AssertionError(f"{t.__name__} crashed on the correct rolling_mean: {err}") from None
    for bug, what in [(_rolling_centered, "looks into the future (a centred window)"),
                      (_rolling_excl, "leaves out the current value"),
                      (_rolling_div_k, "always divides by k, even for the first k-1 values")]:
        caught = False
        for t in tests:
            try:
                t(bug)
            except AssertionError:
                caught = True
                break
            except Exception:
                caught = True
                break
        if not caught:
            raise AssertionError(f"none of your tests catches a rolling_mean that {what}")


_SEGS = ("consumer", "small_business", "student")


@exercise("w12.final_request_model", hint="pydantic BaseModel with Field(ge=0), FiniteFloat, Literal[...] and "
                                          "model_config = ConfigDict(extra='forbid').")
def _(model):
    if model is None:
        raise NotImplementedError
    from pydantic import BaseModel, ValidationError
    if not (isinstance(model, type) and issubclass(model, BaseModel)):
        raise AssertionError("ChurnRequest should be a pydantic BaseModel class")
    good = {"recency_days": 12, "orders_90d": 3, "spend_90d": 120.5, "tenure_days": 400, "segment": "student"}
    try:
        m = model(**good)
    except ValidationError as err:
        raise AssertionError(f"a valid request was rejected: {err.errors()[0]['loc']}") from None
    if getattr(m, "spend_90d", None) != 120.5:
        raise AssertionError("the fields should keep their values")
    bad = [({"recency_days": -1}, "a negative recency_days"), ({"orders_90d": -2}, "a negative orders_90d"),
           ({"spend_90d": -0.01}, "a negative spend_90d"), ({"spend_90d": float("inf")}, "an infinite spend_90d"),
           ({"tenure_days": -5}, "a negative tenure_days"), ({"segment": "enterprise"}, "an unknown segment"),
           ({"extra_field": 1}, "an unexpected extra field")]
    for change, what in bad:
        try:
            model(**{**good, **change})
        except ValidationError:
            continue
        raise AssertionError(f"{what} was accepted; it should be rejected")
    for k in good:
        try:
            model(**{kk: v for kk, v in good.items() if kk != k})
        except ValidationError:
            continue
        raise AssertionError(f"a request without {k!r} was accepted; every field is required")
    for s in _SEGS:
        model(**{**good, "segment": s})


def _ref_psi(reference, current, bins=10):
    r = np.asarray(reference, dtype=float)
    c = np.asarray(current, dtype=float)
    edges = np.quantile(r, np.linspace(0, 1, bins + 1))[1:-1]
    rp = np.bincount(np.digitize(r, edges), minlength=bins) / len(r)
    cp = np.bincount(np.digitize(c, edges), minlength=bins) / len(c)
    rp, cp = np.clip(rp, 1e-4, None), np.clip(cp, 1e-4, None)
    return float(np.sum((cp - rp) * np.log(cp / rp)))


@exercise("w12.final_psi", hint="Inner edges = np.quantile(reference, np.linspace(0, 1, bins+1))[1:-1]; "
                                "np.digitize; proportions clipped at 1e-4; sum (cur - ref) * ln(cur / ref).")
def _(fn):
    _callable(fn)
    rng = np.random.default_rng(0)
    ref = rng.normal(0, 1, 2000)
    for cur, bins in [(rng.normal(0, 1, 1500), 10), (rng.normal(0.5, 1, 1500), 10), (rng.normal(0, 2, 800), 5),
                      (rng.normal(3, 1, 500), 10)]:
        got = fn(ref, cur, bins)
        exp = _ref_psi(ref, cur, bins)
        if not _close(got, exp, 1e-3):
            if _close(got, _ref_psi(cur, ref, bins), 1e-3):
                raise AssertionError("reference and current are swapped: the bins come from the REFERENCE data")
            raise AssertionError(f"expected PSI about {exp:.3f}, got {float(got):.3f}")
    if fn(ref, ref) > 1e-9:
        raise AssertionError("identical data should give PSI 0")
    if not _close(fn(list(ref), list(ref[:500])), _ref_psi(ref, ref[:500]), 1e-3):
        raise AssertionError("it should accept lists and use bins=10 by default")


@exercise("w12.final_judgement", hint="Three headings; name both models; mention the intervals (overlap?), latency "
                                      "and at least one risk as a bullet; 80-400 words.")
def _(md):
    if md is None or (isinstance(md, str) and "YOUR" in md and "HERE" in md):
        raise NotImplementedError
    if not isinstance(md, str):
        raise AssertionError("the judgement should be a Markdown string")
    missing = _ref_missing(md, ["Recommendation", "Evidence", "Risks"])
    if missing:
        raise AssertionError(f"missing section headings: {missing}")
    low = md.lower()
    if "logistic" not in low or "boost" not in low:
        raise AssertionError("name both candidates (the logistic regression and the boosted trees)")
    if not any(w in low for w in ("interval", "overlap", "ci")):
        raise AssertionError("the evidence should use the intervals, not only the point estimates")
    if "latency" not in low and " ms" not in low:
        raise AssertionError("the scenario gives latencies: weigh them in the evidence")
    if not _bullets(_section_lines(md, "Risks")):
        raise AssertionError("list at least one risk as a bullet under 'Risks'")
    found = _ref_overclaims(md)
    if found:
        raise AssertionError(f"claims the evidence cannot support: {found}")
    n = _words(md)
    if not (80 <= n <= 400):
        raise AssertionError(f"about {n} words; aim for 80-400")


register_quiz("w12.48_q1", "b",
              "Overlapping intervals mean the data cannot tell the two apart; prefer the simpler, cheaper model "
              "unless something else decides.",
              {"a": "A higher point estimate inside overlapping intervals is not evidence of a better model.",
               "c": "Re-running until one wins is a garden of forking paths.",
               "d": "The test set is for a final estimate, not for repeated comparisons."})
register_quiz("w12.48_q2", "d",
              "A drift alarm says the inputs changed; only labels (when they arrive) can show whether performance "
              "dropped. Investigate before retraining.",
              {"a": "Retraining on drifted data without checking can bake in a sensor fault.",
               "b": "Drift is a signal to look, not proof of degradation.",
               "c": "Ignoring the alarm wastes the monitoring you built."})
register_quiz("w12.48_q3", "a",
              "Tests catch the specific bug they are written for; a test that passes on the buggy code protects "
              "nothing.",
              {"b": "Line coverage says code ran, not that its result was checked.",
               "c": "Tests should be fast, but speed is not what makes them useful.",
               "d": "Tests of model accuracy are brittle and do not catch logic bugs."})
register_quiz("w12.48_q4", "c",
              "A 422 tells the client its request was invalid and why; a 500 says the server failed. Bad input is "
              "the client's to fix.",
              {"a": "A 200 with a wrong prediction hides the problem.",
               "b": "Silently replacing values guesses on the client's behalf.",
               "d": "A 500 blames the server for the client's mistake."})


# Reference versions for `use()` in notebook 48, registered under the names the notebook uses.
_REFERENCES.update(customer_summary=_ref_customer_summary, honest_score=_ref_group_cv, psi=_ref_psi)
