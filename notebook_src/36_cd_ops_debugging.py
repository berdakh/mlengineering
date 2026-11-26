# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/36_cd_ops_debugging.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 36 · Delivery and operational debugging; project milestone 3
#
# **Week 6 · day 6 · 2 h essential path + up to 1 h optional** · lab files: [`labs/w6d6_cd_ops_debugging/`](../labs/w6d6_cd_ops_debugging/)
#
# **Objective.** Promote an image by tag, configure through environment, read logs to diagnose seeded failures, and roll back.

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
    if not Path("/content/mlengineering").exists():
        subprocess.run(["git", "clone", "--depth", "1",
                        "https://github.com/berdakh/mlengineering.git",
                        "/content/mlengineering"], check=True)
    os.chdir("/content/mlengineering")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "-r", "requirements.txt"], check=True)

REPO_ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents]
                 if (p / "src" / "mlcourse").is_dir())
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "src"))
print("repo root:", REPO_ROOT)

# %% [markdown]
# **Status: Execution verified** (see the verification record at the end). Everything runs locally with
# Docker; nothing touches a cloud account.
#
# | | |
# |---|---|
# | **Primary objective** | Promote an image by digest between environments, configure the service through its environment, diagnose three seeded production incidents from logs and container state, and fix each one correctly: roll back when the image is at fault, revert configuration when it is not. |
# | **Deliverable** | Startup configuration validation (`flowguard.settings`), a digest-pinned rollback tool (`ops/rollback.py`), and `DEBUG_LOG.md` with three complete incident write-ups quoting real evidence. Milestone 3: the same practices in your project repository. |
# | **Completion criteria** | `python wb.py check w6d6` passes; all three incidents diagnosed and fixed in your local environments, with `fgops.py history` showing the recovery; you can explain without notes why a rollback fixed one incident and would not have fixed the other two. |
# | **Handbook** | [H14.2 Delivery, promotion, rollback](../docs/handbook/ch14_cicd/h14_2_delivery_promotion_rollback.md), [H15.2 Operational debugging](../docs/handbook/ch15_logging_monitoring_updates/h15_2_operational_debugging.md) |
#
# ---

# %% [markdown]
# ## 1. Purpose
#
# **What you will learn.** How a release travels from a build to production without being changed on the
# way (build once, promote the digest), how the same image behaves differently through its configuration,
# and how to debug a running service methodically: observe, form competing hypotheses, run the one test
# that separates them, fix, verify, write it down. You will meet three incidents that look alike from the
# outside ("production is not working") and have three different correct fixes.
#
# **Why an applied ML engineer needs it.** Model services fail more often through delivery and configuration
# than through the model: a bundle edited by hand, a path pointing at a model version the image does not
# contain, a memory limit set from a guess. On-call work and interview debugging questions test the same
# skill: reading evidence before acting, and knowing whether "roll back" is the fix or a way to make things
# worse.
#
# **Prerequisites.**
# * [w6d5](35_cloud_deployment.ipynb) (the container, JSON logs, `/version` with the release;
#   this lab ships the same service snapshot, package 0.6.0).
# * [w5d2](26_artifacts_versioning.ipynb): bundles verified by checksum (incident 2 depends on it).
# * Docker Engine running, with permission to run containers. Ports 5005, 8101 and 8102 on 127.0.0.1 free.
#   About 1 GB of disk for images.
#
# **Time budget (2 h essential + optional extension up to 1 h).**
#
# | Activity | Minutes |
# |---|---|
# | Read sections 2 and 3, run the worked example | 30 |
# | Lab tasks 1-3: settings validation, first releases, promotion | 30 |
# | Lab tasks 4-5: rollback tool, three incidents and the debugging log | 45 |
# | Start the challenge (postmortem) | 5 |
# | Assessment and reflection | 10 |
# | *Optional extension*: finish the postmortem; milestone 3 in your project repository (section 4, task 6) | up to 60 |
#
# ---

