# w6d5 assessment

Answer in writing (or aloud, recorded) before opening the model answers in
`solutions/lessons/w6d5_cloud_deployment/assessment_answers.md`. Aim for 25 minutes in total.

## Reasoning questions

1. **Order.** Why does the deploy script create the budget before the ECR repository, and the task
   definition before the service? Give one consequence of each wrong order.
2. **Teardown.** The teardown deletes the service before the cluster and before the security group.
   What happens, concretely, if you try them in the opposite order?
3. **Credentials.** A colleague says: "I rotate my access key every month, so storing it in
   `~/.aws/credentials` is as safe as SSO." Give two ways in which it is still worse.
4. **Exposure.** The task has a public IP address, yet the lesson calls the default deployment "not
   public". Explain, and state the one setting that would make it public.
5. **Tags.** Why is `latest` on an *immutable* repository not a fix for the `latest` problem?
6. **Health.** The task definition's health check calls `/readyz`, not `/healthz`. What failure would a
   `/healthz` health check let through, and what would ECS do differently in each case?
7. **Cost reasoning.** Using only the structure in section 2.3 (no prices), which change cuts the cost of
   a forgotten deployment more: halving the task size, or setting a budget alert that e-mails you after
   one day? Explain.

## Design-choice explanation (write 150-250 words)

8. The planner prints a bash script, and `--live` runs **that exact text** (the checks compare them). An
   alternative design calls the AWS SDK (boto3) directly from Python, step by step, with no script. Argue
   for one of the two for *this* course project and name what you give up.

## Interview rep (10-15 minutes, system design, reduced assistance)

> "You have a trained anomaly-detection model packaged as a Docker image that serves predictions over
> HTTP. A plant team wants to try it for two weeks. Walk me through how you would deploy it on AWS, what
> you would set up before the first request, and how you would know whether it is working."

Talk for 10 minutes without notes (record yourself if you can), then score yourself with the rubric in
the answers file. Do not look at the rubric before you have answered.

## Rubric for the open questions (self-assessment)

| Score | Meaning |
|---|---|
| 2 | Correct, specific to this deployment, names a concrete consequence or mechanism |
| 1 | Correct in general but vague ("it is more secure"), or misses the main mechanism |
| 0 | Incorrect, or confuses two concepts (e.g. liveness with readiness, IP address with exposure) |

Questions 1-7: 2 points each. Question 8: 4 points (2 for a defensible choice with a reason specific to
the project, 2 for naming a real cost of that choice). 13 or more of 18: move on; below 10: redo the
lab's tasks 4-6 without looking at your solution, a day later.
