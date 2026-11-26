# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/40_lab_container_and_ci.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 40 · Lab: containerise the API and add CI
#
# **Week 10 · lab · about 100 minutes**
#
# You get a small, working prediction API: a scikit-learn model that scores how likely an online-shop basket is to
# be returned, served by FastAPI. Your job is everything that turns it into something a team can ship: pinned
# requirements, tests of the API's promises, a `.dockerignore`, a Dockerfile you check with your own linter, and a
# GitHub Actions workflow that tests the code and then builds the image. Each step uses the previous one's files.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c40-01.svg" alt="The lab project: the model and app, pinned requirements, tests, Dockerfile and .dockerignore, and a CI workflow whose docker job needs the test job" style="max-width:100%">
#
# **Where things run.** Everything graded runs in Colab. Building the image and watching CI happen
# **💻 on your computer and on GitHub** at the end (optional, recommended for your portfolio).
#
# **What you need:** notebooks 37-39, and notebook 34 (FastAPI) and 35 (testing APIs). No new concepts: if a step
# is unclear, go back to the lesson it names.
#
# **How grading works:** each exercise writes a file in the project folder or defines a function; run the grader
# cell under it. The data and model are synthetic (generated below), so the lab runs offline.

# %%
# --- Setup: works in Google Colab AND on your own computer. Safe to re-run. ---
# In Colab this downloads the course (about 30 s) and installs what it needs (about a minute, once
# per session). On your computer it just finds the course folder.
import os, sys, subprocess
from pathlib import Path

if "google.colab" in sys.modules and not Path("/content/mlengineering").exists():
    subprocess.run(["git", "clone", "--depth", "1",
                    "https://github.com/berdakh/mlengineering.git", "/content/mlengineering"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r",
                    "/content/mlengineering/requirements.txt"], check=True)
REPO_ROOT = Path("/content/mlengineering") if "google.colab" in sys.modules else next(
    p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src" / "mlcourse").is_dir())
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "src"))
from mlcourse.grader import grade, quiz
print("Ready. Course folder:", REPO_ROOT)
import json
from importlib.metadata import version
import numpy as np
from mlcourse.graders.w10 import use, work_dir, nb38_helpers

LAB = work_dir() / "basket-api"
for sub in ("app", "model", "tests", ".github/workflows"):
    (LAB / sub).mkdir(parents=True, exist_ok=True)
print("project folder:", LAB)

# %% [markdown]
# ## The starting point: a model and an API (given)
#
# The next cell generates 2,000 synthetic baskets (number of items, total in dollars, and whether the basket was
# returned), trains a small pipeline, and saves it with its **metadata** next to it, as in notebook 33. Read it, run
# it, and note the scikit-learn version it records: the service must load the model with that same version.

# %%
import joblib
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

rng = np.random.default_rng(40)
n_items = rng.integers(1, 31, size=2000)
total = np.round(n_items * rng.uniform(5, 40, size=2000), 2)
logit = -2.5 + 0.08 * n_items + 0.003 * total          # synthetic: bigger baskets are returned more often
returned = rng.random(2000) < 1 / (1 + np.exp(-logit))
X = np.column_stack([n_items, total])
X_train, X_test, y_train, y_test = train_test_split(X, returned, test_size=0.25, random_state=0, stratify=returned)

model = make_pipeline(StandardScaler(), LogisticRegression()).fit(X_train, y_train)
auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
joblib.dump(model, LAB / "model" / "model.joblib")
metadata = {"model_version": "2026-11-basket-v1", "features": ["n_items", "total"],
            "sklearn_version": sklearn.__version__, "test_roc_auc": round(float(auc), 3),
            "data": "synthetic baskets generated in notebook 40 (seed 40)"}
(LAB / "model" / "metadata.json").write_text(json.dumps(metadata, indent=2))
print(json.dumps(metadata, indent=2))

# %% [markdown]
# And the service. It loads the model once, when the module is imported, and keeps three promises (its
# **contract**):
#
# 1. `GET /health` answers 200 with `{"status": "ok"}`;
# 2. `POST /predict` with `{"n_items": <1-100>, "total": <0 or more>}` answers 200 with `return_risk`, a probability
#    between 0 and 1, and the `model_version`;
# 3. anything else sent to `/predict` (missing fields, wrong types, out-of-range values) gets 422.