# %% [markdown]
# ## 2. Conceptual explanation
#
# ### 2.1 Intuition: build once, move the same bytes
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-36-01.svg" alt="Diagram 1 of notebook 36" style="max-width:100%">
#
# The image is the unit of release. Staging and production run **the same digest** with different
# environment files. If production ran a rebuild of the same commit instead, "tested in staging" would be a
# claim about a different artifact: rebuilds are not byte-identical. In the authoring run, three builds of the
# same unchanged source tree produced three different digests (`sha256:1672158c...`, `sha256:4a558673...`,
# `sha256:78b580ec...`), because layer metadata such as timestamps differs between builds.
#
# ### 2.2 Precise terms
#
# * **Continuous delivery** keeps every change releasable and makes deploying a routine, reviewed step.
#   **Continuous deployment** deploys every change that passes the pipeline automatically. Both rest on the
#   same mechanics; they differ in who presses the button.
# * **Tag versus digest.** A tag (`flowguard:1a2b3c4d5e6f`) is a name a registry *can* move (unless the
#   repository is immutable, w6d5). A digest (`flowguard@sha256:...`) is the hash of the image manifest: it
#   cannot point at different content. Deploying by digest makes the deployment record exact.
# * **Promotion.** Deploying to the next environment the digest that the previous environment ran
#   successfully. It never rebuilds. `fgops.py promote` refuses unless the source environment's current
#   deployment is `good`.
# * **Release history.** An append-only record of deployments: environment, release, digest, time, and
#   outcome (`good`, `failed`, `rolled_back`). It is the first thing to read in an incident.
# * **Rollback.** Redeploying the most recent *earlier* good digest. It undoes an image change. It does
#   nothing for a configuration change made with the same image.
# * **Configuration validation at startup.** The service checks its environment once and exits with one
#   clear error if it is wrong (fail fast), instead of running with a silently wrong setting.
# * **Liveness versus readiness, again.** A container can be running and live (`/healthz` 200) and not ready
#   (`/readyz` 503, model not loaded). Deployment tooling must wait for readiness, and should watch for
#   longer than one health-check cycle (incident 3).
#
# ### 2.3 Configuration: validate format at startup, existence by readiness
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-36-02.svg" alt="Diagram 2 of notebook 36" style="max-width:100%">
#
# Two layers, on purpose. A **typo** in a variable name or a malformed value is a configuration bug that
# can never fix itself: stop at once, with the variable's name in the error. A **missing or corrupt model**
# is about the state of a file: the process stays up, keeps logging, and tells the platform through
# readiness that it should not receive traffic. Both are visible in the first seconds of a deployment, which
# is exactly where you want them.
#
# ### 2.4 The debugging method
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-36-03.svg" alt="Diagram 3 of notebook 36" style="max-width:100%">
#
# The habit that matters most is the first box. In each incident of this lab, `fgops.py history` and the
# service's own startup log lines identify the change within a minute; most wasted time in real incidents is
# spent changing things before reading what already happened.
#
# ### 2.5 Connection to other domains
#
# A well-run lab experiment never rebuilds its software between the dry run and the real session: it runs
# the build that was tested. That is promotion by digest. When a session fails, a careful experimenter
# checks what changed since the last good session (the settings file, the hardware configuration, the
# software build) before touching anything: that is reading the release history first. And they separate
# "the software is wrong" from "the configuration is wrong" before deciding between going back to the last
# build and fixing a settings file: that is the rollback-versus-revert decision of this lesson.
#
# ### 2.6 An industry example
#
# A team changes a feature-store endpoint in production through an environment variable; a model service
# starts answering with defaults for a missing feature. The on-call engineer sees errors start at the time of
# a recent image release and rolls back the image; nothing improves, because the image was never the cause,
# and the rollback has now also removed an unrelated fix. The release history would have shown that the last
# change was configuration, not code. (Illustrative composite, not a cited incident.)
#
# ### 2.7 Limitations and common misconceptions
#
# * **"Rollback is always safe."** It is safe when the previous image is compatible with the current data,
#   configuration and clients. A rollback across a schema or API change can break callers. And it does not
#   fix configuration incidents (incidents 1 and 3 here).
# * **"The deployment succeeded, so the service is fine."** Incident 3 answered `/readyz` with 200 for a few
#   seconds and was then killed. A deployment should count as good only after the service stays healthy for
#   longer than its failure modes take to appear.
# * **"Logs show errors, so look for ERROR lines."** The OOM-killed container's last log line is a normal
#   startup message: the kernel killed the process before it could log anything. Container state
#   (`OOMKilled`, exit code 137 = 128 + SIGKILL) is evidence logs cannot provide.
# * **"Healthy service, correct model."** None of this week's signals say whether predictions are right
#   (the challenge's incident; week 7).
# * **This is a local simulation.** Two containers on one machine stand in for environments; real
#   environments differ in data, traffic and permissions, and "staging passed" means less than it does here.
#
# ---

