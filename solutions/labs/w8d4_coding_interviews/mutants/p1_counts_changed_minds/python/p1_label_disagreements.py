"""P1 (easy, hash maps): samples on which annotators disagree. Reference solution."""
from __future__ import annotations

from collections import defaultdict
from typing import Hashable, Iterable


def label_disagreements(records: Iterable[tuple[Hashable, Hashable, Hashable]]) -> list:
    """Sample ids whose annotators' latest labels are not all equal, sorted ascending.

    records: (sample_id, annotator, label) in arrival order. If an annotator labels the same sample
    twice, only their latest label counts. O(n) time, O(n) memory.
    """
    labels: dict = defaultdict(set)
    for sample, _annotator, label in records:
        labels[sample].add(label)
    return sorted(s for s, seen in labels.items() if len(seen) > 1)
