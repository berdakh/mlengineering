# w8d3 — two timed system-design prompts

**Conditions (Weeks 6-8 level).** 45 minutes each, timer on, spoken aloud and recorded (phone audio is
enough) while you sketch boxes on paper. No hints, no notes, no AI assistance. When the timer ends,
**score yourself against the rubric first**, then open the worked answer:
`solutions/lessons/w8d3_system_design/DESIGN_ANSWERS.md` (part A rubrics, part B worked answers).
Do D1 in the essential session and D2 in the optional extension or on the review day.

The interviewer will answer any clarifying question with the facts below. Anything not listed: make an
assumption, say it out loud, and move on. Both scenarios are constructed for this course; the companies
and numbers are invented, chosen to be realistic in size.

---

## D1 — Search ranking for an internal knowledge base (45 minutes)

A 9,000-employee engineering company has an internal knowledge base: design docs, runbooks, wiki pages,
meeting notes and Q&A threads, about 4 million documents in total, 15,000 new or edited per day. Search
today is a keyword engine (BM25) with no learning. Employees complain that the right runbook is on page
two. You are asked to design an ML-based ranking system.

Facts available on request:
* About 250,000 searches per working day; the busiest hour carries 4 times the average hourly rate.
  Search results must render within **500 ms at p95** end to end; the keyword engine alone takes 80 ms.
* Logs exist for the last year: query, results shown with positions, clicks, dwell time on the opened
  document, and whether the user searched again within 2 minutes.
* About 2 % of documents are restricted (HR, security, legal). A user must never see a restricted title
  or snippet they are not allowed to open. Permissions change daily.
* There are no human relevance judgements. A team of 6 technical writers could spend a few hours a week
  on judgement tasks.
* Content is in English, plus code snippets and stack traces pasted into Q&A threads.

Follow-ups the interviewer will ask in the last 8 minutes:
1. *"Your offline metric improved, but the online click-through rate did not move. Why might that be?"*
2. *"A new on-call engineer searches for an error message that appears in no document yet. What happens?"*
3. *"How would you know if the new ranker made search worse for the legal team only?"*

---

## D2 — Delivery-time estimates for a grocery delivery service (45 minutes)

A grocery delivery company operates in 14 cities. When a customer opens the checkout, the app shows an
estimated delivery time ("arrives in 35-45 min"). Today the estimate is a per-city constant plus distance
times a speed. Customers complain about late orders; operations complain that the estimate is so
pessimistic that people do not order. You are asked to design the ML system that produces the estimate.

Facts available on request:
* About 600,000 orders per day; at checkout the estimate is requested about 5 times per order on average
  (the basket changes, the customer edits the address). Dinner peak is 3 times the daily average rate.
* The estimate must be returned within **150 ms at p99**; the checkout service calls it synchronously.
* An order passes through stages: accepted by a store, picked by a shopper, handed to a courier, driven,
  delivered. Each stage has a timestamp in the order database; GPS pings from couriers every 10 s.
* Real-time state is available: number of open orders per store, shoppers and couriers on shift, weather,
  traffic speed by road segment from a third-party API.
* About 1.5 % of orders are cancelled before delivery. Late deliveries (over the upper bound shown) cost
  goodwill credits; operations think a late order costs about three times as much as an over-estimate of
  the same size.
* A new city launches next month with no history.

Follow-ups the interviewer will ask in the last 8 minutes:
1. *"Your model's mean absolute error is better than the formula's, but customer complaints about late
   orders went up. How?"*
2. *"The traffic API is down for an hour during dinner peak. What does the checkout show?"*
3. *"How do you produce estimates in the new city on day one?"*
