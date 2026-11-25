"""Fixtures for the w7d1 lab checks. Grades <target>/src/flowguard/{observability,api,logquery}.py.

Everything runs in-process through FastAPI's TestClient; logs are captured by pointing the learner's
``configure_logging`` at a StringIO. All data is SYNTHETIC; no network, no downloaded data.
"""
from __future__ import annotations

import importlib
import io
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w7d1_service_logging_metrics"
SENSORS = ("accelerometer1_rms", "accelerometer2_rms", "current", "pressure",
           "temperature", "thermocouple", "voltage", "flow_rate")
N_BURN = 20
# Distinctive raw values: if any of these strings shows up in a log line, raw samples were logged.
MARKER_VALUES = (31.987654, 1.876543, 229.876543)


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "lab")


@pytest.fixture(scope="session")
def fg(target):
    src = target / "src"
    assert (src / "flowguard" / "api.py").is_file(), f"no {src}/flowguard/api.py"
    sys.path.insert(0, str(src))
    for name in [m for m in sys.modules if m == "flowguard" or m.startswith("flowguard.")]:
        del sys.modules[name]
    try:
        mods = {n: importlib.import_module(f"flowguard.{n}")
                for n in ("api", "observability", "logquery", "bundle", "inference")}
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import flowguard from {src}: {exc!r}", pytrace=False)
    return mods


@pytest.fixture()
def model_dir(fg, tmp_path):
    det = fg["inference"].Detector(n_burn=N_BURN, threshold=3.0, version="synthetic-obs-1")
    return fg["bundle"].save_bundle(det, tmp_path / "model")


@pytest.fixture()
def logbuf(fg):
    buf = io.StringIO()
    handler = fg["observability"].configure_logging(buf)
    yield buf
    import logging
    logging.getLogger("flowguard").removeHandler(handler)


def _client(fg, model_dir):
    from fastapi.testclient import TestClient
    return TestClient(fg["api"].create_app(model_dir), raise_server_exceptions=False)


@pytest.fixture()
def client(fg, model_dir, logbuf):
    with _client(fg, model_dir) as c:
        yield c


@pytest.fixture()
def client_without_model(fg, tmp_path, logbuf):
    with _client(fg, tmp_path / "does-not-exist") as c:
        yield c


class Exploding:
    """Stands in for the detector so /predict raises an unhandled exception (-> 500)."""

    version = "synthetic-obs-1"
    threshold = 3.0

    def score_batch(self, frame):
        raise RuntimeError("deliberate failure inside the model call")


def make_samples(n: int = 60, seed: int = 0, shift_at: int | None = 45, markers: bool = False) -> list[dict]:
    """SYNTHETIC run in the API's JSON shape (1 Hz), with a flow drop at ``shift_at``."""
    rng = np.random.default_rng(seed)
    centre = {"accelerometer1_rms": 0.21, "accelerometer2_rms": 0.27, "current": 1.9, "pressure": 0.3,
              "temperature": 80.0, "thermocouple": 25.0, "voltage": 230.0, "flow_rate": 32.0}
    times = pd.date_range("2026-03-01 10:00:00", periods=n, freq="1s")
    rows = []
    for i, t in enumerate(times):
        row = {"timestamp": t.isoformat()}
        for s in SENSORS:
            row[s] = float(round(centre[s] * (1 + rng.normal(0, 0.02)), 6))
        if shift_at is not None and i >= shift_at:
            row["flow_rate"] = round(row["flow_rate"] - 8.0, 6)
        rows.append(row)
    if markers:
        rows[3]["flow_rate"], rows[7]["current"], rows[11]["voltage"] = MARKER_VALUES
    return rows


def body(n: int = 60, **kw) -> dict:
    return {"machine_id": "pump-07", "samples": make_samples(n, **kw)}


def log_events(buf) -> list[dict]:
    """Every line written so far must be a JSON object; returns them."""
    out = []
    for i, line in enumerate(buf.getvalue().splitlines()):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            pytest.fail(f"log line {i} is not JSON: {line[:200]!r}", pytrace=False)
        assert isinstance(obj, dict), f"log line {i} is JSON but not an object: {line[:200]!r}"
        out.append(obj)
    return out


SAMPLE_RE = re.compile(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{(.*)\})?\s+(\S+)$')
LABEL_RE = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)="((?:[^"\\]|\\.)*)"')


def parse_metrics(text: str) -> dict[str, list[tuple[dict, float]]]:
    """Tiny parser for the Prometheus text format: {sample_name: [(labels, value), ...]}."""
    samples: dict[str, list[tuple[dict, float]]] = {}
    typed: dict[str, str] = {}
    for i, line in enumerate(text.splitlines()):
        if not line.strip():
            continue
        if line.startswith("# TYPE "):
            _, _, name, kind = line.split(None, 3)
            typed[name] = kind
            continue
        if line.startswith("#"):
            continue
        m = SAMPLE_RE.match(line)
        assert m, f"metrics line {i} does not parse: {line!r}"
        name, _, labels_txt, value = m.groups()
        labels = dict(LABEL_RE.findall(labels_txt or ""))
        try:
            v = float(value.replace("+Inf", "inf").replace("-Inf", "-inf"))
        except ValueError:
            pytest.fail(f"metrics line {i} has a non-numeric value: {line!r}", pytrace=False)
        base = re.sub(r"_(bucket|sum|count)$", "", name)
        assert name in typed or base in typed, f"sample {name} has no preceding # TYPE line"
        samples.setdefault(name, []).append((labels, v))
    return samples


def value(parsed: dict, name: str, **labels) -> float:
    """Value of the single sample of ``name`` whose labels include ``labels`` (0.0 if absent)."""
    hits = [v for lab, v in parsed.get(name, []) if all(lab.get(k) == str(w) for k, w in labels.items())]
    assert len(hits) <= 1, f"{name}{labels} matches {len(hits)} series; expected at most one"
    return hits[0] if hits else 0.0
