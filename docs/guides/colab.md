---
title: Running in Colab
parent: Guides
nav_order: 4
---

# Running in Google Colab

Every notebook has an **Open in Colab** badge at the top. Click it, sign in with a Google account,
and run the first code cell: it clones this repository into `/content/mlengineering-`, installs
`requirements.txt` (about a minute), and moves into the repository root so every later command works.

What works in Colab: everything that runs in Python, including the labs, the checks, the SKAB download
and the FastAPI tests (they use an in-process test client, not a network port).

What does not:

* **Docker** (notebooks 31-36). Colab has no Docker daemon. Read those notebooks there, run them locally.
* **Persistence.** A Colab runtime is deleted when it disconnects, and your lab edits with it. For real
  work, clone the repository locally, or push your changes from Colab to your own fork before closing.
* **Long-running servers.** Commands that start a server for you to `curl` are left as text in the
  notebooks; run them in a local terminal.

Editing lab files in Colab: open the file browser on the left, double-click a file under
`mlengineering-/labs/<session>/lab/`, edit, save, then re-run the notebook's check cell.
