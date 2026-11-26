"""Week 9 graders: serving models (notebooks 33-36).

Notebook 33 saves a model with its metadata and runs a batch job; 34 builds a FastAPI service; 35 tests it;
36 (project milestone 2) puts the SKAB burn-in z-score detector behind POST /score.

Grading never needs a network, a server or the SKAB download: APIs are exercised in-process with FastAPI's
TestClient, and the detector is checked on small synthetic sensor series. Reference versions below are written
independently of the notebook solutions so that tests check behaviour, not one way of writing it.
"""

import hashlib
import importlib.util
import inspect
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
import warnings
from pathlib import Path
from typing import Any, Literal, Optional

import numpy as np
import pandas as pd

from mlcourse.grader import exercise, register_quiz

FEATURES = ["recency_days", "orders_90d", "spend_90d", "tenure_days", "segment"]
NUMERIC = ["recency_days", "orders_90d", "spend_90d", "tenure_days"]
SEGMENTS = ["consumer", "small_business", "student"]
CUTOFF = pd.Timestamp("2025-09-30")


# ============================================================================ shared data and models
def churn_table(cutoff: pd.Timestamp = CUTOFF) -> pd.DataFrame:
    """The churn table of Weeks 4-5, compactly: one row per active customer, five features and the label.

    Active = at least one non-cancelled order on or before `cutoff`; churned = no non-cancelled order in the
    90 days after it. Built from data/course/shop.db (synthetic).
    """
    from mlcourse.sql import sql

    orders = sql("SELECT order_id, customer_id, order_date, status FROM orders", "shop")
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    items = sql("SELECT order_id, quantity, unit_price, discount FROM order_items", "shop")
    customers = sql("SELECT customer_id, signup_date, segment FROM customers", "shop")
    customers["signup_date"] = pd.to_datetime(customers["signup_date"])
    kept = orders[orders["status"] != "cancelled"].copy()
    value = (items["quantity"] * items["unit_price"] * (1 - items["discount"])).groupby(items["order_id"]).sum()
    kept["value"] = kept["order_id"].map(value).fillna(0.0)
    past = kept[kept["order_date"] <= cutoff]
    recent = past[past["order_date"] > cutoff - pd.Timedelta(days=90)]
    future = kept[(kept["order_date"] > cutoff) & (kept["order_date"] <= cutoff + pd.Timedelta(days=90))]
    t = pd.DataFrame(index=pd.Index(sorted(past["customer_id"].unique()), name="customer_id"))
    t["recency_days"] = (cutoff - past.groupby("customer_id")["order_date"].max()).dt.days
    t["orders_90d"] = recent.groupby("customer_id").size().reindex(t.index, fill_value=0)
    t["spend_90d"] = recent.groupby("customer_id")["value"].sum().reindex(t.index, fill_value=0.0).round(2)
    info = customers.set_index("customer_id")
    t["tenure_days"] = (cutoff - info["signup_date"]).dt.days.reindex(t.index)
    t["segment"] = info["segment"].reindex(t.index)
    t["churned"] = (~t.index.isin(future["customer_id"])).astype(int)
    return t.reset_index()


def make_pipeline():
    """The Week 4 pipeline: scale numbers, one-hot the segment, logistic regression."""
    from sklearn.compose import ColumnTransformer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    pre = ColumnTransformer([("num", StandardScaler(), NUMERIC),
                             ("cat", OneHotEncoder(handle_unknown="ignore"), ["segment"])])
    return Pipeline([("pre", pre), ("model", LogisticRegression(max_iter=1000))])


def train_churn_model(seed: int = 0):
    """Train the churn pipeline on a stratified 75% split. Returns (pipeline, test accuracy, train rows)."""
    from sklearn.model_selection import train_test_split

    t = churn_table()
    X, y = t[FEATURES], t["churned"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=seed, stratify=y)
    pipe = make_pipeline().fit(X_tr, y_tr)
    return pipe, float((pipe.predict(X_te) == y_te).mean()), len(X_tr)


class StubModel:
    """A stand-in for a trained model: churn probability = recency_days / 180, capped at 1.

    Tests use it because it is instant and predictable: you can work out the right answer by hand.
    """

    version = "stub-1"

    def predict_proba(self, X):
        r = np.asarray(pd.DataFrame(X)["recency_days"], dtype=float)
        p = np.clip(r / 180.0, 0.0, 1.0)
        return np.column_stack([1 - p, p])


class _BrokenModel:
    def predict_proba(self, X):
        raise RuntimeError("secret-internal-detail: matrix not invertible")


class _ShapeModel:
    """Probability from spend and segment, so tests notice columns being dropped or renamed."""

    def predict_proba(self, X):
        X = pd.DataFrame(X)
        missing = [c for c in FEATURES if c not in X.columns]
        if missing:
            raise KeyError(f"columns missing: {missing}")
        p = np.clip(0.05 + X["spend_90d"].astype(float) / 1000.0 + (X["segment"] == "student") * 0.3, 0, 1)
        return np.column_stack([1 - p, p.to_numpy()])


# ============================================================================ helpers
def _tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="w09_"))


def _not_attempted_fn(fn):
    if not callable(fn):
        raise AssertionError(f"expected a function, got {type(fn).__name__}")


def _client(app, raise_errors: bool = False):
    from fastapi.testclient import TestClient

    try:
        from fastapi import FastAPI
    except ImportError:  # pragma: no cover
        FastAPI = object
    assert isinstance(app, FastAPI), f"expected a FastAPI app object, got {type(app).__name__}"
    return TestClient(app, raise_server_exceptions=raise_errors)


def _sample_rows() -> pd.DataFrame:
    return pd.DataFrame({
        "customer_id": [1, 2, 3, 4, 5, 6],
        "recency_days": [10, 200, 45, 0, 90, 30],
        "orders_90d": [3, 0, 1, 5, 0, 2],
        "spend_90d": [120.5, 0.0, 33.0, 410.0, 0.0, 75.25],
        "tenure_days": [400, 800, 120, 30, 365, 60],
        "segment": ["consumer", "student", "small_business", "consumer", "student", "consumer"],
    })


GOOD = {"recency_days": 90, "orders_90d": 1, "spend_90d": 40.0, "tenure_days": 300, "segment": "consumer"}


def _detail_text(resp) -> str:
    try:
        return json.dumps(resp.json())
    except Exception:
        return resp.text


