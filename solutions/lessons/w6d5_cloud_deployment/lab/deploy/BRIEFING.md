# Cost and credential briefing (read before any live AWS step)

This is the briefing `SIGNOFF.md` refers to. It is short on purpose. The lesson
(`lessons/w6d5_cloud_deployment/README.md`, section 2) explains the reasons.

## What gets created, and what each item costs

The deployment creates eight kinds of resources. Prices are **not** quoted here: they differ by
region, change over time, and could not be checked against AWS's pricing pages when this course was
written (those pages were unreachable from the authoring environment). Look them up yourself on the
official pricing pages on the day you deploy, and write them into the table in the RUNBOOK.

| Resource | Billed? | How it is billed (structure only) |
|---|---|---|
| ECS service with 1 Fargate task (0.25 vCPU, 0.5 GB) | yes, while the task runs | per vCPU-hour and per GB-hour, by the second with a minimum (check the page) |
| Public IPv4 address of the task | yes, while attached | per address-hour |
| ECR repository | yes | per GB-month of stored images, plus data transfer out |
| CloudWatch Logs group | yes | per GB ingested and per GB-month stored (retention is set to 7 days) |
| ECS cluster, task definition, IAM role, security group | no direct charge (verify) | - |
| AWS Budgets budget | usually free for the first few budgets (verify) | - |

What to expect: a single small task running for a couple of hours costs little, but a forgotten one
runs 730 hours a month. The teardown is part of the exercise, not optional clean-up.

## Credentials: the rules

1. **No long-lived access keys.** Use IAM Identity Center: `aws configure sso` once, then
   `aws sso login --profile flowguard-sso` each session. The credentials expire on their own.
2. **Never put credentials, account ids or e-mail addresses in the repository.** `deploy/config.toml`
   is git-ignored; the account id can come from `FLOWGUARD_AWS_ACCOUNT_ID`.
3. **Use a role with only the permissions this deployment needs**, not the account's administrator,
   if your account setup allows it. The lesson lists the services involved.
4. **Never paste credentials into a chat, an issue, or a log.** If one leaks, deactivate it first and
   investigate second.
5. **Do not use the root user** for anything in this lesson.

## Network exposure

The default configuration adds **no inbound rule**: the service runs, passes its health checks and
writes logs, but nobody can connect to it. Setting `network.allowed_cidr` to your own address as a
`/32` lets only you reach port 8000. Anything wider is public and needs `allow_public = true` plus the
public sign-off boxes. Public exposure of an unauthenticated prediction API is never the default.

## Stop conditions

Stop and tear down if: `get-caller-identity` shows an unexpected account; any command fails half-way
(run the teardown, which tolerates partly-created stacks only if you run its lines one by one); the
budget alert e-mail arrives; you are unsure what something costs.
