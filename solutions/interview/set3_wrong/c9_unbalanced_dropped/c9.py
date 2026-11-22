"""WRONG: round-robin over shuffled groups ignoring size, and no validation of k."""
import random
from collections import defaultdict


def group_kfold(groups, k, seed=0):
    rows = defaultdict(list)
    for i, g in enumerate(groups):
        rows[g].append(i)
    ids = sorted(rows, key=repr)
    random.Random(seed).shuffle(ids)
    n = len(groups)
    for f in range(k):
        test = sorted(i for g in ids[f::k] for i in rows[g])
        held = set(test)
        yield [i for i in range(n) if i not in held], test
