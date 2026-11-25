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

## Who this is for

Researchers and engineers who already train models (PyTorch, scikit-learn, time series) and want to
**deliver them as reliable software**: packaged, tested, served, containerised, deployed and monitored.
The course does not re-teach what a CNN or a cross-validation fold is. It assumes you can write Python
comfortably and use a terminal, and it checks that assumption in the first two sessions.

## What you need

| You have | You can do |
|---|---|
| Any laptop with Python 3.11 or newer | Weeks 1-5 and 7-8 entirely, Week 6 except containers |
| The same, plus Docker Engine | Everything except the optional cloud step |
| No install at all | Read everything on this site; run notebooks in [Colab](colab.html) |
| An AWS account (optional) | The gated deployment step in notebook 35. Never required |

No GPU is needed. One notebook (21) trains a small neural network on the CPU.

## How a day works

Every core day is **one notebook**: about two hours on the essential path, plus up to an hour of
optional extension. Each notebook follows the same eight parts: purpose, concepts, a worked example
you run, a guided lab with automated checks, an independent challenge, progressive hints, an assessment,
and a reflection. Day 7 of each week is a lighter review day on its [week page](../weeks/).

Your work happens in the lab folders (`labs/<session>/lab/` and `challenge/`); the notebook runs the
checks for you. **Passing the supplied checks is guided practice, not mastery.** Mark a session
*independent* only for work you did without hints or solutions.

## The first two sessions

Notebooks **01** and **02** are a time-boxed, unassisted diagnostic: Python, SQL, data cleaning,
baselines, leakage, testing and API concepts, and a written decision. Do them honestly: the results
decide which Week 1-3 sessions you can compress or skip. Do not open `solutions/` first.

[Set up your machine](setup.html){: .btn .btn-primary .mr-2 }
[Start Week 1](../weeks/week-1.html){: .btn }
