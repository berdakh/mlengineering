# w6d5 model answers, common wrong answers, rubrics

## 1. Order

Budget first because it is the only control that tells you when something is costing money; any resource
created before it can bill unobserved, and a failure half-way through the script leaves billed resources
behind with no alert. Task definition before service because `create-service` references a registered
task-definition family; in the wrong order the call fails (the service has nothing to run). The service
also needs the image pushed, the role and the log group to exist, or the task fails to start and ECS keeps
retrying (each attempt pulling the image).

*Common wrong answer:* "the budget limits spending." It does not stop anything; it notifies. (AWS Budgets
actions can apply policies, but that is not what this lesson configures.)

## 2. Teardown order

`delete-cluster` fails while the cluster still has an active service (the API returns an error; the
cluster stays). Deleting the security group while a task's network interface uses it fails with a
dependency violation. The script stops at the first failure (`set -euo pipefail`), so everything after it
is left running: the order is what makes a teardown complete.

*Common wrong answer:* "it doesn't matter, AWS deletes dependents." Most AWS delete calls refuse rather
than cascade; `ecr delete-repository` needs `--force` for exactly this reason.

## 3. Rotated keys versus SSO

(a) The key is valid until it is rotated: a leak today is usable for up to a month; SSO credentials expire
within hours on their own. (b) A key on disk is readable by every process running as you (a malicious
package, a debugging tool that uploads the home directory) and gets copied into backups and images;
SSO credentials are short-lived and tied to a sign-in with MFA. (c) Keys belong to an IAM user, which tends
to accumulate permissions; Identity Center permission sets are managed centrally. Any two with mechanisms.

*Common wrong answer:* "SSO is more secure because it is newer." No mechanism, no points.

## 4. Exposure

Reachability is decided by the security group's inbound rules, not by the address. With no inbound rule,
packets to the public IP are dropped. The public IP exists so the task can reach ECR (and Logs) without a
NAT gateway. The setting that makes it public: an inbound rule with a CIDR wider than one address (e.g.
`0.0.0.0/0`), i.e. `allowed_cidr` wider than `/32` with `allow_public = true`.

*Common wrong answer:* "it is not public because it has no DNS name." Scanners use addresses.

## 5. `latest` on an immutable repository

Immutability then makes the *second* push of `latest` fail, so the pipeline breaks at the next release,
and the tag still says nothing about which build it is. The fix is a tag that identifies the build (the
git SHA) on an immutable repository; then the tag is a permanent name, and rollback means "deploy the
previous SHA".

## 6. `/readyz` versus `/healthz`

With `/healthz`, a task whose model failed to load (missing bundle, checksum mismatch) is reported healthy:
the process is up. ECS keeps it running and the service is "stable" while every `/predict` returns 503.
With `/readyz` the task becomes unhealthy, ECS stops and replaces it, the deployment does not reach a
steady state, and `services-stable` times out: the failure is visible during deployment, not after.

## 7. Cost reasoning

The alert. Cost is proportional to running time; a forgotten deployment runs 730 hours a month. Halving
task size halves vCPU and GB charges but not the per-hour public IPv4 charge, and still bills for 730
hours. An alert after one day caps the running time at roughly 24 hours plus your reaction time: about a
30-fold reduction for the month. (Both together are better; the question asks which matters more.)

*Common wrong answer:* "halving size halves the bill." Not the IPv4 part, and it ignores time.

## 8. Design choice: printed script versus SDK calls (model answer, about 200 words)

For this project the printed script is better. The reason is review: the person paying for and
authorising the deployment can read every command, with every value substituted, before anything runs,
and the live run is guaranteed to be that text. That makes the dry run a real artefact (it can be
attached to a pull request or a change ticket) and keeps the learning visible: each line maps to one AWS
API call the learner can look up. It also needs no extra dependency beyond the AWS CLI.

What I give up: error handling and idempotency. A script stops at the first failure and cannot easily
resume, check whether a resource already exists, or roll back what it created; it parses outputs with
`--query` strings; and it is bash, which is hard to test. An SDK program can check state before acting,
retry with backoff, and clean up on failure. Beyond one service, neither is the industry answer:
infrastructure as code (CloudFormation, CDK, Terraform) declares the desired state and computes the plan,
which combines a reviewable plan with idempotent execution.

*Rubric:* 2 points for a choice justified by this project's needs (review, gating, learning); 2 points
for a real cost (idempotency, partial failure, testing) or for placing both against IaC. Answers that
claim one option "has no downside" get at most 2.

## Challenge rubric (review of the colleague's plan)

The checks cover the facts; score the writing here (2 points each, 14 total; 10+ is a pass):

1. Credentials: identifies the committed administrator key as the most severe issue, says to delete the
   key and user, and to scan history because the key may be in old commits (treat as leaked).
2. Budget: budget first, with alert thresholds, and a stated expected cost structure.
3. Registry: explains why `latest` blocks rollback and attribution; turns scanning back on.
4. Artifacts: private bucket with Block Public Access and a task role, or the model baked into the image.
5. Network: replaces 0.0.0.0/0 with specific addresses; says what to do if that is not enough (VPN,
   authentication), rather than widening the rule.
6. Teardown: a dated teardown of every resource and an independent not-billing check.
7. Tone and decision: specific, actionable, not condescending; a clear decision with conditions.

Common weak reviews: listing problems without the risk ("bucket should not be public"); proposing a
`/16` "company network" range as a fix; rotating the key instead of removing it; a decision of "go" with
the stored administrator key still in place.

## Interview rep rubric (deploy a model service, 10 minutes)

| Element | Strong answer contains |
|---|---|
| Clarify | who calls it, how many requests, latency need, data sensitivity, two-week lifetime |
| Artifact | one immutable image per release, tagged by git SHA, scanned; model inside or fetched with a role |
| Identity | short-lived credentials for people; a minimal execution role; no keys in code or image |
| Compute | a managed container service, one or two tasks, health check on readiness, sized from measurement |
| Exposure | private by default; restricted ingress or authentication; TLS if anything leaves a trusted network |
| Cost | budget and alert first; expected cost structure; teardown date |
| Observability | structured logs with release id; service metrics (rate, errors, latency); a check that predictions are sane (distribution), not only that the service is up |
| Rollback | redeploy the previous digest; keep the last good release |

Scoring: 1 point per element covered with a specific mechanism (8 total). 6+: good; 4-5: revisit
sections 2.2-2.5 and redo the rep in a week; below 4: re-read H13.1 and H13.2 first. The most common gap
at this stage is the last observability item: everything above says whether the service is *up*, not
whether its predictions are *right* (week 7).