# ============================================================================ references (notebook 33)
def _ref_save_model(model, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    import joblib

    joblib.dump(model, path)
    return path


def _ref_load_model(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"no model file at {path}")
    import joblib

    return joblib.load(path)


def _ref_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _ref_verify(path, expected):
    got = _ref_sha256(path)
    if got != expected:
        raise ValueError(f"checksum mismatch for {path}")
    return True


def _ref_metadata(model, feature_names, metrics, train_rows):
    import platform
    from datetime import datetime, timezone

    import sklearn

    return {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "python_version": platform.python_version(), "sklearn_version": sklearn.__version__,
            "model_class": type(model).__name__, "features": list(feature_names),
            "metrics": {k: float(v) for k, v in metrics.items()}, "train_rows": int(train_rows)}


def _ref_save_bundle(model, metadata, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    _ref_save_model(model, folder / "model.joblib")
    meta = dict(metadata, sha256=_ref_sha256(folder / "model.joblib"))
    (folder / "metadata.json").write_text(json.dumps(meta, indent=2))
    return folder


def _ref_load_bundle(folder):
    import sklearn

    folder = Path(folder)
    meta_path, model_path = folder / "metadata.json", folder / "model.joblib"
    if not meta_path.is_file() or not model_path.is_file():
        raise FileNotFoundError(f"{folder} is not a complete bundle")
    meta = json.loads(meta_path.read_text())
    _ref_verify(model_path, meta["sha256"])
    if meta.get("sklearn_version") != sklearn.__version__:
        raise RuntimeError(f"bundle saved with scikit-learn {meta.get('sklearn_version')}, running {sklearn.__version__}")
    return _ref_load_model(model_path), meta


def _ref_missing_columns(df, required):
    return sorted(c for c in required if c not in df.columns)


def _ref_row_problems(df):
    out = []
    for _, row in df.iterrows():
        msg = ""
        for c in NUMERIC:
            v = row.get(c)
            if v is None or pd.isna(v):
                msg = f"{c} is missing"
                break
            if float(v) < 0:
                msg = f"{c} is negative"
                break
        if not msg and row.get("segment") not in SEGMENTS:
            msg = f"segment {row.get('segment')!r} is unknown"
        out.append(msg)
    return pd.Series(out, index=df.index, dtype=object)


def _ref_predict_batch(model, df, features=FEATURES):
    miss = _ref_missing_columns(df, list(features) + ["customer_id"])
    if miss:
        raise ValueError(f"input is missing columns: {miss}")
    problems = _ref_row_problems(df)
    ok = problems == ""
    prob = pd.Series(np.nan, index=df.index)
    if ok.any():
        prob[ok] = model.predict_proba(df.loc[ok, list(features)])[:, 1]
    return pd.DataFrame({"customer_id": df["customer_id"].to_numpy(), "churn_probability": prob.to_numpy(),
                         "status": np.where(ok, "ok", problems)})


def _ref_run_batch(bundle_folder, in_csv, out_csv):
    model, meta = _ref_load_bundle(bundle_folder)
    df = pd.read_csv(in_csv)
    res = _ref_predict_batch(model, df, meta["features"])
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(out_csv, index=False)
    n_ok = int((res["status"] == "ok").sum())
    return {"ok": n_ok, "rejected": len(res) - n_ok}


# ============================================================================ references (notebook 34)
def _ref_status_family(code):
    if not isinstance(code, int) or isinstance(code, bool) or not 100 <= code <= 599:
        raise ValueError(f"not an HTTP status code: {code!r}")
    return {1: "informational", 2: "success", 3: "redirect", 4: "client error", 5: "server error"}[code // 100]


def _ref_jsonable(record):
    out = {}
    for k, v in record.items():
        if isinstance(v, (np.bool_, bool)):
            out[k] = bool(v)
        elif isinstance(v, (np.integer,)):
            out[k] = int(v)
        elif isinstance(v, (float, np.floating)):
            out[k] = None if math.isnan(float(v)) else float(v)
        elif isinstance(v, pd.Timestamp):
            out[k] = v.isoformat()
        elif v is None or v is pd.NA or v is pd.NaT:
            out[k] = None
        else:
            out[k] = v
    return out


def _ref_models():
    from pydantic import BaseModel, ConfigDict, Field

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

    return CustomerFeatures, PredictionOut


REF_CustomerFeatures, REF_PredictionOut = _ref_models()


def _ref_health_app():
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


def _ref_lookup_app(table):
    from fastapi import FastAPI, HTTPException

    app = FastAPI()

    @app.get("/customers/{customer_id}")
    def lookup(customer_id: int):
        if customer_id not in table:
            raise HTTPException(status_code=404, detail=f"customer {customer_id} not found")
        return {"customer_id": customer_id, **table[customer_id]}

    return app


def _ref_predict_app(model, threshold=0.5, version="v1"):
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok", "model_version": version}

    @app.post("/predict", response_model=REF_PredictionOut)
    def predict(features: REF_CustomerFeatures):
        p = float(model.predict_proba(pd.DataFrame([features.model_dump()]))[0, 1])
        return REF_PredictionOut(churn_probability=p, will_churn=p >= threshold, model_version=version)

    return app


def _ref_call_predict(client, features):
    r = client.post("/predict", json=features)
    if r.status_code != 200:
        raise RuntimeError(f"prediction failed with status {r.status_code}: {r.text}")
    return r.json()


# ============================================================================ references (notebook 35)
def _ref_safe_app(model, threshold=0.5, version="v1"):
    from fastapi import FastAPI, HTTPException

    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok" if model is not None else "degraded", "model_loaded": model is not None}

    @app.post("/predict", response_model=REF_PredictionOut)
    def predict(features: REF_CustomerFeatures):
        if model is None:
            raise HTTPException(status_code=503, detail="model not loaded")
        try:
            p = float(model.predict_proba(pd.DataFrame([features.model_dump()]))[0, 1])
        except Exception:
            raise HTTPException(status_code=500, detail="prediction failed")
        return REF_PredictionOut(churn_probability=p, will_churn=p >= threshold, model_version=version)

    return app


def _ref_friendly(app):
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse

    @app.exception_handler(RequestValidationError)
    async def handler(request, exc):
        problems = [{"field": ".".join(str(p) for p in e["loc"] if p != "body") or "body", "message": e["msg"]}
                    for e in exc.errors()]
        return JSONResponse(status_code=422, content={"error": "invalid input", "problems": problems})

    return app


def _mutant_app(kind: str, threshold: float = 0.5, version: str = "v1"):
    """The correct service (kind='good') or one with a single planted bug."""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, ConfigDict, Field

    lax_extra = "allow" if kind == "extra_allowed" else "forbid"
    zero = 0 if kind == "missing_defaults" else ...
    lo = None if kind == "no_range" else 0
    seg_type = str if kind == "no_segment_check" else Literal["consumer", "small_business", "student"]
    rec_type = Any if kind == "any_type" else int

    class Features(BaseModel):
        model_config = ConfigDict(extra=lax_extra)
        recency_days: rec_type = Field(zero, ge=lo) if kind != "any_type" else Field(...)
        orders_90d: int = Field(zero, ge=lo)
        spend_90d: float = Field(zero, ge=lo)
        tenure_days: int = Field(zero, ge=lo)
        segment: seg_type = "consumer" if kind == "missing_defaults" else ...

    model = StubModel()
    app = FastAPI()

    @app.get("/health")
    def health():
        if kind == "health_broken":
            raise HTTPException(status_code=500, detail="boom")
        return {"status": "down" if kind == "health_wrong_body" else "ok", "model_version": version}

    @app.post("/predict")
    def predict(f: Features):
        row = f.model_dump()
        row = {k: row[k] for k in FEATURES}
        p = float(model.predict_proba(pd.DataFrame([row]))[0, 1])
        out = {"churn_probability": p * 100 if kind == "prob_percent" else p,
               "will_churn": (p < threshold) if kind == "inverted" else (p >= threshold),
               "model_version": version}
        if kind == "no_version":
            out.pop("model_version")
        return out

    return app


def buggy_app(kind: str = "good"):
    """The service from notebook 35 with one planted bug (see MUTANT_STORY), or the correct one (kind='good')."""
    return _mutant_app(kind)


# ============================================================================ references (notebook 36)
FLOW = "Volume Flow RateRMS"


def _ref_burn_in_stats(values, burn_in):
    v = np.asarray(values, dtype=float)
    if burn_in < 2 or len(v) < burn_in:
        raise ValueError(f"need at least burn_in={burn_in} values, got {len(v)}")
    b = v[:burn_in]
    return float(b.mean()), float(b.std())


def _ref_zscores(values, burn_in):
    mean, std = _ref_burn_in_stats(values, burn_in)
    if std == 0:
        raise ValueError("the burn-in window is constant, so z-scores are undefined")
    return np.abs((np.asarray(values, dtype=float) - mean) / std)


def _ref_alarms(values, burn_in=100, threshold=3.0, min_run=5):
    z = _ref_zscores(values, burn_in)
    above = z > threshold
    above[:burn_in] = False
    out, run = [], 0
    for i, a in enumerate(above):
        run = run + 1 if a else 0
        if run >= min_run:
            out.append(i)
    return out


def _ref_score_models():
    from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

    class ScoreRequest(BaseModel):
        model_config = ConfigDict(extra="forbid")
        readings: list[FiniteFloat] = Field(max_length=100_000)
        burn_in: int = Field(100, ge=10, le=10_000)
        threshold: float = Field(3.0, gt=0, le=50)
        min_run: int = Field(5, ge=1, le=100)

        @model_validator(mode="after")
        def long_enough(self):
            if len(self.readings) <= self.burn_in:
                raise ValueError(f"need more than burn_in={self.burn_in} readings, got {len(self.readings)}")
            return self

    class ScoreResponse(BaseModel):
        n: int
        n_alarms: int
        first_alarm: Optional[int]
        max_z: float

    return ScoreRequest, ScoreResponse


REF_ScoreRequest, REF_ScoreResponse = _ref_score_models()


def _ref_score_app(kind: str = "good"):
    from fastapi import FastAPI, HTTPException

    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok", "detector": "burn-in z-score"}

    if kind == "accepts_short":
        from pydantic import BaseModel

        class Req(BaseModel):
            readings: list[float]
            burn_in: int = 100
            threshold: float = 3.0
            min_run: int = 5
    else:
        Req = REF_ScoreRequest

    @app.post("/score", response_model=REF_ScoreResponse)
    def score(req: Req):
        v = np.asarray(req.readings, dtype=float)
        if len(v) <= req.burn_in:  # the planted bug: no 422, crash instead
            raise RuntimeError("index out of range")
        try:
            z = _ref_zscores(v, req.burn_in)
        except ValueError as err:
            if kind == "constant_500":
                raise RuntimeError("division by zero")
            raise HTTPException(status_code=422, detail=str(err))
        if kind == "alarms_in_burn_in":
            above = z > req.threshold
            idx, run = [], 0
            for i, a in enumerate(above):
                run = run + 1 if a else 0
                if run >= req.min_run:
                    idx.append(i)
        elif kind == "ignores_min_run":
            idx = _ref_alarms(v, req.burn_in, req.threshold, 1)
        else:
            idx = _ref_alarms(v, req.burn_in, req.threshold, req.min_run)
        return {"n": len(v), "n_alarms": len(idx), "first_alarm": idx[0] if idx else None,
                "max_z": float(z[req.burn_in:].max())}

    return app


def _ref_score_experiment(client, df, column=FLOW, **params):
    r = client.post("/score", json={"readings": [float(x) for x in df[column]], **params})
    if r.status_code != 200:
        raise RuntimeError(f"scoring failed with status {r.status_code}: {r.text}")
    first = r.json()["first_alarm"]
    start = int(np.argmax(df["anomaly"].to_numpy() == 1)) if "anomaly" in df and (df["anomaly"] == 1).any() else None
    delay = first - start if first is not None and start is not None else None
    return {"first_alarm": first, "anomaly_start": start, "delay": delay}


def synthetic_experiment(n=600, start=400, shift=3.0, noise=0.4, seed=0, base=32.0):
    """A synthetic SKAB-like experiment: flow rate around `base`, shifted by `shift` from row `start` on."""
    rng = np.random.default_rng(seed)
    flow = base + rng.normal(0, noise, n)
    anomaly = np.zeros(n, dtype=int)
    if start is not None:
        flow[start:] += shift
        anomaly[start:] = 1
    return pd.DataFrame({FLOW: flow.round(3), "anomaly": anomaly})


_REFERENCES = {
    "save_model": _ref_save_model, "load_model": _ref_load_model, "sha256_of": _ref_sha256,
    "verify_checksum": _ref_verify, "make_metadata": _ref_metadata, "save_bundle": _ref_save_bundle,
    "load_bundle": _ref_load_bundle, "missing_columns": _ref_missing_columns, "row_problems": _ref_row_problems,
    "predict_batch": _ref_predict_batch, "run_batch": _ref_run_batch,
    "status_family": _ref_status_family, "jsonable": _ref_jsonable, "make_health_app": _ref_health_app,
    "make_lookup_app": _ref_lookup_app, "make_predict_app": _ref_predict_app, "call_predict": _ref_call_predict,
    "make_app_safe": _ref_safe_app, "add_friendly_errors": _ref_friendly,
    "burn_in_stats": _ref_burn_in_stats, "zscores": _ref_zscores, "alarms": _ref_alarms,
    "make_score_app": lambda: _ref_score_app("good"), "score_experiment": _ref_score_experiment,
}


def use(fn, *args, **kwargs):
    """Call your function `fn`; if it is not written yet, use the course's reference version (and say so)."""
    try:
        return fn(*args, **kwargs)
    except NotImplementedError:
        name = getattr(fn, "__name__", "")
        if name not in _REFERENCES:
            raise
        print(f"(note: `{name}` is not finished yet, so the course's reference version was used here. "
              "Come back to that exercise.)")
        return _REFERENCES[name](*args, **kwargs)


# ============================================================================ notebook 33 tests
@exercise("w09.save_model", hint="Create the parent folder with Path(path).parent.mkdir(parents=True, exist_ok=True), "
          "then joblib.dump(model, path).")
def _t_save_model(fn):
    import joblib

    _not_attempted_fn(fn)
    d = _tmp()
    for target in [d / "m.joblib", d / "deep" / "er" / "model.joblib", str(d / "as_string.joblib")]:
        out = fn(StubModel(), target)
        assert Path(target).is_file(), f"no file was written at {target} (does your function create missing folders?)"
        assert out is not None and Path(out) == Path(target), "return the path of the file you wrote"
        loaded = joblib.load(target)
        X = _sample_rows()
        assert np.allclose(loaded.predict_proba(X), StubModel().predict_proba(X)), \
            "the file does not load back as the same model"
    shutil.rmtree(d, ignore_errors=True)


@exercise("w09.load_model", hint="Check Path(path).is_file() first and raise FileNotFoundError with the path in the "
          "message; otherwise return joblib.load(path).")
def _t_load_model(fn):
    import joblib

    _not_attempted_fn(fn)
    d = _tmp()
    joblib.dump(StubModel(), d / "ok.joblib")
    m = fn(d / "ok.joblib")
    assert hasattr(m, "predict_proba"), "loading a saved model should return the model object"
    m2 = fn(str(d / "ok.joblib"))
    assert hasattr(m2, "predict_proba"), "your function should accept a string path too"
    try:
        fn(d / "missing.joblib")
    except FileNotFoundError as err:
        assert "missing.joblib" in str(err), "the FileNotFoundError message should name the file that is missing"
    else:
        raise AssertionError("a missing file should raise FileNotFoundError, not return something")
    shutil.rmtree(d, ignore_errors=True)


@exercise("w09.sha256_of", hint="hashlib.sha256(); read the file in binary mode ('rb') and call .update() on each "
          "chunk; return .hexdigest().")
def _t_sha(fn):
    _not_attempted_fn(fn)
    d = _tmp()
    cases = {"empty.bin": b"", "small.txt": b"hello\n", "big.bin": os.urandom(300_000)}
    for name, data in cases.items():
        (d / name).write_bytes(data)
        got = fn(d / name)
        assert isinstance(got, str), f"return the digest as a hex string (got {type(got).__name__})"
        assert got == hashlib.sha256(data).hexdigest(), \
            f"wrong digest for a {len(data)}-byte file: are you reading in binary mode and hashing ALL of it?"
    shutil.rmtree(d, ignore_errors=True)


@exercise("w09.verify_checksum", hint="Compute the file's digest (your sha256_of) and compare with `expected`; raise "
          "ValueError when they differ.")
def _t_verify(fn):
    _not_attempted_fn(fn)
    d = _tmp()
    f = d / "model.joblib"
    f.write_bytes(b"model bytes v1")
    good = hashlib.sha256(b"model bytes v1").hexdigest()
    assert fn(f, good) is True, "a matching checksum should return True"
    for bad in [hashlib.sha256(b"other").hexdigest(), "0" * 64]:
        try:
            fn(f, bad)
        except ValueError:
            pass
        else:
            raise AssertionError("a checksum that does not match should raise ValueError")
    f.write_bytes(b"model bytes v1 tampered")
    try:
        fn(f, good)
    except ValueError:
        pass
    else:
        raise AssertionError("after the file changed, the old checksum must no longer verify")
    shutil.rmtree(d, ignore_errors=True)


@exercise("w09.make_metadata", hint="Use datetime.now(timezone.utc).isoformat(), platform.python_version() and "
          "sklearn.__version__; convert metrics values to float and train_rows to int.")
def _t_metadata(fn):
    import platform

    import sklearn

    _not_attempted_fn(fn)
    meta = fn(StubModel(), ["a", "b"], {"accuracy": np.float64(0.71), "auc": 0.75}, np.int64(645))
    assert isinstance(meta, dict), "return a dict"
    need = {"created_at", "python_version", "sklearn_version", "model_class", "features", "metrics", "train_rows"}
    missing = need - set(meta)
    assert not missing, f"metadata is missing keys: {sorted(missing)}"
    try:
        json.dumps(meta)
    except TypeError as err:
        raise AssertionError(f"metadata must be JSON-serialisable (convert NumPy numbers to float/int): {err}")
    assert meta["sklearn_version"] == sklearn.__version__, "sklearn_version should be the installed scikit-learn version"
    assert meta["python_version"] == platform.python_version(), "python_version should look like '3.11.9'"
    assert meta["model_class"] == "StubModel", "model_class should be the class name of the model, e.g. 'Pipeline'"
    assert list(meta["features"]) == ["a", "b"], "features should be the list of feature names, in order"
    assert meta["train_rows"] == 645 and meta["metrics"]["accuracy"] == 0.71, "train_rows and metrics are not stored"
    ts = pd.Timestamp(meta["created_at"])
    assert ts.tzinfo is not None, "created_at should include a time zone (use UTC)"
    assert abs((pd.Timestamp.now(tz="UTC") - ts).total_seconds()) < 300, "created_at should be the current time"
    meta2 = fn(StubModel(), ("x",), {}, 3)
    assert list(meta2["features"]) == ["x"] and json.dumps(meta2), "features should be stored as a list"


@exercise("w09.save_bundle", hint="mkdir the folder, save model.joblib, compute its sha256, then write metadata "
          "(plus the 'sha256' key) to metadata.json with json.dumps.")
def _t_save_bundle(fn):
    import joblib

    _not_attempted_fn(fn)
    d = _tmp() / "bundles" / "churn_v1"
    meta_in = {"features": FEATURES, "train_rows": 10}
    out = fn(StubModel(), dict(meta_in), d)
    assert out is not None and Path(out) == d, "return the bundle folder"
    assert (d / "model.joblib").is_file(), "the folder should contain model.joblib"
    assert (d / "metadata.json").is_file(), "the folder should contain metadata.json"
    meta = json.loads((d / "metadata.json").read_text())
    assert meta.get("features") == FEATURES and meta.get("train_rows") == 10, "metadata.json lost the metadata you passed"
    assert meta.get("sha256") == hashlib.sha256((d / "model.joblib").read_bytes()).hexdigest(), \
        "metadata.json needs a 'sha256' key holding the checksum of model.joblib (computed after saving it)"
    assert hasattr(joblib.load(d / "model.joblib"), "predict_proba"), "model.joblib does not load as the model"
    assert "sha256" not in meta_in, "do not change the caller's dict: copy it before adding sha256"


@exercise("w09.load_bundle", hint="Read metadata.json, verify the checksum BEFORE joblib.load, compare "
          "sklearn_version with sklearn.__version__, then load.")
def _t_load_bundle(fn):
    import sklearn

    _not_attempted_fn(fn)
    root = _tmp()
    good = _ref_save_bundle(StubModel(), {"features": FEATURES, "sklearn_version": sklearn.__version__}, root / "good")
    model, meta = fn(good)
    assert hasattr(model, "predict_proba") and meta.get("features") == FEATURES, "return (model, metadata) for a good bundle"
    # tampered model file
    bad = _ref_save_bundle(StubModel(), {"features": FEATURES, "sklearn_version": sklearn.__version__}, root / "tampered")
    with open(bad / "model.joblib", "ab") as fh:
        fh.write(b"\x00")
    try:
        fn(bad)
    except ValueError:
        pass
    except Exception as err:
        raise AssertionError(f"a tampered model file should raise ValueError (checksum), got {type(err).__name__}")
    else:
        raise AssertionError("a model file that no longer matches its checksum was loaded anyway")
    # version mismatch
    old = _ref_save_bundle(StubModel(), {"features": FEATURES, "sklearn_version": "0.0.1"}, root / "old")
    try:
        fn(old)
    except RuntimeError:
        pass
    else:
        raise AssertionError("a bundle saved with a different scikit-learn version should raise RuntimeError")
    # incomplete
    (root / "empty").mkdir()
    try:
        fn(root / "empty")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("a folder without metadata.json / model.joblib should raise FileNotFoundError")
    shutil.rmtree(root, ignore_errors=True)


@exercise("w09.missing_columns", hint="A list comprehension over `required`, keeping names not in df.columns; sort it.")
def _t_missing(fn):
    _not_attempted_fn(fn)
    df = _sample_rows()
    assert list(fn(df, FEATURES)) == [], "nothing is missing from a complete table"
    assert list(fn(df.drop(columns=["segment", "orders_90d"]), FEATURES)) == ["orders_90d", "segment"], \
        "return the missing names, sorted"
    assert list(fn(pd.DataFrame(), ["b", "a"])) == ["a", "b"], "an empty table is missing every required column"
    assert list(fn(df.assign(extra=1), ["recency_days"])) == [], "extra columns are fine; only report missing ones"


@exercise("w09.row_problems", hint="Loop over rows (df.iterrows()) and build one message per row: '' when fine, "
          "otherwise name the column, e.g. 'orders_90d is negative'.")
def _t_row_problems(fn):
    _not_attempted_fn(fn)
    df = _sample_rows()
    df.loc[1, "orders_90d"] = -2
    df.loc[2, "spend_90d"] = np.nan
    df.loc[4, "segment"] = "enterprise"
    df.index = [10, 11, 12, 13, 14, 15]
    got = fn(df)
    assert isinstance(got, pd.Series), "return a pandas Series with one message per row"
    assert list(got.index) == list(df.index), "the Series should have the same index as the input rows"
    got = got.fillna("")
    for i in [10, 13, 15]:
        assert got[i] == "", f"row {i} is valid but got the message {got[i]!r}"
    for i, col in [(11, "orders_90d"), (12, "spend_90d"), (14, "segment")]:
        assert got[i], f"row {i} has a bad {col} but no problem was reported"
        assert col in got[i], f"the message for row {i} should name the column ({col}); got {got[i]!r}"
    zero = _sample_rows().iloc[[3]]
    assert fn(zero).fillna("").iloc[0] == "", "zero is a valid value (only negative numbers are a problem)"
    empty = fn(_sample_rows().iloc[:0])
    assert len(empty) == 0, "an empty table has no problems"


@exercise("w09.predict_batch", hint="Check columns first (raise ValueError), then compute problems, predict only the "
          "rows with no problem (df.loc[ok, features]) and fill a probability column that is NaN elsewhere.")
def _t_predict_batch(fn):
    _not_attempted_fn(fn)
    m = StubModel()
    df = _sample_rows()
    df.loc[1, "orders_90d"] = -1
    df.loc[4, "segment"] = "robot"
    out = fn(m, df, FEATURES)
    assert isinstance(out, pd.DataFrame), "return a DataFrame"
    for c in ["customer_id", "churn_probability", "status"]:
        assert c in out.columns, f"the result needs a {c!r} column"
    assert len(out) == len(df), "one output row per input row, rejected ones included"
    assert list(out["customer_id"]) == list(df["customer_id"]), "keep the input order and customer ids"
    st = list(out["status"])
    assert [s == "ok" for s in st] == [True, False, True, True, False, True], \
        "status should be 'ok' for good rows and the problem message for rejected rows"
    probs = out["churn_probability"].to_numpy(dtype=float)
    assert np.isnan(probs[1]) and np.isnan(probs[4]), "rejected rows should have no probability (NaN)"
    want = m.predict_proba(df.iloc[[0, 2, 3, 5]][FEATURES])[:, 1]
    assert np.allclose(probs[[0, 2, 3, 5]], want), "probabilities for good rows are wrong (use column 1 of predict_proba)"
    allbad = _sample_rows().assign(orders_90d=-1)
    out2 = fn(m, allbad, FEATURES)
    assert len(out2) == 6 and (out2["status"] != "ok").all(), "a batch where every row is bad must still return a report"
    try:
        fn(m, _sample_rows().drop(columns=["tenure_days"]), FEATURES)
    except ValueError as err:
        assert "tenure_days" in str(err), "the error should name the missing column"
    else:
        raise AssertionError("a batch missing a required column should raise ValueError before predicting")
    shape = fn(_ShapeModel(), _sample_rows(), FEATURES)
    assert np.allclose(shape["churn_probability"], _ShapeModel().predict_proba(_sample_rows())[:, 1]), \
        "pass the model the feature columns by name"


@exercise("w09.run_batch", hint="load_bundle -> pd.read_csv -> predict_batch(model, df, meta['features']) -> "
          "to_csv(out_csv, index=False); count statuses.")
def _t_run_batch(fn):
    import sklearn

    _not_attempted_fn(fn)
    root = _tmp()
    b = _ref_save_bundle(StubModel(), {"features": FEATURES, "sklearn_version": sklearn.__version__}, root / "bundle")
    df = _sample_rows()
    df.loc[2, "recency_days"] = -5
    df.to_csv(root / "in.csv", index=False)
    res = fn(b, root / "in.csv", root / "out" / "scores.csv")
    assert isinstance(res, dict) and res.get("ok") == 5 and res.get("rejected") == 1, \
        f"expected {{'ok': 5, 'rejected': 1}}, got {res}"
    out = pd.read_csv(root / "out" / "scores.csv")
    assert len(out) == 6 and "churn_probability" in out.columns, "the output CSV should have one scored row per input row"
    assert "Unnamed: 0" not in out.columns, "write the CSV without the index (index=False)"
    with open(b / "model.joblib", "ab") as fh:
        fh.write(b"x")
    try:
        fn(b, root / "in.csv", root / "out2.csv")
    except ValueError:
        pass
    else:
        raise AssertionError("the batch job should refuse a bundle whose checksum does not match")
    shutil.rmtree(root, ignore_errors=True)


# ============================================================================ notebook 34 tests
@exercise("w09.status_family", hint="Integer-divide the code by 100; check 100 <= code <= 599 first.")
def _t_status_family(fn):
    _not_attempted_fn(fn)
    for code, fam in [(200, "success"), (201, "success"), (204, "success"), (301, "redirect"), (404, "client error"),
                      (422, "client error"), (400, "client error"), (500, "server error"), (503, "server error"),
                      (599, "server error"), (299, "success")]:
        got = fn(code)
        assert got == fam, f"{code} should be {fam!r}, got {got!r}"
    for bad in [0, 99, 600, 1000, -200]:
        try:
            fn(bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} is not an HTTP status code: raise ValueError")


@exercise("w09.jsonable", hint="Check isinstance(v, np.integer), np.floating (NaN -> None), np.bool_, pd.Timestamp; "
          "leave plain Python values alone.")
def _t_jsonable(fn):
    _not_attempted_fn(fn)
    rec = {"customer_id": np.int64(7), "p": np.float64(0.25), "flag": np.bool_(True), "name": "Ana",
           "missing": float("nan"), "when": pd.Timestamp("2025-09-30"), "n": 3, "x": 1.5, "nothing": None,
           "np_nan": np.float32("nan")}
    got = fn(dict(rec))
    try:
        text = json.dumps(got, allow_nan=False)
    except (TypeError, ValueError) as err:
        raise AssertionError(f"the result still cannot be turned into strict JSON: {err}")
    back = json.loads(text)
    assert back["customer_id"] == 7 and back["p"] == 0.25 and back["flag"] is True, "numeric values changed"
    assert back["missing"] is None and back["np_nan"] is None, "NaN should become None (JSON null)"
    assert str(back["when"]).startswith("2025-09-30"), "timestamps should become ISO strings like '2025-09-30T00:00:00'"
    assert back["name"] == "Ana" and back["n"] == 3 and back["x"] == 1.5 and back["nothing"] is None, \
        "plain Python values should pass through unchanged"
    assert set(got) == set(rec), "keep every key"


@exercise("w09.make_health_app", hint="app = FastAPI(); decorate a function with @app.get('/health') that returns "
          "{'status': 'ok'}; return app.")
def _t_health(fn):
    _not_attempted_fn(fn)
    c = _client(fn())
    r = c.get("/health")
    assert r.status_code == 200, f"GET /health should return status 200, got {r.status_code}"
    assert r.json() == {"status": "ok"}, f"GET /health should return {{'status': 'ok'}}, got {r.json()}"
    assert c.get("/nothing-here").status_code == 404, "other paths should not exist (404)"
    assert c.post("/health").status_code == 405, "/health should only answer GET (POST gives 405)"
    assert fn() is not fn(), "make_health_app() should build a new app each time it is called"


@exercise("w09.make_lookup_app", hint="Path parameter: @app.get('/customers/{customer_id}') with a function argument "
          "customer_id: int; raise HTTPException(status_code=404, detail=...) when it is not in the table.")
def _t_lookup(fn):
    _not_attempted_fn(fn)
    for table in [{1: {"segment": "student"}, 2: {"segment": "consumer", "city": "Oslo"}},
                  {42: {"segment": "small_business"}}]:
        c = _client(fn(table))
        for cid, rec in table.items():
            r = c.get(f"/customers/{cid}")
            assert r.status_code == 200, f"GET /customers/{cid} should be 200, got {r.status_code}"
            body = r.json()
            assert body.get("customer_id") == cid, "include customer_id (as a number) in the response"
            for k, v in rec.items():
                assert body.get(k) == v, f"the response for customer {cid} should include {k}={v!r}"
        r = c.get("/customers/999")
        assert r.status_code == 404, f"an unknown customer should give 404, got {r.status_code}"
        assert "detail" in r.json(), "use HTTPException so the 404 body has a 'detail' message"
        r = c.get("/customers/abc")
        assert r.status_code == 422, "a non-numeric id should be rejected with 422 (declare customer_id: int)"


def _check_features_class(cls):
    from pydantic import BaseModel, ValidationError

    if not (inspect.isclass(cls) and issubclass(cls, BaseModel)):
        raise AssertionError("CustomerFeatures should be a class that inherits from pydantic's BaseModel")
    if not cls.model_fields:
        raise NotImplementedError
    obj = cls(**GOOD)
    for k, v in GOOD.items():
        assert getattr(obj, k) == v, f"a valid input should keep {k}={v!r}"
    bad_cases = [
        ({k: v for k, v in GOOD.items() if k != "tenure_days"}, "a missing field (tenure_days)"),
        (dict(GOOD, orders_90d=-1), "a negative orders_90d"),
        (dict(GOOD, spend_90d=-0.01), "a negative spend_90d"),
        (dict(GOOD, recency_days=-3), "a negative recency_days"),
        (dict(GOOD, recency_days="soon"), "a non-number recency_days ('soon')"),
        (dict(GOOD, segment="enterprise"), "an unknown segment ('enterprise')"),
        (dict(GOOD, segmnt="consumer"), "an unexpected extra field (a typo: 'segmnt')"),
    ]
    for data, what in bad_cases:
        try:
            cls(**data)
        except ValidationError:
            continue
        raise AssertionError(f"{what} should be rejected with a ValidationError")
    for seg in SEGMENTS:
        cls(**dict(GOOD, segment=seg))
    cls(**dict(GOOD, recency_days=0, orders_90d=0, spend_90d=0, tenure_days=0))


@exercise("w09.customer_features", hint="Field(ge=0) for each number, Literal['consumer', 'small_business', 'student'] "
          "for segment, and model_config = ConfigDict(extra='forbid').")
def _t_customer_features(cls):
    _check_features_class(cls)


@exercise("w09.prediction_out", hint="churn_probability: float = Field(ge=0, le=1); will_churn: bool; "
          "model_version: str.")
def _t_prediction_out(cls):
    from pydantic import BaseModel, ValidationError

    if not (inspect.isclass(cls) and issubclass(cls, BaseModel)):
        raise AssertionError("PredictionOut should be a pydantic BaseModel class")
    if not cls.model_fields:
        raise NotImplementedError
    ok = cls(churn_probability=0.3, will_churn=False, model_version="v1")
    assert ok.churn_probability == 0.3 and ok.will_churn is False and ok.model_version == "v1", "valid values changed"
    cls(churn_probability=0.0, will_churn=False, model_version="v1")
    cls(churn_probability=1.0, will_churn=True, model_version="v2")
    for data, what in [(dict(churn_probability=1.2, will_churn=True, model_version="v1"), "a probability of 1.2"),
                       (dict(churn_probability=-0.1, will_churn=False, model_version="v1"), "a probability of -0.1"),
                       (dict(churn_probability=0.5, will_churn=True), "a missing model_version"),
                       (dict(churn_probability=0.5, model_version="v1"), "a missing will_churn")]:
        try:
            cls(**data)
        except ValidationError:
            continue
        raise AssertionError(f"{what} should be rejected")


@exercise("w09.make_predict_app", hint="Inside the function: app = FastAPI(); @app.post('/predict', "
          "response_model=PredictionOut) taking `features: CustomerFeatures`; build a one-row DataFrame from "
          "features.model_dump(); p = model.predict_proba(row)[0, 1].")
def _t_predict_app(fn):
    _not_attempted_fn(fn)
    m = StubModel()
    for threshold, version in [(0.5, "v1"), (0.3, "2025-10-churn")]:
        c = _client(fn(m, threshold=threshold, version=version))
        h = c.get("/health")
        assert h.status_code == 200 and h.json().get("status") == "ok", "GET /health should return status 'ok'"
        assert h.json().get("model_version") == version, "GET /health should report the model_version"
        for rec in [36, 72, 90, 180, 400, 0]:
            r = c.post("/predict", json=dict(GOOD, recency_days=rec))
            assert r.status_code == 200, f"a valid request returned {r.status_code}: {_detail_text(r)[:200]}"
            body = r.json()
            p = min(rec / 180, 1.0)
            assert abs(body.get("churn_probability", -1) - p) < 1e-9, \
                f"for recency_days={rec} the stand-in model gives {p:.3f}; your API returned {body.get('churn_probability')}"
            assert body.get("will_churn") == (p >= threshold), \
                f"will_churn should be True exactly when the probability is >= threshold ({threshold})"
            assert body.get("model_version") == version, "every prediction should carry the model_version"
        for bad in [dict(GOOD, orders_90d=-1), {k: v for k, v in GOOD.items() if k != "segment"},
                    dict(GOOD, segment="vip"), dict(GOOD, recency_days="soon")]:
            r = c.post("/predict", json=bad)
            assert r.status_code == 422, f"an invalid request should get 422 (use CustomerFeatures), got {r.status_code}"
    c = _client(fn(_ShapeModel()))
    r = c.post("/predict", json=dict(GOOD, spend_90d=200.0, segment="student"))
    assert r.status_code == 200 and abs(r.json()["churn_probability"] - 0.55) < 1e-9, \
        "the model should receive every feature column by name (build the DataFrame from features.model_dump())"


@exercise("w09.call_predict", hint="r = client.post('/predict', json=features); if r.status_code != 200 raise "
          "RuntimeError with the code; else return r.json().")
def _t_call_predict(fn):
    _not_attempted_fn(fn)
    c = _client(_ref_predict_app(StubModel(), 0.5, "v9"))
    out = fn(c, dict(GOOD, recency_days=90))
    assert isinstance(out, dict) and out.get("model_version") == "v9", "return the parsed JSON body as a dict"
    assert abs(out["churn_probability"] - 0.5) < 1e-9, "the probability does not match the service's answer"
    try:
        fn(c, dict(GOOD, orders_90d=-4))
    except RuntimeError as err:
        assert "422" in str(err), "the RuntimeError message should include the status code"
    else:
        raise AssertionError("a rejected request (422) should raise RuntimeError, not return the error body")


def _import_file(path: Path, env: dict | None = None):
    old = {k: os.environ.get(k) for k in (env or {})}
    os.environ.update(env or {})
    try:
        name = f"_w09_student_{uuid.uuid4().hex[:8]}"
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@exercise("w09.api_file", hint="The file must create `app` at import time, reading the bundle folder from "
          "os.environ.get('CHURN_MODEL_DIR', ...) and loading model.joblib and metadata.json ONCE, outside the "
          "endpoint functions.")
def _t_api_file(path):
    import sklearn

    path = Path(path)
    assert path.is_file(), f"no file at {path}: run the %%writefile cell first"
    root = _tmp()
    bundle = _ref_save_bundle(StubModel(), {"features": FEATURES, "sklearn_version": sklearn.__version__},
                              root / "churn_test_bundle")
    mod = _import_file(path, {"CHURN_MODEL_DIR": str(bundle)})
    assert hasattr(mod, "app"), "the file should define a variable called `app`"
    c = _client(mod.app)
    h = c.get("/health")
    assert h.status_code == 200 and h.json().get("status") == "ok", "GET /health should return status 'ok'"
    assert h.json().get("model_version") == "churn_test_bundle", \
        "model_version should be the bundle folder's name (read CHURN_MODEL_DIR, don't hard-code the path)"
    r = c.post("/predict", json=dict(GOOD, recency_days=45))
    assert r.status_code == 200, f"POST /predict returned {r.status_code}: {_detail_text(r)[:200]}"
    assert abs(r.json()["churn_probability"] - 0.25) < 1e-9, \
        "the service did not use the model in CHURN_MODEL_DIR (the stand-in model gives 0.25 here)"
    assert c.post("/predict", json=dict(GOOD, tenure_days=-1)).status_code == 422, "invalid input should get 422"
    src = path.read_text()
    assert "joblib.load" in src or "load_bundle" in src, "load the model from the bundle (joblib.load)"
    shutil.rmtree(root, ignore_errors=True)


# ============================================================================ notebook 35 tests
def _run_test(test, kind: str) -> tuple[bool, str]:
    """Run a student's test function against the good service or a mutant. (passed, message)."""
    c = _client(_mutant_app(kind))
    try:
        test(c)
    except NotImplementedError:
        raise
    except AssertionError as err:
        return False, f"AssertionError: {err}"
    except Exception as err:
        return False, f"{type(err).__name__}: {err}"
    return True, ""


def _grade_tests(tests: list, must_catch: list[str], what: str):
    for t in tests:
        if not callable(t):
            raise AssertionError(f"expected test functions, got {type(t).__name__}")
    for t in tests:
        ok, msg = _run_test(t, "good")
        assert ok, (f"your test {t.__name__} FAILS on the correct service, so it would block a good release. "
                    f"It raised {msg[:200]}")
    for kind in must_catch:
        if all(_run_test(t, kind)[0] for t in tests):
            raise AssertionError(f"{what} still passes when the service has this bug: {MUTANT_STORY[kind]}")


MUTANT_STORY = {
    "health_broken": "GET /health answers with status 500",
    "health_wrong_body": "GET /health answers 200 but says the service is 'down'",
    "prob_percent": "the probability is returned as a percentage (e.g. 50.0 instead of 0.5)",
    "inverted": "will_churn is True when the probability is BELOW the threshold",
    "no_version": "the response forgets model_version",
    "missing_defaults": "a missing field is silently filled with 0 instead of being rejected",
    "any_type": "recency_days accepts any type, so 'soon' reaches the model",
    "no_range": "negative numbers are accepted",
    "no_segment_check": "any segment text is accepted, e.g. 'vip'",
    "extra_allowed": "unexpected extra fields (typos) are silently ignored",
}


@exercise("w09.test_health", hint="r = client.get('/health'); assert r.status_code == 200; assert r.json()['status'] == 'ok'.")
def _t_test_health(test):
    _grade_tests([test], ["health_broken", "health_wrong_body"], "your test")


@exercise("w09.test_predict_happy", hint="Post a valid payload; check the status, that 0 <= probability <= 1, that "
          "will_churn == (probability >= 0.5), and that model_version is present.")
def _t_test_happy(test):
    _grade_tests([test], ["prob_percent", "inverted", "no_version"], "your test")


@exercise("w09.test_missing_field", hint="Copy a valid payload, delete one key, post it, and assert the status is 422.")
def _t_test_missing(test):
    _grade_tests([test], ["missing_defaults"], "your test")


@exercise("w09.test_wrong_type", hint="Send recency_days='soon' and assert 422 (not 500, not 200).")
def _t_test_type(test):
    _grade_tests([test], ["any_type"], "your test")


@exercise("w09.test_out_of_range", hint="Send a negative number for one feature and assert 422.")
def _t_test_range(test):
    _grade_tests([test], ["no_range"], "your test")


@exercise("w09.bad_payloads", hint="Each case is a whole JSON body (a dict). Start from a valid payload and break one "
          "thing per case: missing key, wrong type, negative number, unknown segment, extra key.")
def _t_bad_payloads(cases):
    if not isinstance(cases, (list, tuple)):
        raise AssertionError("BAD_PAYLOADS should be a list of dicts")
    if not cases:
        raise NotImplementedError
    assert all(isinstance(p, dict) for p in cases), "each case should be a dict (a JSON body)"
    assert len(cases) >= 5, f"write at least 5 cases (you have {len(cases)})"
    good = _client(_mutant_app("good"))
    for p in cases:
        r = good.post("/predict", json=p)
        assert r.status_code == 422, (f"this case is accepted by the correct service ({r.status_code}), so it is not a "
                                      f"bad payload: {p}")
    for kind in ["missing_defaults", "any_type", "no_range", "no_segment_check", "extra_allowed"]:
        c = _client(_mutant_app(kind))
        if all(c.post("/predict", json=p).status_code == 422 for p in cases):
            raise AssertionError(f"no case catches this bug: {MUTANT_STORY[kind]}")


@exercise("w09.make_app_safe", hint="If model is None: /health reports status 'degraded' and model_loaded False, and "
          "/predict raises HTTPException(503). Wrap predict_proba in try/except and raise HTTPException(500, "
          "detail='prediction failed').")
def _t_safe(fn):
    _not_attempted_fn(fn)
    c = _client(fn(StubModel()))
    h = c.get("/health")
    assert h.status_code == 200 and h.json().get("status") == "ok" and h.json().get("model_loaded") is True, \
        "with a model, /health should say status 'ok' and model_loaded true"
    r = c.post("/predict", json=GOOD)
    assert r.status_code == 200 and abs(r.json()["churn_probability"] - 0.5) < 1e-9, "normal predictions should still work"
    assert c.post("/predict", json=dict(GOOD, orders_90d=-1)).status_code == 422, "bad input should still get 422"
    c = _client(fn(None))
    h = c.get("/health")
    assert h.status_code == 200, "/health should still answer (200) when the model is missing: it reports, it does not crash"
    assert h.json().get("model_loaded") is False and h.json().get("status") == "degraded", \
        "without a model, /health should say status 'degraded' and model_loaded false"
    r = c.post("/predict", json=GOOD)
    assert r.status_code == 503, f"predicting without a model should give 503 Service Unavailable, got {r.status_code}"
    assert "model" in str(r.json().get("detail", "")).lower(), "the 503 detail should say the model is not loaded"
    c = _client(fn(_BrokenModel()))
    r = c.post("/predict", json=GOOD)
    assert r.status_code == 500, f"a model that crashes should give 500, got {r.status_code}"
    body = _detail_text(r)
    assert "secret-internal-detail" not in body, "do not send the internal exception text to the client"
    assert r.headers.get("content-type", "").startswith("application/json") and "detail" in r.json(), \
        "return a JSON error with a short 'detail' (raise HTTPException), not a bare crash"


@exercise("w09.add_friendly_errors", hint="@app.exception_handler(RequestValidationError) on an async function "
          "(request, exc) returning JSONResponse(status_code=422, content={...}); build problems from exc.errors().")
def _t_friendly(fn):
    _not_attempted_fn(fn)
    app = fn(_ref_predict_app(StubModel()))
    c = _client(app)
    assert c.post("/predict", json=GOOD).status_code == 200, "valid requests should be unaffected"
    for bad, field in [(dict(GOOD, orders_90d=-1), "orders_90d"), (dict(GOOD, segment="vip"), "segment"),
                       ({k: v for k, v in GOOD.items() if k != "tenure_days"}, "tenure_days")]:
        r = c.post("/predict", json=bad)
        assert r.status_code == 422, f"invalid input should still return 422, got {r.status_code}"
        body = r.json()
        assert body.get("error") == "invalid input", "the body should have \"error\": \"invalid input\""
        probs = body.get("problems")
        assert isinstance(probs, list) and probs, "the body should have a non-empty list called problems"
        assert all(isinstance(p, dict) and "field" in p and "message" in p for p in probs), \
            "each problem should be a dict with 'field' and 'message'"
        fields = [p["field"] for p in probs]
        assert field in fields, f"for this request the problem field should be {field!r} (got {fields}); drop 'body'"
    r = c.post("/predict", json=dict(GOOD, orders_90d=-1, recency_days="x"))
    assert len(r.json()["problems"]) == 2, "report every problem in the request, not just the first"


SERVICE_TEMPLATE = '''"""churn_service: the API under test (written by the grader; a stand-in model keeps it fast)."""
from typing import Literal, Any
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field


class StubModel:
    def predict_proba(self, X):
        p = np.clip(np.asarray(X["recency_days"], dtype=float) / 180.0, 0, 1)
        return np.column_stack([1 - p, p])


class CustomerFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recency_days: int = Field(ge=0)
    orders_90d: int = Field(ge=0)
    spend_90d: float = Field(ge=0)
    tenure_days: int = Field(ge=0)
    segment: Literal["consumer", "small_business", "student"]


model = StubModel()
THRESHOLD = 0.5
app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model is not None}


@app.post("/predict")
def predict(f: CustomerFeatures):
    p = float(model.predict_proba(pd.DataFrame([f.model_dump()]))[0, 1])
    return {"churn_probability": p, "will_churn": p >= THRESHOLD, "model_version": "v1"}
'''

SERVICE_MUTANTS = {
    "good": [],
    "no_range": [("Field(ge=0)", "Field()")],
    "inverted": [("p >= THRESHOLD", "p < THRESHOLD")],
    "percent": [('"churn_probability": p,', '"churn_probability": p * 100,')],
}


def service_source(kind: str = "good") -> str:
    src = SERVICE_TEMPLATE
    for old, new in SERVICE_MUTANTS[kind]:
        assert old in src
        src = src.replace(old, new)
    return src


@exercise("w09.pytest_file", hint="The file needs a @pytest.fixture called client that returns "
          "TestClient(app) (with `from churn_service import app`), and test_ functions that take `client`.")
def _t_pytest_file(path):
    path = Path(path)
    assert path.is_file(), f"no file at {path}: run the %%writefile cell first"
    src = path.read_text()
    if "def test_" not in src:
        raise NotImplementedError
    results, procs, dirs = {}, {}, []
    for kind in SERVICE_MUTANTS:  # run the four pytest sessions in parallel: about 1-2 s in total
        d = _tmp()
        dirs.append(d)
        (d / "churn_service.py").write_text(service_source(kind))
        shutil.copy(path, d / "test_churn_service.py")
        procs[kind] = subprocess.Popen([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                        "test_churn_service.py"], cwd=d, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True)
    for kind, proc in procs.items():
        out, _ = proc.communicate(timeout=120)
        results[kind] = (proc.returncode, out[-600:])
    for d in dirs:
        shutil.rmtree(d, ignore_errors=True)
    code, out = results["good"]
    assert code != 5, "pytest found no tests: name the functions test_something and the file test_*.py"
    assert code == 0, f"your tests fail on the correct service. pytest said:\n{out}"
    n = sum(1 for line in src.splitlines() if line.lstrip().startswith("def test_"))
    assert n >= 3, f"write at least 3 test functions (found {n})"
    missed = [k for k in ("no_range", "inverted", "percent") if results[k][0] == 0]
    stories = {"no_range": "negative numbers are accepted", "inverted": "will_churn is inverted",
               "percent": "the probability is returned as a percentage"}
    assert not missed, "your test file still passes when the service has this bug: " + \
        "; ".join(stories[k] for k in missed)


# ============================================================================ notebook 36 tests
def _series(n=300, seed=1, base=50.0, noise=1.0):
    return list(np.round(base + np.random.default_rng(seed).normal(0, noise, n), 4))


@exercise("w09.burn_in_stats", hint="Take values[:burn_in] as a NumPy array and return (mean, std) with the default "
          "np.std (ddof=0); raise ValueError when there are fewer than burn_in values.")
def _t_burn_stats(fn):
    _not_attempted_fn(fn)
    for seed, burn in [(1, 100), (2, 20), (3, 250)]:
        v = _series(300, seed)
        got = fn(v, burn)
        want = _ref_burn_in_stats(v, burn)
        assert isinstance(got, tuple) and len(got) == 2, "return a tuple (mean, std)"
        assert abs(got[0] - want[0]) < 1e-9, "the mean should use only the first burn_in values"
        assert abs(got[1] - want[1]) < 1e-9, \
            "the std is off: use only the first burn_in values and np.std's default (ddof=0), as the batch code does"
    got = fn(np.array([1.0, 2.0, 3.0, 100.0]), 3)
    assert abs(got[0] - 2.0) < 1e-12, "accept a NumPy array too, and ignore values after the burn-in"
    for bad in [([1.0, 2.0], 5), ([], 10)]:
        try:
            fn(*bad)
        except ValueError:
            continue
        raise AssertionError("fewer values than burn_in should raise ValueError")


@exercise("w09.zscores", hint="(values - mean) / std using the burn-in stats, then np.abs; raise ValueError if std == 0.")
def _t_zscores(fn):
    _not_attempted_fn(fn)
    for seed, burn in [(4, 100), (5, 30)]:
        v = _series(250, seed)
        got = np.asarray(fn(v, burn), dtype=float)
        want = _ref_zscores(v, burn)
        assert got.shape == want.shape, f"return one z-score per value ({len(v)}), got shape {got.shape}"
        assert np.allclose(got, want), "z-scores are wrong: |value - burn-in mean| / burn-in std, for EVERY value"
    try:
        fn([5.0] * 50 + [6.0] * 10, 50)
    except ValueError as err:
        assert str(err), "give the ValueError a message"
    else:
        raise AssertionError("a constant burn-in window (std 0) should raise ValueError, not divide by zero")


@exercise("w09.alarms", hint="Mark z > threshold, set the first burn_in marks to False, count consecutive marks, and "
          "record index i whenever the run length reaches min_run or more.")
def _t_alarms(fn):
    _not_attempted_fn(fn)
    for seed, start, shift in [(0, 400, 3.0), (1, 300, -4.0), (2, None, 0.0), (3, 150, 6.0)]:
        df = synthetic_experiment(600, start, shift, seed=seed)
        v = df[FLOW].tolist()
        for params in [dict(burn_in=100, threshold=3.0, min_run=5), dict(burn_in=120, threshold=2.0, min_run=1),
                       dict(burn_in=50, threshold=4.0, min_run=10)]:
            got = [int(i) for i in fn(v, **params)]
            want = _ref_alarms(v, **params)
            if got != want:
                early = [i for i in got if i < params["burn_in"]]
                assert not early, f"alarms inside the burn-in ({early[:3]}...): points before burn_in never alarm"
                assert len(got) == len(want), (f"expected {len(want)} alarm indices with {params}, got {len(got)}: "
                                               "check the run counting (min_run consecutive points above threshold)")
                raise AssertionError(f"alarm indices differ from the expected ones with {params}")
    spike = [0.0, 1.0] * 60 + [50.0] + [0.0, 1.0] * 20
    assert [int(i) for i in fn(spike, burn_in=100, threshold=3.0, min_run=2)] == [], \
        "a single spike should not alarm when min_run=2"


@exercise("w09.make_score_app", hint="Define ScoreRequest with readings: list[FiniteFloat] and a model_validator "
          "that checks len(readings) > burn_in; the /score endpoint calls your alarms() and zscores(); turn a "
          "ValueError from a constant burn-in into HTTPException(422).")
def _t_score_app(fn):
    _not_attempted_fn(fn)
    c = _client(fn())
    h = c.get("/health")
    assert h.status_code == 200 and h.json().get("status") == "ok", "GET /health should return status 'ok'"
    for seed, start, shift, params in [(0, 400, 3.0, {}), (1, 300, -4.0, {"threshold": 2.5}),
                                       (2, None, 0.0, {"min_run": 1}), (3, 200, 5.0, {"burn_in": 150})]:
        df = synthetic_experiment(600, start, shift, seed=seed)
        v = df[FLOW].tolist()
        r = c.post("/score", json={"readings": v, **params})
        assert r.status_code == 200, f"a valid request returned {r.status_code}: {_detail_text(r)[:200]}"
        body = r.json()
        full = dict(burn_in=100, threshold=3.0, min_run=5)
        full.update(params)
        want = _ref_alarms(v, **full)
        z = _ref_zscores(v, full["burn_in"])
        assert body.get("n") == len(v), "n should be the number of readings received"
        assert body.get("n_alarms") == len(want), f"n_alarms is {body.get('n_alarms')}, expected {len(want)} with {params or 'defaults'}"
        assert body.get("first_alarm") == (want[0] if want else None), "first_alarm should be the first alarm index or null"
        assert abs(body.get("max_z", -1) - float(z[full['burn_in']:].max())) < 1e-6, \
            "max_z should be the largest |z| AFTER the burn-in"
    short = c.post("/score", json={"readings": [1.0, 2.0, 3.0]})
    assert short.status_code == 422, f"too few readings (3 with burn_in 100) should get 422, got {short.status_code}"
    for bad, what in [({"readings": _series(200) + [None]}, "a null reading"),
                      ({"readings": _series(200), "threshold": 0}, "threshold 0"),
                      ({"readings": _series(200), "burn_in": 5}, "burn_in 5"),
                      ({"readings": _series(200), "thresold": 3}, "a misspelled field"),
                      ({}, "a request without readings")]:
        r = c.post("/score", json=bad)
        assert r.status_code == 422, f"{what} should be rejected with 422, got {r.status_code}"
    const = c.post("/score", json={"readings": [32.0] * 150 + [33.0] * 20})
    assert const.status_code == 422, f"a constant burn-in should be a clear 422, got {const.status_code}"
    assert "constant" in _detail_text(const).lower(), "say in the 422 detail that the burn-in window is constant"


@exercise("w09.score_experiment", hint="Post df[column] as a list of floats plus **params; the anomaly start is the "
          "first index where df['anomaly'] == 1; delay = first_alarm - start when both exist.")
def _t_score_experiment(fn):
    _not_attempted_fn(fn)
    c = _client(_ref_score_app("good"))
    for seed, start, shift in [(0, 400, 3.0), (5, 250, -5.0), (6, None, 0.0)]:
        df = synthetic_experiment(600, start, shift, seed=seed)
        got = fn(c, df)
        want = _ref_score_experiment(c, df)
        assert isinstance(got, dict), "return a dict with first_alarm, anomaly_start and delay"
        for k in ("first_alarm", "anomaly_start", "delay"):
            g = got.get(k)
            g = int(g) if g is not None and not (isinstance(g, float) and math.isnan(g)) else None
            assert g == want[k], f"{k} should be {want[k]} for a synthetic experiment starting at {start}, got {got.get(k)}"
    df = synthetic_experiment(600, 400, 3.0, seed=0)
    assert fn(c, df, threshold=2.0)["first_alarm"] == _ref_score_experiment(c, df, threshold=2.0)["first_alarm"], \
        "pass extra keyword arguments (like threshold) through to the API"
    df2 = df.rename(columns={FLOW: "Pressure"})
    assert fn(c, df2, column="Pressure")["first_alarm"] == want_first(c, df2), "use the `column` argument"
    try:
        fn(c, df.iloc[:50])
    except RuntimeError:
        pass
    else:
        raise AssertionError("when the API rejects the request (422), raise RuntimeError")


def want_first(c, df):
    return _ref_score_experiment(c, df, column="Pressure")["first_alarm"]


@exercise("w09.score_tests", hint="One test per promise: short windows get 422; no alarm index is < burn_in; a single "
          "spike does not alarm with min_run=5; a constant burn-in gets 422.")
def _t_score_tests(tests):
    if not isinstance(tests, (list, tuple)):
        raise AssertionError("SCORE_TESTS should be a list of your test functions")
    if not tests:
        raise NotImplementedError
    for t in tests:
        assert callable(t), "put the test functions themselves in the list (no parentheses)"
    for t in tests:
        try:
            t(_client(_ref_score_app("good")))
        except NotImplementedError:
            raise
        except Exception as err:
            raise AssertionError(f"{t.__name__} fails on the correct service: {type(err).__name__}: {str(err)[:200]}")
    stories = {"accepts_short": "a window shorter than the burn-in crashes with 500 instead of 422",
               "alarms_in_burn_in": "alarms are raised inside the burn-in",
               "ignores_min_run": "min_run is ignored, so one spike alarms",
               "constant_500": "a constant burn-in crashes with 500 instead of a clear 422"}
    for kind, story in stories.items():
        caught = False
        for t in tests:
            try:
                t(_client(_ref_score_app(kind)))
            except Exception:
                caught = True
                break
        assert caught, f"none of your tests fails when {story}"


# ============================================================================ quizzes
register_quiz(
    "w09.33_q1", "c",
    "Unpickling (which joblib.load does) can run arbitrary code chosen by whoever made the file. Load only files "
    "you or your pipeline produced, and check their checksum first.",
    {"a": "Size has nothing to do with it: a tiny file can carry a harmful payload.",
     "b": "Version mismatches are a real problem, but the danger here is code execution.",
     "d": "Compression does not change what unpickling does."})
register_quiz(
    "w09.33_q2", "b",
    "The checksum says the file is the exact one the metadata describes: not truncated, not swapped, not edited.",
    {"a": "A checksum does not measure quality; a terrible model has a perfectly valid checksum.",
     "c": "Checksums make nothing faster.",
     "d": "A checksum cannot tell who made the file; anyone can compute one. It proves 'unchanged since recorded'."})
register_quiz(
    "w09.33_q3", "d",
    "scikit-learn only promises that a pickled model works with the same version that saved it; recording the "
    "versions lets you recreate the environment or refuse to load.",
    {"a": "Versions do not change the training data.",
     "b": "It does not make loading faster.",
     "c": "Python itself loads fine; it is the library internals that may change between versions."})
register_quiz(
    "w09.33_q4", "a",
    "In a batch job one bad row should not stop 10,000 good ones: score the valid rows, report the rejected ones "
    "with a reason, and let someone fix them.",
    {"b": "Filling bad values with zero invents data and produces confident nonsense.",
     "c": "Silently dropping rows hides problems: nobody knows those customers were never scored.",
     "d": "Failing the whole run for one bad row makes the job fragile; reserve that for structural problems "
          "such as missing columns."})
register_quiz(
    "w09.33_q5", "c",
    "A missing column means the file has the wrong structure: nothing can be scored correctly, so stop loudly "
    "before predicting anything.",
    {"a": "A missing column is not a per-row problem; every row is affected.",
     "b": "Guessing a default for a whole column produces meaningless predictions.",
     "d": "A model given fewer columns either crashes with a confusing error or, worse, uses them in the wrong place."})

register_quiz(
    "w09.34_q1", "b",
    "422 Unprocessable Content: the request arrived and was valid JSON, but its content broke the rules (here, a "
    "negative count). It is the client's mistake, so it is a 4xx code.",
    {"a": "200 would mean the request succeeded; it did not.",
     "c": "500 means the server failed; here the server worked correctly by refusing bad input.",
     "d": "404 means the path does not exist; /predict exists."})
register_quiz(
    "w09.34_q2", "d",
    "TestClient calls the app's code directly inside your Python process: no network, no open port, nothing "
    "reachable from outside. That is why it works in Colab and in tests.",
    {"a": "No server is started and nothing is exposed to the internet.",
     "b": "It does not deploy anything.",
     "c": "It does not need uvicorn; uvicorn is for running a real server on your own computer."})
register_quiz(
    "w09.34_q3", "a",
    "With the pydantic model as the endpoint's argument type, FastAPI validates the JSON before your function runs "
    "and sends a 422 with details if it is invalid.",
    {"b": "pydantic validates; it does not fix values for you.",
     "c": "Validation happens at request time for every request, not once at startup.",
     "d": "Invalid requests never reach your function, so it never sees them."})
register_quiz(
    "w09.34_q4", "c",
    "GET reads without changing anything (and has no body); POST sends data in the body for the server to process, "
    "which is what a prediction request does.",
    {"a": "Both can be fast or slow; the difference is meaning, not speed.",
     "b": "Neither is more secure by itself; use HTTPS and authentication for that.",
     "d": "Browsers send both; the difference is what the request means."})
register_quiz(
    "w09.34_q5", "b",
    "Loading once at startup makes each request fast and means a broken bundle is discovered immediately, not on "
    "the first customer request.",
    {"a": "Loading per request makes every request slow (and repeats the checksum work).",
     "c": "Global variables are fine here: the model is read-only.",
     "d": "Loading inside the endpoint does not make the model fresher; the file is the same."})

register_quiz(
    "w09.35_q1", "c",
    "A test is only useful if it can fail: a test that passes on the broken service gives false confidence.",
    {"a": "Passing on the correct code is necessary but not enough.",
     "b": "The number of tests says little; what matters is which bugs they catch.",
     "d": "Coverage measures lines run, not whether the asserts would notice a bug."})
register_quiz(
    "w09.35_q2", "a",
    "The stand-in model is instant and predictable (you can compute the right answer by hand), so API tests check "
    "the API's behaviour, not the model's accuracy.",
    {"b": "Model quality is evaluated elsewhere (Weeks 5-7), not in API tests.",
     "c": "The real model is still used in production; the stub only replaces it in tests.",
     "d": "Tests with the real model are fine too, but they are slower and the expected numbers are harder to know."})
register_quiz(
    "w09.35_q3", "d",
    "503 Service Unavailable says 'I am up but cannot serve this right now', which tells clients and load balancers "
    "to try later or elsewhere.",
    {"a": "422 blames the client's input; the input was fine.",
     "b": "200 with a made-up probability is the worst option: silent nonsense.",
     "c": "404 means the path does not exist, which is false and confusing."})
register_quiz(
    "w09.35_q4", "b",
    "Internal error text can reveal file paths, library versions or data. Log it on the server; send the client a "
    "short, stable message.",
    {"a": "Clients cannot act on a stack trace; they need a clear, short message.",
     "c": "Hiding errors from logs makes debugging impossible; the point is where the detail goes.",
     "d": "Returning 200 for a failure lies to the client."})
register_quiz(
    "w09.35_q5", "a",
    "Parametrising runs the same test body once per case, and pytest reports each case separately, so you see "
    "exactly which bad payload slipped through.",
    {"b": "Each case is still a separate run; nothing is skipped.",
     "c": "It does not make tests faster.",
     "d": "Parametrize is about inputs, not about choosing a model."})

register_quiz(
    "w09.36_q1", "c",
    "The baseline is computed from the first readings of the window the client sends. If the client sends a window "
    "that starts mid-fault, the baseline is the fault, and nothing alarms: the API's behaviour depends on what the "
    "caller sends, which is why it is documented and tested.",
    {"a": "The model does not adapt between requests; each request is scored independently.",
     "b": "Threshold choice affects sensitivity, but the problem here is the baseline itself.",
     "d": "Latency is unrelated to what the baseline contains."})
register_quiz(
    "w09.36_q2", "a",
    "Requiring several consecutive points above the threshold filters single spikes, at the cost of alarming a few "
    "seconds later. That is a trade-off you report, not a free improvement.",
    {"b": "It delays every true alarm by at least min_run - 1 readings.",
     "c": "It changes the alarms, not the z-scores.",
     "d": "Persistence reduces false alarms; it does not remove the need for a burn-in."})
register_quiz(
    "w09.36_q3", "d",
    "Parity means the API and the batch code give the same answer on the same input. If they differ, one of them "
    "is not the detector you evaluated in milestone 1.",
    {"a": "Speed is a separate property.",
     "b": "The API's numbers should match the batch evaluation exactly, not just look plausible.",
     "c": "Parity is about code, not data volume."})
register_quiz(
    "w09.36_q4", "b",
    "The milestone delivers a tested service around a simple detector with known limits; claiming production "
    "readiness would need monitoring, load tests and evaluation on new data.",
    {"a": "Detection quality on 34 laboratory experiments is not evidence about a real plant.",
     "c": "Passing your own tests shows the code does what you intended, not that the intention is right.",
     "d": "A 422 for bad input is correct behaviour, not a weakness."})
