# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/34_apis_and_fastapi.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 34 · APIs and FastAPI
#
# **Week 9 · lesson · about 100 minutes**
#
# A batch job (notebook 33) scores everyone overnight. But sometimes a prediction is needed *now*: the support
# agent opens a customer's page and wants the churn risk on screen. Then the model must sit behind an **API**, a
# small program that other programs can ask questions over the network. This notebook teaches HTTP from zero and
# builds a prediction API with **FastAPI**, all inside Colab, without opening any port to the internet.
#
# **What you will learn in this notebook**
#
# - HTTP from zero: requests, responses, methods, paths, status codes and JSON.
# - A first FastAPI app, called in-process with `TestClient` (no server needed).
# - Path parameters and `HTTPException` for "not found".
# - **pydantic** models: describing and validating the input and output of an API.
# - A `POST /predict` endpoint for the churn model, and a service file that loads a model bundle once at start-up.
#
# **What you need:** notebook 33 (model bundles). No web experience is assumed.
#
# **How grading works:** after each exercise there is a grader cell. Run it and it tells you immediately
# whether your answer works, and if not, what to look at.

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

# %% [markdown]
# **Given:** the churn model from notebook 33, trained again here so this notebook stands on its own, and saved as
# a bundle in `runs/week09/bundles/churn_v1` (the folder name is the model's version).

# %%
import json
import numpy as np
import pandas as pd
from mlcourse.graders.w09 import train_churn_model, FEATURES, use, _ref_save_bundle, _ref_metadata

WORK = REPO_ROOT / "runs" / "week09"
pipe, test_accuracy, train_rows = train_churn_model()
BUNDLE = _ref_save_bundle(pipe, _ref_metadata(pipe, FEATURES, {"test_accuracy": test_accuracy}, train_rows),
                          WORK / "bundles" / "churn_v1")
print("model saved in", BUNDLE.relative_to(REPO_ROOT), "| test accuracy", round(test_accuracy, 3))

# %% [markdown]
# ## 1. HTTP from zero
#
# **Why.** Almost every system you will connect a model to (a website, a mobile app, another team's service) talks
# **HTTP**, the protocol of the web. You need its vocabulary to build an API and to read its errors.
#
# **Idea.** HTTP is a conversation of **requests** and **responses** between a **client** (the program asking)
# and a **server** (the program answering).
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c34-01.svg" alt="A client sends POST /predict with a JSON body; FastAPI validates it with pydantic; invalid input gets 422; valid input reaches the endpoint, which calls the model and returns 200 with JSON" style="max-width:100%">
#
# A **request** has:
#
# * a **method**, the kind of action: `GET` (read something, no body) or `POST` (send data to be processed). There
#   are others (`PUT`, `DELETE`), which you will not need this week;
# * a **path**, which thing: `/health`, `/predict`, `/customers/42`;
# * **headers**, small labelled facts, e.g. `content-type: application/json` (the body is JSON);
# * an optional **body**, the data, almost always **JSON** for APIs.
#
# A **response** has a **status code** (a 3-digit number saying how it went), headers, and a body.
#
# | Code | Name | Meaning in an ML API |
# |---|---|---|
# | 200 | OK | here is your prediction |
# | 404 | Not Found | that path or that customer does not exist |
# | 405 | Method Not Allowed | right path, wrong method (e.g. GET on a POST-only endpoint) |
# | 422 | Unprocessable Content | your JSON broke the rules (missing field, negative count) |
# | 500 | Internal Server Error | the server crashed: our fault |
# | 503 | Service Unavailable | the server is up but cannot serve now (e.g. model not loaded) |
#
# The first digit is the **family**: 2xx success, 3xx redirect (go elsewhere), 4xx **client error** (the caller
# must fix the request), 5xx **server error** (we must fix the server). **JSON** (JavaScript Object Notation) is
# text that looks like Python dicts and lists; `json.dumps` turns Python into JSON text, `json.loads` reads it back.
#
# **See it.**

# %%
request_body = {"recency_days": 90, "orders_90d": 1, "spend_90d": 40.0, "tenure_days": 300, "segment": "consumer"}
text = json.dumps(request_body)
print(type(text).__name__, text)
print(json.loads(text)["segment"])

# %% [markdown]
# JSON is just a string; `json.loads` gives you a dict again.
#
# **Try it.** Run `json.dumps({"ok": True, "missing": None})`. How do Python's `True` and `None` appear in JSON?

