# w8d3 challenge rubric — design review

Score after you finish. The checks verify structure; this rubric scores judgement.

| Area | Demonstrated | Partial | Not yet |
|---|---|---|---|
| **Finds the leak (§4)** | Names both post-routing fields as unavailable at prediction time, rates it blocker, links it to the inflated 0.94 | Flags the fields as suspicious but not as a blocker or not as leakage | Misses it or praises the feature importance |
| **Evaluation matches deployment (§5)** | Time-based split; same customer/outage on one side; final number compared with the rules on the same period | Says "random split is bad" without saying what to do | Accepts the random split |
| **Label and data (§3)** | Label inherits today's routing; 30-day closed-ticket window selects easy tickets; fixes both | One of the two | Not addressed |
| **Metric (§2)** | Accuracy vs majority-class baseline; macro/per-team recall; business metric (re-assignments) | Mentions imbalance only | Not addressed |
| **Serving arithmetic (§6)** | Shows 220 > 200 ms and 3 busy cores > 2; proposes headroom, timeout and fallback | Finds one of the two | Accepts the plan |
| **Operations (§7-§8)** | Delayed labels make nightly accuracy impossible; input/latency monitoring; shadow, canary, rollback | Monitoring or rollout, not both | Not addressed |
| **Data handling (§9)** | Stops logging text and emails; retention; does not over-weight the small embedding cost | Mentions privacy vaguely | Calls the $40/month cost the main issue |
| **Prioritisation** | Verdict and summary order the fixes: leakage and evaluation first, then the rest | Correct verdict, flat list | Approves, or buries the blockers among minor points |

**Common wrong reviews and why they fail.**
* *Twenty minor comments on wording and model choice, no blocker.* A review's value is in stopping the
  doc from shipping a wrong number; the leak and the split decide whether anything else matters.
* *"Use a transformer instead of gradient-boosted trees."* Model choice is not the problem; the
  measurement is. A better model on a leaky split is still unmeasured.
* *"The embedding API is too expensive."* 400,000 calls a month at $0.10 per 1,000 is about $40 a month.
  Check the arithmetic before raising cost; the real issue with the API is latency and availability.
* *Fix = "improve monitoring".* Not actionable. Say what is measured, on which window, by whom.
