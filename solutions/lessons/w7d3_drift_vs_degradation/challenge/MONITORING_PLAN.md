# Monitoring plan: flowguard

## Three questions

The plan keeps three questions apart, because each has a different signal and a different owner.
*Is the input valid?* is answered at the API boundary, per request and immediately: the w5d4 contract
rejects malformed requests with 422 and counts them, and timestamp gaps are counted per run. *Has the
input changed?* is answered by a PSI monitor on the flow rate, the detector's only input, every 5 days,
with a threshold calibrated on development recordings so that it fires on about 1 % of stable windows.
A drift flag starts an investigation of the input source (sensor work, process change); it never
retrains or rolls back by itself, because the w7d3 replay showed a recalibrated sensor moving PSI from
0.24-0.42 to 6.1-8.9 while the detector caught exactly the same faults. *Is the model still good?* is answered only by
labels: alarm precision from maintenance verdicts and event recall from inspection reports, each over
21-day windows, each reported as unknown below its minimum label count.

## Label backfill

Maintenance verdicts join on `alarm_id`; the latest verdict wins, so corrections are honoured.
They arrive 2 to 10 days after an alarm, so precision for a window is computed 10 days after it closes.
Missed faults reach us only through inspections, which join on `fault_id`, arrive 14 to 60 days after
the fault and find about 60 % of misses. Recall is therefore computed 60 days after a window closes and
read as an upper bound. In the replay, the estimate for the degraded period read 1.0 on day 65 (no
misses reported yet), 0.67 on day 90 and 0.36 on day 150, against a true 4 of 20. Orphan verdicts and
pending alarms are counted on the dashboard so that a broken id pipeline is visible.

## What this plan cannot detect

It cannot detect a recall drop quickly: with 7 faults a week and 60-day label delays, a degradation
like the replay's period C is visible about two months late, and with 20 faults per period it stays
statistically inconclusive at a 15-point margin. Faults that inspections never find are invisible for
ever, so recall can only be bounded from above. Real plants see far fewer faults than this constructed
timeline, which would push windows to months. Precision is uninformative at this operating point (no
false alarm in any replayed period). The plan also cannot see a change in what the plant calls a fault
(a concept change) until people say so; that needs a periodic review with the reliability engineer.
