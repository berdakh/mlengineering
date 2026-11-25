# f7_explain - reviewer notes (parallel form of b4; rubric only)

## What a strong memo contains

**Recommendation:** do not replace the forecaster in all stores before the holidays; re-evaluate
against the current rule with a forward-in-time backtest first, then pilot in a limited set of stores
(about a week of work for the backtest).

**Reasons specific to this scenario (the top two or three):**

1. **A random split of store-product-day rows lets the model see the future.** Neighbouring days of
   the same series land in train and test, and lag/rolling features computed from them carry the test
   day's level. Daily demand is strongly autocorrelated, so the 9 % is optimistic. Forecasting must
   be evaluated forward in time (rolling-origin backtest: train up to day t, forecast t+1 ...).
2. **The decision is about a period the data barely covers.** Only two December holiday seasons
   exist; a random split mixes them into training. The question "will it be better this December?"
   needs a backtest that holds out the most recent holiday season entirely, and its uncertainty is
   large (one season).
3. **The metric does not match the cost, and the comparison is against the wrong baseline.** MAPE
   is undefined or explodes on zero-sales days (common for fresh products) and treats over- and
   under-forecasting alike, while waste and empty shelves cost differently. And the incumbent is the
   seasonal-naive rule, which was not scored on the same split; gradient boosting is not the
   incumbent.

Also acceptable as secondary points: stores or products not seen in training; promotions and
stock-outs censoring demand (sales are not demand when the shelf is empty); operational fallback if
the model fails on a holiday morning; the risk of changing every store at once.

**Smallest decisive evidence:** a rolling-origin backtest over the last 6-8 months including the last
holiday season, scoring the current rule, boosting and the deep model with a cost-weighted error
(or waste units and stock-out days), per store with an interval over stores. Days, not weeks, if the
data pipeline exists.

**Deliberate tradeoff:** e.g. accepting the known waste of the current rule through the holidays in
exchange for not betting the peak season on an unvalidated model; or piloting in 10 stores, accepting
a slower rollout to bound the risk.

## Common weak answers and why they fall short

* **"9 % beats 12 %, ship it"**: accepts the evaluation.
* **Fifteen generic caveats** with no tie to random splits of time series, two holiday seasons or
  the incumbent rule.
* **"Use store-wise cross-validation"** without time: the right instinct from cross-subject work, but
  the leaking dimension here is time.
* **"MAPE is bad, use RMSE"** without the link to waste and empty shelves.
* **Correct content, unusable form:** recommendation hidden at the end, jargon, over the word limit.

## Rubric

| Aspect | Demonstrated independently | Partial | Not yet demonstrated |
|---|---|---|---|
| Technical reasoning | Identifies the temporal leakage of a random split of autocorrelated series, and at least one of: holiday coverage, metric vs cost, wrong baseline - each with the mechanism | Names "leakage" or "overfitting" without the mechanism in this data | Accepts the result |
| Prioritisation | Two or three reasons, most important first | Correct points diluted among generic ones | Unranked list or a minor point only |
| Actionability | Clear recommendation up front, concrete backtest with effort estimate | Recommendation without a path to a decision | No recommendation |
| Communication | Readable by the operations director; within the limit; tradeoff stated | Accurate but written for ML specialists | Unclear |
