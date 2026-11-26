---
title: "Cloud basics (AWS)"
parent: Tool guides
nav_order: 15
---

# Cloud basics (AWS)

A **cloud provider** rents you computers, storage and services by the hour, managed from a web console or the
command line. **Amazon Web Services (AWS)** is the largest; Google Cloud and Microsoft Azure have the same ideas
under different names. This guide covers what Week 11 uses (notebook 41) and what you need to deploy the course's
prediction API **if and when you decide to**.

{: .warning }
> **Read this first.** Nothing in the course creates cloud resources, and you do not need an AWS account to finish
> it. Everything below that creates a resource **costs money** from the moment it exists, until you delete it.
> Follow the steps only if you understand the bill, have a budget alert in place, and will tear everything down
> afterwards. Never expose a service to the internet without a reason and someone's agreement. Prices and free-tier
> terms change: always read AWS's current pricing pages; this guide quotes no prices on purpose.

## What it is, and why teams use it

Running a model service yourself means buying a server, keeping it patched, replacing broken disks, paying for
electricity and a network connection, and being woken up when it fails. A cloud provider does those parts. You
pay per hour or per request, start in minutes, and can delete everything when you are done.

What you trade for it: a bill that grows quietly if you forget something, permissions that are easy to get wrong,
and a large catalogue of services with overlapping purposes. The habits in this guide (identity first, a budget
first, least privilege, written teardown) exist because of those three.

## The vocabulary

| Term | Meaning |
|---|---|
| **Account** | The container for all resources and the bill. Identified by a 12-digit number (AWS's documentation uses `123456789012` as a placeholder). |
| **Root user** | The email address that created the account. Can do anything, including closing it. Protect it with MFA and do not use it for daily work. |
| **Region** | A geographic location, e.g. `eu-central-1` (Frankfurt), `us-east-1` (N. Virginia). Resources live in one region; prices differ a little between regions; data protection rules may require a region. |
| **IAM** | Identity and Access Management: identities, roles and permission policies. |
| **IAM user** | A long-lived identity; may have **access keys** (an id starting with `AKIA` plus a secret). Keys work until deleted: the thing that usually leaks. |
| **Role** | An identity without permanent credentials. People or services *assume* it and get **temporary credentials** that expire. |
| **IAM Identity Center** | Single sign-on for people: you log in (with MFA) and receive role credentials. The recommended way for humans to use the CLI. |
| **Policy** | A JSON document saying which actions are allowed on which resources. |
| **ARN** | Amazon Resource Name, the unique id of a resource, e.g. `arn:aws:s3:::course-models-example`. |
| **S3** | Simple Storage Service: files ("objects") in **buckets**. Good for model files and datasets. |
| **ECR** | Elastic Container Registry: stores your Docker images. |
| **ECS / Fargate** | Elastic Container Service runs containers; **Fargate** runs them without you managing servers. |
| **CloudWatch** | Logs, metrics and alarms. |
| **Secrets Manager / Parameter Store** | Stores secrets; services receive them at start-up by reference. |
| **Budgets** | Sends an alert when your spending (actual or forecast) passes an amount. |

## Choosing where to run a model service

| Option | You provide | Pay for | Fits |
|---|---|---|---|
| EC2 (virtual machine) | a whole server to install and patch | every hour it is on | special hardware, full control |
| ECS on Fargate | a container image | every hour the containers run | a steady HTTP service (this course's path) |
| App Runner | a container image; it adds HTTPS and scaling | running time and requests | the simplest container route; check its current availability in the AWS docs first |
| Lambda | a function (or image) per event | each call and its duration | spiky, short jobs; 15-minute limit per call |
| SageMaker endpoints | a model in SageMaker's format | instance hours | teams already on SageMaker |

The course uses **ECR + ECS on Fargate** because the image you tested locally in Week 10 runs unchanged, with
health checks and logs. The handbook chapter [13. One cloud deployment path](../handbook/ch13_cloud_deployment/index.md)
explains the choice in more depth.

## Before anything else: account safety

1. **Secure the root user**: turn on MFA (a phone authenticator app), and do not create access keys for it.
2. **Create a budget with an alert.** In the console: *Billing and Cost Management → Budgets → Create budget*,
   choose a monthly cost budget, a small amount, and your email for alerts. Budgets themselves are free to
   create (check the current Budgets pricing page); they alert, they do **not** stop spending.
3. **Set up IAM Identity Center** and create a user for yourself with a permission set, then sign in through it
   for daily work.
4. **Pick one region** and use it everywhere.

## Installing and signing in with the AWS CLI (local, not Colab)

The **AWS CLI** is the command-line tool for AWS. Install it from the official instructions for your operating
system (search "Install AWS CLI version 2"). Check:

```bash
aws --version          # aws-cli/2.x.y ...
```

Sign in with Identity Center (single sign-on), once per profile:

```bash
aws configure sso                         # asks for the start URL and region, then opens a browser
aws sso login --profile course            # later sessions: refresh the temporary credentials
aws sts get-caller-identity --profile course   # who am I? prints the account and the role
```

`get-caller-identity` is the first command to run whenever something is denied: it shows which identity the CLI
is actually using. Credentials from `aws sso login` are cached and expire; nothing long-lived is written to disk.

Do **not** run the CLI from Colab with your credentials: a notebook is easy to share, and its outputs keep what
was printed.

## Secrets: the rules

* Code reads secrets from **environment variables**; it never contains them.
* The platform fills those variables from **Secrets Manager** or **Parameter Store** at start-up (in ECS: the
  `secrets` field of the task definition, which references an ARN).
* Never put a secret in Git (any file, any branch), a Docker image, a log line, a notebook output, an issue or a
  chat.
* `.gitignore` the files where local secrets live (`.env`, `credentials*`, `*.pem`); this repository already does.
* If a key leaks: **deactivate it first** in IAM, then remove it from the code, then check what it was used for.
  Deleting the line in a new commit is not enough: history keeps it.

## Least-privilege policies

A policy is JSON:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": "s3:ListBucket", "Resource": "arn:aws:s3:::course-models-example"},
    {"Effect": "Allow", "Action": "s3:GetObject",  "Resource": "arn:aws:s3:::course-models-example/*"}
  ]
}
```

* `Version` is always `"2012-10-17"`: the version of the policy language.
* `Action` is `service:Operation`; `Resource` is one or more ARNs.
* Avoid `"*"` in actions (`"s3:*"` includes deleting everything) and in resources (every resource in the account).
* Some actions do not support resource-level restrictions and require `"Resource": "*"` (for example
  `ecr:GetAuthorizationToken`, which logs Docker in to the registry). The IAM documentation lists, for each
  service, which actions support which resources.
* Give the **running service** its own role (an ECS **task role**) with only what it needs at run time, e.g. read
  the model bucket. The **task execution role** is separate: it lets ECS pull the image and write logs (AWS
  provides the managed policy `AmazonECSTaskExecutionRolePolicy` for it).

## A deployment path, step by step (prepared, not run by the course)

The commands follow the AWS CLI documentation at the time of writing; check the current documentation before
running them, and replace `123456789012`, `eu-central-1` and the names with your own. Each step says how to undo
it.

**1. A registry for the image.**

```bash
aws ecr create-repository --repository-name churn-api \
    --image-tag-mutability IMMUTABLE --image-scanning-configuration scanOnPush=true
