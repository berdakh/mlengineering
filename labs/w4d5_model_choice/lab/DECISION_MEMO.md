# Decision memo: which detector flowguard ships

Author: · Date: · Decision owner: (the reliability engineer who acts on the alarms) · Status: draft

<!-- One page. Numbers from YOUR run of `python labs/w4d5_model_choice/lab/decision_table.py`.
     Replace every TODO. Graded with the rubric in labs/w4d5_model_choice/assessment.md. -->

## Context

TODO: what is being decided, for whom, and what was fixed before the results were seen
(MPID, alert budget, latency budget, complexity ranking).

## Options

TODO: the four candidates in one line each, simplest first, plus "do not ship a detector yet".

## Evidence

TODO: the development table (PR-AUC with interval, difference to the reference with interval and its
reading, events at the budget, false alarms per hour, p95 latency, size, retraining needs). State
the unit of resampling and the number of clusters.

## Decision

TODO: the choice and the rule that produced it. Then the single test look for the chosen model.

## Risks

TODO: at least three, each with how you would notice it in operation.

## What would change the decision

TODO: measurable conditions, for example "with N more labelled faults, an interval for logistic minus
flow-rate wholly above +0.05".
