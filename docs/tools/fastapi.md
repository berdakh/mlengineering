---
title: "FastAPI and pydantic"
parent: Tool guides
nav_order: 11
---

# FastAPI and pydantic

**FastAPI** is a Python library for building web APIs: programs that answer requests from other programs over
HTTP. **pydantic** is the library FastAPI uses to describe and validate data. Together they are the most common
way to put a Python model behind an API. This guide covers what Week 9 uses (notebooks 33-36) and what you will
meet again in Weeks 10-11.

## What it is, and why teams use it

A trained model is a Python object. Other systems (a website, a mobile app, a scheduler, another team's service)
cannot call a Python object; they can send an **HTTP request**. An API is the small program in between: it
receives the request, checks it, calls the model and sends back the answer.

Teams pick FastAPI because:

* endpoints are ordinary Python functions with type hints; no boilerplate;
* request bodies are validated automatically from pydantic classes, with precise `422` errors;
* it generates interactive documentation (`/docs`) from the same code;
* it ships a `TestClient` that calls the app in-process, which makes testing easy.

Alternatives you may meet: Flask (older, more manual), Django REST framework (inside Django projects), and
model-serving platforms that wrap a model for you. The ideas (HTTP, validation, status codes) are the same.

## HTTP in five minutes

A **request** has a **method** (`GET` to read, `POST` to send data to be processed), a **path** (`/predict`),
**headers** (e.g. `content-type: application/json`) and an optional **body** (JSON). A **response** has a
**status code**, headers and a body.

| Code | Meaning | Typical cause in an ML API |
|---|---|---|
| 200 | OK | a prediction was made |
| 404 | Not Found | wrong path, or an unknown id |
| 405 | Method Not Allowed | GET on a POST-only endpoint |
| 422 | Unprocessable Content | the JSON broke the rules: missing field, wrong type, out of range |
| 500 | Internal Server Error | the server crashed (a bug, or the model raised) |
| 503 | Service Unavailable | the server is up but cannot serve (e.g. model not loaded) |

4xx codes mean "the client must change the request"; 5xx codes mean "the server must be fixed". **JSON** is text
with objects (`{"a": 1}`), lists, strings, numbers, `true`/`false` and `null`. It has no NaN and no dates: send
missing values as `null` and dates as ISO strings (`"2025-09-30T00:00:00"`).

## Installing and opening it

In Colab and in the course environment, `pip install -r requirements.txt` installs `fastapi`, `uvicorn` (the
server) and `httpx` (needed by `TestClient`). On your own computer, in an activated virtual environment:

```bash
pip install fastapi uvicorn httpx
```

You do not need a server to develop or test: `TestClient` is enough (see below). To run a real server on your own
computer:

```bash
uvicorn churn_api:app --port 8000          # module churn_api.py, variable app
uvicorn --app-dir runs/week09 churn_api:app --port 8000 --reload   # file in another folder; restart on edits
```

Then open `http://127.0.0.1:8000/docs` in your browser. `127.0.0.1` (also `localhost`) means "this computer only":
nothing is reachable from other machines. Never run a service on `0.0.0.0` on a cloud machine unless you have
decided, and been authorised, to expose it (Week 11 covers safe deployment). In Colab, do not try to open ports;
use `TestClient`.

## The 20% you will use 80% of the time

### An app and endpoints

```python
from fastapi import FastAPI

app = FastAPI(title="Churn prediction API")

@app.get("/health")
def health():
    return {"status": "ok"}          # a dict becomes a JSON response with status 200
```

`@app.get(path)` and `@app.post(path)` register the function below as the handler for that method and path. The
function's return value (a dict, a list, a pydantic object) is converted to JSON.

### Calling it with TestClient

```python
from fastapi.testclient import TestClient

client = TestClient(app)
r = client.get("/health")
r.status_code        # 200
r.json()             # {'status': 'ok'}
r = client.post("/predict", json={"recency_days": 90, ...})   # json= sends a JSON body
r.text               # the raw body, useful in error messages
```

`TestClient` runs the app inside your Python process: no network, no port. By default, if your endpoint raises an
unexpected exception, `TestClient` re-raises it in your code (handy while debugging). To see what a real client
would see (a 500 response), use `TestClient(app, raise_server_exceptions=False)`.

### Path parameters and HTTPException

```python
from fastapi import HTTPException

@app.get("/customers/{customer_id}")
def get_customer(customer_id: int):                    # "42" -> 42; "abc" -> automatic 422
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail=f"customer {customer_id} not found")
    return {"customer_id": customer_id, **CUSTOMERS[customer_id]}
```

`raise HTTPException(status_code, detail)` stops the handler and returns `{"detail": ...}` with that status.

### pydantic models: describing data

```python
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

class CustomerFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")       # unknown fields are errors (catches typos)
    recency_days: int = Field(ge=0)                 # required int, >= 0
    spend_90d: float = Field(ge=0)
    segment: Literal["consumer", "small_business", "student"]
    note: Optional[str] = None                      # optional, defaults to None

f = CustomerFeatures(recency_days="12", spend_90d=3.5, segment="student")
f.recency_days           # 12 (the string was safely converted)
f.model_dump()           # back to a plain dict
```

Useful field rules: `ge`/`le` (>=, <=), `gt`/`lt` (strict), `min_length`/`max_length` (strings and lists).
A field without a default is required. Invalid data raises `pydantic.ValidationError`, whose `.errors()` is a
list of dicts with `loc` (where), `msg` (what) and `type`.

Useful types: `int`, `float`, `bool`, `str`, `list[float]`, `Literal[...]` (one of fixed values), `Optional[X]`
(X or None), and `FiniteFloat` (a float that is not infinity or NaN).

### Validating request bodies

```python
@app.post("/predict", response_model=PredictionOut)
def predict(features: CustomerFeatures):
    row = pd.DataFrame([features.model_dump()])
    p = float(model.predict_proba(row)[0, 1])
    return PredictionOut(churn_probability=p, will_churn=p >= 0.5, model_version="churn_v1")
```

Because the argument is typed with a pydantic class, FastAPI parses the JSON body, validates it, and either calls
your function with a valid object or answers 422 by itself. `response_model=` validates and documents what you
send back. Two habits from the course: build a **one-row DataFrame** so the pipeline finds its columns by name, and
convert NumPy numbers with `float(...)` / `int(...)` before returning them.

### Rules involving several fields

```python
from pydantic import model_validator

class ScoreRequest(BaseModel):
    readings: list[float]
    burn_in: int = 100

    @model_validator(mode="after")
    def long_enough(self):
        if len(self.readings) <= self.burn_in:
            raise ValueError("need more readings than burn_in")     # becomes a 422
        return self
```

### Loading the model once

```python
import os, joblib
from pathlib import Path

MODEL_DIR = Path(os.environ.get("CHURN_MODEL_DIR", "runs/week09/bundles/churn_v1"))
MODEL = joblib.load(MODEL_DIR / "model.joblib")   # at import time: once per process
VERSION = MODEL_DIR.name
```

Load at start-up, not per request: requests stay fast and a broken bundle fails immediately. Read locations and
settings from environment variables so the same code runs everywhere. Only load model files you produced
yourself (a pickle/joblib file can run code when loaded) and verify their checksum first (notebook 33).

### Errors that help the caller

```python
@app.post("/predict")
def predict(features: CustomerFeatures):
    if MODEL is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    try:
        p = float(MODEL.predict_proba(pd.DataFrame([features.model_dump()]))[0, 1])
    except Exception:
        raise HTTPException(status_code=500, detail="prediction failed")   # details go to the logs, not the client
    ...
```

One error format for all invalid requests:

```python
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def friendly(request, exc):
    problems = [{"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
                for e in exc.errors()]
    return JSONResponse(status_code=422, content={"error": "invalid input", "problems": problems})
```

### Testing an API with pytest

```python
import pytest
from fastapi.testclient import TestClient
from churn_service import app

VALID = {"recency_days": 90, "orders_90d": 1, "spend_90d": 40.0, "tenure_days": 300, "segment": "consumer"}

@pytest.fixture
def client():
    return TestClient(app)

def test_happy_path(client):
    body = client.post("/predict", json=VALID).json()
    assert 0 <= body["churn_probability"] <= 1

@pytest.mark.parametrize("payload", [dict(VALID, orders_90d=-1), dict(VALID, segment="vip")])
def test_bad_input_is_422(client, payload):
    assert client.post("/predict", json=payload).status_code == 422
```

Test the contract (status codes, ranges, required fields), not exact model outputs; use a stand-in model whose
answers you know. Every test should fail when the behaviour it protects is broken.

## Common errors and how to read them

| What you see | What it usually means | Fix |
|---|---|---|
| `422` with `"type": "missing"`, `"loc": ["body", "segment"]` | the request lacks a required field | send the field, or give it a default if it is truly optional |
| `422` with `"loc": ["body"]`, `"msg": "Field required"` | the request had no JSON body at all | use `client.post(path, json=...)`, not `data=` |
| `422` with `"type": "json_invalid"` | the body is not valid JSON | check quotes, commas, `true`/`null` spelling |
| `405 Method Not Allowed` | right path, wrong method | `/predict` is POST; `/health` is GET |
| `404 Not Found` on a path you defined | a typo in the path, or the decorator is on another app object | compare paths character by character |
| `ValueError: Out of range float values are not JSON compliant` | you returned NaN or infinity | check the model output; clients cannot receive NaN in JSON |
| `TypeError: Object of type int64 is not JSON serializable` | a NumPy number in a dict you built by hand | convert with `int(...)` / `float(...)` |
| `RuntimeError: The starlette.testclient module requires the httpx package` | `httpx` is not installed | `pip install httpx` |
| `Error loading ASGI app. Could not import module "churn_api"` (uvicorn) | uvicorn cannot find the file | run from the file's folder or pass `--app-dir` |
| `[Errno 98] Address already in use` (uvicorn) | another server uses the port | stop it (Ctrl+C in its terminal) or use `--port 8001` |

When a test fails, print `r.status_code` and `r.json()` first: FastAPI's 422 bodies say exactly which field is wrong.

## Cheat sheet

```python
# app and endpoints
from fastapi import FastAPI, HTTPException
app = FastAPI(title="...")
@app.get("/health")                           # read, no body
@app.post("/predict", response_model=Out)     # send a body; validate the answer
def predict(x: In): ...
raise HTTPException(status_code=404, detail="...")

# pydantic
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator
class In(BaseModel):
    model_config = ConfigDict(extra="forbid")
    n: int = Field(ge=0)                      # required, >= 0
    p: float = Field(0.5, gt=0, le=1)         # default 0.5, 0 < p <= 1
    kind: Literal["a", "b"]
    xs: list[FiniteFloat] = Field(max_length=10_000)
obj = In(**data); obj.model_dump()

# calling it
from fastapi.testclient import TestClient
c = TestClient(app)                           # raise_server_exceptions=False to see 500s as responses
r = c.post("/predict", json={...}); r.status_code; r.json(); r.text

# running it locally (not in Colab)
#   uvicorn module_name:app --port 8000 --reload     then open http://127.0.0.1:8000/docs
```

Status codes to remember: 200 OK · 404 not found · 405 wrong method · 422 invalid input · 500 server bug ·
503 not ready.

## Where to go next

* FastAPI tutorial: <https://fastapi.tiangolo.com/tutorial/> (first steps, path and body parameters, testing).
* pydantic documentation: <https://docs.pydantic.dev/latest/concepts/models/> (models, fields, validators).
* HTTP status codes reference: <https://developer.mozilla.org/en-US/docs/Web/HTTP/Status>.
* In this course: notebooks 33-36 (Week 9), then Week 10 puts the service in Docker and runs its tests in CI.
* Advanced track: notebooks 27-30 (online inference, validation, API testing, the packaged project service).
