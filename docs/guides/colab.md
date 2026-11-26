---
title: Running in Colab
parent: Guides
nav_order: 3
---

# Running in Google Colab

Every notebook starts with an **Open in Colab** badge. Click it, sign in with a Google account, and run the first
code cell: it downloads the course into `/content/mlengineering`, installs what it needs (about a minute, once per
session) and moves into the course folder, so every later cell works. The
[Google Colab tool guide](../tools/colab.html) is the full reference; these are the points that matter most.

**What works in Colab:** everything graded in the course: SQL on the course database, pandas, scikit-learn,
pytest (run with `!python -m pytest`), packages installed with `pip install -e`, FastAPI services tested in-process
with `TestClient`, and the SKAB download.

**What does not:**

* **Keeping files.** A Colab runtime is deleted when it disconnects, with everything you wrote in it. Use
  **File → Save a copy in Drive** for the notebook; files written with `%%writefile` must be downloaded or
  recreated (re-running the notebook recreates them).
* **Docker and long-running servers.** Colab has no Docker daemon, and a server started there is not reachable
  from your browser. Week 10 runs these on your own computer; their graded parts still run in Colab.

**When something goes wrong:** *Runtime → Restart session*, then run the cells again from the top. Most problems
come from running cells out of order.