# %%
(LAB / "app" / "__init__.py").write_text("")
(LAB / "app" / "main.py").write_text('''"""Basket return-risk API: serves the model in ../model/ (see model/metadata.json)."""
import json
from pathlib import Path

import joblib
from fastapi import FastAPI
from pydantic import BaseModel, Field

MODEL_DIR = Path(__file__).resolve().parent.parent / "model"
model = joblib.load(MODEL_DIR / "model.joblib")
metadata = json.loads((MODEL_DIR / "metadata.json").read_text())

app = FastAPI(title="basket-api", version=metadata["model_version"])


class Basket(BaseModel):
    n_items: int = Field(ge=1, le=100)
    total: float = Field(ge=0)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def predict(basket: Basket):
    risk = model.predict_proba([[basket.n_items, basket.total]])[0, 1]
    return {"return_risk": round(float(risk), 4), "model_version": metadata["model_version"]}
''')
(LAB / "requirements-dev.txt").write_text("-r requirements.txt\n"
                                         f"pytest=={version('pytest')}\nhttpx=={version('httpx')}\n")

sys.path.insert(0, str(LAB))
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
print(client.get("/health").json())
print(client.post("/predict", json={"n_items": 3, "total": 45.0}).json())
print(client.post("/predict", json={"n_items": 0, "total": 45.0}).status_code)

# %% [markdown]
# ## Exercise 1 · pinned runtime requirements
#
# Write the text of `requirements.txt` for the **service**: exactly the packages it imports at run time
# (`fastapi`, `uvicorn` to serve it, `scikit-learn` and `joblib` for the model), each pinned with `==` to the
# version installed here (the cell below prints them). Test tools are already in `requirements-dev.txt`, which
# includes this file with `-r`; they do not belong in the image.

# %%
for package in ("fastapi", "uvicorn", "scikit-learn", "joblib"):
    print(f"{package}=={version(package)}")

# %%
### BEGIN SOLUTION
requirements = "".join(f"{p}=={version(p)}\n" for p in ("fastapi", "uvicorn", "scikit-learn", "joblib"))
### STARTER
requirements = """# YOUR PINNED REQUIREMENTS HERE
"""
### END SOLUTION
(LAB / "requirements.txt").write_text(requirements)
print(requirements)

# %%
grade("w10.lab_requirements", LAB / "requirements.txt")

# %% [markdown]
# ## Exercise 2 · tests of the contract
#
# Write `tests/test_api.py`: plain test functions (no fixtures) that use `TestClient` to check each of the three
# promises above. Do **not** assert an exact `return_risk`: it changes every time the model is retrained, and that
# is not a bug. The grader runs your tests against a correct app (they must pass) and against five apps with planted
# bugs (each must make at least one of your tests fail). The next cell also runs them for real with pytest against
# the actual service.

# %%
%%writefile {LAB}/tests/test_api.py
### BEGIN SOLUTION
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_says_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_predict_returns_a_probability_and_version():
    response = client.post("/predict", json={"n_items": 3, "total": 45.0})
    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["return_risk"] <= 1
    assert isinstance(body["model_version"], str)


def test_predict_rejects_bad_baskets():
    bad_baskets = [
        {"n_items": 0, "total": 10.0},       # too few items
        {"n_items": 101, "total": 10.0},     # too many
        {"n_items": 3, "total": -1.0},       # negative total
        {"n_items": 3},                      # missing field
        {"n_items": "three", "total": 10.0}, # wrong type
    ]
    for basket in bad_baskets:
        assert client.post("/predict", json=basket).status_code == 422, basket
### STARTER
# YOUR TESTS HERE
### END SOLUTION

# %%
result = subprocess.run([sys.executable, "-m", "pytest", "-q", "--color=no", "-p", "no:cacheprovider",
                         "-o", "pythonpath=.", "tests"], cwd=LAB, capture_output=True, text=True)
print(result.stdout[-1200:])

# %%
grade("w10.lab_tests", LAB / "tests" / "test_api.py")

# %% [markdown]
# ## Exercise 3 · your own Dockerfile linter
#
# Before writing the Dockerfile, build the reviewer. Write `lint_dockerfile(text)` returning a **set** of problem
# codes (empty when the Dockerfile is fine):
#
# | Code | When |
# |---|---|
# | `unpinned_base` | the `FROM` image is not pinned |
# | `runs_as_root` | there is no `USER`, or the last `USER` is `root` or `0` |
# | `deps_after_code` | a `COPY`/`ADD` of something other than a requirements file comes before the first `pip install` |
# | `pip_cache` | some `RUN ... pip install` lacks `--no-cache-dir` |
# | `secret_in_env` | `find_secrets` finds anything |
# | `shell_form_cmd` | the last `CMD` is not a JSON list (exec form) |
#
# The notebook-38 helpers are ready for you as `nb38_helpers.parse_dockerfile`, `nb38_helpers.is_pinned` and
# `nb38_helpers.find_secrets`.

