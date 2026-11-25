# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/35_cloud_deployment.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 35 · One small cloud deployment on AWS (authorisation-gated)
#
# **Week 6 · day 5 · 2 h essential path + up to 1 h optional** · lab files: [`labs/w6d5_cloud_deployment/`](../labs/w6d5_cloud_deployment/)
#
# **Objective.** Understand IAM, credentials, registries and cost; deploy the container by one route, or complete the fully local equivalent if cloud use is not authorised.

# %%
# --- Setup: works on your laptop AND in Google Colab ----------------------------
# In Colab this clones the course repository and installs the requirements (about a
# minute, first run only). On your own machine it just finds the repository. Every
# command in this notebook runs from the repository root. Safe to re-run.
import os
import subprocess
import sys
from pathlib import Path

if "google.colab" in sys.modules:
    if not Path("/content/mlengineering-").exists():
        subprocess.run(["git", "clone", "--depth", "1",
                        "https://github.com/berdakh/mlengineering-.git",
                        "/content/mlengineering-"], check=True)
    os.chdir("/content/mlengineering-")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "-r", "requirements.txt"], check=True)

REPO_ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents]
                 if (p / "src" / "mlcourse").is_dir())
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "src"))
print("repo root:", REPO_ROOT)

# %% [markdown]
# **Status: Execution verified** for everything that runs locally (see the verification record at the
# end). Nothing in this lesson was run against AWS: the authoring environment had no AWS account and
# could not reach AWS's documentation or pricing sites. Version-sensitive AWS statements are marked.
#
# | | |
# |---|---|
# | **Primary objective** | Understand identity, credentials, registries and cost well enough to deploy the flowguard container by one route (Amazon ECR + Amazon ECS on AWS Fargate), and complete the fully local equivalent whether or not you deploy. |
# | **Deliverable** | `deploy/aws_deploy.py` that prints a reviewable deploy script and a teardown script, refuses `--live` without a signed `SIGNOFF.md`; a completed task definition; the local run of the same container; *if, and only if, you decide to*: one deployment and its same-day teardown. |
# | **Completion criteria** | `python wb.py check w6d5` passes; `bash deploy/run_local.sh` prints `"status":"ready"`; you can name every resource the deploy creates, what it costs (structure), and the teardown command for it, without notes. |
# | **Handbook** | [H13.1 Identity, credentials, cost](../docs/handbook/ch13_cloud_deployment/h13_1_identity_credentials_cost.md), [H13.2 Registry and a container service on AWS](../docs/handbook/ch13_cloud_deployment/h13_2_registry_and_container_service_on_aws.md) |
#
# > **Read this first.** Steps that touch AWS cost money and are **your** decision. This lesson never
# > asks you to create anything: the essential path ends with a dry run and a local container. The live
# > steps are behind three gates: an explicit `--live` flag, a signed `deploy/SIGNOFF.md`, and a config
# > with no placeholders. Nothing is exposed publicly unless you opt in twice.
#
# ---

# %% [markdown]
# ## 1. Purpose
#
# **What you will learn.** What a "cloud deployment" of one container actually consists of: an identity
# that is allowed to act, a registry that stores an immutable image, a compute service that runs it with
# a health check, a log destination, a network rule that decides who can connect, a budget that tells you
# when something is wrong, and a teardown that removes all of it. You will write the deployment as a
# reviewable script, gate its execution, and run the identical container locally.
#
# **Why an applied ML engineer needs it.** "Deploy the model" is a sentence in every MLE job description,
# and the expensive mistakes in it are not about the model: a forgotten service billing for a month, an
# access key pushed to GitHub, an unauthenticated endpoint open to the internet, a `latest` tag that
# makes rollback impossible. Interviewers ask "how would you deploy this?" to hear whether you think of
# those, not whether you remember console clicks.
#
# **Prerequisites.**
# * [w5d6](30_project_milestone_2.ipynb): the packaged service and its bundle. This lab ships its
#   own snapshot (package 0.6.0) with a minimal Dockerfile, JSON logs and a `/version` that reports the release.
# * Docker lessons w6d1-w6d2 (images, layers, Dockerfiles): helpful, not required; the Dockerfile here is
#   deliberately plain. Docker Engine must be installed for the local run.
# * `pip install -r requirements.txt` from the repository root. The AWS CLI v2 is needed **only** for the
#   optional live part.
#
# **Time budget (2 h essential + optional extension up to 1 h).**
#
# | Activity | Minutes |
# |---|---|
# | Read sections 2 and 3 | 30 |
# | Run and read the worked examples (secret scan, billed units) | 10 |
# | Guided lab, tasks 1-7 (local run, config validation, scripts, task definition, gate) | 65 |
# | Start the independent challenge (review a colleague's plan) | 5 |
# | Assessment questions and reflection | 10 |
# | *Optional extension (only if you decided to deploy)*: live deploy, verify, teardown, not-billing check | up to 60 |
#
# ---

