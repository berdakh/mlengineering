# w8d3 assessment

Answer in writing (or aloud, recorded) before opening
`solutions/lessons/w8d3_system_design/assessment_answers.md`.

**Q1 (estimation).** A fraud model scores 40 million card transactions a day with a 6x peak. Each
prediction takes 8 ms on one core. Replicas have 4 cores and you run them at 50 % utilisation. How many
replicas do you need at peak? Show the units at each step.

**Q2 (labels).** A churn model predicts monthly; churn is known 60 days after the prediction; you keep a
90-day evaluation window. What fraction of the window's predictions have labels today? What happens to
your monitoring if the label delay grows to 100 days?

**Q3 (batch vs online).** For each, choose batch, online (request-time) or streaming, and give one reason:
(a) weekly product recommendations e-mailed on Monday; (b) a fraud decision at card authorisation;
(c) a machine-health score that must react to vibration within a minute; (d) a demand forecast that sets
tomorrow's staffing.

**Q4 (design choice — explain).** In D2 you quote the 0.75 quantile as the upper bound rather than the
mean plus a margin. Explain why, using the cost ratio, and state the assumption that makes 0.75 optimal.

**Q5 (training/serving parity).** A feature "orders in the store in the last 15 minutes" is computed in SQL
for training and in a streaming job for serving. List three ways they can disagree and one design that
prevents it.

**Q6 (launch criteria).** Why should a launch criterion include at least one metric the model was not
trained on? Give an example from D1 or D2.

**Q7 (failure patterns).** Name four ways candidates commonly lose a design interview in the first ten
minutes, and what to do instead.

## Interview rep (the session's main event)

The two timed designs in [`DESIGN_PROMPTS.md`](DESIGN_PROMPTS.md), 45 minutes each, recorded, self-scored
against part A of `solutions/lessons/w8d3_system_design/DESIGN_ANSWERS.md` before you read part B.
Log in `progress/notes.md`: area scores, the follow-up you handled worst, and one structural habit to
change on the next attempt.

## Rubric for Q1-Q7 (open-ended reasoning)

| Score | Meaning |
|---|---|
| Demonstrated | Correct, with units or mechanism; states the assumption that would change the answer |
| Partial | Right direction but missing a step, a unit, or the key assumption |
| Not yet | Incorrect, or a slogan without mechanism |
