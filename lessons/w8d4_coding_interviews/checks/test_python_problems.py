"""Checks for the six Python problems: known answers, edge cases, agreement with a slow brute force on
random inputs, and a time limit on large inputs that only a solution with the required complexity meets.
The limits are generous (the reference runs each large case in well under a second on the authoring
machine) but a quadratic solution needs minutes."""
from __future__ import annotations

import random
import statistics
import time

import pytest
from conftest import load

LIMIT_S = 4.0


def timed(fn, *args):
    t0 = time.perf_counter()
    out = fn(*args)
    return out, time.perf_counter() - t0


# ---------------------------------------------------------------- P1
@pytest.fixture(scope="module")
def p1(target):
    return load(target, "p1_label_disagreements").label_disagreements


def test_p1_known_answers(p1):
    recs = [(1, "a", "x"), (1, "b", "y"), (2, "a", "x"), (2, "a", "y"), (3, "a", "x"), (3, "b", "x")]
    assert p1(recs) == [1]          # sample 2: one annotator changed their mind - not a disagreement
    assert p1([]) == []
    assert p1([("s", "a", 1), ("s", "b", 1), ("s", "a", 2), ("s", "a", 1)]) == []   # latest labels agree


def test_p1_matches_brute_force(p1):
    rng = random.Random(1)
    for _ in range(200):
        recs = [(rng.randint(0, 9), rng.choice("abc"), rng.choice("xyz")) for _ in range(rng.randint(0, 30))]
        latest = {}
        for s, a, lab in recs:
            latest[(s, a)] = lab
        expected = sorted({s for (s, _), _ in latest.items()
                           if len({lab for (s2, _), lab in latest.items() if s2 == s}) > 1})
        assert p1(recs) == expected


def test_p1_is_linear(p1):
    rng = random.Random(2)
    recs = [(rng.randrange(100_000), rng.randrange(5), rng.randrange(3)) for _ in range(300_000)]
    _, secs = timed(p1, recs)
    assert secs < LIMIT_S


# ---------------------------------------------------------------- P2
@pytest.fixture(scope="module")
def p2(target):
    return load(target, "p2_match_alarms").match_alarms


def _brute_match(alarms, faults, tol):
    used = [False] * len(alarms)
    out = []
    for f in faults:
        for i, a in enumerate(alarms):
            if not used[i] and f <= a <= f + tol:
                used[i] = True
                out.append(a - f)
                break
    return out


def test_p2_known_answers(p2):
    assert p2([1, 5, 6, 20], [0, 4, 4.5, 19], 2) == [1, 1, 1.5, 1]
    assert p2([3], [0, 1, 2], 5) == [3]          # one alarm cannot detect three faults
    assert p2([0.5], [1], 5) == []               # an alarm before the fault is not a detection
    assert p2([], [1, 2], 1) == [] and p2([1], [], 1) == []
    assert p2([1, 3], [1], 0) == [0]             # boundary: a == f counts


def test_p2_matches_brute_force(p2):
    rng = random.Random(3)
    for _ in range(300):
        alarms = sorted(rng.randint(0, 50) for _ in range(rng.randint(0, 15)))
        faults = sorted(rng.randint(0, 50) for _ in range(rng.randint(0, 15)))
        tol = rng.randint(0, 6)
        assert p2(alarms, faults, tol) == _brute_match(alarms, faults, tol)


def test_p2_is_linear(p2):
    rng = random.Random(4)
    alarms = sorted(rng.uniform(0, 1e6) for _ in range(200_000))
    faults = sorted(rng.uniform(0, 1e6) for _ in range(200_000))
    _, secs = timed(p2, alarms, faults, 1.0)
    assert secs < LIMIT_S


# ---------------------------------------------------------------- P3
@pytest.fixture(scope="module")
def p3(target):
    return load(target, "p3_dedup_events").dedup_events


def _brute_dedup(events, window):
    kept = []
    for t, k in events:
        same = [tt for tt, kk in kept if kk == k]
        if not same or t - same[-1] >= window:
            kept.append((t, k))
    return kept