# %% [markdown]
# ## 2. Conceptual explanation
#
# ### 2.1 Intuition: eight resources, one picture
#
# The route chosen here is the smallest that still teaches the general pattern: one image in **Amazon
# ECR** (the registry), one **ECS service** that keeps one **Fargate task** (a container on managed
# compute) running, logs to **CloudWatch Logs**, and a **security group** as the firewall. No load
# balancer, no NAT gateway, no database.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-35-01.svg" alt="Diagram 1 of notebook 35" style="max-width:100%">
#
# Everything else in the lesson is about making each arrow safe: who may push (identity), what is pushed
# (an immutable, scanned image), who may connect (no one by default), what it costs (budget first), and
# how it all goes away (teardown).
#
# ### 2.2 Precise terms
#
# * **Shared responsibility.** AWS secures the infrastructure; you secure what you put on it: identities
#   and their permissions, network exposure, the image's contents, your data, your bill.
# * **IAM user / role / IAM Identity Center.** An *IAM user* is a long-lived identity that can hold
#   long-lived access keys. A *role* is an identity that is *assumed* and yields **temporary credentials**.
#   *IAM Identity Center* (formerly AWS SSO) signs people in and hands out role credentials that expire on
#   their own: `aws configure sso` once, `aws sso login` per session. The course uses only this.
# * **Least privilege.** An identity gets the permissions its job needs and nothing else. The deploying
#   person needs ECR, ECS, Logs, the budget, and `iam:PassRole` on one role; not `AdministratorAccess`.
# * **Task execution role vs task role.** The *execution role* lets ECS itself pull the image and write
#   logs (managed policy `AmazonECSTaskExecutionRolePolicy`). A *task role* would give your code AWS
#   permissions; this service needs none, so it has none.
# * **Immutable tag.** A repository setting that refuses to move a tag once pushed. With the git SHA as the
#   tag, "release `1a2b3c4d5e6f`" names exactly one build forever, and rollback has something to point at.
# * **Health check.** A command the platform runs inside the container. Ours probes `/readyz`, so a task
#   whose model failed to load is reported unhealthy and replaced, not silently kept.
# * **Dry run / live.** The planner prints the exact shell script; `--live` runs that same text. Review and
#   execution cannot drift apart.
# * **Teardown.** The script that deletes every created resource in dependency order, followed by an
#   independent check that nothing is left (the RUNBOOK's "nothing is billing" list).
#
# ### 2.3 Cost: a structure you can reason about without prices
#
# Every billed item here is *rate × quantity × time*. For a Fargate task the quantities are vCPU and GB,
# the time is how long the task runs; the public IPv4 address is billed per hour while attached; ECR is
# per GB-month stored; logs per GB ingested and per GB-month kept. With rates $r$ looked up on the day:
#
# $$
# \text{cost} \approx T_{\text{hours}} \cdot n_{\text{tasks}} \cdot \left( r_{\text{vCPU}} \cdot \text{vCPU} + r_{\text{GB}} \cdot \text{GB} + r_{\text{IPv4}} \right) + r_{\text{ECR}} \cdot \text{GB}_{\text{images}} + r_{\text{logs}} \cdot \text{GB}_{\text{logs}}
# $$
#
# No prices are quoted in this course: they vary by region and change over time, and AWS's pricing pages
# were unreachable from the authoring environment, so any number here would be unverified. What the
# formula already tells you is that $T$ dominates. The worked example `task_hours.py` computes the billed
# *units* for four realistic scenarios:
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w6d5_cloud_deployment/figures/billed_units.svg" alt="Billed vCPU-hours for four scenarios: 0.5 for a same-day lab, 16 for a weekend, 182.5 for a forgotten month, 365 for two forgotten tasks" width="100%">
#
# *Figure 1. Billed vCPU-hours of a 0.25 vCPU task (arithmetic, no prices). A forgotten task bills 365 times
# more than one torn down the same day; "two tasks for availability" doubles it again. Source:
# `example/task_hours.py`.*
#
# This is why the budget is created **before** anything billable, why the sign-off asks for a calendar
# reminder, and why the teardown is part of the deliverable.
#
# ### 2.4 Credentials: what goes where
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-35-02.svg" alt="Diagram 2 of notebook 35" style="max-width:100%">
#
# The rules, in order of how often they are broken: never commit credentials (the lab's checks scan for
# key-shaped strings and 12-digit account ids); never bake them into an image (anyone who can pull it
# can read them); never pass secrets as plain environment variables in a task definition (they are visible
# to anyone who can describe it; ECS has a separate `secrets` field backed by Secrets Manager or
# Parameter Store, which this service does not need); never use the root user.
#
# ### 2.5 Exposure: "not public" is the default, on purpose
#
# The task needs a public IP address only to **pull** its image from ECR without a NAT gateway (which is
# billed per hour). Having a public address is not the same as being reachable: the security group has
# **no inbound rule** unless you set `network.allowed_cidr`, and then only your own address as a `/32`.
# Anything wider counts as public and needs `allow_public = true` *and* the public sign-off boxes. The
# planner turns that policy into code: a `/24` without `allow_public` is a configuration error, not a
# warning.
#
# > **Verification note (unresolved).** The current ECS API reference (botocore service model, read
# > 2026-11-22) says of `assignPublicIp`: "When the service `deploymentController` is `ECS`, the value must
# > be `DISABLED`", while the official AWS CLI example for `create-service` with Fargate uses
# > `assignPublicIp=ENABLED`. The rendered ECS documentation was unreachable, so this could not be
# > resolved. If your `create-service` call is rejected for this reason, stop (nothing billable is running
# > yet besides storage), run the teardown, and read the ECS developer guide's Fargate networking page:
# > the alternatives are private subnets with VPC endpoints for ECR and Logs, or a NAT gateway, both of
# > which add hourly cost.
#
# ### 2.6 Connection to other domains
#
# A real-time system in a research lab has all of these concerns, just on one lab machine: which build of
# the model is running (the image tag), whether it initialised correctly before the session started (the
# readiness probe), where its logs go (CloudWatch), who may connect to its socket (the security group),
# and switching it off at the end of the session (teardown). The cloud makes each of these explicit and
# billable. The analogy breaks on cost and exposure: a lab machine left on costs electricity and is
# reachable from the lab; a cloud service left on costs money every hour and is reachable from wherever
# its rules allow.
#
# ### 2.7 An industry example
#
# A data-science team deploys a demo of a churn model "for one afternoon" with an access key in the repo
# and the port open to the internet. Within days a bot harvests the key from a public fork and launches
# mining instances; separately, scanners find the open endpoint and send it enough traffic to matter. The
# model was fine. Every failure was in the parts this lesson covers: credentials, exposure, budget alerts
# and teardown. (This is an illustrative composite of well-known failure patterns, not a cited incident.)
#
# ### 2.8 Limitations and common misconceptions
#
# * **"A dry run proves the deployment works."** It proves the plan is what you intend and syntactically
#   complete. Permissions, quotas, region availability and the networking note above are only tested live.
# * **"Private repo means safe credentials."** Repositories get forked, cloned to lost laptops, and printed
#   in CI logs. Treat a committed key as leaked: deactivate first, investigate second.
# * **"Small task, small bill."** Size multiplies; *time* dominates (figure 1).
# * **"The health check is the same as `/healthz`."** Liveness (`/healthz`: the process answers) and
#   readiness (`/readyz`: the model is loaded) differ. The platform's health check should use readiness for
#   this service, or a task that cannot serve predictions counts as healthy.
# * **"Teardown in the console is fine."** A console clean-up misses what you did not create by hand (ENIs,
#   log groups, task definition revisions). Script it, then check independently.
# * **"This is production-ready."** It is a single task with no TLS, no authentication, no load balancer and
#   no autoscaling. It is a correct *small* deployment for learning and demos, not an operationally mature
#   service (week 7 adds the operational side).
#
# ---

