# Mutant: any overlap is a detection

An alarm detects a true event whenever the two intervals overlap, including an alarm that was
already on before the event started; the delay is then negative and floored at 0.

**Why it is plausible.** "Any overlap" is the most common matching rule in offline event scoring.

**What goes wrong.** A detector whose alarm is permanently on detects every event with zero delay.
On SKAB a clock that fires at a fixed elapsed time just before the scripted onset is credited with
instant detections. Whatever started the alarm, it was not the event.

**Caught by.** `test_matching.py` (alarm already on, long alarm over two events) and `test_time.py`.
