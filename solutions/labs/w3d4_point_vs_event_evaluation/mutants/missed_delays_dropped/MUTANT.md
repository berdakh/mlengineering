# Mutant: delays of detected events only

`detection_delay` returns delays for the detected events and leaves the missed ones out.

**Why it is plausible.** A missed event has no delay to compute, and `np.median` of the detected ones
runs without complaint.

**What goes wrong.** Survivorship bias: a detector that only catches the most abrupt faults reports
the shortest delays. Raising the threshold can make the reported median delay *improve*.

**Caught by.** `test_time.py` (missed events stay in the result, pooled check).
