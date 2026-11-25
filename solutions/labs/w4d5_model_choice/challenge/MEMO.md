# Decision memo: churn model for the account page (Larkspur, SYNTHETIC case)

Author: reference solution · Date: 2026-11-22 · Decision owner: head of retention · Status: final

<!-- Reference answer. Numbers from `python challenge/analyse.py` (n_boot 2000, seed 0). -->

## Context

The retention team asks whether to replace churn model A with model B on the account page, where
the score picks which retention offer a customer sees. The page has a p95 latency budget of 50 ms
for the scoring call. We fixed the minimum practically important difference (MPID) at +0.02 AUC
before looking at results: below that, offer targeting does not change enough to pay for any
migration. If nothing changes, A keeps running as it does today.

## Options

1. **Keep A** (gradient-boosted trees in the existing Python service).
2. **Switch to B** (sequence transformer; needs a GPU-backed model server, `onnxruntime-gpu`, and a
   GPU node pool).
3. **Keep A and invest the effort in labels and features instead**: for example, adding the
   order-event features B uses as aggregated inputs to A. Not evaluated here.

## Evidence

Held-out month, 15,295 customers in 40 regions. Intervals are 95 % paired bootstrap intervals that
resample **regions**, because customers in a region share prices, couriers and promotions.

| | A | B | B - A |
|---|---|---|---|
| ROC AUC | 0.705 | 0.716 | +0.011 [-0.006, +0.029] |
| Practical reading (MPID 0.02) | | | inconclusive: could be anywhere from slightly worse to slightly better than the MPID |
| p95 latency (staging load test) | 5.3 ms | 108.2 ms | B breaks the 50 ms budget by 2x |
| New dependencies | none | GPU model server, `onnxruntime-gpu`, GPU nodes | new on-call surface |
| Who can debug it today | the current team | nobody yet | |

A customer-level bootstrap would give [+0.001, +0.022]. That interval excludes zero and would invite
the claim "B is significantly better". It is too narrow because it treats 15,295 customers as
independent when the evidence comes from 40 regions.

## Decision

**Keep A.** The rule fixed in advance was: switch only if B is shown to be practically better (the
whole interval above +0.02) **and** B meets the latency budget. B fails both conditions. Its gain is
not shown to matter, and its p95 latency is twice the budget. Either failure alone would be enough.

## Risks

* B's advantage may be real but small and uneven. The region-level spread suggests B helps a lot in
  some regions and hurts in others. A future slice analysis could find a segment where B pays off.
* AUC is a proxy. The quantity that matters is retained revenue per offer shown. A model with equal
  AUC but better calibration in the top decile could still be worth more.
* The latency figure comes from staging. Production could be faster with batching, but nothing here
  shows that.

## What would change the decision

* A paired region-level interval for B - A wholly above +0.02, on at least two held-out months.
* B at p95 under 50 ms on infrastructure we already run, or a product change that moves scoring
  off the request path (precompute nightly) so the latency budget no longer applies.
* An online test showing retained revenue per offer at least 2 % higher with B, with an interval.
