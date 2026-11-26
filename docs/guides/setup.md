---
title: Setup
parent: Guides
nav_order: 3
---

# Setup
{: .no_toc }

1. TOC
{:toc}

---

## 1. Python 3.11 or newer

```bash
python3 --version
```

Ubuntu 22.04 and the distributions built on it ship Python 3.10, which is too old (the labs use `tomllib`, added in 3.11). Options,
explained in [handbook H2.1](../handbook/ch02_maintainable_python/h2_1_project_structure_environments.html):
upgrade to a release that ships 3.11+ (for example Ubuntu 24.04, Python 3.12), install a newer interpreter with `uv python install 3.12`,
or use a distribution package for a newer Python. Everything here was executed on Python 3.13.

## 2. Clone and install

```bash
git clone https://github.com/berdakh/mlengineering.git
cd mlengineering

python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-lock.txt      # the exact versions the course was tested with
pip install -r requirements-dev.txt       # JupyterLab and friends, for running notebooks locally

python scripts/check_env.py               # what this machine can run
jupyter lab notebooks/01_diagnostic_a.ipynb
```

`requirements.txt` has lower bounds instead of exact pins; use it if the locked versions do not
install on your platform.

## 3. The project data (from notebook 06 on)

```bash
python project/get_skab.py            # about 4 MB into data/raw/skab/, with SHA-256 manifest
python project/get_skab.py --verify   # re-check the files at any time
```

SKAB is GPL-3.0; it is downloaded from its source and never committed to this repository.

## 4. Optional extras, when a notebook asks for them

| For | Install |
|---|---|
| Notebook 21 (neural comparison) | `pip install -r requirements-neural.txt` (CPU-only PyTorch is enough) |
| Notebooks 31-36 (containers, CI, delivery) | Docker Engine: follow Docker's official instructions for your system (Docker Desktop on macOS and Windows) |
| Notebook 35 live step (optional) | An AWS account, the AWS CLI v2, and the notebook's cost and credential briefing first |
| The study app | `pip install -r requirements-app.txt`, then `streamlit run app/study_app.py` |

## 5. Check that everything works

```bash
python wb.py status                         # all 56 sessions and your progress flags
python wb.py check diagnostic/a1_python     # fails on the fresh starter, as it should
make test                                   # the course's own tests
```