# %% [markdown]
# ## 3. Worked example: triage before you touch anything
#
# `example/triage_logs.py` generates a SYNTHETIC JSON-lines log from a *different* service (a product
# recommendation API, 40 minutes at about 5 requests per second, a new release `r2` at 10:20) and answers the
# four first questions of any incident: what changed, how each release behaves, what the first error is, and
# whether the effect is everywhere or in a slice.

# %%
!python labs/w6d6_cd_ops_debugging/example/triage_logs.py

# %% [markdown]
# Output (executed 2026-11-22, seed 7, reproducible):
#
# ```
# SYNTHETIC log: 12256 lines
#
# 1. changes:
#    2026-03-10T10:00:00+00:00  deploy r1
#    2026-03-10T10:20:00+00:00  deploy r2
# 2. behaviour by release:
#    r1:  5909 requests, 5xx  0.00%, p50  34.9 ms, p95  62.1 ms
#    r2:  5936 requests, 5xx  6.50%, p50  53.1 ms, p95 251.0 ms
# 3. errors:
#    first ERROR at 2026-03-10T10:20:00.539926+00:00 (0.5 s after the deploy at 2026-03-10T10:20:00+00:00): feature_store_timeout release=r2
#      386 x feature_store_timeout (release r2)
# 4. 5xx rate by endpoint and release:
#    r1 /recommend   0.00% of 4719
#    r1 /similar     0.00% of 1190
#    r2 /recommend   8.14% of 4741
#    r2 /similar     0.00% of 1195
# ```
#
# **Interpretation.** Within seconds of `r2` going out, `/recommend` (and only `/recommend`) starts failing at
# 8.1 % with feature-store timeouts, and its p95 latency hits the 250 ms timeout. `/similar` is unaffected.
# That points at a change in `r2`'s `/recommend` path that calls the feature store, makes rollback to `r1`
# the right mitigation (the image changed; nothing else did), and gives the follow-up a precise target.
# Notice what the script does *not* do: it does not restart anything. Every number above comes from reading.
#
# **Key code decisions.** One JSON object per line (so the triage is a `json.loads` per line, no regex); the
# release id on every line (so behaviour can be split by release); deploys logged as events (so "what
# changed" is a query, not a memory). The lab's service logs the same way.
#
# ---

