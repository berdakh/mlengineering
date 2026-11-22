# Assessment - w3d4 point versus event evaluation

Answer in writing before opening `solutions/lessons/w3d4_point_vs_event_evaluation/assessment_answers.md`.
About 15 minutes for the questions; the interview rep is separate.

## Reasoning questions

1. Two detectors on the same nine test events. A: point F1 0.82, 8/9 events, 88 false alarms per hour.
   B: point F1 0.79, 9/9 events, 96 false alarms per hour. A colleague says "A is better, higher F1 and
   fewer false alarms". Give two reasons this conclusion is not supported, one about the metric and one
   about the data.
2. Under any-overlap matching the elapsed-time detector "finds" 8 of 9 SKAB test events; under the
   course's start-based rule it finds 4. Which number is closer to what an operator would experience,
   and what property of the clock's alarms makes the two rules disagree?
3. A paper reports point-adjusted F1 0.96 on SKAB. Without access to the code, what single additional
   number would let you judge whether 0.96 means anything? Explain.
4. Why must `min_duration` and `merge_gap` be chosen on development experiments, and what goes wrong in
   the reported delay if the confirmation wait is not added to it?
5. A detector raised zero false alarms in 1.63 hours of held-out normal operation. State the strongest
   claim about its false-alarm rate that the data support at 95 % confidence, and the number of hours
   with zero false alarms needed to claim "at most one per 8 hours".
6. Median detection delay is computed over the detected events only and reported as 40 s; three of nine
   events were missed. What is the median over all events, and why is the second number the one to
   report?

## Design-choice explanation (write 6-10 sentences)

Your team is about to adopt a matching rule for a new detector of compressor surges, labelled from
maintenance tickets that are entered by hand, typically 5-30 minutes after the event starts. Propose a
rule (what counts as a detection, early tolerance, treatment of repeated alarms, what counts as a false
alarm, how hours are counted) and justify each element from a property of the labels or of the
operator's use of the alarm. Name one thing your rule can no longer measure.

## Rubric (for questions and the design explanation)

| Level | Description |
|---|---|
| Demonstrated | Distinguishes rows from alarms in every answer; quantifies with counts and exposures; ties each rule element to a property of labels or use; states what the chosen rule cannot measure. |
| Partial | Correct mechanics (e.g. rule of three, censored delays) but justifications are generic ("to be fair", "standard practice") or one element is chosen by its effect on the score. |
| Not yet | Treats point F1 or point-adjusted F1 as evidence of detection quality, or reports rates without exposure, or averages delays over detected events only without saying so. |

## Interview rep (Python, 12 minutes, no notes)

Implement, with tests you write yourself:

```python
Interval = tuple[int, int]   # half-open [start, end)

def merge_intervals(intervals: list[Interval]) -> list[Interval]:
    """Union as sorted disjoint intervals. Touching intervals merge; empty ones are ignored."""

def overlap_length(a: list[Interval], b: list[Interval]) -> int:
    """Total length covered by both a and b (each may contain overlapping intervals)."""
```

State the time complexity of each. Then answer aloud: how would `overlap_length` let you compute the
point-level recall of a set of alarms against a set of true events without materialising per-row arrays?

Self-score against the interview rubric in the answers file; a reference implementation with tests is in
`solutions/lessons/w3d4_point_vs_event_evaluation/interview_rep/`.
