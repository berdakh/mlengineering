# Retention-offer decision note - reference

Data: **synthetic** StreamBox snapshots. Numbers show that the method is applied correctly; they are
not evidence about real customers. Run 2026-11-21 with `offer_policy.py` (logistic regression,
unweighted, on all non-identifier features).

1. **Recommendation.** Send the offer only to customers whose predicted churn probability exceeds
   their break-even value `4 / (0.25 * 6 * monthly_price)` (0.27 at 9.99, 0.18 at 14.99, 0.13 at
   19.99 USD). On the four test months that is 73 of 1,968 customer-months (3.7 %), with an expected
   net value of about **+123 USD per 1,000 customers per month** under the stated assumptions.
   Offering to everybody loses about 2,174 per 1,000.

2. **Evidence.**

   | Policy | Offered | Churners reached | Net value per 1,000 |
   |---|---|---|---|
   | nobody | 0 % | 0 % | 0 |
   | everybody | 100 % | 100 % | -2,174 |
   | prevalence forecast | 0 % | 0 % | 0 |
   | model | 3.7 % | 13.1 % | +123 |

   A forecast of the base rate (6.8 %) is below every customer's break-even probability, so it offers
   to nobody: without a model that separates customers there is no profitable campaign at these
   costs. Brier score on test: model 0.0775, prevalence forecast 0.0814. The skill is small.
   73 offers is a small sample; +123 carries wide, unquantified uncertainty (bootstrap by customer
   would be the next step; w3d5).

3. **Calibration on the test months did not hold.** Validation (last two training months): mean
   predicted 0.057, observed 0.060. Test: mean predicted 0.061, observed **0.089**. Every one of five
   equal-count bins is under-predicted (top bin 0.151 predicted, 0.193 observed). The churn rate rose
   after the training period; the model's ranking survived, its level did not. Consequence: the rule
   `p >= threshold` is too conservative now; customers who are profitable to contact are skipped.
   Temporal validation did not reveal this because the shift came after the validation months. What
   I would do: monitor mean predicted against observed rate monthly (labels arrive 30 days late);
   recalibrate the intercept on the most recent labelled month; not retune the threshold on test data.

4. **Sensitivity to the assumed success rate** (policy fixed at the one built for 0.25):

   | True success rate | Net value per 1,000 |
   |---|---|
   | 0.125 | -13 |
   | 0.25 | +123 |
   | 0.50 | +394 (a policy built for 0.5 would earn +760) |

   The sign of the result depends on a number that is not in the data.

5. **What this cannot tell us.** The model predicts who will churn, not who will stay *because of*
   the offer. Customers with the highest churn probability may be the least persuadable, and the 25 %
   figure is an average from past campaigns with unknown targeting. Only a randomised holdout
   (offer versus no offer among customers above the threshold) measures the effect; that is the
   experiment to run before scaling. Also unassessed: offers train customers to wait for discounts.
