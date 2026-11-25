# A matching rule for short network outages (Part B) - reference

All numbers are from `outages.py` (SYNTHETIC, seed 7). They show what the *rule* does; they say
nothing about real networks.

## 1. Why the SKAB rule misleads here

| | SKAB rule: A fast | SKAB rule: B steady | truth by construction |
|---|---|---|---|
| events found | 11/40 | 30/40 | A 38/40, B 40/40 |
| false alarms | 33 | 11 | A 6, B 1 |

* **Label timing.** The log lags the outage by 0-8 s. Detector A fires 2 s after the real start,
  which is usually *before* the logged start. The SKAB rule calls that an alarm raised in normal
  operation: a false alarm, and the event is then missed. The better the detector, the worse it scores.
* **Event length.** Outages last 3-20 s. Detector B fires 12 s after the real start, which can be
  after a short outage's logged end. Start-inside-event fails for events shorter than the detector's latency.
* **Event rate.** Forty events a day instead of one per recording: an alarm can sit between two
  outages, so windows around events must not be allowed to swallow the neighbour.

## 2. My rule

A logged outage `[s, e)` gets a detection window `[s - 8, e + 15)`, cut short so that it ends at
least 8 s before the next logged onset. An alarm detects the outage if it *starts* inside the
window. The earliest such alarm is the hit; later ones are redundant; alarms that start outside
every window are false alarms. One alarm has one start, so it can be the hit for one outage at most.
Delay = alarm start minus logged start, floored at 0. False alarms are counted per day of time
outside all windows.

## 3. Justification of each parameter

| choice | value | property of the domain that fixes it |
|---|---|---|
| early tolerance | 8 s | documented maximum lag of the ticket log behind the real outage |
| grace after logged end | 15 s | must exceed the acceptable detection latency for the shortest outage; here the requirement is "page within 15 s" |
| window capped before next onset | 8 s before it | keeps windows of neighbouring outages disjoint so one alarm cannot serve two |
| start-based, not overlap-based | - | an alarm that began in normal operation carries no information about this outage |
| exposure = time outside windows | - | alarms inside a window are never false, so that time is not at risk |

None of these was chosen by looking at which value makes a detector score best. If the lag or the
latency requirement were unknown, I would measure the lag on a sample with packet-level ground
truth before fixing the tolerance.

## 4. Results under my rule

| | events found | alarms | false alarms | false alarms/day | median delay |
|---|---|---|---|---|---|
| A fast | 38/40 | 44 | 6 | 6.1 | 0 s |
| B steady | 40/40 | 41 | 1 | 1.0 | 8 s |

Both match the construction (A misses 2 and has 6 spurious alarms; B misses none and has 1).

## 5. What the rule cannot measure, and how it could be gamed

* **Delay below 8 s is not resolvable.** The tolerance equals the label jitter, so A's "0 s" and a
  hypothetical 6 s detector are indistinguishable. The true latencies are 2 s and 12 s; the rule
  reports 0 s and 8 s. Report delay as "<= 8 s" or obtain better onset labels.
* **Windows are 26-43 s wide around 3-20 s outages.** A detector that fires at random gains hits in
  proportion to window coverage: 40 windows of about 35 s cover 1.6 % of the day, so 100 random
  alarms a day would "find" one or two outages. Check: score a random alarm stream with the same
  alarm count and report it next to the detector (the same trick as the point-adjust experiment).
* **Alarm length is ignored.** A detector could hold every alarm for an hour and never pay for it.
  Add a clearing-time metric (alarm end minus logged end) if operators act on the all-clear.
* **The grace period forgives lateness.** If latency matters more than it does here, shorten the
  grace period and accept that short outages become undetectable by slow detectors, which is then
  the truth about them.