def test_p3_known_answers(p3):
    ev = [(0, "a"), (3, "a"), (6, "a"), (9, "a"), (10, "b")]
    assert p3(ev, 5) == [(0, "a"), (6, "a"), (10, "b")]   # 9 is 3 after the kept 6; 3 does not extend
    assert p3([(0, "a"), (5, "a")], 5) == [(0, "a"), (5, "a")]   # exactly one window apart is kept
    assert p3([], 5) == []
    stream = [(t, "k") for t in range(0, 20, 2)]           # every 2 s with a 3 s window
    assert p3(stream, 3) == [(0, "k"), (4, "k"), (8, "k"), (12, "k"), (16, "k")]


def test_p3_matches_brute_force(p3):
    rng = random.Random(5)
    for _ in range(300):
        ts = sorted(rng.randint(0, 40) for _ in range(rng.randint(0, 25)))
        ev = [(t, rng.choice("abc")) for t in ts]
        w = rng.randint(1, 8)
        assert p3(ev, w) == _brute_dedup(ev, w)


def test_p3_is_linear(p3):
    rng = random.Random(6)
    ev = [(i * 0.5, rng.randrange(20)) for i in range(200_000)]
    _, secs = timed(p3, ev, 1.0)
    assert secs < LIMIT_S


# ---------------------------------------------------------------- P4
@pytest.fixture(scope="module")
def p4(target):
    return load(target, "p4_top_k_variance").top_k_variance


def _brute_topk(readings, k):
    by = {}
    for s, x in readings:
        by.setdefault(s, []).append(x)
    scored = [(statistics.pvariance(v), s) for s, v in by.items() if len(v) >= 2]
    scored.sort(key=lambda vs: (-vs[0], vs[1]))
    return [s for _, s in scored[:k]]


def test_p4_known_answers(p4):
    assert p4([("a", 1), ("a", 3), ("b", 0), ("b", 10), ("c", 5)], 2) == ["b", "a"]   # c has one reading
    # Population, not sample, variance: s1 = [0, 2] -> 1.0; s2 = [0, 0, 3] -> 2.0 (sample: 2.0 vs 3.0)
    # s3 = [0, 2.9] -> 2.1025 (sample 4.205). Population order s3, s2, s1; sample order s3, s2, s1 too,
    # so add s4 = [0, 0, 0, 0, 4.2] -> pop 2.8224 (sample 3.528): population ranks s4 over s3, sample does not.
    data = [("s1", 0), ("s1", 2), ("s2", 0), ("s2", 0), ("s2", 3), ("s3", 0), ("s3", 2.9),
            ("s4", 0), ("s4", 0), ("s4", 0), ("s4", 0), ("s4", 4.2)]
    assert p4(data, 2) == ["s4", "s3"]
    assert p4([("b", 1), ("b", 3), ("a", 5), ("a", 7)], 1) == ["a"]   # tie -> smaller id
    assert p4([("a", 1)], 3) == []


def _valid_topk(answer, readings, k, tol=1e-9):
    """True if `answer` is a correct top-k list. Exact variances come from statistics.pvariance; two
    variances within `tol` count as a tie (floating-point summation order may differ between correct
    implementations), and ties must be ordered by sensor id."""
    by = {}
    for s, x in readings:
        by.setdefault(s, []).append(x)
    var = {s: float(statistics.pvariance(v)) for s, v in by.items() if len(v) >= 2}
    if len(answer) != min(k, len(var)) or len(set(answer)) != len(answer) or not set(answer) <= set(var):
        return False
    key = lambda s: (-var[s], s)  # noqa: E731
    for a, b in zip(answer, answer[1:]):
        if var[a] < var[b] - tol or (abs(var[a] - var[b]) <= tol and a > b):
            return False
    for s in set(var) - set(answer):
        for a in answer:
            if var[s] > var[a] + tol or (abs(var[s] - var[a]) <= tol and s < a):
                return False
    return True


def test_p4_matches_brute_force(p4):
    rng = random.Random(7)
    for _ in range(200):
        readings = [(rng.choice("abcdefg"), rng.choice([0, 1, 2, 5, 10])) for _ in range(rng.randint(0, 40))]
        k = rng.randint(1, 5)
        answer = p4(readings, k)
        assert _valid_topk(answer, readings, k), (answer, _brute_topk(readings, k))


def test_p4_large_offset_is_stable(p4):
    # Values near 1e9 with tiny spread: naive E[x^2] - E[x]^2 loses all precision.
    base = 1e9
    data = [("tight", base + d) for d in (0.0, 0.1, 0.2)] + [("wide", base + d) for d in (0.0, 1.0, 2.0)]
    assert p4(data, 2) == ["wide", "tight"]