# undo: aws ecr delete-repository --repository-name churn-api --force
```

Immutable tags mean a tag (use the Git commit id) always names the same image. Registry storage is billed per GB
per month, so add a lifecycle policy that keeps only the last few images.

**2. Push the image built in Week 10.**

```bash
REGISTRY=123456789012.dkr.ecr.eu-central-1.amazonaws.com
aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin $REGISTRY
docker tag churn-api:local $REGISTRY/churn-api:$(git rev-parse --short HEAD)
docker push $REGISTRY/churn-api:$(git rev-parse --short HEAD)
```

**3. A task definition**: a versioned JSON description of the container. The important parts:

```json
{
  "family": "churn-api",
  "requiresCompatibilities": ["FARGATE"],
  "networkMode": "awsvpc",
  "cpu": "256", "memory": "512",
  "executionRoleArn": "arn:aws:iam::123456789012:role/churn-api-execution",
  "taskRoleArn": "arn:aws:iam::123456789012:role/churn-api-task",
  "containerDefinitions": [{
    "name": "api",
    "image": "123456789012.dkr.ecr.eu-central-1.amazonaws.com/churn-api:3f2a9c1",
    "portMappings": [{"containerPort": 8000}],
    "environment": [{"name": "MODEL_VERSION", "value": "churn_v3"}],
    "secrets": [{"name": "DB_PASSWORD",
                 "valueFrom": "arn:aws:secretsmanager:eu-central-1:123456789012:secret:churn-db"}],
    "logConfiguration": {"logDriver": "awslogs", "options": {
      "awslogs-group": "/ecs/churn-api", "awslogs-region": "eu-central-1", "awslogs-stream-prefix": "api"}}
  }]
}
```

`cpu` `"256"` is 0.25 vCPU and `memory` `"512"` is 0.5 GB; Fargate accepts only certain combinations (listed in
its documentation). Register it with `aws ecs register-task-definition --cli-input-json file://taskdef.json`; each
registration creates a new revision. The log group must exist (`aws logs create-log-group --log-group-name
/ecs/churn-api`; undo with `aws logs delete-log-group`).

**4. A cluster and a service.** A **service** keeps N copies of the task running and replaces unhealthy ones.

