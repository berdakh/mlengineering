# Assessment: w7d4 model updates and rollback

Answer in writing before opening `solutions/lessons/w7d4_model_updates_rollback/assessment_answers.md`.

## Reasoning questions

1. List four retraining triggers. For each, give one situation where it fires but retraining would be the
   wrong response.
2. In task 6, 1.1.0's recall difference has interval [+0.000, +0.429]. Explain why the lower end is exactly
   zero, and why that makes the superiority and non-inferiority policies disagree.
3. 2.0.0 looked marginally better on development data (12/27 against 11/27 faults) and much worse on the
   test experiments (1/7 against 5/7). Give two explanations and say which data would distinguish them.
4. The shadow run showed 4 extra alarms from 1.1.0, all on real faults, and no false alarms. Why is that
   not evidence that 1.1.0 will meet its alert budget in production?
5. A canary routes 10 % of machines to the candidate for one week. Faults occur about twice a week across
   the fleet. What can the canary tell you about recall? What should its stopping rule watch instead?
6. Why must the audit entry be written *after* the pointer moves, and why must the pointer move be atomic?
   Describe the failure each rule prevents.

## Design-choice explanation (required)

7. `rollback` treats promotions as a stack instead of returning to the `from` of the last audit entry.
   Construct the sequence of operations where the simpler rule does harm, and defend the stack.

## Interview rep (15 minutes, timed, rubric only)

> "You own a model that scores card transactions for fraud in real time (p99 budget 50 ms). The data
> science team hands you a new model that is 3 % better offline. Walk me through how you would get it
> into production, and how you would get it out again if something goes wrong."

## Rubric for questions 2, 4, 7 and the interview rep

| Score | Meaning |
|---|---|
| 0 | Ships on one offline number, or has no rollback path |
| 1 | Mentions shadow/canary/rollback as words, without what each measures or when it stops |
| 2 | Paired offline gate with a predeclared rule, shadow for disagreement and operational checks, canary with guardrails and a stopping rule, rollback as an audited pointer move |
| 3 | All of 2, plus label delay for the primary metric, what the canary cannot measure, compatibility of schema/threshold/preprocessing as one versioned unit, and who can trigger the rollback |
