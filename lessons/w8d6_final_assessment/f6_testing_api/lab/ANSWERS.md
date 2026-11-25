# f6 written answers (2-4 sentences each)

## 1. A client sends `"shipments_30d": "many"` to `POST /score`.
Which HTTP status class should the service return, who has to act, and should the request reach the model?

## 2. The service reads account history from a feature store, and the feature store times out.
What should `POST /score` return, what should a readiness endpoint report while the outage lasts,
and why does the difference between this case and question 1 matter to whoever operates the service?

## 3. `POST /score` also creates a "call this account" task in the CRM when the risk is high.
A client's request times out and it retries. Is that safe? What would make it safe?

## 4. A request passes validation, but `avg_parcel_kg` is 65 while the largest training value was 24.
Is this a validation problem or a model problem? What should the service do, and what must it not do?

## 5. Unit test or not?
"A test asserts that the deployed model ranks account A00007 above account A00042." Is that a good
unit test? What does it test, when will it break, and what would you write instead?
