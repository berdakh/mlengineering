---
title: "Week 10 · Containers and CI"
parent: Weekly plan
nav_order: 10
---

# Week 10 · Containers and CI

**Goal:** set up VS Code locally, run the service in Docker, and test every push with GitHub Actions.

This is the week you leave Colab for your own computer. The code you wrote so far ran in one place; now you make
it run the same way everywhere: in a virtual environment on your laptop, in a Docker container, and on a fresh
GitHub machine for every push. All graded exercises still run in Google Colab (they check your files and
functions as text). The steps marked **💻 On your computer** install and run the real tools: VS Code, Python and
Git on Windows, macOS or Linux, Docker, and a GitHub repository of your own.

| # | Notebook | Kind | Time | Open |
|---|---|---|---|---|
| 37 | VS Code and a local setup | lesson | 90 min | [read](../notebooks/37_vscode_local_setup.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/37_vscode_local_setup.ipynb) |
| 38 | Docker from zero | lesson | 100 min | [read](../notebooks/38_docker_from_zero.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/38_docker_from_zero.ipynb) |
| 39 | Continuous integration with GitHub Actions | lesson | 90 min | [read](../notebooks/39_ci_github_actions.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/39_ci_github_actions.ipynb) |
| 40 | Lab: containerise the API and add CI | lab | 100 min | [read](../notebooks/40_lab_container_and_ci.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/40_lab_container_and_ci.ipynb) |

## Before you start

* Week 8 (packages, pytest) and Week 9 (FastAPI, testing APIs): this week ships that kind of service.
* Notebook 03 (terminal and Git), and a free GitHub account.
* For the local steps: a computer where you may install software (about 3 GB free for Docker and images). If you
  cannot install Docker, do every graded part in Colab and read the quoted outputs; you lose the practice, not
  the grade.

## What you will be able to do

* install VS Code, Python and Git on your system, clone a project, create and activate a virtual environment, and
  select it in VS Code for the editor, notebooks and tests;
* explain the PATH, diagnose the common setup errors, and find a bug with breakpoints;
* pin runtime dependencies in `requirements.txt` and keep the right files out of Git;
* write a cache-friendly, non-root Dockerfile with a health check and a `.dockerignore`, then build, run, map
  ports, pass settings and read logs;
* write a GitHub Actions workflow that tests on push and pull request across Python versions, read a failed run,
  and keep secrets and permissions safe;
* ship a model API with tests, an image and CI, as one small portfolio repository.

## Suggested pacing (6-8 hours)

| Session | Work | Time |
|---|---|---|
| 1 | Notebook 37, sections 1-4 (tools, PATH, venv, requirements); 💻 install Python, Git, VS Code | 60 min |
| 2 | Notebook 37, sections 5-6 and quiz; 💻 clone the course and run notebook 37 in VS Code | 50 min |
| 3 | Notebook 38, sections 1-3 (images, the Dockerfile, the cache); 💻 install Docker | 55 min |
| 4 | Notebook 38, sections 4-5 and quiz; 💻 build and run the scorer image | 55 min |
| 5 | Notebook 39, sections 1-4 (CI, YAML, a first workflow, the matrix) | 50 min |
| 6 | Notebook 39, sections 5-6 and quiz; 💻 push a repository and watch a red, then green, run | 45 min |
| 7 | Notebook 40, the lab, without looking at the solutions | 1.5 h |
| 8 | 💻 Lab on your computer and GitHub: build, run `(healthy)`, push, both jobs green; write the README | 45 min |

The 💻 parts take longer the first time (installers, restarts). If an install blocks you, keep going with the
Colab parts and come back to it: section 5 of notebook 37 and the tool guides list the usual fixes.

## Cost and safety

Everything this week is free: VS Code, Python, Git and Docker on your computer, and GitHub Actions on a public
repository. Nothing is deployed to the cloud. Never put passwords, tokens or keys in a Dockerfile, an image, a
workflow file or a commit; Week 11 covers where they go when you deploy.

## Tool guides

* [VS Code](../tools/vscode.html): install, interpreter, terminal, notebooks, tests, debugger, troubleshooting.
* [Docker](../tools/docker.html): images, Dockerfile instructions, build/run, ports, volumes, small and safe
  images, errors.
* [GitHub Actions](../tools/github-actions.html): workflow syntax, events, matrix, caching, secrets, branch
  protection, errors.
* Also useful: [pytest](../tools/pytest.html), [Python packaging](../tools/packaging.html) and
  [FastAPI](../tools/fastapi.html).

Previous week: [Week 9 · Serving models](week-9.html). Next week:
[Week 11 · Deploy and operate](week-11.html).
