# Design review: ML ticket routing (v0.3)

Reviewer: reference review (w8d3 solutions)          Time spent: 40 minutes

## Findings

| ID | Section | Severity | Finding | Proposed fix |
|---|---|---|---|---|
| F2 | §5 | major | A random split of tickets mixes past and future and puts follow-up tickets of the same customer and duplicate tickets from the same outage on both sides. Deployment scores future tickets. | Split by time: train on weeks 1..k, validate on the next week, test on the last two weeks; keep customers' threads on one side; report per-week accuracy to see variation. |
| F3 | §3 | major | The label is the team that closed the ticket, which bakes in today's rules and re-routes, and "closed in the last 30 days" drops long-running and still-open tickets, which are the hard ones. | Define the label as the team that resolved the ticket after the last transfer, audit a labelled sample by hand, and train on several months including tickets that closed late (snapshot by creation date, not close date). |
| F4 | §2 | major | Accuracy with a 41 % majority class says little; a model that never routes to small teams can reach a high number while every integrations ticket bounces. The cost of a wrong route differs by team. | Report macro-averaged recall and per-team recall plus the re-assignment rate; set the launch criterion on re-assignments and time to resolution, compared with the current rules on the same period. |
| F5 | §6 | major | The latency budget does not fit: 40 + 120 + 60 = 220 ms against 200 ms at p99, and p99s do not add up linearly in your favour. The external embedding API is also a hard dependency. | Drop or cache the hosted embedding (TF-IDF alone first), measure p99 of each hop, keep at least 20 % headroom, and add a timeout with a fallback to the rules engine when the API is slow. |
| F6 | §6 | major | Capacity is off: 50 tickets/s x 60 ms is 3 busy cores, so one replica with 2 cores is over 100 % utilised at peak and queues grow without bound. | Plan replicas from Little's law at about 60 % utilisation: 3 / (2 x 0.6) gives 3 replicas, at least 2 zones, and a load test at the outage-notification peak. |
| F7 | §7 | major | Nightly accuracy on yesterday's tickets uses labels that do not exist yet (tickets close days later), and nothing watches inputs, latency, errors or the share of each team. | Monitor inputs and service health in real time, compute accuracy on a delayed window of tickets whose labels have settled, and track re-assignment rate daily as the leading business signal. |
| F8 | §8 | major | Switching all traffic at once with "retrain if accuracy drops" has no shadow phase, no guardrail and no rollback path. | Run the model in shadow against the rules for two weeks, then a canary for a share of teams or traffic with a guardrail on re-assignment rate, and keep the rules as a one-step rollback. |
| F9 | §9 | major | Logging full ticket bodies and customer emails indefinitely creates a privacy and security liability for no debugging need. | Log ticket id, model version, predicted team, scores and latency; keep raw text only in the ticket system with its existing access controls; set a retention period for service logs. |
| F10 | §3 | minor | The optional product-area field is empty 60 % of the time; its absence may itself correlate with the team and will change if the form changes. | Treat missingness explicitly, measure performance with and without it, and monitor its fill rate after launch. |

## Verdict

Verdict: reject and redesign

## Summary for the author (at most 120 words)

Two problems make the 0.94 meaningless: two features are only known after routing (§4), and the random
split lets the model see the future and the same customers on both sides (§5). Fix those first and
re-measure on a time-based split with macro recall and re-assignment rate against the rules. Then fix
the label definition (§3), the latency budget, which is already 20 ms over, and the capacity plan (§6).
Launch through shadow and canary with a rollback to the rules, monitor inputs and delayed accuracy, and
stop logging ticket text. The embedding cost is small (about $40 a month at current volume) and is not
the concern.