```bash
aws ecs create-cluster --cluster-name course
aws ecs create-service --cluster course --service-name churn-api --task-definition churn-api \
    --desired-count 1 --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-...],securityGroups=[sg-...],assignPublicIp=DISABLED}"
# undo: aws ecs update-service --cluster course --service churn-api --desired-count 0
#       aws ecs delete-service --cluster course --service churn-api
#       aws ecs delete-cluster --cluster course
```

The **security group** is the network rule. Allow the service port only from where it must be reached (your own
network range, or a load balancer), never SSH (22) or remote desktop (3389) from `0.0.0.0/0`. Note that pulling
an image from ECR needs a network route to it (a public IP, a NAT gateway, or VPC endpoints), and some of those
are billed by the hour too: read the ECS networking documentation before choosing.

**5. Check it.** `aws ecs describe-services --cluster course --services churn-api` shows running and desired
counts and recent events; the logs are in CloudWatch under `/ecs/churn-api`.

**6. Tear down** in reverse order (service, cluster, log group, repository, roles, secrets), then the next day
open *Billing → Bills* and *Cost Explorer* and confirm nothing is still charging. Secrets Manager secrets are
billed per secret per month and, when deleted, wait out a recovery window.

## Estimating the cost

For a container service the main term is

```
tasks × hours × (vCPU × price per vCPU-hour + memory GB × price per GB-hour)
```

with a month ≈ 730 hours, plus smaller items: log ingestion and storage, registry storage, data transfer out,
and anything that runs by the hour beside your task (load balancers, NAT gateways). Look up each unit price on
the AWS pricing page for your region, or use the AWS Pricing Calculator, and write the estimate down **before**
you create anything. Notebook 41 practises the arithmetic with invented prices.

Cheap habits: run one small task, stop it (`--desired-count 0`) when nobody uses it, keep few images, set short
log retention, and delete the whole stack when the demo is over.

## Releases and rollback

* Tag images with the Git commit; keep the previous images in the registry.
* A new task definition revision points at the new image; `aws ecs update-service --task-definition
  churn-api:<revision>` rolls it out. ECS replaces tasks gradually and can roll back automatically when new
  tasks fail health checks (see "deployment circuit breaker" in the ECS documentation).
* **Rollback** = update the service to the previous revision. Write the exact command in your release notes
  before you deploy.

## Common errors and how to read them

| Message | What it means | What to do |
|---|---|---|
| `Unable to locate credentials` | the CLI has no credentials | `aws sso login --profile ...`, and pass `--profile` (or set `AWS_PROFILE`) |
| `The SSO session associated with this profile has expired` | temporary credentials expired | `aws sso login` again |
| `AccessDenied ... is not authorized to perform: ecr:...` | the identity lacks a permission | `aws sts get-caller-identity` to see who you are; add only the missing action |
| `no basic auth credentials` on `docker push` | Docker is not logged in to ECR (tokens expire after hours) | rerun the `get-login-password` command |
| task stops with `CannotPullContainerError` | the task cannot reach ECR, or the execution role lacks permissions | check the network route to ECR and the execution role |
| task keeps restarting | the container exits or fails its health check | read its CloudWatch logs; run the same image locally |
| `ResourceInitializationError: unable to pull secrets` | the execution role may not read the secret, or no route to Secrets Manager | grant `secretsmanager:GetSecretValue` on that secret ARN; check networking |

## Cheat sheet

```bash
aws sso login --profile course                    # sign in (temporary credentials)
aws sts get-caller-identity --profile course      # who am I?
aws ecr create-repository --repository-name NAME --image-tag-mutability IMMUTABLE
aws ecr get-login-password | docker login --username AWS --password-stdin ACCOUNT.dkr.ecr.REGION.amazonaws.com
aws ecs register-task-definition --cli-input-json file://taskdef.json
aws ecs create-service ... --desired-count 1 --launch-type FARGATE
aws ecs update-service --cluster C --service S --task-definition FAMILY:REV   # release / rollback
aws ecs update-service --cluster C --service S --desired-count 0              # stop paying for compute
aws ecs describe-services --cluster C --services S
aws logs tail /ecs/NAME --follow                  # follow the service's logs
```

Before creating anything: budget alert ✔ · region chosen ✔ · cost estimate written ✔ · teardown commands
written ✔ · no secrets in code ✔ · no admin ports open to the world ✔.

## Where to go next

* Course: [41 · Deploying to the cloud safely](../notebooks/41_cloud_deployment_basics.html), and the handbook's
  [H13.1 Identity, credentials and cost](../handbook/ch13_cloud_deployment/h13_1_identity_credentials_cost.md) and
  [H13.2 Registry and a container service](../handbook/ch13_cloud_deployment/h13_2_registry_and_container_service_on_aws.md).
* AWS documentation: the IAM User Guide (policies, roles), the Amazon ECS Developer Guide (task definitions,
  Fargate, networking), the AWS CLI User Guide (IAM Identity Center sign-in), and AWS Budgets.
* AWS pricing pages and the AWS Pricing Calculator, for real numbers on the day you decide.
