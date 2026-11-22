# Interview set 5 - ML system design rep 1; an API contract in code

**Use on:** the Week 5 review day (`w5d7`). **Total time: 45 minutes, timer on.**
**Conditions (Weeks 3-5 level):** timed; the design is **spoken aloud** as at a whiteboard (record
yourself, or sketch boxes on paper while talking); no hints, no solutions, no AI assistance. After the
first attempt open the **rubric only** (`solutions/interview/set5.md`, part A). The worked answer
(part B) stays closed until you have made a second attempt at every rubric area scored below
"Demonstrated".

| # | Type | Time |
|---|---|---|
| D1 | System design: real-time credit risk at a buy-now-pay-later checkout | 30 min |
| C2 | Coding: the scoring endpoint's request contract (FastAPI + pydantic) | 15 min |

On a short day: D1 alone (30 minutes).

**How a design round is judged.** Not on the model. An interviewer listens for whether you (1) ask
for the requirements that change the design, (2) define the prediction target and when its label is
known, (3) evaluate in a way that matches deployment and avoids leakage, (4) design a serving path that
meets the latency budget and fails safely, (5) say how the system is versioned, monitored and updated,
and (6) make trade-offs explicit with numbers. Spend about three minutes on requirements, then
structure the rest; say what you would do first and what you would postpone.

---

## D1 - "Decide at checkout" (30 minutes)

You join a company that offers **buy-now-pay-later** (BNPL) at the checkout of online shops: the
customer pays for a purchase in four instalments, one every two weeks. Today a hand-written rules
engine approves or declines each application. The company wants a model.

What the interviewer tells you when asked (anything else, make and state an assumption):

* **Volume:** about 2 million applications a month; peak 200 per second during sales.
* **Latency:** the merchant's checkout waits for the decision. The whole decision call must answer
  within 300 ms at p99; the merchant's page times out at 1 s and then shows "payment method
  unavailable".
* **Outcome of interest:** a customer is in **default** if any instalment is more than 60 days past
  due. The last instalment is due six weeks after purchase, so the label of an application is final
  only about **14 weeks** after the decision.
* **Selective labels:** about 85 % of applications are approved by the current rules. Declined
  applications never produce an outcome.
* **Data available at decision time:** the application (amount, merchant, basket), the customer's
  history with the company (if any), device and session signals from the checkout, and a credit-bureau
  lookup that costs money per call and adds 80-150 ms.
* **Repeat structure:** many customers return; a few hundred merchants make up most of the volume.
* **Constraints:** a declined customer must receive a reason; decisions must be reproducible for audit
  months later; the risk team wants to set the approval policy (how much default risk is acceptable per
  segment), not the data scientists.

**Design the system.** Cover what you judge important, in an order you choose. The interviewer will
interrupt with these follow-ups near the end (keep about 5 minutes for them):

1. *"Your offline AUC is excellent. Two months after launch, defaults are higher than predicted. List
   what could explain it, in the order you would check."*
2. *"The bureau provider has an outage for 40 minutes on Black Friday. What does your system do?"*
3. *"How do you know the model is better than the rules engine before you replace it?"*

## C2 - The scoring endpoint's request contract (15 minutes)

Implement `create_app(model=None)` in `interview/set5_work/c2.py`. Use FastAPI and pydantic v2; no
other dependencies. The app exposes **`POST /score`**.

**Request body** (JSON):

| Field | Type | Constraint |
|---|---|---|
| `application_id` | string | 1 to 64 characters |
| `amount` | number | finite, `> 0` and `<= 5000` |
| `currency` | string | one of `EUR`, `GBP`, `USD` |
| `customer_age_days` | integer | `0` to `36500` |
| `items` | list | 1 to 50 objects `{"sku": string of 1-40 characters, "price": finite number > 0 and <= 5000}` |

Unknown fields, at the top level or inside an item, are **rejected**, not ignored.

**Behaviour**

* `model` is a callable `model(amount, customer_age_days, n_items) -> float`. `None` means "not loaded".
* Order of checks: schema first, then readiness, then the domain rule, then scoring.
* Schema violation → **422** with body `{"error": "validation_error", "message": ..., "details": [...]}`;
  each detail has `loc` (the path, e.g. `["body", "items", 1, "price"]`), `type` and `msg`. The body
  must **not** echo the submitted values, and a non-finite number (`NaN`, `Infinity`; Python's JSON
  parser accepts them) must produce a 422 of type `finite_number`, never a 500.
* Model not loaded → **503** with `{"error": "not_ready", ...}`.
* Domain rule: the sum of item prices must equal `amount` within 0.01; otherwise **400** with
  `{"error": "amount_mismatch", ...}`.
* Success → **200** with `{"application_id", "score", "model_version"}`, where `score` is the model's
  output and `model_version` is the module's `MODEL_VERSION`.

Before coding, say which errors are 422 and which are 400, and why the amount rule is not a schema
rule. After coding, say what your service returns for `GET /score`, and why.

```bash
python -m pytest interview/set5_tests -q
```

Note: the test harness loads your file as a module named `set5_c2`. If you use
`from __future__ import annotations`, pydantic still resolves your models through that module.