# %% [markdown]
# ## 3. Worked examples
#
# ### 3.1 A secret scanner, and its blind spots
#
# `example/secret_scan.py --demo` builds a throw-away SYNTHETIC project with the mistakes people make
# (a key in a notebook, a credentials file, an account id in a config, a CSV with a 12-digit order number,
# a key split across two strings) and scans it with four rules. The fake keys are assembled at run time,
# so the file itself contains none.

# %%
!python labs/w6d5_cloud_deployment/example/secret_scan.py --demo

# %% [markdown]
# Output (executed 2026-11-22):
#
# ```
# <demo>/config/aws_credentials:2: aws-access-key-id
# <demo>/config/aws_credentials:3: aws-secret-key-assignment
# <demo>/config/deploy.toml:2: aws-account-id
# <demo>/notebooks/explore.py:2: aws-access-key-id
# <demo>/orders.csv:2: aws-account-id
# 5 finding(s)
# ```
#
# **Interpretation.** Four true findings and one false positive (`orders.csv`: a 12-digit order number
# looks like an account id). And one false negative that is not in the list: `sneaky.py` builds a key from
# two string literals, which no regular expression sees. Pattern scanners are a net with a mesh size; real
# tools (gitleaks, trufflehog, GitHub secret scanning) add entropy checks and verify candidates with the
# provider, and still cannot replace "credentials never touch the repository". The exit status is 1 when
# anything is found, which is what lets a pre-commit hook block the commit.
#
# ### 3.2 Billed units, without pretending to know prices