# %% [markdown]
# ## 4. Guided lab
#
# Work in `labs/w6d6_cd_ops_debugging/lab/`. Run every command from there. Files you edit:
# `service/src/flowguard/settings.py` (task 1), `ops/rollback.py` (task 4) and `DEBUG_LOG.md` (task 5).
# `ops/fgops.py` is given: read `deploy`, `promote` and `run_args` before task 2.
#
# **Task 1 - Startup configuration validation (15 min).** Implement `load_settings` as specified in its
# docstring. The service calls it before anything else (`flowguard/serve.py`), so until it works the
# container cannot start.
#
# ```bash
# python ../../../wb.py check w6d6 2>&1 | grep -E "settings|passed|failed"
# ```
#
# *Checkpoint:* the `settings` checks pass. In particular, `FLOWGUARD_MODEL_DlR` (lower-case L instead of I)
# must be an error that names it: an unknown variable is almost always a typo.
#
# **Task 2 - Registry, first release, promotion (10 min).**
#
# ```bash
# python ops/fgops.py registry-up
# python ops/fgops.py build                     # tags with `git rev-parse --short=12 HEAD`
# python ops/fgops.py deploy staging <release printed by build>
# python ops/fgops.py promote                   # staging -> production, same digest
# python ops/fgops.py status
# python ops/fgops.py history
# ```
#
# *Checkpoint:* both environments `running ... health=healthy readyz=200`, and `/version` shows the same
# release with `"environment":"staging"` and `"environment":"production"`. Behind a TLS-intercepting proxy,
# fill `service/wheels/` and export `PIP_INSTALL_OPTS` first (as in w6d5, task 1).
#
# **Task 3 - A second release (5 min).** Make a small real change (for example bump `__version__` in
# `service/src/flowguard/__init__.py` to `0.6.1`), commit it, then `build`, `deploy staging <new release>`,
# `promote`. *Checkpoint:* `history production` shows two good releases with different digests. Run `docker
# images 127.0.0.1:5005/flowguard --digests` and note that each release is one digest.
#
# **Task 4 - The rollback tool (10 min).** Implement `select_rollback_target` and `image_reference` in
# `ops/rollback.py` to the contract in its docstring; `main` is given. Then:
#
# ```bash
# python ops/rollback.py production             # plan only: shows the target and the docker command
# ```
#
# *Checkpoint:* the target is your *first* release, the command ends in `@sha256:...`, and the rollback checks
# pass. Do not apply it.
#
# **Task 5 - Three incidents (35 min).** Start each one, diagnose it from evidence only, fix it, verify, and
# write it up in `DEBUG_LOG.md` (fields as in the template) **before** starting the next:
#
# ```bash
# python ops/fgops.py scenario 1      # then diagnose and fix; then scenario 2; then scenario 3
# ```
#
# Evidence you can use (and nothing else; do not read `fgops.py scenario` until you are done):
#
# ```bash
# python ops/fgops.py status
# python ops/fgops.py history production
# docker logs fgops-production 2>&1 | grep -v uvicorn.access | tail -20
# docker inspect -f '{{.State.Status}} oom={{.State.OOMKilled}} exit={{.State.ExitCode}}' fgops-production
# git diff -- ops/env                  # configuration is version-controlled: what changed?
# ```
#
# Fix tools: `python ops/rollback.py production --apply` (image problems), `python ops/fgops.py reset`
# followed by `python ops/fgops.py deploy production <current release>` (configuration problems).
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/labs/w6d6_cd_ops_debugging/figures/readiness_timeline.svg" alt="Production readiness through the three incidents of the authoring run: 503 during the bad promotion and the MODEL_DIR incident, ready then no answer during the memory incident" width="100%">
#
# *Figure 1. Production `/readyz` polled every 0.25 s during the authoring replay of all three incidents
# (real run, 2026-11-22; `solutions/.../record/record_incidents.py`). Two incidents fail loudly (503 from the
# first second); the memory incident answers 200 for about 3 s and then stops answering. Short "no answer"
# gaps are container replacements. Do not use this figure to solve the incidents; it shows symptoms only.*
#
# **Debugging guidance.**
# * If `status` shows `no container`, the deployment's container exited: `docker ps -a` and `docker inspect`
#   still show the stopped container until the next deploy replaces it.
# * The access log is noisy (the deploy tool polls `/readyz`); filter it out before reading.
# * If a fix "works" but `history` still shows `failed` as the current entry, you fixed the container by hand
#   outside the tool: redeploy through `fgops.py` so the record is true.
# * When finished: `python ops/fgops.py cleanup` removes every container, the registry and the images.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/labs/w6d6_cd_ops_debugging/figures/deployment_history.svg" alt="Release history of the authoring run: staging and production deployments over time, coloured good, failed or rolled back" width="100%">
#
# *Figure 2. The release history at the end of the authoring replay (real). The hotfix release `6c7f7b` failed
# in staging and was promoted by hand anyway; rollback then returned production to `b7c8d9`. The two later
# failures are the same digest `b7c8d9` with broken configuration: rolling back to `a1b2c3` would have been the
# wrong fix.*
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/labs/w6d6_cd_ops_debugging/figures/time_not_ready.svg" alt="Seconds production was not ready per incident in the scripted replay: 20, 20 and 13" width="100%">
#
# *Figure 3. Time production was not ready per incident in the scripted replay (real; the script applied each fix
# immediately). With a person diagnosing, add the minutes the diagnosis takes: the method in section 2.4 is
# what keeps those minutes short.*
#
# **Task 6 (optional extension) - Milestone 3 in your project.** In your `flowguard` project repository:
# validate configuration at startup, tag images with the git SHA, deploy by digest, keep an append-only
# release history, and write a one-page RUNBOOK with your three most likely incidents and their fixes. Submit
# the repository link with `DEBUG_LOG.md` for review.
#
# ---

# %%
# Run the automated checks on your guided lab.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w6d6")

# %% [markdown]
# ## 5. Independent challenge: a blameless postmortem
#
# [challenge/README.md](../labs/w6d6_cd_ops_debugging/challenge/README.md): an incident in a different service (a demand forecaster) whose
# release passed every operational check and was still wrong for 47 minutes. Write the postmortem. Do it
# without hints first.

