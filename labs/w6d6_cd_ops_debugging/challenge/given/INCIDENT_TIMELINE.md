# Incident timeline: demandcast forecasts too low after release 9e1f07c2

SYNTHETIC scenario for the w6d6 challenge. The service, people and numbers are invented. All times are
UTC on Tuesday 2026-03-10. Collected from chat, the deploy pipeline and dashboards by the on-call
engineer the same afternoon.

The service: `demandcast-api` predicts next-day demand per store and product; the store-ordering
system calls it every 5 minutes and turns forecasts into supplier orders, which an analyst can review
before they are sent (most are sent automatically after 15 minutes).

| Time (UTC) | Source | Entry |
|---|---|---|
| 13:41 | pipeline | Release `9e1f07c2` built and pushed. It contains a refactor of the weather-feature code. Unit tests pass (they use a synthetic weather fixture). Staging smoke tests pass: `/readyz` 200, `/predict` 200 for 20 sample requests. |
| 13:55 | pipeline | Promotion of the staging digest to production, triggered by Mei (deploy on-call) after the green staging run. |
| 14:02 | dashboards | First production requests answered by `9e1f07c2`. Latency and error rate unchanged. |
| 14:09 | chat | Store-ops analyst: "next-day order suggestions for North and Lakes regions look about a third lower than usual, is something wrong?" |
| 14:21 | chat | Ravi (ML on-call) acknowledges. Service dashboards: p95 latency 41 ms, 0 errors. "Service looks healthy." |
| 14:30 | notebook | Ravi compares the distribution of forecasts by release from the prediction log: mean forecast 31 % lower since 14:02; no change in request volume or input missingness. |
| 14:36 | code review | The refactor reads the temperature feature from a new weather client that returns degrees Fahrenheit; the model was trained on Celsius. The unit test fixture was written in Fahrenheit too. |
| 14:41 | chat | Dana (team lead) agrees to roll back. |
| 14:45 | pipeline | Rollback started: production redeployed with the previous digest (release `4b2a9d10`). |
| 14:49 | dashboards | Rollback complete; mean forecast back within the normal band. |
| 15:10 | chat | Store-ops confirms: 212 store orders were generated from the low forecasts; 37 had already been sent to suppliers and were corrected by phone; the rest were regenerated. |

Facts you may also use: the model's training pipeline and the serving code share no feature code;
the prediction log records each forecast with its release id; there is no alert on the forecast
distribution; the staging smoke test checks status codes only.