# %%
def lint_dockerfile(text):
    ### BEGIN SOLUTION
    steps = nb38_helpers.parse_dockerfile(text)
    codes = set()
    base = next((args.split()[0] for ins, args in steps if ins == "FROM"), "")
    if not nb38_helpers.is_pinned(base):
        codes.add("unpinned_base")
    users = [args.strip() for ins, args in steps if ins == "USER"]
    if not users or users[-1] in ("root", "0"):
        codes.add("runs_as_root")
    installs = [k for k, (ins, args) in enumerate(steps) if ins == "RUN" and "pip install" in args]
    code_copies = [k for k, (ins, args) in enumerate(steps) if ins in ("COPY", "ADD") and "requirements" not in args]
    if installs and code_copies and min(code_copies) < min(installs):
        codes.add("deps_after_code")
    if any("--no-cache-dir" not in steps[k][1] for k in installs):
        codes.add("pip_cache")
    if nb38_helpers.find_secrets(text):
        codes.add("secret_in_env")
    cmds = [args for ins, args in steps if ins == "CMD"]
    if cmds:
        try:
            is_list = isinstance(json.loads(cmds[-1]), list)
        except json.JSONDecodeError:
            is_list = False
        if not is_list:
            codes.add("shell_form_cmd")
    return codes
    ### END SOLUTION


# %%
quick_and_dirty = """FROM python
COPY . .
RUN pip install -r requirements.txt
ENV API_KEY=abc123
CMD uvicorn app.main:app --host 0.0.0.0
"""
print(sorted(use(lint_dockerfile, quick_and_dirty)))
grade("w10.lab_lint", lint_dockerfile)

# %% [markdown]
# ## Exercise 4 · `.dockerignore`
#
# The image needs `app/`, `model/` and `requirements.txt`. Keep everything else out: `.git`, `.venv`, `__pycache__`
# folders at any depth, `.env`, `notebooks/`, the `tests/` folder, the `.github/` folder and `requirements-dev.txt`
# (tests run in CI, not inside the service). Remember: `.dockerignore` patterns start at the project root.

# %%
### BEGIN SOLUTION
dockerignore = """.git
.venv
**/__pycache__
.env
notebooks/
tests/
.github/
requirements-dev.txt
"""
### STARTER
dockerignore = """# YOUR PATTERNS HERE
"""
### END SOLUTION
_ = (LAB / ".dockerignore").write_text(dockerignore)

# %%
grade("w10.lab_dockerignore", LAB / ".dockerignore")

# %% [markdown]
# ## Exercise 5 · the Dockerfile
#
# Write the Dockerfile: everything notebook 38's exercise required, plus the `model/` folder copied after the
# dependencies, and a `HEALTHCHECK` that calls `/health` with Python (the slim image has no `curl`), for example
# `HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"`.
# Your linter from exercise 3 must find nothing; the grader then checks the rest.

# %%
### BEGIN SOLUTION
dockerfile = """FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY model/ model/
COPY app/ app/

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
### STARTER
dockerfile = """# YOUR DOCKERFILE HERE
"""
### END SOLUTION
(LAB / "Dockerfile").write_text(dockerfile)
print("your linter says:", use(lint_dockerfile, dockerfile) or "no problems")

# %%
grade("w10.lab_dockerfile", LAB / "Dockerfile")

# %% [markdown]
# ## Exercise 6 · CI: test, then build the image
#
# Write `.github/workflows/ci.yml` with read-only permissions, triggered on push and pull request, and two jobs,
# each with `timeout-minutes`:
#
# - `test`: checkout, setup-python `"3.12"` with `cache: pip`, `python -m pip install -r requirements-dev.txt`,
#   `python -m pytest -q`;
# - `docker`: `needs: test`, checkout, `docker build -t basket-api:ci .`, and (recommended) a smoke test that starts
#   the container and waits for `/health`:
#
# ```bash
# docker run -d --name api -p 8000:8000 basket-api:ci
# for i in $(seq 1 20); do curl -fs localhost:8000/health && exit 0; sleep 1; done
# docker logs api; exit 1
# ```
#
# (The runner has `curl`; the slim image does not, which is why the smoke test runs it on the runner.)

# %%
### BEGIN SOLUTION
workflow = """name: CI

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: "3.12"
          cache: pip
      - name: Install dependencies
        run: python -m pip install -r requirements-dev.txt
      - name: Run the tests
        run: python -m pytest -q

  docker:
    needs: test
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v7
      - name: Build the image
        run: docker build -t basket-api:ci .
      - name: Smoke-test the container
        run: |
          docker run -d --name api -p 8000:8000 basket-api:ci
          for i in $(seq 1 20); do curl -fs localhost:8000/health && exit 0; sleep 1; done
          docker logs api; exit 1
