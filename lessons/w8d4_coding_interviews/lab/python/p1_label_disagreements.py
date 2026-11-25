"""P1 (easy, hash maps): samples on which annotators disagree. Starter: implement the function; the docstring is the specification."""
from __future__ import annotations

from typing import Hashable, Iterable


def label_disagreements(records: Iterable[tuple[Hashable, Hashable, Hashable]]) -> list:
    """Sample ids whose annotators' latest labels are not all equal, sorted ascending.

    records: (sample_id, annotator, label) in arrival order. If an annotator labels the same sample
    twice, only their latest label counts. Required: O(n) time.
    """
    raise NotImplementedError("w8d4: implement this")