# %%
!python labs/w6d5_cloud_deployment/example/task_hours.py
!python labs/w6d5_cloud_deployment/example/task_hours.py --vcpu-hour 0.04 --gb-hour 0.004 --ipv4-hour 0.005

# %% [markdown]
# The first call prints vCPU-hours, GB-hours and address-hours (the numbers in figure 1). The second shows
# the arithmetic with **placeholder rates**, which are explicitly not prices; replace them with the rates
# you look up. Decision this supports: whether a demo needs to run over a weekend, and how much a forgotten
# teardown costs relative to the demo itself (365 times, at these sizes).
#
# ### 3.3 The local equivalent runs the same container
#
# The image the cloud would run is built from `lab/service/Dockerfile` and started with the task
# definition's settings: same environment variables, 0.25 CPU, 512 MiB, and the same health-check command.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w6d5_cloud_deployment/figures/startup_timeline.svg" alt="Five local runs: /healthz and /readyz answer 200 after 2.9-3.3 s, Docker reports healthy after 5.6-5.7 s" width="100%">
#
# *Figure 2. Five local runs of the image with the task definition's settings (real measurements, Docker
# 29.10 on the authoring machine, 2026-11-22). The service answers `/readyz` about 3 s after `docker run`;
# the container is marked healthy at the next health-check (every 2 s in this measurement). Memory in use
# once healthy: 63.5-64.2 MiB. Source: `figures/startup_runs.csv`.*
#
# On Fargate, add image pull time and task scheduling to these numbers (not measured here). The figure
# also explains the task definition's `startPeriod`: health-check failures during the first seconds should
# not count against a container that is still loading its model.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w6d5_cloud_deployment/figures/image_layers.svg" alt="Image layer sizes: dependencies 180 MB, base OS 87.7 MB, Python 41.4 MB, leftover wheel layer 31.6 MB, application code 57 kB" width="100%">
#
# *Figure 3. Layers of the lab's image (`docker history`). The application and model are kilobytes; the
# image is dominated by dependencies and the base. The orange layer is the wheelhouse copied for builds
# behind a proxy and left in a layer although a later step deletes it, a classic mistake that w6d2's
# multi-stage build removes. Image size matters for pull time (cold start) and ECR storage.*
#
# ---

