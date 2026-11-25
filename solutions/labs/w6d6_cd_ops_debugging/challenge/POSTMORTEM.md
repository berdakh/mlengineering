# Postmortem: demandcast forecasts too low after release 9e1f07c2

REFERENCE (w6d6 challenge). SYNTHETIC incident.

## Summary
Release `9e1f07c2` fed the model temperatures in degrees Fahrenheit instead of Celsius. Every
operational signal stayed green (status codes, latency, errors), so the release passed staging and
production checks, and forecasts were about a third too low for 47 minutes until it was rolled back.
The error was found because a store-ops analyst noticed unusual order suggestions, not by monitoring.

## Impact
Customer impact lasted **47 minutes**, from 14:02 (first production requests answered by
`9e1f07c2`) to 14:49 (rollback complete). Mean forecast was 31 % below normal in that window. 212 store
orders were generated from the low forecasts; 37 of them had already been sent to suppliers and were
corrected by phone, the other 175 were regenerated. No data was lost; the prediction log covers the
whole window.

## Timeline
All times UTC, 2026-03-10.
- 13:41 Release `9e1f07c2` built; unit tests (synthetic weather fixture) and staging smoke tests pass.
- 13:55 Staging digest promoted to production by the deploy pipeline.
- 14:02 Production starts serving `9e1f07c2`. **Impact begins.** Latency and errors unchanged.
- 14:09 Store-ops analyst reports order suggestions about a third lower in two regions.
- 14:21 ML on-call acknowledges; service dashboards show the service healthy.
- 14:30 Forecast distribution by release, from the prediction log: mean 31 % lower since 14:02.
- 14:36 Cause found in code review: the new weather client returns Fahrenheit; the model expects Celsius.
- 14:41 Decision to roll back.
- 14:45 Rollback started: previous digest (release `4b2a9d10`).
- 14:49 Rollback complete; forecasts back in the normal band. **Impact ends.**
- 15:10 Store-ops confirms the order corrections.

## Root cause
A refactor moved the temperature feature to a new weather client whose values are in Fahrenheit. The
model was trained on Celsius values, and nothing between the client and the model states or checks the
unit, so the model received plausible-looking numbers on a different scale and produced lower forecasts.

## Contributing factors
- The unit test fixture for the new client was also in Fahrenheit, so the test confirmed the code
  matched the fixture, not that the feature matched training.
- Training and serving compute features with separate code, so a serving-side change cannot be checked
  against the training pipeline (training/serving skew, w5d1).
- The staging smoke test checks status codes only; a model that answers 200 with wrong numbers passes.
- There is no alert on the distribution of inputs or forecasts; detection depended on a human noticing.
- Orders are sent automatically after 15 minutes, so the time to detect directly set the business cost.

## What went well
- The prediction log records the release with each forecast, which made the 14:30 comparison quick and
  conclusive.
- Rollback by digest took four minutes and restored a known-good image exactly.
- The analyst's report was taken seriously although every dashboard was green.

## What went wrong
- 19 minutes passed between the start of impact and the first acknowledgement, and 39 minutes before the
  cause was known; during that time orders kept being sent.
- The first check (14:21) looked at service health, which cannot show a model-quality problem.
- No gate compared the new release's predictions with the old one's before promotion.

## Action items

| Action | Type | Owner | Due |
|---|---|---|---|
| Add a unit-checked feature contract (name, unit, plausible range) validated at the serving boundary | prevent | ML platform team | 2026-03-24 |
| Staging gate: replay yesterday's requests against old and new release; block promotion if the mean forecast moves > 5 % | prevent | ML on-call rota | 2026-03-31 |
| Alert on forecast and input distribution shift per release (PSI on temperature and forecast mean) | detect | ML platform team | 2026-03-31 |
| Hold automatic supplier orders for 30 minutes after a new model release reaches production | mitigate | Store-ops engineering | 2026-03-20 |
| Replace the synthetic weather fixture with values recorded from the training data source | prevent | Forecasting team | 2026-03-17 |
| Add "check the prediction log by release" to the ML on-call runbook's first steps | process | ML on-call rota | 2026-03-13 |

## Lessons
A healthy service is not a correct model: status codes, latency and error rates say nothing about
whether predictions are right. Checks that compare a new release's outputs with the current one's, and
monitoring of prediction distributions, are the operational signals a model service needs in addition
to service health. Tests built from the same assumption as the code cannot catch that assumption.
