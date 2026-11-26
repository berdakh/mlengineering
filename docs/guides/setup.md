---
title: Setup
parent: Guides
nav_order: 2
---

# Setup
{: .no_toc }

1. TOC
{:toc}

---

## Weeks 1-9 and 12: Google Colab, nothing to install

1. Open a notebook's **Open in Colab** badge (start with
   [notebook 01](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/01_welcome_and_colab.ipynb)).
2. Sign in with a Google account.
3. Run the first code cell. It downloads the course into `/content/mlengineering` (about 30 s), installs
   `requirements.txt` (about a minute, once per Colab session) and prints `Ready. Course folder: ...`.
4. Work top to bottom. To keep your answers, use **File → Save a copy in Drive**.

The [Google Colab tool guide](../tools/colab.html) explains runtimes, files, shortcuts and common errors.

## Weeks 10-11: your own computer with VS Code

Week 10 moves you to a local setup, the way most teams work. [Notebook 37](../notebooks/37_vscode_local_setup.html)
walks through it step by step on Linux, macOS and Windows, and the [VS Code guide](../tools/vscode.html) is the
reference. In brief:

1. Install **Python 3.11 or newer**, **Git** and **VS Code** (with its Python and Jupyter extensions).
2. Clone the course and create a virtual environment:

   ```bash
   git clone https://github.com/berdakh/mlengineering.git
   cd mlengineering
   python3 -m venv .venv
   source .venv/bin/activate        # Windows (PowerShell): .venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. `code .` opens the folder in VS Code. Open a notebook in `notebooks/`, pick the `.venv` interpreter as the
   kernel, and run the first cell. It finds the course folder by itself; nothing else changes.
4. Check that grading works: `python -m pytest tests -q` runs the course's own tests.

Docker is optional: install Docker Desktop (macOS, Windows) or Docker Engine (Linux) from Docker's official
instructions if you want to run the Week 10 containers yourself; see the [Docker guide](../tools/docker.html).

`requirements.txt` has lower bounds. `requirements-lock.txt` pins the exact versions the material was tested with;
use it if a newer release behaves differently.

## The project data

The project notebooks (28, 36, 44, 45) download the SKAB dataset when they need it:

```bash
python project/get_skab.py            # about 4 MB into data/raw/skab/, with a SHA-256 manifest
python project/get_skab.py --verify   # re-check the files at any time
```

SKAB is GPL-3.0; it is downloaded from its source and never committed to this repository. Grading never needs it.

## The advanced track

The [advanced track](../advanced/) uses the same environment plus a few extras:

| For | Install |
|---|---|
| Its neural-comparison session | `pip install -r requirements-neural.txt` (CPU-only PyTorch is enough) |
| Its container sessions | Docker Engine or Docker Desktop |
| Its optional AWS step | An AWS account and the AWS CLI v2, after reading that session's cost and credential briefing |
| Its study app | `pip install -r requirements-app.txt`, then `streamlit run app/study_app.py` |
| Running its lab checks | `pip install -r requirements-dev.txt`, then `python wb.py check <session>` |