# %% [markdown]
# ## 4. Guided lab
#
# Work in `labs/w6d5_cloud_deployment/lab/`. All commands run from that directory unless stated.
# Files you edit: `deploy/aws_deploy.py` (tasks 3-6) and `deploy/taskdef.template.json` (task 4).
# Everything else is given; read it.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-35-03.svg" alt="Diagram 3 of notebook 35" style="max-width:100%">
#
# **Task 1 - Run the container locally (10 min).**
#
# ```bash
# bash deploy/run_local.sh
# ```
#
# Expected: `readyz: {"status":"ready","model_version":"flowguard-z-1.0.0"}`, a `/version` line with your
# release (the git SHA) and `"environment":"production"`, one JSON log line with `"event": "model_loaded"`,
# and `removed container flowguard-local`.
#
# *If `docker build` fails in `pip install` with a certificate error,* you are behind a TLS-intercepting
# proxy (as the authoring environment was). Download wheels on the host, which trusts the proxy, and build
# from them:
#
# ```bash
# pip download --only-binary=:all: --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64 \
#     --python-version 3.12 --implementation cp -d service/wheels -r service/requirements.lock
# PIP_INSTALL_OPTS="--no-index --find-links=/srv/wheels" bash deploy/run_local.sh
# rm service/wheels/*.whl     # never commit wheels
# ```
#
# **Task 2 - Read the given files (10 min).** `BRIEFING.md`, `SIGNOFF.md`, `RUNBOOK.md`,
# `config.example.toml`, the two JSON policies and the templates. Write down, before reading section 4 of
# the RUNBOOK, which resources you expect the deployment to create. *Checkpoint:* eight kinds (section 2.1).
#
# **Task 3 - Validate the configuration (`load_config`, 10 min).** The TOML loading and environment
# overrides are given. Add the two rules in the TODO: the release must be a git SHA (or still a
# `<placeholder>`), never `latest`; `allowed_cidr` is empty, a placeholder, or a valid CIDR, and a CIDR that
# admits more than one address requires `allow_public`. `ipaddress.ip_network(cidr, strict=True)` and its
# `prefixlen` / `max_prefixlen` do the work. Raise `ConfigError` with the key in the message; `main` turns it
# into exit status 2.
#
# **Task 4 - The deploy script and the task definition (20 min).** Implement `deploy_script(cfg)` to return a
# bash script with the steps of section 2.1 in a safe order: identity check, budget, repository (immutable,
# scan on push) and lifecycle policy, registry login, build and push `<registry>/<name>:<release>`, log group
# with retention, execution role and its managed policy, cluster, task definition, security group (an
# inbound rule only when `allowed_cidr` is set), service, wait. Use `_vars(cfg)` for every name. Then add
# `healthCheck` (probing `/readyz`) and `logConfiguration` (`awslogs`, with group, region and stream prefix)
# to `taskdef.template.json`.
#
# *Checkpoint:*
#
# ```bash
# cp deploy/config.example.toml deploy/config.toml
# FLOWGUARD_AWS_ACCOUNT_ID=000011112222 FLOWGUARD_RELEASE=$(git rev-parse --short=12 HEAD) \
#     python deploy/aws_deploy.py plan --config deploy/config.toml | bash -n && echo "syntax ok"
# ```
#
# (`bash -n` parses without executing. With placeholders such as `<VPC_ID>` still in the config, bash
# reports a syntax error near `<`; that is expected until you fill them or override them.)
#
# **Task 5 - The teardown (10 min).** Implement `teardown_script(cfg)`: every resource type the deploy
# creates, deleted in dependency order (service before cluster and security group; detach the policy before
# deleting the role; `--force` for a repository that holds images). The check pairs each `create` with its
# `delete`.
#
# **Task 6 - The gate (5 min).** Implement `signoff_status` and the refusal in `main`: with `--live`, refuse
# (exit 3, message on stderr) unless all required boxes are ticked, plus the public boxes when
# `allow_public`, and no `<placeholder>` is left in the config.
#
# **Task 7 - Check, and decide (5 min).**
#
# ```bash
# python ../../../wb.py check w6d5          # from the lab dir; or `python wb.py check w6d5` from the repo root
# python deploy/aws_deploy.py plan --config deploy/config.toml > deploy/rendered/deploy.sh
# python deploy/aws_deploy.py teardown --config deploy/config.toml > deploy/rendered/teardown.sh
# ```
#
# Read both scripts and `deploy/rendered/taskdef.json`. Then decide whether you will deploy. Not deploying
# is a complete outcome for this lesson.
#
# **Debugging guidance.**
# * `ConfigError ... release` with a valid-looking SHA: uppercase hex is rejected on purpose (git prints
#   lowercase).
# * `KeyError` in `string.Template.substitute`: a `${NAME}` in a template has no entry in `_vars`.
# * A check says the live run did not run "exactly the reviewed script": you are probably writing the
#   rendered files inside `deploy_script`, or building the script twice with different values.
# * `docker: port is already allocated`: something else uses port 8000; run `PORT=18080 bash deploy/run_local.sh`.
#
# **Optional extension: the live deployment (up to 60 min, only after you decided).** Follow
# `deploy/RUNBOOK.md` steps 5-9: fill the price table from the official pricing pages, sign in with SSO, tick
# `SIGNOFF.md`, run `plan --live`, verify (service stable, task healthy, the `model_loaded` log line in
# CloudWatch), then `teardown --live` the same day and work through the not-billing list. Record what you did
# and any surprises with `python wb.py note w6d5 "..."`.
#
# ---

# %%
# Run the automated checks on your guided lab.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w6d5")

# %% [markdown]
# ## 5. Independent challenge: review a colleague's deployment plan
#
# Transfer the same reasoning to a different service and team: [challenge/README.md](../labs/w6d5_cloud_deployment/challenge/README.md).
# You receive a plan for a two-day demo of a demand-forecast API with several cost and security problems, and
# hand back a corrected machine-readable plan and a written review with a go / no-go decision. No AWS access is
# involved. Do it without hints first.

# %%
!python wb.py check w6d5 --challenge

# %% [markdown]
# ---
#
#
# ### The challenge brief
#
#
# **Time:** 30-45 minutes, unassisted. **Scenario (SYNTHETIC):** a colleague asks you to review their
# plan for a two-day demo of a demand-forecast API before they run it tomorrow. Read
# `given/PLAN.md` and its machine-readable form `given/plan.json`.
#
# This is the transfer task: a different service, a different team, the same cost and security
# reasoning as the lab. You are reviewing a *plan*; nothing is deployed and no AWS access is involved.
#
# #### What to hand in
#
# 1. **`challenge/plan_fixed.json`** (the starter is an unchanged copy of the colleague's plan): a
#    corrected plan in the same schema that you would approve. Keep every key; change values; add keys
#    where the corrected plan needs them (for example a `budget` object or `teardown` entries).
# 2. **`challenge/REVIEW.md`**: the review you would send back, under the headings in the starter. For
#    each problem: what is wrong, the concrete risk or cost, and the change you require. End with a
#    decision (go / go with changes / no-go) and its conditions. Write it for the colleague: direct,
#    specific, not condescending.
#
# #### Acceptance criteria
#
# `python wb.py check w6d5 --challenge` checks the corrected plan and the review's structure:
#
# * credentials come from IAM Identity Center (`"mode": "sso"`) with a named, non-administrator
#   permission set or role; no key material, no stored credential file, no IAM user for deployment;
# * a budget exists before anything is created: `limit_usd` > 0 and at least one alert at or below
#   100 % of the limit;
# * the registry is immutable, scans on push, and the image tag is a git SHA;
# * the model artifacts are not public: either the bucket blocks public access and the task reads it with
#   its task role, or the bucket is gone and the model is baked into the image;
# * no inbound rule admits more than one address (no `0.0.0.0/0`, no `::/0`, every CIDR a `/32`);
# * logs have a retention between 1 and 30 days;
# * the teardown lists every resource in `resources`, by type and name;
# * the review has every heading filled in (no TODO) and the decision section states go, go with changes,
#   or no-go.
#
# The checks cannot judge whether your reasoning is good; the rubric in
# `solutions/labs/w6d5_cloud_deployment/assessment_answers.md` does (open it after you finish).

