---
title: Home
layout: home
nav_order: 1
---

# Applied ML Engineering
{: .fs-9 }

A 12-week, self-paced course in the engineering around the model: SQL, pandas, feature pipelines, honest
validation, testing, packaging, APIs, Docker, CI, cloud basics and monitoring. Every lesson is a notebook that
runs in Google Colab with one click and grades your exercises as you go.
{: .fs-6 .fw-300 }

[Start with notebook 01 in Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/01_welcome_and_colab.ipynb){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[See the weekly plan](weeks/){: .btn .fs-5 .mb-4 .mb-md-0 .mr-2 }
[View on GitHub](https://github.com/berdakh/mlengineering){: .btn .fs-5 .mb-4 .mb-md-0 }

---

## Who it is for

You have taken an introductory machine-learning course (for example *Learning from Data*) and can write basic
Python. You have not used SQL, Git, pytest, APIs, Docker or the cloud: the course starts each of them from the
beginning. Plan on **6-8 hours a week**, at your own pace. A Google account and a browser are enough for
Weeks 1-9 and 12; Weeks 10-11 add VS Code on your own computer.

The course teaches skills and builds a portfolio project; it does not promise a job.
[Before you start](guides/before-you-start.html) has a short self-check.

## The twelve weeks

<img src="assets/diagrams/course-roadmap.svg" alt="The 12-week roadmap" style="max-width:100%">

| Week | You will be able to |
|---|---|
| [1 · Your engineering workbench](weeks/week-1.html) | Work confidently in Colab, write clean Python, and use the terminal and Git |
| [2 · SQL from zero](weeks/week-2.html) | Answer business questions from a relational database with SELECT, GROUP BY and JOIN |
| [3 · Advanced SQL and pandas](weeks/week-3.html) | Use window functions and CTEs, do the same work in pandas, and clean messy data with quality checks |
| [4 · From data to features](weeks/week-4.html) | Explore a dataset with purpose and turn it into features with scikit-learn pipelines |
| [5 · From theory to practice: framing, baselines, metrics](weeks/week-5.html) | Frame a business problem as an ML task, beat honest baselines, and pick metrics and thresholds from costs |
| [6 · Validation and leakage](weeks/week-6.html) | Validate the way the model will be used and find leakage before it fools you |
| [7 · Models, uncertainty and error analysis](weeks/week-7.html) | Compare models fairly with uncertainty, analyse errors, and start the project |
| [8 · Code you can trust](weeks/week-8.html) | Turn notebook code into a tested, configurable Python package |
| [9 · Serving models](weeks/week-9.html) | Save models safely and serve predictions through a tested FastAPI service |
| [10 · Containers and CI](weeks/week-10.html) | Set up VS Code locally, run the service in Docker, and test every push with GitHub Actions |
| [11 · Deploy and operate](weeks/week-11.html) | Deploy safely, log and monitor a model, and tell input drift from real degradation |
| [12 · Capstone and career](weeks/week-12.html) | Finish and present the project, and practise for interviews |

Each week has three lessons and one graded lab. A fault-detection project on real sensor data (SKAB, an
educational prototype) runs through notebooks [28](notebooks/28_project_m1_fault_detection.html),
[36](notebooks/36_project_m2_prediction_api.html), [44](notebooks/44_project_m3_monitoring.html) and
[45](notebooks/45_capstone_build.html).

## How a lesson works

| Part | What you do |
|---|---|
| **Why** | Read the problem this solves on the job |
| **Idea** | Read the concept in plain language, often with a diagram |
| **See it** | Run a worked example |
| **Try it** | Change something small and predict the result |
| **Exercise** | Write the code; the next cell grades it: ✅ passed, or ❌ what is wrong and a hint |

Each lesson ends with a quiz whose wrong answers explain the misconception, a recap, an "on the job" paragraph
and links for going further. Solved copies of every notebook are in
[`solutions/notebooks/`](https://github.com/berdakh/mlengineering/tree/main/solutions/notebooks): open one only
after a real attempt.

## Everything else

| | |
|---|---|
| [Notebooks](notebooks/) | All 48 notebooks, readable here and runnable in Colab |
| [Tool guides](tools/) | A beginner's reference for every tool: Colab, Git, SQL, pandas, pytest, FastAPI, Docker, AWS and more |
| [Handbook](handbook/) | Deeper reading: 55 sections on the ideas behind the lessons |
| [Guides](guides/) | Setup, troubleshooting, glossary, the project, interview practice, status |
| [Advanced track](advanced/) | 48 more demanding sessions that take the project much further, for after the course |

Code is MIT licensed; prose is CC BY 4.0. The SKAB dataset (GPL-3.0) is downloaded, never redistributed.