"""
### STARTER
workflow = """# YOUR WORKFLOW HERE
"""
### END SOLUTION
_ = (LAB / ".github" / "workflows" / "ci.yml").write_text(workflow)

# %%
grade("w10.lab_workflow", LAB / ".github" / "workflows" / "ci.yml")

# %% [markdown]
# ## 💻 Run it for real (optional, recommended)
#
# Download the project: the next cell zips it (in Colab it also offers the download). On your computer, unzip it,
# open a terminal in the folder and run:
#
# ```bash
# docker build -t basket-api:0.1 .
# docker run -d --rm --name api -p 8000:8000 basket-api:0.1
# docker ps                      # after about 30 s the STATUS column says (healthy)
# curl -s -X POST localhost:8000/predict -H "Content-Type: application/json" -d '{"n_items": 3, "total": 45}'
# docker stop api
# ```
#
# On Windows PowerShell, use `curl.exe` instead of `curl`, or open `http://localhost:8000/docs` and use the page.
#
# When we built the reference solution of this lab with Docker 29.10 on Linux (with the model trained by this
# notebook on our machine), the build took about 20 seconds with an empty cache, `docker ps` showed
# `Up About a minute (healthy)`, and the image used about 470 MB of disk, most of it scikit-learn, NumPy and SciPy.
# We also ran both jobs' commands locally, in a fresh virtual environment, and they passed; we did not run the
# workflow on GitHub. To see it there, put the folder in a new public GitHub repository and push (notebook 39's
# last section): the `test` job turns green, then the `docker` job builds and smoke-tests the image.

# %%
import shutil
archive = shutil.make_archive(str(LAB.parent / "basket-api"), "zip", root_dir=LAB)
print("zipped:", archive)
if "google.colab" in sys.modules:
    from google.colab import files
    files.download(archive)

# %% [markdown]
# ## Quiz
#
# **Q1.** Why must `requirements.txt` pin scikit-learn to the version that trained the model? (a) it installs faster
# (b) pip refuses other versions (c) a pickled model should be loaded by the version that saved it; another may fail
# to load it or predict differently (d) any version string is fine

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w10.40_q1", answer)

# %% [markdown]
# **Q2.** Why do the tests check `0 <= return_risk <= 1` instead of an exact value? (a) exact values are more
# rigorous (b) the contract is a probability; the exact value changes with every retrain, which is not a bug
# (c) contract tests cannot catch bugs (d) only `/health` should be tested

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w10.40_q2", answer)

# %% [markdown]
# **Q3.** What does the `HEALTHCHECK` line do? (a) Docker runs it inside the container periodically and marks the
# container unhealthy when `/health` stops answering (b) it restarts the server on every request (c) CI runs it
# from the runner (d) it checks the image while building

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w10.40_q3", answer)

# %% [markdown]
# **Q4.** What does `needs: test` on the `docker` job achieve? (a) nothing; jobs always run in order (b) it picks
# the runner (c) it shares files between jobs (d) the image is built only after the tests passed, so a broken commit
# never produces an image

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w10.40_q4", answer)

# %% [markdown]
# ## Reflection
#
# Write three or four sentences in your notes: which of your tests caught which planted bug? Which Dockerfile rule
# did you break first, and why does it matter? What would you add to the workflow next (a matrix, pushing the image
# to a registry, a scheduled run)?
#
# **What to show in your portfolio.** A public repository with this project: the README says what the service does
# and how to run it with one `docker run`; the Actions tab shows a green run with both jobs; the Dockerfile is short
# and commented. Mention that the data is synthetic. That is a small, credible piece of evidence that you can ship a
# model, not just train one.

# %%
# Record your progress (optional; stored in progress/progress.json):
from mlcourse.progress import mark
# mark("40", "reading")
# mark("40", "guided")
