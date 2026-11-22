"""WRONG: shuffles rows, not groups. Every group ends up on both sides."""
import random


def group_kfold(groups, k, seed=0):
    if k < 2 or k > len(set(groups)):
        raise ValueError("bad k")
    idx = list(range(len(groups)))
    random.Random(seed).shuffle(idx)
    for f in range(k):
        test = sorted(idx[f::k])
        held = set(test)
        yield [i for i in idx if i not in held], test