# %%
json.dumps({"ok": True, "missing": None})

# %% [markdown]
# (`true` and `null`: JSON's spellings.)
#
# ### Exercise 1 · status code families
#
# Write `status_family(code)` returning `"informational"` (1xx), `"success"` (2xx), `"redirect"` (3xx),
# `"client error"` (4xx) or `"server error"` (5xx). Raise `ValueError` for anything outside 100-599.

# %%
def status_family(code):
    ### BEGIN SOLUTION
    if not 100 <= code <= 599:
        raise ValueError(f"{code} is not an HTTP status code")
    return {1: "informational", 2: "success", 3: "redirect", 4: "client error", 5: "server error"}[code // 100]
    ### END SOLUTION


# %%
grade("w09.status_family", status_family)

# %% [markdown]
# ### Exercise 2 · make a record JSON-safe
#
# Rows that come out of pandas contain NumPy types (`np.int64`, `np.float64`, `np.bool_`), `NaN` and
# `pd.Timestamp`. Strict JSON rejects `np.int64`, `NaN` (JSON has no NaN) and timestamps. Write `jsonable(record)`
# that takes a dict and returns a new dict where:
#
# * NumPy integers become `int`, NumPy booleans become `bool`, NumPy/Python floats become `float`;
# * `NaN` becomes `None` (JSON `null`);
# * a `pd.Timestamp` becomes its ISO string (`ts.isoformat()`);
# * anything else is kept as it is.
#
# Test with `isinstance(v, np.integer)`, `isinstance(v, (float, np.floating))`, `isinstance(v, np.bool_)`,
# `isinstance(v, pd.Timestamp)`. Check booleans before integers.

# %%
def jsonable(record):
    ### BEGIN SOLUTION
    clean = {}
    for key, value in record.items():
        if isinstance(value, np.bool_):
            value = bool(value)
        elif isinstance(value, np.integer):
            value = int(value)
        elif isinstance(value, (float, np.floating)):
            value = None if np.isnan(value) else float(value)
        elif isinstance(value, pd.Timestamp):
            value = value.isoformat()
        clean[key] = value
    return clean
    ### END SOLUTION


# %%
grade("w09.jsonable", jsonable)

# %% [markdown]
# ## 2. Your first FastAPI app
#
# **Why.** You could handle HTTP by hand, but nobody does. **FastAPI** is a Python library for writing APIs: you
# write ordinary functions, and it handles the HTTP, the JSON, the validation and even documentation pages.
#
# **Idea.** Three pieces:
#
# ```python
# from fastapi import FastAPI
# app = FastAPI()                 # 1. the application object
#
# @app.get("/health")             # 2. a decorator: "when a GET request for /health arrives, call this"
# def health():
#     return {"status": "ok"}     # 3. return a dict; FastAPI turns it into a JSON response with status 200
# ```
#
# Each decorated function is an **endpoint**. A `/health` endpoint is a convention: monitoring tools call it every
# few seconds to check the service is alive.
#
# How do you call the app? Normally you would start a **server** (the program **uvicorn**: `uvicorn app:app
# --port 8000`) and send requests over the network. In Colab and in tests we use **`TestClient`** instead: it calls
# your app's code directly inside this Python process. No server, no open port, nothing reachable from the
# internet. You use it exactly like a real HTTP client: `client.get(path)`, `client.post(path, json=body)`, and get
# back a response with `.status_code` and `.json()`.
#
# **See it.**

# %%
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

demo = FastAPI()


@demo.get("/hello")
def hello():
    return {"message": "hello from FastAPI"}


client = TestClient(demo)
r = client.get("/hello")
print(r.status_code, r.json())
r = client.get("/goodbye")
print(r.status_code, r.json())

# %% [markdown]
# `/hello` answers 200 with your dict; `/goodbye` does not exist, so FastAPI answers **404** by itself.
#
# **Try it.** Call `client.post("/hello")`. Which status code do you get, and what does it mean (see the table)?

# %%
client.post("/hello").status_code

# %% [markdown]
# ### Exercise 3 · a health endpoint
#
# Write `make_health_app()` that creates a **new** `FastAPI()` app, adds `GET /health` returning
# `{"status": "ok"}`, and returns the app. (Building the app inside a function lets the grader create fresh copies.)

# %%
def make_health_app():
    ### BEGIN SOLUTION
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
    ### END SOLUTION


# %%
grade("w09.make_health_app", make_health_app)

# %% [markdown]
# ## 3. Path parameters and "not found"
#
# **Why.** APIs often look things up: `/customers/42` means "customer 42". When the thing does not exist, the
# right answer is a clear 404, not a crash (500) and not an empty 200.
#
# **Idea.** Put a name in braces in the path, and a function argument with the same name and a **type**:
#
# ```python
# @app.get("/customers/{customer_id}")
# def get_customer(customer_id: int):        # FastAPI converts "42" to 42, or answers 422 for "abc"
#     if customer_id not in DB:
#         raise HTTPException(status_code=404, detail=f"customer {customer_id} not found")
#     return DB[customer_id]
# ```
#
# `raise HTTPException(status_code=..., detail=...)` stops the endpoint and sends that status with a JSON body
# `{"detail": ...}`. The type annotation `customer_id: int` is not decoration: FastAPI **uses** it to convert and
# validate.
#
# **See it.**

# %%
segments = {7: "student", 9: "consumer"}
lookup = FastAPI()


@lookup.get("/segments/{customer_id}")
def get_segment(customer_id: int):
    if customer_id not in segments:
        raise HTTPException(status_code=404, detail=f"customer {customer_id} not found")
    return {"customer_id": customer_id, "segment": segments[customer_id]}


c = TestClient(lookup)
for path in ["/segments/7", "/segments/8", "/segments/seven"]:
    r = c.get(path)
    print(path, r.status_code, r.json())

# %% [markdown]
# Customer 7 is found (200); 8 is unknown (404, with our message); `"seven"` is not an integer, so FastAPI rejects
# it with **422** and explains where (`"loc": ["path", "customer_id"]`), before our function even runs.
#
# ### Exercise 4 · a lookup service
#
# Write `make_lookup_app(table)` where `table` is a dict like `{42: {"segment": "student", "city": "Oslo"}}`. The app
# answers `GET /customers/{customer_id}` with the customer's record **plus** `"customer_id"`, e.g.
# `{"customer_id": 42, "segment": "student", "city": "Oslo"}`, and with 404 (via `HTTPException`) for an unknown id.
# Tip: `{"customer_id": customer_id, **table[customer_id]}` merges two dicts.

# %%
def make_lookup_app(table):
    ### BEGIN SOLUTION
    app = FastAPI()

    @app.get("/customers/{customer_id}")
    def get_customer(customer_id: int):
        if customer_id not in table:
            raise HTTPException(status_code=404, detail=f"customer {customer_id} not found")
        return {"customer_id": customer_id, **table[customer_id]}

    return app
    ### END SOLUTION


# %%
grade("w09.make_lookup_app", make_lookup_app)

# %% [markdown]
# ## 4. pydantic: describe the input, get validation for free
#
# **Why.** A prediction request carries five features. Clients make mistakes: a missing field, `"soon"` instead of
# a number, a negative count, a typo in a field name, a segment the model never saw. If any of these reaches the
# model, you get a crash (500) or, worse, a confident nonsense prediction. Validation must happen at the door.
#
# **Idea.** **pydantic** lets you describe data as a class with typed fields. Creating an object checks every rule
# and raises a `ValidationError` listing all problems:
#
# ```python
# from typing import Literal
# from pydantic import BaseModel, ConfigDict, Field
#
# class Order(BaseModel):
#     model_config = ConfigDict(extra="forbid")      # unknown fields (typos!) are an error, not silently ignored
#     quantity: int = Field(ge=1)                     # an int, greater than or equal to 1
#     price: float = Field(ge=0, le=10_000)           # a float between 0 and 10,000
#     channel: Literal["web", "app"]                  # exactly one of these strings
# ```
#
# `Field(ge=..., le=...)` adds limits (`gt`/`lt` for strict ones). A field without a default is **required**.
# pydantic converts where it is safe (the string `"3"` becomes the int `3`) but refuses `"soon"` or `2.5` for an
# `int`. `.model_dump()` turns a valid object back into a dict.
#
# **See it.**

# %%
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class Order(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quantity: int = Field(ge=1)
    price: float = Field(ge=0, le=10_000)
    channel: Literal["web", "app"]


print(Order(quantity="3", price=9.5, channel="web").model_dump())
try:
    Order(quantity=0, price=-1, channel="phone", colour="red")
except ValidationError as err:
    for e in err.errors():
        print(e["loc"], "->", e["msg"])

# %% [markdown]
# The valid order comes back with `quantity` converted to the integer 3. The invalid one produces **four** problems
# at once, each with its location and a readable message: that list is what FastAPI sends back in a 422.
#
# **Try it.** Change `extra="forbid"` to `extra="ignore"` in the class and re-run both cells. What happens to the
# `colour` problem? Why is that dangerous for an API whose client misspelled `segmnt`?

# %% [markdown]
# ### Exercise 5 · the request model
#
# Define the class `CustomerFeatures` for one churn prediction request:
#
# * `recency_days`, `orders_90d`, `tenure_days`: integers, 0 or more;
# * `spend_90d`: a float, 0 or more;
# * `segment`: exactly one of `"consumer"`, `"small_business"`, `"student"`;
# * extra fields are forbidden.

# %%
class CustomerFeatures(BaseModel):
    ### BEGIN SOLUTION
    model_config = ConfigDict(extra="forbid")
    recency_days: int = Field(ge=0)
    orders_90d: int = Field(ge=0)
    spend_90d: float = Field(ge=0)
    tenure_days: int = Field(ge=0)
    segment: Literal["consumer", "small_business", "student"]
    ### STARTER
    pass  # YOUR CODE HERE: replace this line with the five fields and the model_config
    ### END SOLUTION


# %%
grade("w09.customer_features", CustomerFeatures)

# %% [markdown]
# ### Exercise 6 · the response model
#
# Define `PredictionOut`, what `/predict` sends back: `churn_probability` (a float between 0 and 1 inclusive),
# `will_churn` (a bool) and `model_version` (a string). Describing the *output* too means the service can never
# send a probability of 1.3 by accident: FastAPI checks responses against it.

# %%
class PredictionOut(BaseModel):
    ### BEGIN SOLUTION
    churn_probability: float = Field(ge=0, le=1)
    will_churn: bool
    model_version: str
    ### STARTER
    pass  # YOUR CODE HERE: replace this line with the three fields
    ### END SOLUTION


# %%
grade("w09.prediction_out", PredictionOut)

# %% [markdown]
# ## 5. The prediction endpoint
#
# **Why.** Now combine everything: a `POST /predict` that takes one customer's features, asks the model, and
# answers with a validated response.
#
# **Idea.** If an endpoint's argument is typed with a pydantic class, FastAPI reads the JSON body, validates it with
# that class, and either calls your function with a ready object or answers **422** without calling it. The
# decorator's `response_model=` names the class the answer must fit.
#
# ```python
# @app.post("/predict", response_model=PredictionOut)
# def predict(features: CustomerFeatures):
#     row = pd.DataFrame([features.model_dump()])      # a one-row table with named columns
#     p = float(model.predict_proba(row)[0, 1])         # column 1 = probability of churn
#     return PredictionOut(churn_probability=p, will_churn=p >= threshold, model_version=version)
# ```
#
# The DataFrame matters: the pipeline selects columns **by name**, exactly as in training. And `float(...)` turns
# NumPy's `np.float64` into a plain float. The **threshold** (from Week 5: chosen from the costs of mistakes) turns
# a probability into a decision.
#
# ### Exercise 7 · a prediction app
#
# Write `make_predict_app(model, threshold=0.5, version="v1")` returning an app with:
#
# * `GET /health` returning `{"status": "ok", "model_version": version}`;
# * `POST /predict` taking a `CustomerFeatures` body and returning a `PredictionOut` where `will_churn` is True
#   exactly when the probability is **at least** the threshold.
#
# The grader calls it with a stand-in model whose answer you can compute by hand, so it checks your API, not the
# model.

# %%
import pandas as pd


def make_predict_app(model, threshold=0.5, version="v1"):
    ### BEGIN SOLUTION
    app = FastAPI(title="Churn prediction API")

    @app.get("/health")
    def health():
        return {"status": "ok", "model_version": version}

    @app.post("/predict", response_model=PredictionOut)
    def predict(features: CustomerFeatures):
        row = pd.DataFrame([features.model_dump()])
        p = float(model.predict_proba(row)[0, 1])
        return PredictionOut(churn_probability=p, will_churn=p >= threshold, model_version=version)

    return app
    ### END SOLUTION


# %%
grade("w09.make_predict_app", make_predict_app)

# %% [markdown]
# **See it.** The real churn model behind your API: one good request, one bad one.

# %%
api = TestClient(use(make_predict_app, pipe, threshold=0.5, version="churn_v1"))
print(api.get("/health").json())
good = {"recency_days": 120, "orders_90d": 0, "spend_90d": 0.0, "tenure_days": 400, "segment": "consumer"}
r = api.post("/predict", json=good)
print(r.status_code, r.json())
r = api.post("/predict", json=dict(good, orders_90d=-1, segment="vip"))
print(r.status_code, [(e["loc"], e["msg"]) for e in r.json()["detail"]])

# %% [markdown]
# The good request gets 200 and a probability; the bad one gets 422 with both problems listed, and the model was
# never called.
#
# **Try it.** Send the good request with `orders_90d` set to 0, then 8 (a customer who ordered a lot recently).
# Which way does the probability move? Then try `recency_days` 10 and 300: this model barely reacts to recency,
# because recent order counts already carry most of that information.

# %%
api.post("/predict", json=dict(good, orders_90d=8)).json()

# %% [markdown]
# ### Exercise 8 · a client function
#
# Other programs call your API too. Write `call_predict(client, features)`: post `features` (a dict) to `/predict`;
# if the status is not 200, raise `RuntimeError` with a message containing the status code and the response text
# (`r.text`); otherwise return the JSON body as a dict.

# %%
def call_predict(client, features):
    ### BEGIN SOLUTION
    r = client.post("/predict", json=features)
    if r.status_code != 200:
        raise RuntimeError(f"/predict answered {r.status_code}: {r.text}")
    return r.json()
    ### END SOLUTION


# %%
grade("w09.call_predict", call_predict)

# %% [markdown]
# ## 6. A real service file
#
# **Why.** A notebook is not a service. To run it with uvicorn, in Docker (Week 10) or in the cloud (Week 11), the
# API must live in a `.py` file that creates `app` when it is imported.
#
# **Idea.** Three rules for the service file:
#
# 1. **Load the model once, at start-up** (at the top of the module), not inside the endpoint. Loading per request
#    is slow, and a broken bundle should be noticed when the service starts, not when the first customer calls.
# 2. **Configuration from the environment.** The bundle folder comes from an **environment variable**
#    (`os.environ.get("CHURN_MODEL_DIR", "<default>")`), so the same file serves `churn_v1` today and `churn_v2`
#    tomorrow without editing code. An environment variable is a named setting the operating system passes to a
#    program.
# 3. **The version is the bundle's folder name** (`Path(MODEL_DIR).name`), so every answer says which model made it.
#
# On your own computer you would then run, in a terminal in the course folder,
# `uvicorn --app-dir runs/week09 churn_api:app --port 8000` and open `http://127.0.0.1:8000/docs`, a page FastAPI generates where you can try the API. `127.0.0.1`
# means "this computer only". In Colab we keep using `TestClient`.
#
# ### Exercise 9 · write the service file
#
# Complete the cell below, which writes `runs/week09/churn_api.py`. The file must be **standalone** (it cannot see
# this notebook's variables), so it repeats the two pydantic classes. It must:
#
# * read `MODEL_DIR` from the `CHURN_MODEL_DIR` environment variable (default: `runs/week09/bundles/churn_v1`);
# * load `model.joblib` with `joblib.load` **once**, at import time, and set `VERSION = Path(MODEL_DIR).name`;
# * create `app` with `GET /health` (`{"status": "ok", "model_version": VERSION}`) and `POST /predict` exactly
#   as in exercise 7.
#
# (A production file would also verify the checksum with your `load_bundle` from notebook 33; Week 10 packages that
# code so the service can import it.)

# %%
%%writefile runs/week09/churn_api.py
"""Churn prediction API. Run locally from the course folder:  uvicorn --app-dir runs/week09 churn_api:app --port 8000"""
### BEGIN SOLUTION
import os
from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

MODEL_DIR = Path(os.environ.get("CHURN_MODEL_DIR", "runs/week09/bundles/churn_v1"))
MODEL = joblib.load(MODEL_DIR / "model.joblib")      # loaded once, when the service starts
VERSION = MODEL_DIR.name
THRESHOLD = 0.5


class CustomerFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recency_days: int = Field(ge=0)
    orders_90d: int = Field(ge=0)
    spend_90d: float = Field(ge=0)
    tenure_days: int = Field(ge=0)
    segment: Literal["consumer", "small_business", "student"]


class PredictionOut(BaseModel):
    churn_probability: float = Field(ge=0, le=1)
    will_churn: bool
    model_version: str


app = FastAPI(title="Churn prediction API")


@app.get("/health")
def health():
    return {"status": "ok", "model_version": VERSION}


@app.post("/predict", response_model=PredictionOut)
def predict(features: CustomerFeatures):
    p = float(MODEL.predict_proba(pd.DataFrame([features.model_dump()]))[0, 1])
    return PredictionOut(churn_probability=p, will_churn=p >= THRESHOLD, model_version=VERSION)
### END SOLUTION

# %% [markdown]
# (The first line of that cell, `%%writefile <path>`, is a Colab/Jupyter **cell magic**: instead of running the
# cell, it saves the cell's text into that file. It must be the very first line of the cell.)

# %%
grade("w09.api_file", WORK / "churn_api.py")

# %% [markdown]
# **See it.** Import the file the way uvicorn would, and call it. (This is a check, not new material.)

# %%
import importlib.util

try:
    spec = importlib.util.spec_from_file_location("churn_api", WORK / "churn_api.py")
    churn_api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(churn_api)
    service = TestClient(churn_api.app)
    print(service.get("/health").json())
    print(service.post("/predict", json=good).json())
except NotImplementedError:
    print("(exercise 9 is not finished yet, so there is no service to call)")

# %% [markdown]
# ## Quiz
#
# **Q1.** A client sends `{"orders_90d": -3, ...}` and your API refuses it. Which status code is right?
#
# - a) 200
# - b) 422
# - c) 500
# - d) 404

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w09.34_q1", answer)

# %% [markdown]
# **Q2.** What does `TestClient(app)` do?
#
# - a) Starts a public web server for the app.
# - b) Deploys the app to the cloud.
# - c) Starts uvicorn in the background.
# - d) Calls the app's code directly inside the current Python process, as if HTTP requests had arrived.

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w09.34_q2", answer)

# %% [markdown]
# **Q3.** The `/predict` function takes `features: CustomerFeatures`. A request arrives with `segment: "vip"`.
# What happens?
#
# - a) FastAPI validates the body before calling the function and answers 422 listing the problem.
# - b) pydantic replaces "vip" with the closest allowed value.
# - c) The check only happens once, when the app starts.
# - d) The function runs and must check the segment itself.

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w09.34_q3", answer)

# %% [markdown]
# **Q4.** Why is `/predict` a POST and `/health` a GET?
#
# - a) POST is faster.
# - b) POST is more secure.
# - c) GET asks for something without sending data; POST sends a body (the features) to be processed.
# - d) Browsers cannot send POST requests.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w09.34_q4", answer)

# %% [markdown]
# **Q5.** Why does the service file load the model at import time rather than inside `predict`?
#
# - a) Because loading inside `predict` gives different predictions.
# - b) Each request stays fast, and a missing or broken bundle is discovered when the service starts.
# - c) Because global variables are faster than local ones.
# - d) To always use the newest model file.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w09.34_q5", answer)

# %% [markdown]
# ## Recap
#
# - HTTP: a request has a method, a path, headers and a body; a response has a status code and a body, usually JSON.
# - Status families: 2xx success, 4xx the client must fix the request, 5xx the server must be fixed.
# - FastAPI: `app = FastAPI()`, `@app.get(...)` / `@app.post(...)` endpoints returning dicts or pydantic objects.
# - `TestClient(app)` calls the app in-process: perfect for Colab and tests; uvicorn runs a real server locally.
# - Path parameters with types, and `HTTPException(status_code=404, detail=...)` for "not found".
# - pydantic models describe input and output; invalid requests get 422 before your code runs.
# - A service file loads its model once, reads its configuration from environment variables, and reports its version.
#
# ## On the job
#
# "Wrap the model in an API" is one of the most common tickets an ML engineer gets. Reviewers will look for exactly
# what you did here: validated input with clear 422s, an output schema, a health endpoint, the model version in
# every answer, and a model loaded once from a configurable location. The interactive `/docs` page FastAPI
# generates is often how other teams first try your service.
#
# ## Going further
#
# - Tool guide: [FastAPI and pydantic](../docs/tools/fastapi.md).
# - Advanced track: notebooks 27 (online inference) and 28 (FastAPI validation), in `advanced/notebooks/`.
# - Next: [35 · Testing APIs and handling bad input](35_testing_apis_bad_input.ipynb).

# %% [markdown]
# ## Record your progress

# %%
from mlcourse.progress import mark

# mark("34", "reading")
# mark("34", "guided")
