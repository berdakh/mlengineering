# Assessment answers - w3d4

## Reasoning questions

**1.** (a) Metric: point F1 counts rows; it ranks by the share of anomalous rows covered and is blind
to fragmentation and timing. The operator-relevant columns are events found (B 9/9 vs A 8/9), delay
and false alarms per hour, and they do not agree with the F1 ordering. (b) Data: nine events; one
event is 11 percentage points of event recall, and 88 vs 96 false alarms per hour come from 1.63 hours
(144 vs 156 alarms). Neither difference is established without intervals (w3d5). Also both rates are
operationally unusable, so the comparison is moot until post-processing is tuned.
*Common wrong answers:* "F1 balances precision and recall so it is fine" (it balances row counts);
"8/9 vs 9/9 is a big difference" (it is one event).

**2.** The start-based count (4/9). The clock's alarm for an experiment is a single run that starts at
the frozen threshold (row 571) and lasts to the end. When the onset is a few rows after 571, the alarm
starts in normal operation and runs into the event: any-overlap credits it with a detection at delay 0;
the start-based rule calls it a false alarm, because it told the operator nothing at onset. Both
numbers are inflated by the protocol leak (onsets cluster at rows 550-600); neither is evidence about
sensors.
*Common wrong answer:* "any-overlap is more lenient so it is fairer to the detector" - fairness to the
detector is not the goal; matching what the alarm communicated is.

**3.** The point-adjusted F1 of a random (or trivially periodic) flag stream with the same flag rate,
on the same data. On SKAB a random detector flagging 1 % of rows scores 0.984 after point-adjust. If
0.96 is not clearly above that reference, it means nothing. (Equivalent acceptable answers: the
non-adjusted F1, or the event-level false-alarm rate.)

**4.** They change which alarms exist and when they are raised; tuning them on test is selecting on
test (w3d3). The confirmation wait is real latency: an alarm requiring 10 rows is raised 9 rows after
its first flag. Omitting it understates delay by exactly that amount and makes long confirmation
windows look free.

**5.** Rate ≤ -ln(0.05)/1.63 ≈ 3.0/1.63 ≈ 1.84 per hour (one-sided 95 %, Poisson). To claim ≤ 0.125 per
hour with zero false alarms: 3.0/0.125 ≈ 24 hours of normal operation. Assumes a constant rate; with
regime changes (the fault-free recording behaves differently) even that is optimistic.
*Common wrong answer:* "0 false alarms per hour, so the budget is met".

**6.** With nine delays, three of them infinite, the median is the 5th smallest value, which is a finite
delay larger than the reported 40 s (the median of the six detected ones lies between their 3rd and 4th
values; over all nine it is the 5th). Report the all-events median, with missed events counted as
infinite, because dropping misses rewards a detector for failing on the hardest cases. If more than
half are missed, the median is "missed".

## Design-choice explanation - what a strong answer contains

* Detection: alarm *starts* within a window around the ticket time, with an early tolerance of about
  30 minutes (the documented lag) and a late grace limited by the operational requirement; start-based
  because an alarm that began in normal operation conveys nothing about the surge.
* Repeated alarms within one event are redundant (not TP, not FA); report them separately as operator
  load.
* False alarms: starts outside every window; exposure is time outside all windows, from timestamps.
* Delay resolution is limited by label jitter (5-30 min): report delay as "within the window" or with
  that resolution, not to the second.
* Cannot measure: true onset delay below ~25 min; event ends (tickets have no end time), so alarm
  clearing behaviour is unmeasured.
* A good answer also says how the tolerance would be validated (a sample of events with sensor-based
  onset annotation).

## Interview rubric

| Level | Description |
|---|---|
| Strong | Sorts once, merges in one pass with `start <= last_end`, ignores empty intervals, two-pointer overlap after merging; O(n log n); writes tests for touching, nested, empty and disjoint inputs; explains point recall = overlap(alarms, events) / total event length. |
| Adequate | Correct merge; overlap by nested loops O(nm) with correct result; some edge cases untested. |
| Not yet | Materialises arrays of all integers (fails for large coordinates) or mishandles touching/nested intervals. |

Reference: `interview_rep/intervals.py`, tests `interview_rep/test_intervals.py` (5 pass).

## Lab and challenge: what the reference readings contain

See `lab/EVENT_EVAL.md`, `challenge/REPORT.md` and `challenge/OUTAGE_RULE.md` in this directory. Rubric
for the challenge's written parts:

| Element | Demonstrated when |
|---|---|
| Budget claim (A) | States counts and hours, the 95 % upper bound, and does not claim the budget is met from a zero count over ~1.6 h. |
| Fault-free recording (A) | Notices that the same setting raises false alarms on a different regime and says the rate is not one number. |
| Domain analysis (B) | Names label lag/jitter, event length vs detector latency, and event spacing as the reasons the SKAB rule fails. |
| Parameter justification (B) | Each parameter tied to a domain property (lag, latency requirement, spacing), none chosen by score. |
| Limits (B) | States delay resolution equal to the jitter and one way to game the rule (random alarms in wide windows, held alarms) with a check. |