# %%
# Run the automated checks on your independent challenge.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w6d5", challenge=True)

# %% [markdown]
# ## 6. Progressive hints
#
# Open them in order, only when stuck for more than ten minutes:
# [hint 1: concept](../labs/w6d5_cloud_deployment/hints/hint1_concept.md) - [hint 2: approach](../labs/w6d5_cloud_deployment/hints/hint2_approach.md) -
# [hint 3: partial implementation](../labs/w6d5_cloud_deployment/hints/hint3_partial.md). The reference solution is in
# `solutions/labs/w6d5_cloud_deployment/` (open it after the checks pass or after a real attempt).
#
# ---
#
#
# Open one hint at a time, only after a real attempt.
#
# <details>
# <summary><b>Hint 1 concept</b></summary>
#
#
# * The deploy script is **a plan you can read**. Think of it as the experiment protocol you would get a
#   colleague to check before an expensive session: every step written out, in order, with the actual
#   values, before anything runs. `--live` then executes that same text, nothing else.
# * Order follows dependencies **and cost**: confirm who you are, then put the budget in place, then
#   create things that can bill. A service needs its task definition; the task definition needs the role
#   and the log group; the image must be pushed before the service starts it.
# * Teardown is the deploy in reverse dependency order, not in reverse line order: a cluster cannot be
#   deleted while a service is in it; a role cannot be deleted while a policy is attached; a security
#   group cannot be deleted while a task's network interface uses it.
# * "Not public" is a property of the **security group**, not of the IP address: a task can have a public
#   IP and still accept no connection at all.
# * A gate that can be passed without reading anything is not a gate: the flag says "I mean it", the
#   sign-off says "I read the briefing and accept the cost".
#
# </details>
#
# <details>
# <summary><b>Hint 2 approach</b></summary>
#
#
# **Task 3 (`load_config`).**
# 1. `release = str(cfg["app"].get("release", ""))`; reject `"latest"`; accept `RELEASE.match(...)` or
#    `PLACEHOLDER.fullmatch(...)`; otherwise `raise ConfigError("app.release ...")`.
# 2. For a non-empty, non-placeholder `allowed_cidr`, parse with `ipaddress.ip_network(cidr, strict=True)`
#    (catch `ValueError`); if `net.prefixlen < net.max_prefixlen` and not `allow_public`, raise.
#
# **Task 4 (`deploy_script`).** Write the script as one module-level string template with `${NAME}`-style
# placeholders (`string.Template`) and fill it with `_vars(cfg)` plus two extra values: the managed policy
# ARN and an `INGRESS` line that is either the `authorize-security-group-ingress` command or a comment.
# Bash's own `$` must be written `$$` inside a `string.Template`. For the security group, capture its id in
# a shell variable: `SG_ID=$$(aws ec2 create-security-group ... --query GroupId --output text)`.
#
# Task definition: add to the container definition
#
# * `"healthCheck"`: `command` (`["CMD-SHELL", "<a command that fails unless /readyz answers 200>"]`),
#   `interval`, `timeout`, `retries`, `startPeriod`;
# * `"logConfiguration"`: `"logDriver": "awslogs"` and `options` with `awslogs-group` (`/ecs/${NAME}`),
#   `awslogs-region` and `awslogs-stream-prefix` (required on Fargate).
#
# The image has Python but not curl, so the health-check command uses `python -c "import urllib.request; ..."`.
#
# **Task 5.** Same template approach. Delete: service (scale to 0, delete with `--force`, wait inactive),
# cluster, task-definition revisions (loop over `list-task-definitions --family-prefix`), security group
# (look its id up by name and VPC), log group, repository (`--force`), detach policy, delete role, budget.
#
# **Task 6.** A box is a list item `- [ ]` or `- [x]`. Track whether you are under a heading containing
# "public" while reading lines; skip those boxes unless `need_public`. Zero boxes found means incomplete.
#
# </details>
#
# <details>
# <summary><b>Hint 3 partial</b></summary>
#
#
# `load_config` validation (complete):
#
# ```python
#     release = str(cfg["app"].get("release", ""))
#     if release == "latest" or not (RELEASE.match(release) or PLACEHOLDER.fullmatch(release)):
#         raise ConfigError(f"app.release must be a git SHA (7-40 lowercase hex), not {release!r}")
#
#     cidr = str(cfg["network"].get("allowed_cidr", "") or "")
#     allow_public = bool(cfg["network"].get("allow_public", False))
#     if cidr and not PLACEHOLDER.fullmatch(cidr):
#         try:
#             net = ipaddress.ip_network(cidr, strict=True)
#         except ValueError as exc:
#             raise ConfigError(f"network.allowed_cidr is not a valid CIDR: {cidr!r}") from exc
#         if net.prefixlen < net.max_prefixlen and not allow_public:
#             raise ConfigError(f"network.allowed_cidr {cidr} is public access: set network.allow_public")
# ```
#
# The start and the end of the deploy template (fill in the middle, steps 2-7 of section 2.1). Write
# each command on one line in your file: the checks look at whole lines.
#
# ```python
# _DEPLOY = """\
# #!/usr/bin/env bash
# set -euo pipefail
# export AWS_PROFILE=${PROFILE} AWS_REGION=${REGION}
# aws sts get-caller-identity
# aws budgets create-budget --account-id ${ACCOUNT_ID} --budget file://deploy/rendered/budget.json --notifications-with-subscribers file://deploy/rendered/budget-notifications.json
# # ... repository, lifecycle, login, build, push, logs, role, cluster, task definition ...
# SG_ID=$$(aws ec2 create-security-group --group-name ${SG} --description "${NAME} service" --vpc-id ${VPC_ID} --query GroupId --output text)
# ${INGRESS}
# aws ecs create-service --cluster ${CLUSTER} --service-name ${SERVICE} --task-definition ${NAME} --desired-count 1 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_ID}],securityGroups=[$$SG_ID],assignPublicIp=ENABLED}"
# aws ecs wait services-stable --cluster ${CLUSTER} --services ${SERVICE}
# """
# ```
#
# `signoff_status` skeleton:
#
# ```python
# _BOX = re.compile(r"^\s*[-*]\s*\[( |x|X)\]\s*(.+?)\s*$")
#
# def signoff_status(path, need_public=False):
#     path = Path(path)
#     if not path.is_file():
#         return False, [f"{path} does not exist"]
#     unticked, in_public, seen = [], False, 0
#     for line in path.read_text().splitlines():
#         if line.lstrip().startswith("#"):
#             in_public = "public" in line.lower()
#             continue
#         ...   # match _BOX; skip public boxes unless need_public; count; collect unticked
#     if seen == 0:
#         return False, ["no check boxes found"]
#     return not unticked, unticked
# ```
#
# </details>

