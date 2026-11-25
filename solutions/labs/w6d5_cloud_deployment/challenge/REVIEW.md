# Review of the demandcast-api deployment plan

## Summary
The service design is fine for a demo, but five things in the plan are risks we should not take even
for two days: a stored administrator key, a public bucket, an internet-open port, a mutable `latest`
tag, and no budget or teardown. All five have cheap fixes, listed below; `plan_fixed.json` has them.

## Credentials
An access key for an IAM user with `AdministratorAccess`, committed to the repo, is the most serious
item. "The repo is private" protects it only until someone forks it, clones it to a laptop that is
lost, or a CI log prints it; the key never expires, and it can do anything in the account, including
running expensive instances for someone else. Change: delete the key and the user; deploy with your
IAM Identity Center sign-in (`aws sso login`) and a `demandcast-deployer` permission set limited to
ECR, ECS, the log group, `iam:PassRole` on our two task roles, and the budget. Then run a secret scan
on the repo history, because the key may already be in an old commit; if it is, treat it as leaked.

## Budget and cost
There is no budget, so the first signal of a mistake would be the monthly bill. Create a monthly
budget of 20 USD with an alert at 50 % actual and 100 % forecasted, before any other resource. I also
halved the task size (0.5 vCPU / 1 GB is plenty for a z-score forecast API at demo load) and went to one
task: "high availability" for a two-day internal demo doubles the cost for a benefit nobody needs. Look
up the Fargate, public IPv4 and log prices for eu-west-1 and put the expected two-day total in the plan.

## Registry and image tags
`latest` in a mutable repository means two tasks can run different code and we cannot say which build
answered a request or roll back to a known one. Use the git SHA as the tag, make the repository
immutable, and turn scanning back on: the delay is seconds and it is the only vulnerability check we have.

## Model artifacts
A public-read bucket exposes the model to anyone who guesses the name, and turning off Block Public
Access is the account-wide setting most often behind data leaks. Keep the bucket private with Block
Public Access on, and give the task a task role with `s3:GetObject` on that one object. (Alternative:
bake the 40 MB model into the image and drop the bucket; one image is then one model, which is simpler.)

## Network exposure
Port 8080 open to 0.0.0.0/0 publishes an unauthenticated API: scanners find new public IPs within
hours, and anyone could send it traffic we pay for. Allow only the two office egress addresses as /32
rules and have home workers use the VPN. If that is not enough, the next step is an authenticated
endpoint, not a wider rule.

## Logs
No retention means keeping, and paying for, every log line forever. Set 7 days; the demo needs at most
that, and we export anything worth keeping.

## Teardown
"Delete things in the console when I have time" is how resources get forgotten. The fixed plan lists
every resource with a teardown entry, in dependency order, and the service teardown has a time with a
calendar reminder. After running it, check the not-billing list from our runbook the next morning.

## Decision
Go with changes: approve once the key is deleted and the repo history scanned, and the plan matches
`plan_fixed.json`. Happy to pair on the permission set tomorrow morning.
