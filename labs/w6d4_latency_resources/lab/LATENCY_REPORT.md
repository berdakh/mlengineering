# Latency report: flowguard /predict

Fill this in from your own runs (`results/*.json`). Numbers you did not measure do not belong here.

## Set-up
Machine (cores, other load), Python and uvicorn versions, request size, launcher, how the load was
generated (open loop, rates, duration, warm-up), and what this set-up over- or under-states.

## Budget
The budget from `budget.toml` and who it serves.

## Results
A table: configuration x offered rate -> p50, p95, p99, error rate, throughput, server memory.

## Bottleneck
What limited the service, the evidence (which numbers, which profile), and the mechanism.

## Fix and effect
What you changed, before/after numbers from the same method, and whether the budget is now met.

## What this does not show
At least two limitations of this measurement.
