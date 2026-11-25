"""Reference solution and self-test for the w1d3 interview rep.

    python solutions/labs/w1d3_package_structure/interview_rep_reference.py
    python solutions/labs/w1d3_package_structure/interview_rep_reference.py path/to/your_file.py

With a path argument, the same tests run against `group_split` defined in your file.
"""
from __future__ import annotations

import importlib.util
import random
import sys


def group_split(groups: list[str], test_fraction: float, seed: int) -> tuple[list[int], list[int]]:
    if not 0.0 < test_fraction < 1.0:
        raise ValueError("test_fraction must be strictly between 0 and 1")
    unique = sorted(set(groups))          # sorted: independent of row order and of set hashing
    if len(unique) < 2:
        raise ValueError("need at least two distinct groups")
    n_test = min(max(round(test_fraction * len(unique)), 1), len(unique) - 1)
    test_groups = set(random.Random(seed).sample(unique, n_test))   # local RNG: no global state
    train, test = [], []
    for i, g in enumerate(groups):
        (test if g in test_groups else train).append(i)
    return train, test


def run_tests(fn) -> None:
    groups = [f"P{i % 7:02d}" for i in range(70)]
    train, test = fn(groups, 0.3, seed=1)
    assert sorted(train + test) == list(range(70)), "every index exactly once"
    assert train == sorted(train) and test == sorted(test), "sorted output"
    g_train, g_test = {groups[i] for i in train}, {groups[i] for i in test}
    assert not (g_train & g_test), "a group is on both sides"
    assert len(g_test) == 2, "round(0.3 * 7) == 2 test groups"
    assert fn(groups, 0.3, seed=1) == (train, test), "not deterministic for a fixed seed"
    assert any({groups[i] for i in fn(groups, 0.3, seed=s)[1]} != g_test for s in range(2, 12)), "seed is ignored"

    order = list(range(70))
    random.Random(0).shuffle(order)
    shuffled = [groups[i] for i in order]
    _, test_s = fn(shuffled, 0.3, seed=1)
    assert {shuffled[i] for i in test_s} == g_test, "test groups depend on row order"

    assert len({["a", "b"][i] for i in fn(["a", "b", "a"], 0.01, seed=0)[1]}) == 1, "never zero test groups"
    tr, _ = fn(["a", "b", "a"], 0.99, seed=0)
    assert tr, "never all groups in test"
    for bad_args in ((["a", "a"], 0.5), (["a", "b"], 0.0), (["a", "b"], 1.0)):
        try:
            fn(*bad_args, seed=0)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {bad_args}")
    state = random.getstate()
    fn(groups, 0.3, seed=5)
    assert random.getstate() == state, "the function reseeded or consumed the global RNG"
    print("all interview-rep tests passed")


if __name__ == "__main__":
    target = group_split
    if len(sys.argv) == 2:
        spec = importlib.util.spec_from_file_location("candidate", sys.argv[1])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        target = module.group_split
    run_tests(target)