# %%
!python wb.py check w6d6 --challenge

# %% [markdown]
# ---
#
#
# ### The challenge brief
#
#
# **Time:** 30-40 minutes, unassisted. Read `given/INCIDENT_TIMELINE.md`:
# an incident in a *different* service (a demand forecaster) whose release passed every check and still
# produced wrong predictions for 47 minutes. Write the postmortem in `challenge/POSTMORTEM.md` (the
# starter has the headings).
#
# This incident is the mirror image of the lab's: there, the service was visibly broken (503, OOM);
# here, it was healthy by every operational signal and wrong. Your postmortem should make clear why the
# existing checks could not catch it, and what would.
#
# #### Acceptance criteria
#
# `python wb.py check w6d6 --challenge` checks structure, facts and tone; the rubric in
# `solutions/labs/w6d6_cd_ops_debugging/assessment_answers.md` judges the reasoning:
#
# * every heading of the starter is present and filled in (no TODO);
# * **Impact** states the duration of customer impact in minutes, measured from when production started
#   serving the release to when the rollback completed, and quantifies the business effect with the
#   numbers from the timeline;
# * **Timeline** has at least eight entries, uses only times that appear in the given timeline, and
#   includes the start and the end of impact;
# * **Action items** is a table with columns Action, Type, Owner, Due and at least four rows; Type is
#   one of prevent, detect, mitigate, process; at least one item detects and one prevents; every item has
#   an owner (a role or team is fine) and a due date;
# * blameless language: no "human error", "should have", "careless", "blame", "fault", "negligent",
#   and no person is named in **Root cause** or **Contributing factors**. Describe the system and the
#   conditions that made the mistake possible and invisible, not who made it.

# %%
# Run the automated checks on your independent challenge.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w6d6", challenge=True)

