---
title: Before you start
parent: Guides
nav_order: 1
---

# Before you start
{: .no_toc }

1. TOC
{:toc}

---

## Who this course is for

You have taken **one introductory machine-learning course** (for example Caltech's *Learning from Data*) and you
can program in **basic Python**. You may have trained a model in a notebook for a class or a research project.
What you have not done yet is the work around the model that teams do every day: pulling data with SQL,
cleaning it, building features without leakage, testing code, serving predictions, shipping containers and
watching a model in production. That is what this course teaches, starting each tool from zero.

## What is assumed, and what is not

| Assumed | Not assumed (taught from the beginning) |
|---|---|
| Training vs test error, overfitting, regularisation | SQL and relational databases |
| Validation and why a test set is used once | pandas beyond `read_csv` |
| Linear and logistic models, the bias-variance idea | The terminal and Git |
| Python variables, loops, functions, lists and dicts | pytest, packaging, logging, configuration |
| A little NumPy | HTTP, APIs, FastAPI |
| | Docker, CI, the cloud, monitoring |

## A five-minute self-check

Answer these without looking anything up. If most feel comfortable, you are ready. If not, a short Python or
intro-ML refresher first will make the course much easier.

1. Write a Python function that takes a list of numbers and returns a dict with their `min`, `max` and mean.
   What should it do with an empty list?
2. What does `[x * 2 for x in range(5) if x % 2 == 0]` produce?
3. Why can a model with a lower training error have a *higher* test error?
4. You tuned ten models on the validation set and picked the best. Why is its validation score now optimistic?
5. In logistic regression, what does a predicted value of 0.8 mean, and how do you turn it into a yes/no decision?

The answers are not graded anywhere; notebook 01 gives you the first graded exercises.

## Time and pacing

* **6-8 hours a week**, for 12 weeks. Each week has three lessons (75-120 minutes each) and one lab (90-120
  minutes). Every week page has a suggested split into short sessions.
* Nothing is dated. If you miss a week, continue where you are.
* A lab is the best check that a week has landed: if its exercises pass without opening the solutions, move on.

## What you need

| Weeks | You need |
|---|---|
| 1-9, 12 | A Google account and a browser ([Google Colab](../tools/colab.html)). Nothing to install |
| 10-11 | Also your own computer (Linux, macOS or Windows) with VS Code, Python 3.11+ and Git. Docker is used in Week 10 if you can install it; the graded parts still run in Colab |

No GPU and no paid service are needed. Week 11 explains cloud deployment and its costs; you are never asked to
create anything that costs money.

## How to get the most out of it

* **Type, do not paste.** The "Try it" cells exist so that you predict, change and run.
* **Read the grader's message.** A ❌ says what is wrong; fix that one thing and re-run.
* **Open the solutions last.** Solved copies are in `solutions/notebooks/`. Looking first turns a 20-minute
  exercise into 2 minutes of reading and teaches far less.
* **Keep your work.** In Colab use **File → Save a copy in Drive**; locally, commit to your own Git repository
  (Week 1 shows how).

[Set up](setup.html){: .btn .btn-primary .mr-2 }
[Start Week 1](../weeks/week-1.html){: .btn }
