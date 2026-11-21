# b3 written answers (2-4 sentences each)

## 1. A client sends `"tenure_days": -5` to `POST /predict`.
Which HTTP status class should the service return, who has to act, and should the request reach the model?

## 2. The model artifact fails to load when the service starts.
What should `POST /predict` return, what should a health/readiness endpoint report, and why does the
difference between this case and question 1 matter to whoever operates the service?

## 3. A client's request times out and it retries the same `POST /predict`.
Is that safe? What would make it unsafe, and what is the standard remedy?

## 4. A request passes validation but the customer is unlike anything in the training data
(e.g. `monthly_price` is valid but ten times higher than any training value).
Is this a validation problem or a model problem? What should the service do, and what must it not do?

## 5. Unit test or statistical check?
"Average precision on the held-out month is at least 0.18." Is that a unit test? Where does a check
like this belong, and what is the risk of putting it in the unit-test suite?