# %% [markdown]
# ## 6. Progressive hints
#
# [hint 1: concept](../labs/w6d6_cd_ops_debugging/hints/hint1_concept.md) - [hint 2: approach](../labs/w6d6_cd_ops_debugging/hints/hint2_approach.md) -
# [hint 3: partial implementation](../labs/w6d6_cd_ops_debugging/hints/hint3_partial.md). The reference solution, including a reference
# `DEBUG_LOG.md` with the authoring run's real evidence, is in `solutions/labs/w6d6_cd_ops_debugging/`.
# Open it only after your own write-ups are done.
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
# * **Settings.** Validate *names* first (an unknown `FLOWGUARD_*` variable is a typo until proven
#   otherwise), then each value's *format*. Do not check whether the model directory exists: that is the
#   readiness probe's job, and the container should keep running and logging when it is not ready.
# * **Rollback target.** "Current" is a fact about time, not about list position: the latest
#   `deployed_at` for that environment. The target is the newest *earlier* entry that was `good` *and* runs
#   a different image. If the image that is running now was good before, a rollback to it changes nothing:
#   that situation is a configuration incident.
# * **Digest, not tag.** A rollback deploys exactly what ran before. Only a digest says that.
# * **Incidents.** Each of the three has one change behind it. Find the change first (history, the startup
#   log line, `git diff -- ops/env`), then decide whether the change was the image or the configuration.
#   Logs tell you what the process saw; `docker inspect` tells you what happened to the process.
#
# </details>
#
# <details>
# <summary><b>Hint 2 approach</b></summary>
#
#
# **`load_settings(env)`**
# 1. `unknown = sorted(k for k in env if k.startswith(PREFIX) and k not in KNOWN)`; raise if any.
# 2. A helper `_required(env, name)` that strips the value and raises `SettingsError(f"{name} is required ...")`.
# 3. Check each required value: environment in `ENVIRONMENTS`; model dir starts with `/`; release matches
#    `^[0-9a-f]{7,40}$`.
# 4. Optional values with defaults: log level (`.upper()`, must be in `LOG_LEVELS`), port (`int(...)` inside
#    `try`, then range 1-65535). Every message starts with the variable's name.
#
# **`select_rollback_target(history, env)`**
# 1. Filter to the environment, sort by `deployed_at`. Empty: raise `RollbackError`.
# 2. `current = entries[-1]`.
# 3. Walk the earlier entries from newest to oldest; return the first with status `good` and a digest
#    different from `current["digest"]`.
# 4. None found: raise `RollbackError` with a message that suggests checking the configuration.
#
# **`image_reference(entry)`**: check `entry["digest"].startswith("sha256:")`, return `f"{image}@{digest}"`.
#
# **The incidents.** For each: run `status` and `history production` first and write down what changed and
# when. Then read the production log without access lines. Then, if the container is not running,
# `docker inspect` its state. Then decide: if the current deployment's digest differs from the last good
# one, the image changed; if the digest is the same, something outside the image changed (`git diff -- ops/env`).
#
# </details>
#
# <details>
# <summary><b>Hint 3 partial</b></summary>
#
#
# `settings.py` (the first half; the remaining checks follow the same pattern):
#
# ```python
# def _required(env, name):
#     value = env.get(name, "").strip()
#     if not value:
#         raise SettingsError(f"{name} is required but not set")
#     return value
#
#
# def load_settings(env):
#     unknown = sorted(k for k in env if k.startswith(PREFIX) and k not in KNOWN)
#     if unknown:
#         raise SettingsError(f"unknown variable(s) {', '.join(unknown)}; expected only {', '.join(KNOWN)}")
#     environment = _required(env, "FLOWGUARD_ENV")
#     if environment not in ENVIRONMENTS:
#         raise SettingsError(f"FLOWGUARD_ENV must be one of {', '.join(ENVIRONMENTS)}, got {environment!r}")
#     model_dir = _required(env, "FLOWGUARD_MODEL_DIR")
#     if not model_dir.startswith("/"):
#         raise SettingsError(f"FLOWGUARD_MODEL_DIR must be an absolute path, got {model_dir!r}")
#     ...  # FLOWGUARD_RELEASE, FLOWGUARD_LOG_LEVEL (default INFO), FLOWGUARD_PORT (default 8000)
#     return Settings(environment=environment, model_dir=model_dir, release=release,
#                     log_level=log_level, port=port)
# ```
#
# `rollback.py`:
#
# ```python
# def select_rollback_target(history, env):
#     entries = sorted((e for e in history if e.get("env") == env), key=lambda e: e["deployed_at"])
#     if not entries:
#         raise RollbackError(f"{env} has no deployments")
#     current = entries[-1]
#     for entry in reversed(entries[:-1]):
#         ...   # good, and a different digest from current
#     raise RollbackError(...)
# ```
#
# **Incident triage, the three questions that separate them:**
#
# | Question | How to answer it |
# |---|---|
# | Did the image change? | `history production`: compare the current digest with the previous good one |
# | What did the process report at startup? | `docker logs fgops-production 2>&1 \| grep -v uvicorn.access \| head` |
# | Is the process still alive, and if not, why? | `docker inspect -f '{{.State.Status}} oom={{.State.OOMKilled}} exit={{.State.ExitCode}}' fgops-production` |
#
# </details>

# %% [markdown]
# ## 7. Assessment
#
# assessment.md (section 7 of this notebook): reasoning questions, one design-choice explanation, a rubric, and a 10-15
# minute debugging-narrative interview rep. Model answers: `solutions/labs/w6d6_cd_ops_debugging/assessment_answers.md`.
#
# ---
#
#
# ### Assessment questions
#
#
# Answer in writing (or aloud, recorded) before opening
# `solutions/labs/w6d6_cd_ops_debugging/assessment_answers.md`. About 25 minutes.
#
# #### Reasoning questions
#
# 1. **Rebuilds.** Three builds of the same commit gave three different digests in the authoring run. Why
#    does that matter for "it passed in staging"? What is promotion doing instead of rebuilding?
# 2. **Rollback scope.** For each of the three lab incidents, say whether `rollback.py --apply` would have
#    fixed it, and what it would have done instead.
# 3. **Two validation layers.** Why does the service *exit* on `FLOWGUARD_MODEL_DlR=...` but *keep running,
#    not ready* when `FLOWGUARD_MODEL_DIR` points at a directory that does not exist?
# 4. **Exit 137.** The OOM-killed container's logs end with a normal startup line. Where does the evidence
#    for the cause come from, and why is it not in the logs?
# 5. **"Good" too early.** The memory incident briefly answered `/readyz` with 200. What rule for marking a
#    deployment good would have caught it during the deployment, and what does that rule cost?
# 6. **History file.** Why does `select_rollback_target` sort by `deployed_at` instead of trusting list order?
#    Give a realistic way the list could be out of order.
#
# #### Design-choice explanation (150-250 words)
#
# 7. The deploy tool pins production to `image@sha256:...` and stores configuration in env files outside the
#    image. A colleague proposes baking the production environment file *into* a separate "production image"
#    so that "the image is the whole truth". Argue for or against for this service, and name the strongest
#    point of the side you reject.
#
# #### Interview rep (10-15 minutes, debugging narrative, reduced assistance)
#
# > "Tell me about a time a system you were responsible for failed in a way that was hard to diagnose. What
# > did you see first, what did you think it was, what did you check, and what was it really?"
#
# Answer with one of this lab's incidents (or a real one from a system you have worked on) in the structure
# symptom - first hypothesis - the test that changed your mind - cause - fix - what you changed afterwards.
# Speak for 5 minutes, then answer the follow-up "how would you make sure it cannot happen again?" for 2
# minutes. Score yourself with the rubric in the answers file afterwards.
#
# #### Rubric (self-assessment)
#
# | Score | Meaning |
# |---|---|
# | 2 | Correct, uses the mechanism (digest, readiness, cgroup OOM, append-only history) and a concrete consequence |
# | 1 | Right conclusion with a vague reason |
# | 0 | Wrong, or treats rollback as a universal fix |
#
# Questions 1-6: 2 points each; question 7: 4 points. 12+ of 16: move on. Below 9: redo task 5 with the
# scenarios in a different order a day later, without your DEBUG_LOG open.