# %% [markdown]
# ## 7. Assessment
#
# assessment.md (section 7 of this notebook): reasoning questions, one design-choice explanation, a rubric, and a
# 10-15 minute system-design interview rep ("deploy this model service"). Model answers are in
# `solutions/labs/w6d5_cloud_deployment/assessment_answers.md`.
#
# ---
#
#
# ### Assessment questions
#
#
# Answer in writing (or aloud, recorded) before opening the model answers in
# `solutions/labs/w6d5_cloud_deployment/assessment_answers.md`. Aim for 25 minutes in total.
#
# #### Reasoning questions
#
# 1. **Order.** Why does the deploy script create the budget before the ECR repository, and the task
#    definition before the service? Give one consequence of each wrong order.
# 2. **Teardown.** The teardown deletes the service before the cluster and before the security group.
#    What happens, concretely, if you try them in the opposite order?
# 3. **Credentials.** A colleague says: "I rotate my access key every month, so storing it in
#    `~/.aws/credentials` is as safe as SSO." Give two ways in which it is still worse.
# 4. **Exposure.** The task has a public IP address, yet the lesson calls the default deployment "not
#    public". Explain, and state the one setting that would make it public.
# 5. **Tags.** Why is `latest` on an *immutable* repository not a fix for the `latest` problem?
# 6. **Health.** The task definition's health check calls `/readyz`, not `/healthz`. What failure would a
#    `/healthz` health check let through, and what would ECS do differently in each case?
# 7. **Cost reasoning.** Using only the structure in section 2.3 (no prices), which change cuts the cost of
#    a forgotten deployment more: halving the task size, or setting a budget alert that e-mails you after
#    one day? Explain.
#
# #### Design-choice explanation (write 150-250 words)
#
# 8. The planner prints a bash script, and `--live` runs **that exact text** (the checks compare them). An
#    alternative design calls the AWS SDK (boto3) directly from Python, step by step, with no script. Argue
#    for one of the two for *this* course project and name what you give up.
#
# #### Interview rep (10-15 minutes, system design, reduced assistance)
#
# > "You have a trained anomaly-detection model packaged as a Docker image that serves predictions over
# > HTTP. A plant team wants to try it for two weeks. Walk me through how you would deploy it on AWS, what
# > you would set up before the first request, and how you would know whether it is working."
#
# Talk for 10 minutes without notes (record yourself if you can), then score yourself with the rubric in
# the answers file. Do not look at the rubric before you have answered.
#
# #### Rubric for the open questions (self-assessment)
#
# | Score | Meaning |
# |---|---|
# | 2 | Correct, specific to this deployment, names a concrete consequence or mechanism |
# | 1 | Correct in general but vague ("it is more secure"), or misses the main mechanism |
# | 0 | Incorrect, or confuses two concepts (e.g. liveness with readiness, IP address with exposure) |
#
# Questions 1-7: 2 points each. Question 8: 4 points (2 for a defensible choice with a reason specific to
# the project, 2 for naming a real cost of that choice). 13 or more of 18: move on; below 10: redo the
# lab's tasks 4-6 without looking at your solution, a day later.

