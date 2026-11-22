# Design doc: ML ticket routing for the support platform (v0.3, for review)

*A colleague's draft. It is a constructed exercise for lesson w8d3: the company, numbers and people are
invented. Review it as you would a real design review: what must change before this is built?*

## 1. Problem

Support tickets arrive by email and web form and are routed by keyword rules to one of 12 teams
(billing, login, integrations, ...). About 30 % of tickets are re-assigned at least once, adding a median
of 9 hours to resolution. We will replace the rules with a model that predicts the right team when the
ticket arrives.

## 2. Requirements and success metric

* Volume: 400,000 tickets per month; peak about 50 tickets per second after an outage notification.
* Routing must complete within **200 ms at p99** (the web form waits for a ticket number and a team).
* Success metric: **accuracy** of the predicted team on held-out tickets. Target: 90 %.
  (Class shares today: billing 41 %, login 22 %, the other ten teams share the remaining 37 %.)

## 3. Data and labels

* Training data: all tickets **closed in the last 30 days** (about 400,000), from the ticket database.
* Label: the team that **closed** the ticket.
* Text: subject and body; metadata: customer plan, product area selected in the form (optional field,
  empty 60 % of the time), language.

## 4. Features

* TF-IDF of subject and body; a sentence embedding from the hosted embedding API.
* Customer plan, product area, language.
* `time_to_first_response_minutes` and `number_of_transfers` from the ticket record — both are strongly
  predictive in our notebook (feature importance rank 1 and 3).

## 5. Evaluation

* Random 80/20 split of the 400,000 tickets, stratified by team. 5-fold cross-validation on the 80 %
  for model selection; the 20 % for the final number.
* Result in the notebook: **accuracy 0.94** with gradient-boosted trees on all features. Ship it.

## 6. Serving

* Request path: form service → routing service (FastAPI) → hosted embedding API → model → response.
* Latency budget (p99): network and form service 40 ms, embedding API 120 ms, model 60 ms. Fits in 200 ms.
* Capacity: model inference takes 60 ms on one core. One replica with 2 cores handles the peak of
  50 tickets per second.

## 7. Monitoring

* A nightly job computes accuracy on yesterday's tickets and posts it to the team channel.

## 8. Rollout

* Deploy on a Monday morning and switch all traffic to the model. If accuracy drops, retrain.

## 9. Cost and data handling

* The hosted embedding API costs $0.10 per 1,000 calls.
* For debugging, the routing service logs the full request (subject, body, customer email) and the
  response for every ticket. Logs are kept indefinitely.