def test_p4_scales(p4):
    rng = random.Random(8)
    readings = [(rng.randrange(40_000), rng.gauss(0, 1 + (i % 7))) for i in range(400_000)]
    _, secs = timed(p4, readings, 10)
    assert secs < LIMIT_S


# ---------------------------------------------------------------- P5
@pytest.fixture(scope="module")
def p5(target):
    return load(target, "p5_min_batch_cost").min_max_batch_cost


def _brute_batches(costs, b):
    n = len(costs)
    if n == 0:
        return 0
    inf = float("inf")
    prefix = [0]
    for c in costs:
        prefix.append(prefix[-1] + c)
    best = [[inf] * (b + 1) for _ in range(n + 1)]
    best[0] = [0] * (b + 1)
    for i in range(1, n + 1):
        for j in range(1, b + 1):
            for split in range(i):
                best[i][j] = min(best[i][j], max(best[split][j - 1], prefix[i] - prefix[split]))
    return int(best[n][b])


def test_p5_known_answers(p5):
    assert p5([7, 2, 5, 10, 8], 2) == 18
    assert p5([1, 2, 3, 4, 5], 2) == 9
    assert p5([5, 5, 5], 5) == 5           # more batches than items
    assert p5([10], 1) == 10 and p5([], 3) == 0
    assert p5([1, 1, 1, 1, 9], 2) == 9     # greedy "fill to total/B" gives 4+9 split wrongly


def test_p5_matches_brute_force(p5):
    rng = random.Random(9)
    for _ in range(150):
        costs = [rng.randint(1, 20) for _ in range(rng.randint(0, 10))]
        b = rng.randint(1, 4)
        assert p5(costs, b) == _brute_batches(costs, b)


def test_p5_is_n_log_sum(p5):
    rng = random.Random(10)
    costs = [rng.randint(1, 1_000_000) for _ in range(100_000)]
    _, secs = timed(p5, costs, 50)
    assert secs < LIMIT_S


# ---------------------------------------------------------------- P6
@pytest.fixture(scope="module")
def p6(target):
    return load(target, "p6_pipeline_order").pipeline_order


def test_p6_known_answers(p6):
    steps = ["load", "clean", "train", "eval", "report"]
    deps = [("load", "clean"), ("clean", "train"), ("train", "eval"), ("clean", "report")]
    assert p6(steps, deps) == ["load", "clean", "report", "train", "eval"]
    assert p6(["b", "a", "c"], []) == ["a", "b", "c"]


def test_p6_cycle_and_unknown_step(p6):
    with pytest.raises(ValueError) as err:
        p6(["a", "b", "c", "d"], [("a", "b"), ("b", "c"), ("c", "b"), ("a", "d")])
    assert "b" in str(err.value) or "c" in str(err.value)
    with pytest.raises(ValueError):
        p6(["a"], [("a", "zzz")])


def test_p6_matches_brute_force(p6):
    rng = random.Random(11)
    for _ in range(200):
        n = rng.randint(1, 8)
        steps = [f"s{i}" for i in range(n)]
        rng.shuffle(steps)
        order = sorted(steps, key=lambda s: rng.random())
        deps = [(order[i], order[j]) for i in range(n) for j in range(i + 1, n) if rng.random() < 0.3]
        indeg = {s: 0 for s in steps}
        for _, a in deps:
            indeg[a] += 1
        done, expected = set(), []
        while len(expected) < n:
            ready = sorted(s for s in steps if s not in done and all(b in done for b, a in deps if a == s))
            expected.append(ready[0])
            done.add(ready[0])
        assert p6(steps, deps) == expected


def test_p6_deep_and_wide_graphs(p6):
    n = 30_000
    chain = [f"n{i:05d}" for i in range(n)]
    deps = [(chain[i], chain[i + 1]) for i in range(n - 1)]
    out, secs = timed(p6, chain[::-1], deps)           # deep: recursion would hit the limit
    assert out == chain and secs < LIMIT_S
    wide = [f"w{i:05d}" for i in range(n)]
    out, secs = timed(p6, wide[::-1], [])               # wide: rescanning all steps each time is O(V^2)
    assert out == sorted(wide) and secs < LIMIT_S
