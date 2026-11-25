# Runbook: deploy flowguard to ECS on Fargate, verify, tear down

All commands run from the lab directory (`labs/w6d5_cloud_deployment/lab`). Steps 1-4 never touch
AWS. Steps 5-9 do, and are only for a learner who has decided to deploy and signed `SIGNOFF.md`.

## Local (always)

1. **Run the same container locally**, with the same environment variables and the same health check
   as the task definition: `bash deploy/run_local.sh`. It builds the image, publishes port 8000 on
   127.0.0.1 only, waits for `/readyz`, prints `/version`, and removes the container.
2. **Configure**: `cp deploy/config.example.toml deploy/config.toml` and fill it in. Leave placeholders
   you do not know yet; a dry run prints them as they are.
3. **Dry run** both scripts and read them:
   `python deploy/aws_deploy.py plan --config deploy/config.toml > deploy/rendered/deploy.sh`
   `python deploy/aws_deploy.py teardown --config deploy/config.toml > deploy/rendered/teardown.sh`
   Also read `deploy/rendered/taskdef.json`.
4. **Decide.** If you will not deploy, stop here: the local run is the deliverable.

## Live (only after SIGNOFF.md)

5. **Prices.** Fill in from the official pricing pages, today:

   | Item | Region | Price looked up | Date |
   |---|---|---|---|
   | Fargate vCPU-hour | | | |
   | Fargate GB-hour | | | |
   | Public IPv4 address-hour | | | |
   | ECR storage GB-month | | | |
   | CloudWatch Logs ingestion GB | | | |

6. **Sign in**: `aws sso login --profile <profile>`; `aws sts get-caller-identity --profile <profile>`.
7. **Deploy**: `python deploy/aws_deploy.py plan --config deploy/config.toml --live`.
8. **Verify** (each with `--profile` and `--region`):
   * `aws ecs describe-services --cluster <name>-cluster --services <name>-svc` shows
     `runningCount: 1` and a deployment with `rolloutState: COMPLETED`;
   * the task's container health status is `HEALTHY`
     (`aws ecs list-tasks ...` then `aws ecs describe-tasks ...`);
   * the CloudWatch log group `/ecs/<name>` has a stream with the JSON line `"event": "model_loaded"`;
   * only if you set `allowed_cidr` to your `/32`: find the task's public IP (describe-tasks gives the
     network interface id; `aws ec2 describe-network-interfaces` gives the address) and
     `curl http://<ip>:8000/readyz` from your machine.
9. **Tear down the same day**: `python deploy/aws_deploy.py teardown --config deploy/config.toml --live`.

## Checking that nothing is billing

After the teardown, each of these must come back empty or not-found:

* `aws ecs list-clusters` (no `<name>-cluster`) and `aws ecs list-services --cluster <name>-cluster`
* `aws ecs list-task-definitions --family-prefix <name>` (no ACTIVE revisions)
* `aws ecr describe-repositories --repository-names <name>` (RepositoryNotFoundException)
* `aws logs describe-log-groups --log-group-name-prefix /ecs/<name>`
* `aws ec2 describe-security-groups --filters Name=group-name,Values=<name>-sg`
* `aws ec2 describe-network-interfaces --filters Name=group-name,Values=<name>-sg` (no leftover ENIs)
* `aws iam get-role --role-name <name>-task-execution` (NoSuchEntity)
* the next day: Billing and Cost Management, bills for the current month, by service.
