"""P1 (easy, hash maps): samples on which annotators disagree. Reference solution."""
from __future__ import annotations

from collections import defaultdict
from typing import Hashable, Iterable


def label_disagreements(records: Iterable[tuple[Hashable, Hashable, Hashable]]) -> list:
    """Sample ids whose annotators' latest labels are not all equal, sorted ascending.

    records: (sample_id, annotator, label) in arrival order. If an annotator labels the same sample
    twice, only their latest label counts. O(n) time, O(n) memory.
    """
    latest: dict = defaultdict(dict)          # sample -> {annotator: label}
    for sample, annotator, label in records:
        latest[sample][annotator] = label
    return sorted(s for s, by_annotator in latest.items() if len(set(by_annotator.values())) > 1)
