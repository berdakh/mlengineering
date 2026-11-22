# Canary decisions: flowguard 1.1.0

## Decisions per scenario

* **a_broken_release: stop at hour 2.** After three hours the canary's error rate (about 3.3 % over the
  log) has a Wilson lower bound of 0.021, above the control's 0.0094 + 0.01. A real regression, caught
  early with little traffic exposed.
* **b_alarm_storm: stop at hour 0.** About 3 alerts per machine-hour; even the first hour's lower bound
  (2.0 per hour) exceeds the budget of 1.
* **c_too_early: continue at hour 5.** Nothing is wrong, but six hours and 595 requests are below the
  24-hour and 2,000-request minimum, so the rule cannot promote.
* **d_healthy: promote at hour 23.** At 24 hours both upper bounds are inside their limits (alert rate
  0.10 per hour, upper bound 0.16; error upper bound 0.018 against control 0.011 + 0.01).
* **e_borderline_alerts: stop at hour 2 when evaluated hourly; continue when evaluated once on all 96
  hours.** The true canary alert rate (1.0 per hour, stated in the generator) sits exactly on the budget.

## Repeated looks

Scenario e stops at hour 2 because the rule was evaluated 96 times. Each hourly look tests "is the
lower bound above 1.0?" at a one-sided 5 % error level, and early looks are based on 10-15
machine-hours, so the bound swings widely; with many looks the chance that at least one swing crosses the
line is far above 5 %. On the full 480 machine-hours the bounds are [0.874, 1.022], which straddle the
budget: the honest answer is "continue", not "stop". Fixes, in order of preference: (1) spend the error
budget across looks, for example evaluate every 6 hours at a stricter one-sided level such as
0.05 / 16 for the stop rule (Bonferroni over the 16 planned looks), or use an alpha-spending boundary
that is strict early and relaxes later; (2) require a minimum exposure, e.g. 24 machine-hours, before
the alert guardrail may stop the canary, while keeping the error guardrail live from hour 0 because
5xx errors are cheap to detect and expensive to serve. The same reasoning applies to the promote side:
promoting on the first look whose upper bound dips under the limit also inflates the false-promote rate.

## What a canary of this size cannot tell you

The canary sees 5 monitored machine-hours per hour, 480 in four days. At the healthy alert rate of
about 0.1 per hour that is roughly 48 alerts, with one-sided bounds of about 0.08 and 0.13 per hour,
so it can detect a doubling of the alert rate or a breach of the 1-per-hour budget with ease. It cannot
say anything about recall: faults are rare, and 10 % of machines for four days will see a handful of
faults at best, probably none, so the canary can confirm the guardrails (errors, alert volume, latency)
but not the benefit. The benefit was established by the offline gate on held-out experiments and by
the shadow comparison; the canary's job is to show that nothing operational broke, and the decision
should be read that way.