# %% [markdown]
# ## 8. Reflection and review
#
# **You should now be able to, without notes:** explain why environments run digests and promotion never
# rebuilds; validate configuration at startup with errors that name the variable; read a release history and
# a container's state to locate a change; separate image incidents from configuration incidents and choose
# rollback or revert accordingly; and write an incident up so that someone else can act on it.
#
# **Reflection prompt (5 minutes, `progress/notes.md`).** Which incident took you longest, and what was the
# first piece of evidence that, in hindsight, already contained the answer?
#
# **Retrieval question for later (w7d7).** *Production is unhealthy right after a deployment. List, in order,
# the first four things you look at, and for each say which kind of cause it would reveal or rule out.*
#
# **Next.** w6d7: the week's review day (retrieval sheet and a timed debugging interview set); then week 7,
# [service logging and metrics](37_service_logging_metrics.ipynb), which adds the signals that would have caught the
# challenge's incident.
#
# ---

# %% [markdown]
# ## Verification record
#
# Executed on 2026-11-22 in the authoring container (Python 3.13.18, Docker 29.10.0, local `registry:3`;
# image Python 3.12-slim built from a local wheelhouse because the network intercepts TLS).
#
# | What | Command | Result |
# |---|---|---|
# | Lab checks | `python tools/verify_checks.py labs/w6d6_cd_ops_debugging --part lab` | reference passes (24 checks; the optional Docker test skipped); 6 of 6 wrong submissions rejected |
# | Challenge checks | `python tools/verify_checks.py labs/w6d6_cd_ops_debugging --part challenge` | reference passes; 4 of 4 wrong submissions rejected |
# | Starter fails | `python -m pytest labs/w6d6_cd_ops_debugging/checks -q` | 24 failed, 1 skipped (the optional Docker test) |
# | Optional live check | `WB_DOCKER=1 ... pytest .../test_live_docker.py` against the reference | 1 passed in 51 s (build, deploy, promote, scenario 2, rollback, readiness 200, cleanup) |
# | Full replay | `record_incidents.py` | all three incidents reproduced and fixed; log lines and history quoted in the reference `DEBUG_LOG.md` and figures 1-3 |
# | Memory incident | `docker run --memory 64m` three times | `exited oom=true exit=137` each time; at 96 MiB the idle service used 63.7 MiB |
# | Rebuild digests | three builds of the same tree | three different digests (section 2.1) |
# | Worked example | `example/triage_logs.py` | output as quoted in section 3 |
# | Clean-up | `fgops.py cleanup`; `docker ps -a` | no `fgops-*` containers or `127.0.0.1:5005/flowguard` images left |

# %% [markdown]
# ## Record your progress
#
# Tick only what is true. Passing the supplied checks is *guided practice*; mark *independent* only for work done without hints or solutions.

# %%
from mlcourse.progress import mark, note

# mark("w6d6", "reading")
# mark("w6d6", "guided")
# mark("w6d6", "independent")
# note("w6d6", "what tripped me up today")

