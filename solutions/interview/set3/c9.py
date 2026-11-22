"""Reference for set 3, C9: grouped K-fold, seeded, balanced in rows (greedy largest-first)."""
import random
from collections import defaultdict


def group_kfold(groups, k, seed=0):
    rows = defaultdict(list)
    for i, g in enumerate(groups):
        rows[g].append(i)
    if k < 2:
        raise ValueError("k must be at least 2")
    if k > len(rows):
        raise ValueError(f"k={k} exceeds the number of groups ({len(rows)})")

    ids = sorted(rows, key=repr)             # fixed starting order: independent of input order
    random.Random(seed).shuffle(ids)         # the seed breaks ties between equal-sized groups
    ids.sort(key=lambda g: -len(rows[g]))    # stable sort: largest first, shuffled order within ties

    fold_rows = [[] for _ in range(k)]
    for g in ids:                            # put each group in the currently smallest fold
        smallest = min(range(k), key=lambda f: len(fold_rows[f]))
        fold_rows[smallest].extend(rows[g])

    n = len(groups)
    for test in fold_rows:
        held_out = set(test)
        yield [i for i in range(n) if i not in held_out], sorted(test)
