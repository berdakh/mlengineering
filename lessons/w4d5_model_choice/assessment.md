# W4D5 assessment

Answer in writing before opening `solutions/lessons/w4d5_model_choice/assessment_answers.md`.

## Reasoning questions

1. An interval for (B - A) in PR-AUC is [+0.004, +0.031]; the MPID is 0.02. Classify it and say, in
   one sentence a product owner would understand, what it means.
2. Why must the MPID be fixed before the comparison is run? Describe one concrete way of fooling
   yourself if it is chosen afterwards.
3. Your Pareto front has three candidates. A colleague says "so any of the three is fine". What is
   right and what is wrong about that?
4. You time 1,000 calls of a model in a loop and report the mean: 2.1 ms. Name three ways this
   number can mislead about production latency.
5. In today's real run the logistic model scored 0.901 PR-AUC on the test set against 0.884 for the
   chosen flow-rate |z|. Give three separate reasons why this does not reopen the decision.
6. `sys.getsizeof(model)` returns 56. What does that number measure, and how do you measure what you
   need instead?

## Design choice (explain in 150-250 words)

The complexity ranking puts the supervised logistic model *above* the isolation forest, although
the forest is far larger and slower. Defend that ordering, or argue for a different one. Your answer
must use the operational context of flowguard: who retrains it, with which data, and how often.

## Memo rubric (lab memo and challenge memo)

| Criterion | Below expectations | Meets | Exceeds |
|---|---|---|---|
| Pre-commitment | MPID or constraints missing, or stated after results | MPID, hard constraints and complexity ranking stated as fixed in advance | Also says who set them and why those values |
| Evidence | Point estimates only, or test data used for the choice | Paired intervals with the unit of resampling and number of clusters; costs; test used once | Also states what the intervals do not cover (training variation, other regimes) |
| Decision | Does not follow from the table, or a leaderboard pick | Stated rule applied mechanically; a reader could predict the decision | Also names the closest alternative and what it would take to switch |
| Risks | Generic ("model may drift") | At least three specific risks, each with a way to notice it | Monitoring signals or owners attached |
| Change conditions | Missing or vague | Measurable conditions | Includes a cheap experiment that would resolve the main uncertainty |
| Brevity | Over two pages, or missing sections | One page, six sections | Every sentence carries information |

## Interview rep (10-15 minutes, spoken; record yourself)

> "Your project compared a z-score, a Mahalanobis distance, an isolation forest and a supervised
> logistic model. The logistic model had the best numbers. Why didn't you ship it?"

Rules (Week 4 fading): timed, no notes for the first answer. Score yourself with the rubric in the
answers file before reading its worked answer. Then answer the two follow-ups:
(a) "Isn't +0.07 PR-AUC a lot?"
(b) "What would make you switch?"
