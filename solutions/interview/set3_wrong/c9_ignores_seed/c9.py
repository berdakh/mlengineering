"""WRONG: correct grouping, but the seed is accepted and ignored."""
from collections import defaultdict


def group_kfold(groups, k, seed=0):
    rows = defaultdict(list)
    for i, g in enumerate(groups):
        rows[g].append(i)
    if k < 2 or k > len(rows):
        raise ValueError("bad k")
    ids = sorted(rows, key=lambda g: (-len(rows[g]), repr(g)))
    folds = [[] for _ in range(k)]
    for g in ids:
        min(folds, key=len).extend(rows[g])
    n = len(groups)
    for test in folds:
        held = set(test)
        yield [i for i in range(n) if i not in held], sorted(test)