# %% [markdown]
# ## 8. Reflection and review
#
# **You should now be able to, without notes:** list the resources of a single-container deployment and the
# order to create and delete them; explain why short-lived SSO credentials replace access keys and where a
# secret must never be; explain immutable tags and why the git SHA is the tag; set up a budget alert before
# anything billable; keep a service unreachable by default; run the exact container locally; and write a
# dry-run-first deployment whose live mode is gated.
#
# **Reflection prompt (5 minutes, in `progress/notes.md`).** Which of the five classic mistakes (stored key,
# public bucket, open port, mutable tag, no teardown) would be easiest to make in a first cloud
# project (yours or a team's you know), and what would have caught it?
#
# **Retrieval question for later (w7d7).** *A task is running, `/healthz` answers 200, and the service is
# marked healthy, but every prediction is wrong. Which of this lesson's controls could have detected it, and
# which could not?* (Answer from memory first; the honest answer is "none of them detect wrong predictions",
# which is week 7's subject.)
#
# **Next.** [w6d6 - delivery and operational debugging](36_cd_ops_debugging.ipynb): promote an image
# by digest between environments, diagnose three seeded incidents from logs, and roll back.
#
# ---

# %% [markdown]
# ## Verification record
#
# Executed on 2026-11-22 in the authoring container (Python 3.13.18, Docker 29.10.0, FastAPI 0.165.0,
# uvicorn 0.54.0, pandas 3.0.5, numpy 2.5.3; image built with Python 3.12-slim from a local wheelhouse
# because the container's network intercepts TLS).
#
# | What | Command | Result |
# |---|---|---|
# | Lab checks against the reference | `python tools/verify_checks.py labs/w6d5_cloud_deployment --part lab` | reference passes (25 checks); 5 of 5 plausible wrong submissions rejected |
# | Challenge checks | `python tools/verify_checks.py labs/w6d5_cloud_deployment --part challenge` | reference passes; 4 of 4 wrong submissions rejected |
# | Starter fails | `python -m pytest labs/w6d5_cloud_deployment/checks -q` | 23 failed, 2 passed (the two hygiene checks pass on a clean starter by design) |
# | Local equivalent | `bash deploy/run_local.sh` (reference lab, wheelhouse) | ready, `/version` with release and environment, `model_loaded` logged, container removed |
# | Startup and memory | `solutions/.../record/record_local.py` | 5 runs: ready after 2.91-3.29 s, healthy after 5.57-5.74 s, 63.5-64.2 MiB |
# | Scripts parse | `python deploy/aws_deploy.py plan ... \| bash -n` (concrete values) | syntax ok for deploy and teardown |
# | Worked examples | both scripts in `example/` | outputs as quoted in section 3 |
# | AWS CLI syntax | read from the AWS CLI v2 example sources and botocore service models (GitHub), 2026-11-22 | operations, waiters (`services-stable`, `services-inactive`) and parameters used here exist in the current models |
# | **Not executed** | any AWS call; App Runner; the console | no account, no credentials, documentation and pricing sites unreachable |
#
# **Route choice.** ECS on Fargate was chosen over AWS App Runner and Lambda container images. App Runner
# would be simpler (public HTTPS endpoint, no security group or cluster), but its current availability to
# new customers could not be verified from any reachable source, so it is described as a conditional
# alternative in H13.2 rather than as the main route. Lambda container images impose an invocation model and
# an adapter for a long-running HTTP server, which would teach Lambda rather than containers.

# %% [markdown]
# ## Record your progress
#
# Tick only what is true. Passing the supplied checks is *guided practice*; mark *independent* only for work done without hints or solutions.

# %%
from mlcourse.progress import mark, note

# mark("w6d5", "reading")
# mark("w6d5", "guided")
# mark("w6d5", "independent")
# note("w6d5", "what tripped me up today")

