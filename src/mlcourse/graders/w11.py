"""Week 11 graders: deploy and operate (notebooks 41-44).

41 prepares a cloud deployment without creating anything (options, secrets, configuration checks, a
least-privilege policy, a cost estimate from hypothetical prices, rollback); 42 logs and monitors a model
service; 43 separates input drift from real degradation and practises safe updates; 44 (project milestone 3)
monitors the SKAB detector.

Everything here is offline: no cloud account, network, server or SKAB download is needed for grading. The
simulated data below is SYNTHETIC. Reference versions are written independently of the notebook solutions, so
tests check behaviour on several inputs, not one way of writing the code.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import math
import os
import re
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from mlcourse.grader import exercise, register_quiz

FEATURES = ["recency_days", "orders_90d", "spend_90d", "tenure_days", "segment"]
FLOW = "Volume Flow RateRMS"
SENSORS = ["Accelerometer1RMS", "Accelerometer2RMS", "Current", "Pressure", "Temperature", "Thermocouple",
           "Voltage", FLOW]
ADMIN_PORTS = (22, 3389)
WORLD = ("0.0.0.0/0", "::/0")
KEY_ID = re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")
SECRET_ASSIGN = re.compile(r"(?i)(secret|password|passwd|token|api_key)\w*['\"]?\s*[:=]\s*[\"'][^\"']+[\"']")
SECRET_NAME_PARTS = ("SECRET", "PASSWORD", "TOKEN", "API_KEY", "ACCESS_KEY")
SECRET_REFS = ("arn:aws:secretsmanager:", "arn:aws:ssm:")


def _tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="w11_"))


def _fn(fn):
    if not callable(fn):
        raise AssertionError(f"expected a function, got {type(fn).__name__}")


# ============================================================================ synthetic data (SYNTHETIC)
def simulate_requests(hours: int = 48, per_hour: int = 40, seed: int = 0, incident: tuple | None = (30, 34),
                      start: str = "2026-03-02 00:00") -> pd.DataFrame:
    """A SYNTHETIC log of a churn-prediction service: one row per request.

    Columns: time (UTC), request_id, model_version, status (200, 422 or 500), latency_ms (NaN for 422, which is
    rejected before the model runs), prediction (0/1 for status 200, else NaN). During the `incident` hours
    (start, end) latency triples and about 8 % of requests fail with 500.
    """
    rng = np.random.default_rng(seed)
    t0 = pd.Timestamp(start, tz="UTC")
    rows = []
    for h in range(hours):
        n = int(rng.poisson(per_hour))
        bad = incident is not None and incident[0] <= h < incident[1]
        for _ in range(n):
            ts = t0 + pd.Timedelta(hours=h) + pd.Timedelta(seconds=float(rng.uniform(0, 3600)))
            u = rng.uniform()
            if u < 0.03:
                status, latency, pred = 422, np.nan, np.nan
            elif bad and u < 0.11:
                status, latency, pred = 500, float(rng.lognormal(np.log(90), 0.3)), np.nan
            else:
                status = 200
                latency = float(rng.lognormal(np.log(35), 0.35)) * (3 if bad else 1)
                pred = float(rng.uniform() < 0.3)
            rows.append({"time": ts, "request_id": f"r{len(rows):05d}", "model_version": "churn_v3",
                         "status": status, "latency_ms": round(latency, 1) if latency == latency else np.nan,
                         "prediction": pred})
    return pd.DataFrame(rows).sort_values("time").reset_index(drop=True)


def make_sensor_stream(days: int = 90, per_day: int = 120, seed: int = 0) -> pd.DataFrame:
    """A SYNTHETIC monitoring stream from pumps: one row per pump check.

    Columns: day, period ("A" days 0-29, "B" 30-59, "C" 60-89), temperature, vibration, pressure, fault (0/1).
    Period B: the temperature sensors are recalibrated (+3 degrees on every reading); faults look as in A.
    Period C: a new fault type raises vibration much less than before. About 10 % of checks are faults.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(days):
        period = "A" if d < 30 else ("B" if d < 60 else "C")
        n = per_day
        fault = rng.uniform(size=n) < 0.10
        temp = rng.normal(60, 1.5, n) + (3.0 if period == "B" else 0.0)
        lift = 0.8 if period == "C" else 2.2
        vib = rng.normal(1.0, 0.35, n) + fault * rng.normal(lift, 0.3, n)
        pres = rng.normal(4.0, 0.25, n) + fault * rng.normal(0.25, 0.1, n)
        rows.append(pd.DataFrame({"day": d, "period": period, "temperature": temp.round(2),
                                  "vibration": vib.round(3), "pressure": pres.round(3),
                                  "fault": fault.astype(int)}))
    return pd.concat(rows, ignore_index=True)


def synthetic_experiment(n: int = 400, seed: int = 0, fault_at: int | None = 250, drop: float = 2.0,
                         offset: float = 0.0) -> pd.DataFrame:
    """A SYNTHETIC SKAB-like experiment: eight sensor columns and `anomaly`; the flow drops at `fault_at`."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "Accelerometer1RMS": rng.normal(0.21, 0.005, n), "Accelerometer2RMS": rng.normal(0.27, 0.005, n),
        "Current": rng.normal(2.0, 0.3, n), "Pressure": rng.normal(0.3, 0.2, n),
        "Temperature": rng.normal(70.0, 0.4, n) + offset, "Thermocouple": rng.normal(28.0, 0.3, n),
        "Voltage": rng.normal(230.0, 5.0, n), FLOW: rng.normal(31.0, 0.5, n)})
    df["anomaly"] = 0
    if fault_at is not None:
        df.loc[fault_at:, FLOW] -= drop
        df.loc[fault_at:, "anomaly"] = 1
    return df


# ============================================================================ references: notebook 41
def _ref_pick_option(needs_os_control, traffic, seconds_per_request):
    if traffic not in ("steady", "spiky"):
        raise ValueError(f"traffic must be 'steady' or 'spiky', got {traffic!r}")
    if needs_os_control:
        return "vm"
    if traffic == "spiky" and seconds_per_request <= 900:
        return "serverless"
    return "container_service"


def _ref_find_secrets(text):
    out = []
    for i, line in enumerate(text.splitlines(), start=1):
        if KEY_ID.search(line) or SECRET_ASSIGN.search(line):
            out.append(i)
    return out


def _ref_read_setting(name, default=None):
    value = os.environ.get(name)
    if value:
        return value
    if default is not None:
        return default
    raise RuntimeError(f"the setting {name} is missing: set the environment variable {name}")


def _secret_env(name, value):
    value = "" if value is None else str(value)
    if KEY_ID.search(value):
        return True
    if any(p in name.upper() for p in SECRET_NAME_PARTS):
        return bool(value) and not value.startswith(SECRET_REFS)
    return False


def _ref_config_problems(cfg):
    found = set()
    for name, value in (cfg.get("environment") or {}).items():
        if _secret_env(name, value):
            found.add("hardcoded_secret")
    for b in cfg.get("buckets") or []:
        if b.get("public"):
            found.add("public_bucket")
    for rule in cfg.get("ingress") or []:
        if rule.get("port") in ADMIN_PORTS and rule.get("cidr") in WORLD:
            found.add("open_admin_port")
    budget = cfg.get("budget_alert_usd")
    if budget is None or not budget > 0:
        found.add("no_budget")
    return sorted(found)


def _as_list(x):
    if x is None:
        return []
    return [x] if isinstance(x, (str, dict)) else list(x)


def _ref_policy_warnings(policy):
    found = set()
    for st in _as_list(policy.get("Statement")):
        if st.get("Effect") != "Allow":
            continue
        for a in _as_list(st.get("Action")):
            verb = a.split(":", 1)[-1]
            if a == "*" or verb == "*" or verb.endswith("*"):
                found.add("wildcard_action")
            if verb.startswith(("Put", "Delete", "Create", "Update")) or a == "*" or verb == "*":
                found.add("allows_write")
        for r in _as_list(st.get("Resource")):
            if r == "*":
                found.add("wildcard_resource")
    return sorted(found)


def _ref_monthly_cost(vcpu, memory_gb, hours, n_tasks, prices, log_gb=0.0):
    for v in (vcpu, memory_gb, hours, n_tasks, log_gb):
        if v < 0:
            raise ValueError("sizes, hours and counts cannot be negative")
    compute = n_tasks * hours * (vcpu * prices["vcpu_hour"] + memory_gb * prices["gb_hour"])
    return round(compute + log_gb * prices.get("log_gb", 0.0), 2)


def _ref_rollback_target(history):
    if len(history) < 2:
        return None
    for d in reversed(history[:-1]):
        if d.get("status") == "healthy":
            return d["version"]
    return None


# ============================================================================ references: notebook 42
def _ref_log_record(request_id, model_version, features, prediction, latency_ms, allowed=FEATURES):
    from datetime import datetime, timezone

    return {"time": datetime.now(timezone.utc).isoformat(), "request_id": request_id,
            "model_version": model_version, "latency_ms": round(float(latency_ms), 1), "prediction": prediction,
            "inputs": {k: features[k] for k in allowed if k in features},
            "n_missing": sum(1 for k in allowed if k not in features)}


def _ref_append_jsonl(path, record):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return path


def _ref_read_jsonl(path):
    rows, bad = [], 0
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        if isinstance(obj, dict):
            rows.append(obj)
        else:
            bad += 1
    return pd.DataFrame(rows), bad


class _RefJsonFormatter(logging.Formatter):
    def format(self, record):
        out = {"time": self.formatTime(record), "level": record.levelname, "logger": record.name,
               "message": record.getMessage()}
        out.update(getattr(record, "fields", {}) or {})
        return json.dumps(out, default=str)


def _ref_latency_percentiles(latencies):
    v = np.asarray(latencies, dtype=float)
    v = v[~np.isnan(v)]
    if v.size == 0:
        raise ValueError("no latencies to summarise")
    p50, p95, p99 = np.percentile(v, [50, 95, 99])
    return {"p50": float(p50), "p95": float(p95), "p99": float(p99)}


def _ref_window_metrics(log, freq="1h"):
    df = log.copy()
    df["window"] = pd.to_datetime(df["time"]).dt.floor(freq)
    out = []
    for w, g in df.groupby("window"):
        ok = g[g["status"] == 200]
        lat = g["latency_ms"].dropna()
        out.append({"window": w, "requests": len(g), "errors": int((g["status"] >= 500).sum()),
                    "error_rate": float((g["status"] >= 500).mean()),
                    "p95_latency_ms": float(np.percentile(lat, 95)) if len(lat) else np.nan,
                    "positive_rate": float(ok["prediction"].mean()) if len(ok) else np.nan})
    return pd.DataFrame(out).set_index("window")


def _ref_alert_threshold(values, k=3.0):
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    if v.size < 5:
        raise ValueError("need at least 5 baseline values to set a threshold")
    return float(v.mean() + k * v.std())


def _ref_evaluate_alerts(row, rules):
    fired = []
    for rule in rules:
        if rule["metric"] not in row:
            raise KeyError(f"no metric called {rule['metric']!r}")
        value = row[rule["metric"]]
        if value is None or (isinstance(value, float) and math.isnan(value)):
            continue
        if rule["op"] == ">" and value > rule["threshold"]:
            fired.append(rule["name"])
        elif rule["op"] == "<" and value < rule["threshold"]:
            fired.append(rule["name"])
        elif rule["op"] not in (">", "<"):
            raise ValueError(f"unknown operator {rule['op']!r}")
    return fired


def _ref_sustained_alerts(values, threshold, n):
    out, run = [], 0
    for i, v in enumerate(values):
        run = run + 1 if (v == v and v > threshold) else 0
        if run == n:
            out.append(i)
    return out


# ============================================================================ references: notebook 43
def _ref_bin_edges(reference, bins=10):
    inner = np.unique(np.quantile(np.asarray(reference, dtype=float), np.linspace(0, 1, bins + 1)[1:-1]))
    return np.concatenate([[-np.inf], inner, [np.inf]])


def _shares(values, edges):
    idx = np.searchsorted(edges[1:-1], np.asarray(values, dtype=float), side="right")
    return np.bincount(idx, minlength=len(edges) - 1) / len(values)


def psi(reference, current, bins=10, eps=1e-4):
    """Population stability index of `current` against `reference` (quantile bins of the reference)."""
    edges = _ref_bin_edges(reference, bins)
    p = np.maximum(_shares(reference, edges), eps)
    q = np.maximum(_shares(current, edges), eps)
    return float(np.sum((q - p) * np.log(q / p)))


def _ref_ks(reference, current):
    a, b = np.sort(np.asarray(reference, float)), np.sort(np.asarray(current, float))
    grid = np.concatenate([a, b])
    fa = np.searchsorted(a, grid, side="right") / len(a)
    fb = np.searchsorted(b, grid, side="right") / len(b)
    return float(np.max(np.abs(fa - fb)))


def _ref_drift_report(reference, current, features, bins=10, psi_threshold=0.2):
    rows = []
    for f in features:
        p = psi(reference[f], current[f], bins)
        rows.append({"feature": f, "psi": p, "ks": _ref_ks(reference[f], current[f]), "drifted": p > psi_threshold})
    return pd.DataFrame(rows).set_index("feature")


def _ref_known_recall(df, as_of, delay_days):
    known = df[(df["day"] <= as_of - delay_days) & (df["fault"] == 1)]
    if known.empty:
        return float("nan")
    return float((known["alarm"] == 1).mean())


def _ref_diagnose(drifted_features, recall_now, recall_reference, tolerance=0.05):
    if recall_now == recall_now and recall_now < recall_reference - tolerance:
        return "degradation"
    if len(drifted_features) > 0:
        return "input drift only"
    return "healthy"


def _ref_shadow_agreement(current, candidate):
    a, b = np.asarray(current), np.asarray(candidate)
    if a.shape != b.shape:
        raise ValueError("the two prediction lists must have the same length")
    return {"agreement": float((a == b).mean()) if a.size else float("nan"),
            "only_current": int(((a == 1) & (b == 0)).sum()), "only_candidate": int(((a == 0) & (b == 1)).sum())}


def _ref_canary_route(request_id, percent):
    bucket = int(hashlib.sha256(str(request_id).encode()).hexdigest(), 16) % 100
    return "candidate" if bucket < percent else "current"


def _ref_canary_decision(baseline, canary, max_error_increase=0.01, max_p95_increase_ms=50, min_requests=200):
    if canary["requests"] < min_requests:
        return "wait"
    if canary["error_rate"] > baseline["error_rate"] + max_error_increase:
        return "rollback"
    if canary["p95_latency_ms"] > baseline["p95_latency_ms"] + max_p95_increase_ms:
        return "rollback"
    return "promote"


# ============================================================================ references: notebook 44
def detect(values, burn_in=100, threshold=3.0, min_run=5):
    """The milestone-2 detector: burn-in z-scores and alarms after `min_run` readings in a row above threshold.

    Returns (alarms, z) where alarms is a list of reading indices. Raises ValueError for a too-short series or a
    constant burn-in.
    """
    v = np.asarray(values, dtype=float)
    if len(v) < burn_in:
        raise ValueError(f"need at least {burn_in} readings, got {len(v)}")
    mean, std = v[:burn_in].mean(), v[:burn_in].std()
    if std == 0:
        raise ValueError("the burn-in window is constant, so z-scores are undefined")
    z = np.abs((v - mean) / std)
    above = z > threshold
    above[:burn_in] = False
    alarms, run = [], 0
    for i, a in enumerate(above):
        run = run + 1 if a else 0
        if run >= min_run:
            alarms.append(i)
    return alarms, z


def _ref_monitor_record(name, df, model_version, column=FLOW):
    import time

    t0 = time.perf_counter()
    alarms, z = detect(df[column].to_numpy())
    return {"experiment": name, "model_version": model_version, "n_readings": int(len(df)),
            "n_alarms": len(alarms), "first_alarm": int(alarms[0]) if alarms else None,
            "max_z": round(float(np.max(z)), 2), "flow_mean": float(df[column].mean()),
            "latency_ms": (time.perf_counter() - t0) * 1000}


def _ref_run_monitoring(experiments, log_path, model_version):
    rows = []
    for name, df in experiments.items():
        try:
            rec = _ref_monitor_record(name, df, model_version)
        except ValueError as err:
            rec = {"experiment": name, "model_version": model_version, "error": str(err)}
        _ref_append_jsonl(log_path, rec)
        rows.append(rec)
    return pd.DataFrame(rows)


def _ref_drift_table(reference, experiments, features, bins=10):
    rows = {name: {f: psi(reference[f], df[f], bins) for f in features} for name, df in experiments.items()}
    out = pd.DataFrame.from_dict(rows, orient="index")[list(features)]
    out.index.name = "experiment"
    return out


def _ref_ops_table(log_df, drift_df, psi_threshold=0.25):
    log = log_df.set_index("experiment")
    out = pd.DataFrame(index=drift_df.index)
    out["n_alarms"] = log["n_alarms"].reindex(out.index) if "n_alarms" in log else np.nan
    out["max_psi"] = drift_df.max(axis=1)
    out["drift_alert"] = out["max_psi"] > psi_threshold
    err = log["error"].reindex(out.index) if "error" in log else pd.Series(np.nan, index=out.index)
    out["error"] = err.notna()
    return out


_REFERENCES = {
    "pick_option": _ref_pick_option, "find_secrets": _ref_find_secrets, "read_setting": _ref_read_setting,
    "config_problems": _ref_config_problems, "policy_warnings": _ref_policy_warnings,
    "monthly_cost": _ref_monthly_cost, "rollback_target": _ref_rollback_target,
    "log_record": _ref_log_record, "append_jsonl": _ref_append_jsonl, "read_jsonl": _ref_read_jsonl,
    "latency_percentiles": _ref_latency_percentiles, "window_metrics": _ref_window_metrics,
    "alert_threshold": _ref_alert_threshold, "evaluate_alerts": _ref_evaluate_alerts,
    "sustained_alerts": _ref_sustained_alerts,
    "bin_edges": _ref_bin_edges, "psi": psi, "ks_statistic": _ref_ks, "drift_report": _ref_drift_report,
    "known_recall": _ref_known_recall, "diagnose": _ref_diagnose, "shadow_agreement": _ref_shadow_agreement,
    "canary_route": _ref_canary_route, "canary_decision": _ref_canary_decision,
    "monitor_record": _ref_monitor_record, "run_monitoring": _ref_run_monitoring,
    "drift_table": _ref_drift_table, "ops_table": _ref_ops_table,
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


# ============================================================================ notebook 41 tests
@exercise("w11.pick_option", hint="Check the rules in the order they are written: OS control first, then spiky "
          "traffic with short requests, then everything else.")
def _t_pick_option(fn):
    _fn(fn)
    cases = [(True, "steady", 1), (True, "spiky", 1), (False, "spiky", 2), (False, "spiky", 900),
             (False, "spiky", 901), (False, "steady", 1), (False, "steady", 5000), (True, "spiky", 3000)]
    for args in cases:
        got, want = fn(*args), _ref_pick_option(*args)
        assert got == want, (f"pick_option{args} returned {got!r}; re-read the rule that applies to "
                             f"needs_os_control={args[0]}, traffic={args[1]!r}, {args[2]} s per request")
    try:
        fn(False, "busy", 1)
    except ValueError:
        pass
    else:
        raise AssertionError("an unknown traffic value such as 'busy' should raise ValueError")


@exercise("w11.find_secrets", hint="Two regular expressions: one for AWS key ids, one for a secret-looking name "
          "assigned a non-empty quoted value. Test each line; enumerate(..., start=1).")
def _t_find_secrets(fn):
    _fn(fn)
    texts = [
        'import os\nDB_PASSWORD = os.environ["DB_PASSWORD"]\napi_key = "sk-live-1234"\n',
        "# keep your API_TOKEN in the environment\ntoken = ''\nregion = 'eu-central-1'\n",
        "aws_access_key_id = AKIAABCDEFGHIJKLMNOP\nname: demo\npassword: \"hunter2\"\nport: 8000\n",
        "x = 1\nsecret_value = load_secret('model-db')\nASIAZZZZYYYYXXXXWWWW in a log line\n",
        "",
        'GITHUB_TOKEN="ghp_abcdef"\nmodel_version = "churn_v3"\n',
    ]
    for t in texts:
        got, want = fn(t), _ref_find_secrets(t)
        assert list(got) == want, (f"for this text\n{t}\nexpected suspicious line numbers {want}, got {list(got)}. "
                                   "Count lines from 1; a value read from os.environ or a function is not "
                                   "hard-coded; an empty string is not a secret.")


@exercise("w11.read_setting", hint="os.environ.get(name) returns None when the variable is not set.")
def _t_read_setting(fn):
    _fn(fn)
    key = "MLCOURSE_TEST_SETTING_XYZ"
    old = os.environ.pop(key, None)
    try:
        os.environ[key] = "s3://bucket/models"
        assert fn(key) == "s3://bucket/models", "when the variable is set, return its value"
        assert fn(key, default="other") == "s3://bucket/models", "a set variable wins over the default"
        del os.environ[key]
        assert fn(key, default="fallback") == "fallback", "when the variable is missing, return the default"
        os.environ[key] = ""
        assert fn(key, default="fallback") == "fallback", "treat an empty variable as missing"
        del os.environ[key]
        try:
            fn(key)
        except NotImplementedError:
            raise
        except Exception as err:  # noqa: BLE001
            assert key in str(err), "the error message should name the missing setting so it can be fixed"
            assert not isinstance(err, AssertionError)
        else:
            raise AssertionError("a missing setting without a default should raise an error, not return None")
    finally:
        os.environ.pop(key, None)
        if old is not None:
            os.environ[key] = old


def _configs():
    base = {"environment": {"MODEL_VERSION": "churn_v3"}, "buckets": [{"name": "models", "public": False}],
            "ingress": [{"port": 8000, "cidr": "10.0.0.0/16"}], "budget_alert_usd": 20}
    out = [base]
    c = json.loads(json.dumps(base)); c["environment"]["DB_PASSWORD"] = "hunter2"; out.append(c)
    c = json.loads(json.dumps(base)); c["environment"]["DB_PASSWORD"] = \
        "arn:aws:secretsmanager:eu-central-1:123456789012:secret:db"; out.append(c)
    c = json.loads(json.dumps(base)); c["environment"]["SOMETHING"] = "AKIAABCDEFGHIJKLMNOP"; out.append(c)
    c = json.loads(json.dumps(base)); c["buckets"].append({"name": "dump", "public": True}); out.append(c)
    c = json.loads(json.dumps(base)); c["ingress"].append({"port": 22, "cidr": "0.0.0.0/0"}); out.append(c)
    c = json.loads(json.dumps(base)); c["ingress"].append({"port": 22, "cidr": "10.0.0.0/16"}); out.append(c)
    c = json.loads(json.dumps(base)); c["ingress"].append({"port": 3389, "cidr": "::/0"}); out.append(c)
    c = json.loads(json.dumps(base)); c["ingress"].append({"port": 443, "cidr": "0.0.0.0/0"}); out.append(c)
    c = json.loads(json.dumps(base)); c["budget_alert_usd"] = None; out.append(c)
    c = json.loads(json.dumps(base)); del c["budget_alert_usd"]; out.append(c)
    c = json.loads(json.dumps(base)); c["budget_alert_usd"] = 0; out.append(c)
    c = {"environment": {"API_TOKEN": "abc"}, "buckets": [{"name": "x", "public": True}],
         "ingress": [{"port": 22, "cidr": "0.0.0.0/0"}]}
    out.append(c)
    out.append({"budget_alert_usd": 5})
    c = json.loads(json.dumps(base)); c["environment"]["MODEL_TOKEN_LIMIT"] = ""; out.append(c)
    return out


@exercise("w11.config_problems", hint="Start from an empty set; check the four kinds of problem one after the "
          "other; use cfg.get(..., default) so a missing section counts as empty; return sorted(found).")
def _t_config_problems(fn):
    _fn(fn)
    for cfg in _configs():
        got, want = fn(json.loads(json.dumps(cfg))), _ref_config_problems(cfg)
        assert sorted(got) == want, (f"for the configuration {cfg}\nexpected the problems {want}, got "
                                     f"{sorted(got)}. Check that rule again (and that missing sections are "
                                     "treated as empty).")
    assert list(fn(_configs()[0])) == [], "the safe base configuration has no problems"


@exercise("w11.fixed_config", hint="Keep the service working (port 8000 from inside the network, the model "
          "version) but remove each problem: a secret reference instead of the password, no public bucket, no "
          "SSH from the world, a positive budget alert.")
def _t_fixed_config(cfg):
    if not isinstance(cfg, dict):
        raise AssertionError("fixed_config should be a dict shaped like the unsafe configuration")
    problems = _ref_config_problems(cfg)
    assert not problems, f"the configuration still has these problems: {problems}"
    env = cfg.get("environment") or {}
    assert env.get("MODEL_VERSION") == "churn_v3", "keep MODEL_VERSION: the service needs it"
    assert "DB_PASSWORD" in env, ("keep a DB_PASSWORD entry, but as a reference to a secret store "
                                  "(arn:aws:secretsmanager:...), not the password itself")
    assert any(r.get("port") == 8000 for r in cfg.get("ingress") or []), \
        "keep an ingress rule for port 8000, or the service is unreachable"


def _good_policy_ok(p):
    sts = _as_list(p.get("Statement"))
    allowed = {}
    for st in sts:
        if st.get("Effect") != "Allow":
            continue
        for a in _as_list(st.get("Action")):
            allowed.setdefault(a, set()).update(_as_list(st.get("Resource")))
    return allowed


@exercise("w11.policy", hint="Two statements: s3:ListBucket on the bucket ARN (no /*), s3:GetObject on the "
          "objects ARN (with /*). Version is the fixed string \"2012-10-17\".")
def _t_policy(p):
    if not isinstance(p, dict):
        raise AssertionError("the policy should be a dict (a JSON object)")
    assert p.get("Version") == "2012-10-17", 'the policy language version must be "2012-10-17" (a fixed date string)'
    sts = _as_list(p.get("Statement"))
    assert sts, "a policy needs a Statement (a list of statements)"
    for st in sts:
        assert st.get("Effect") in ("Allow", "Deny"), "every statement needs Effect \"Allow\" or \"Deny\""
        assert st.get("Action") and st.get("Resource"), "every statement needs both Action and Resource"
    warns = _ref_policy_warnings(p)
    assert not warns, f"the policy is broader than needed: {warns}"
    allowed = _good_policy_ok(p)
    bucket, objects = "arn:aws:s3:::course-models-example", "arn:aws:s3:::course-models-example/*"
    assert set(allowed) == {"s3:GetObject", "s3:ListBucket"}, \
        f"allow exactly the two actions the service needs; your policy allows {sorted(allowed)}"
    assert allowed["s3:ListBucket"] == {bucket}, \
        "ListBucket acts on the bucket itself: its resource is the bucket ARN, without /*"
    assert allowed["s3:GetObject"] == {objects}, \
        "GetObject acts on objects: its resource is the bucket ARN followed by /*"


@exercise("w11.policy_warnings", hint="Normalise Action and Resource to lists first (they may be a single "
          "string). Look only at Allow statements. The part after 'service:' is the verb.")
def _t_policy_warnings(fn):
    _fn(fn)
    pols = [
        {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "s3:GetObject",
                                                  "Resource": "arn:aws:s3:::b/*"}]},
        {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]},
        {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": ["s3:*"],
                                                  "Resource": ["arn:aws:s3:::b", "arn:aws:s3:::b/*"]}]},
        {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": ["s3:Get*", "s3:List*"],
                                                  "Resource": "arn:aws:s3:::b/*"}]},
        {"Version": "2012-10-17", "Statement": [
            {"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": "arn:aws:s3:::b/*"},
            {"Effect": "Allow", "Action": "s3:DeleteObject", "Resource": "*"}]},
        {"Version": "2012-10-17", "Statement": {"Effect": "Allow", "Action": "ecr:PutImage",
                                                "Resource": "arn:aws:ecr:eu-central-1:123456789012:repository/x"}},
        {"Version": "2012-10-17", "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}]},
        {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "logs:CreateLogStream",
                                                  "Resource": "arn:aws:logs:eu-central-1:1:log-group:g:*"}]},
    ]
    for p in pols:
        got, want = fn(json.loads(json.dumps(p))), _ref_policy_warnings(p)
        assert sorted(got) == want, f"for the policy {p}\nexpected warnings {want}, got {sorted(got)}"


PRICES_TEST = {"vcpu_hour": 0.05, "gb_hour": 0.005, "log_gb": 0.5}


@exercise("w11.monthly_cost", hint="compute = n_tasks * hours * (vcpu * vcpu price + memory * GB price); add the "
          "log storage; round the total to 2 decimals.")
def _t_monthly_cost(fn):
    _fn(fn)
    cases = [(0.5, 1.0, 730, 1, PRICES_TEST, 0.0), (1, 2, 730, 2, PRICES_TEST, 3.0),
             (0.25, 0.5, 220, 1, {"vcpu_hour": 0.04, "gb_hour": 0.004}, 0.0),
             (2, 4, 0, 3, PRICES_TEST, 1.0), (1, 2, 730, 0, PRICES_TEST, 0.0)]
    for c in cases:
        got = fn(*c)
        want = _ref_monthly_cost(*c)
        assert isinstance(got, (int, float)), "return a number"
        assert abs(got - want) < 0.006, (f"monthly_cost{c[:4]} with log_gb={c[5]} gave {got}, expected {want}. "
                                        "Check each part: tasks x hours x (vCPU x price + GB x price), plus log GB x log price.")
    assert fn(1, 2, 730, 1, {"vcpu_hour": 0.05, "gb_hour": 0.005}) == _ref_monthly_cost(
        1, 2, 730, 1, {"vcpu_hour": 0.05, "gb_hour": 0.005}), \
        "log_gb should default to 0, and a price list without 'log_gb' should still work"
    try:
        fn(-1, 2, 730, 1, PRICES_TEST)
    except ValueError:
        pass
    else:
        raise AssertionError("a negative size, count or number of hours should raise ValueError")


@exercise("w11.savings", hint="Use your monthly_cost twice with the same service and prices: once with 730 hours, "
          "once with 22 * 10 hours. Savings = always-on minus office-hours.")
def _t_savings(x):
    if not isinstance(x, (int, float)) or isinstance(x, bool):
        raise AssertionError("savings_per_month should be a number")
    want = _ref_monthly_cost(0.5, 1.0, 730, 2, PRICES_TEST, 2.0) - _ref_monthly_cost(0.5, 1.0, 220, 2, PRICES_TEST, 2.0)
    assert abs(x - want) < 0.02, ("not the expected saving: same service (2 tasks, 0.5 vCPU, 1 GB, 2 GB of logs), "
                                  "730 hours against 22 working days of 10 hours")


@exercise("w11.rollback_target", hint="The last entry is the version that is live now; walk backwards through "
          "the earlier ones and return the first healthy version.")
def _t_rollback(fn):
    _fn(fn)
    H = lambda *pairs: [{"version": v, "status": s} for v, s in pairs]  # noqa: E731
    cases = [H(("v1", "healthy"), ("v2", "healthy"), ("v3", "failed")),
             H(("v1", "healthy"), ("v2", "failed"), ("v3", "failed")),
             H(("v1", "failed"), ("v2", "failed")),
             H(("v1", "healthy")), [], H(("v1", "healthy"), ("v2", "healthy")),
             H(("v4", "healthy"), ("v5", "rolled_back"), ("v6", "healthy"), ("v7", "failed"))]
    for h in cases:
        got, want = fn([dict(d) for d in h]), _ref_rollback_target(h)
        assert got == want, (f"for the history {[(d['version'], d['status']) for d in h]} expected {want!r}, "
                             f"got {got!r}")


# ============================================================================ notebook 42 tests
@exercise("w11.log_record", hint="Build the 'inputs' dict by looping over `allowed`, not over the features: that "
          "is what keeps unexpected (personal) fields out.")
def _t_log_record(fn):
    _fn(fn)
    from datetime import datetime

    feats = {"recency_days": 12, "orders_90d": 3, "spend_90d": 81.5, "tenure_days": 400, "segment": "consumer",
             "email": "someone@example.com", "name": "A. Person"}
    rec = fn("req-1", "churn_v3", dict(feats), 1, 12.345)
    assert isinstance(rec, dict), "return a dict"
    for k in ("time", "request_id", "model_version", "latency_ms", "prediction", "inputs", "n_missing"):
        assert k in rec, f"the record needs a '{k}' field"
    text = json.dumps(rec)
    assert "someone@example.com" not in text and "A. Person" not in text, \
        "personal data (email, name) ended up in the log record: keep only the allowed feature names"
    assert rec["inputs"] == {k: feats[k] for k in FEATURES}, "inputs should hold exactly the allowed features"
    assert rec["request_id"] == "req-1" and rec["model_version"] == "churn_v3" and rec["prediction"] == 1
    assert rec["latency_ms"] == 12.3, "round latency_ms to 1 decimal"
    assert rec["n_missing"] == 0
    t = datetime.fromisoformat(rec["time"])
    assert t.tzinfo is not None, "the time should carry a timezone (use datetime.now(timezone.utc))"
    rec2 = fn("req-2", "churn_v3", {"recency_days": 5, "segment": "student"}, 0, 7)
    assert rec2["n_missing"] == 3 and rec2["inputs"] == {"recency_days": 5, "segment": "student"}, \
        "count the allowed features that are missing, and do not invent values for them"
    rec3 = fn("r", "v", {"a": 1, "b": 2}, 0, 1.0, allowed=["b"])
    assert rec3["inputs"] == {"b": 2}, "use the `allowed` argument, not a fixed list"


@exercise("w11.append_jsonl", hint="Create the parent folder, open the file in append mode 'a', write "
          "json.dumps(record) followed by a newline.")
def _t_append_jsonl(fn):
    _fn(fn)
    d = _tmp()
    try:
        p = d / "logs" / "deep" / "service.jsonl"
        fn(p, {"a": 1})
        fn(str(p), {"a": 2, "b": "x"})
        fn(p, {"a": 3})
        lines = p.read_text().splitlines()
        assert len(lines) == 3, f"three calls should give three lines, got {len(lines)} (open in append mode)"
        assert [json.loads(x)["a"] for x in lines] == [1, 2, 3], "each line should be one JSON record, in order"
    finally:
        shutil.rmtree(d, ignore_errors=True)


@exercise("w11.read_jsonl", hint="Skip blank lines; wrap json.loads in try/except json.JSONDecodeError and count "
          "the failures; a line that parses but is not a dict also counts as bad.")
def _t_read_jsonl(fn):
    _fn(fn)
    d = _tmp()
    try:
        p = d / "log.jsonl"
        p.write_text('{"a": 1, "b": 2}\n\n{"a": 3}\nnot json\n{"a": 4, "b"\n[1, 2]\n{"a": 5, "b": null}\n')
        df, bad = fn(p)
        assert isinstance(df, pd.DataFrame), "return a DataFrame and the number of bad lines"
        assert list(df["a"]) == [1, 3, 5], "keep the good records, in order"
        assert bad == 3, f"there are 3 bad lines (two broken, one not an object); you counted {bad}"
        q = d / "empty.jsonl"
        q.write_text("")
        df2, bad2 = fn(str(q))
        assert len(df2) == 0 and bad2 == 0, "an empty file gives an empty DataFrame and 0 bad lines"
    finally:
        shutil.rmtree(d, ignore_errors=True)


@exercise("w11.json_formatter", hint="In format(), build a dict with level, message (record.getMessage()) and "
          "the extra fields from getattr(record, 'fields', {}), and return json.dumps of it.")
def _t_formatter(cls):
    if not isinstance(cls, type) or not issubclass(cls, logging.Formatter):
        raise AssertionError("pass the class JsonFormatter (a subclass of logging.Formatter)")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(cls())
    log = logging.getLogger("w11_grader_test")
    log.handlers[:] = [handler]
    log.setLevel(logging.DEBUG)
    log.propagate = False
    log.info("prediction served", extra={"fields": {"request_id": "r-9", "latency_ms": 12.5}})
    log.warning("slow request %d ms", 812)
    log.debug("plain")
    lines = [x for x in stream.getvalue().splitlines() if x.strip()]
    assert len(lines) == 3, "each log call should produce exactly one line"
    try:
        objs = [json.loads(x) for x in lines]
    except json.JSONDecodeError:
        raise AssertionError("every line should be valid JSON (return json.dumps(...))") from None
    assert objs[0].get("level") == "INFO" and objs[1].get("level") == "WARNING" and objs[2].get("level") == "DEBUG", \
        "include the level name (record.levelname) as 'level'"
    assert objs[0].get("message") == "prediction served", "include the message as 'message'"
    assert objs[1].get("message") == "slow request 812 ms", \
        "use record.getMessage() so %-style arguments are filled in"
    assert objs[0].get("request_id") == "r-9" and objs[0].get("latency_ms") == 12.5, \
        "copy the extra 'fields' into the JSON object as top-level keys"
    assert "request_id" not in objs[2], "a call without extra fields should not invent them"


@exercise("w11.latency_percentiles", hint="Drop NaN first (v[~np.isnan(v)]), then np.percentile(v, [50, 95, 99]).")
def _t_latency(fn):
    _fn(fn)
    rng = np.random.default_rng(3)
    for v in [rng.lognormal(3, 0.5, 500), np.arange(1, 101, dtype=float), np.array([5.0]),
              np.array([10.0, np.nan, 20.0, 30.0, np.nan])]:
        got, want = fn(list(v)), _ref_latency_percentiles(v)
        assert set(got) == {"p50", "p95", "p99"}, "return a dict with keys p50, p95 and p99"
        for k in want:
            assert abs(got[k] - want[k]) < 1e-6, f"{k} is off (expected about {want[k]:.2f}); are NaNs removed?"
    try:
        fn([np.nan, np.nan])
    except ValueError:
        pass
    else:
        raise AssertionError("with no usable latencies, raise ValueError instead of returning NaN")


@exercise("w11.window_metrics", hint="Add a 'window' column with pd.to_datetime(time).dt.floor(freq), group by "
          "it, and compute each column from the group. Errors are status >= 500 only; positive_rate uses status "
          "200 rows only.")
def _t_window_metrics(fn):
    _fn(fn)
    for seed, freq, inc in [(1, "1h", (5, 7)), (2, "6h", None), (4, "30min", (2, 3))]:
        log = simulate_requests(hours=10, per_hour=30, seed=seed, incident=inc)
        got, want = fn(log.copy(), freq), _ref_window_metrics(log, freq)
        assert isinstance(got, pd.DataFrame), "return a DataFrame with one row per window"
        assert len(got) == len(want), f"expected {len(want)} windows of {freq}, got {len(got)}"
        for col in ["requests", "errors", "error_rate", "p95_latency_ms", "positive_rate"]:
            assert col in got.columns, f"missing column {col!r}"
            a, b = np.asarray(got[col], float), np.asarray(want[col], float)
            assert np.allclose(a, b, equal_nan=True, atol=1e-6), (
                f"column {col!r} differs from the expected values"
                + (" (422 is the client's mistake, not a server error)" if "error" in col else "")
                + (" (use only status-200 rows)" if col == "positive_rate" else "")
                + (" (ignore NaN latencies of rejected requests)" if col == "p95_latency_ms" else ""))


@exercise("w11.plot_dashboard", hint="fig, axes = plt.subplots(3, 1, sharex=True); one ax.plot per metric; "
          "ax.set_title(...) on each; return fig.")
def _t_dashboard(fn):
    _fn(fn)
    import matplotlib
    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure

    m = _ref_window_metrics(simulate_requests(hours=12, per_hour=20, seed=5, incident=(6, 8)))
    fig = fn(m)
    try:
        assert isinstance(fig, Figure), "return the matplotlib Figure"
        axes = [ax for ax in fig.axes if ax.lines]
        assert len(axes) >= 3, "the dashboard needs (at least) three panels with a line each"
        for ax in axes[:3]:
            assert any(len(line.get_xdata()) == len(m) for line in ax.lines), \
                "each line should have one point per window"
            assert ax.get_title() or ax.get_ylabel(), "give every panel a title or a y-axis label"
    finally:
        plt.close("all")


@exercise("w11.alert_threshold", hint="Drop NaN, check there are at least 5 values, return mean + k * std "
          "(np.std's default).")
def _t_alert_threshold(fn):
    _fn(fn)
    rng = np.random.default_rng(0)
    for v, k in [(rng.normal(40, 5, 48), 3.0), (np.array([1, 2, 3, 4, 5.0]), 2.0),
                 (np.array([10, np.nan, 12, 11, 13, 9.0]), 3.0)]:
        got, want = fn(list(v), k), _ref_alert_threshold(v, k)
        assert abs(got - want) < 1e-6, f"expected about {want:.3f}; check NaN handling and the std (ddof=0)"
    assert abs(fn([1, 2, 3, 4, 5.0]) - _ref_alert_threshold([1, 2, 3, 4, 5.0])) < 1e-9, "k should default to 3"
    try:
        fn([1.0, 2.0, np.nan, 3.0])
    except ValueError:
        pass
    else:
        raise AssertionError("with fewer than 5 usable values, raise ValueError: a threshold needs a baseline")


_RULES = [{"name": "high error rate", "metric": "error_rate", "op": ">", "threshold": 0.02},
          {"name": "slow", "metric": "p95_latency_ms", "op": ">", "threshold": 120.0},
          {"name": "traffic dropped", "metric": "requests", "op": "<", "threshold": 10}]


@exercise("w11.evaluate_alerts", hint="Loop over the rules in order; look up row[rule['metric']]; skip NaN; "
          "compare with > or < as the rule says.")
def _t_evaluate(fn):
    _fn(fn)
    rows = [{"error_rate": 0.0, "p95_latency_ms": 50.0, "requests": 40},
            {"error_rate": 0.05, "p95_latency_ms": 150.0, "requests": 40},
            {"error_rate": 0.02, "p95_latency_ms": 120.0, "requests": 10},
            {"error_rate": 0.0, "p95_latency_ms": float("nan"), "requests": 3},
            pd.Series({"error_rate": 0.1, "p95_latency_ms": 10.0, "requests": 50})]
    for r in rows:
        got, want = fn(r, _RULES), _ref_evaluate_alerts(r, _RULES)
        assert list(got) == want, (f"for {dict(r)} expected {want}, got {list(got)} (equal to the threshold does "
                                   "not fire; NaN never fires; keep the rules' order)")
    try:
        fn({"error_rate": 0.0}, _RULES)
    except KeyError:
        pass
    else:
        raise AssertionError("a rule about a metric the row does not have should raise KeyError, not be ignored")


@exercise("w11.sustained_alerts", hint="Keep a counter of consecutive values above the threshold; reset it to 0 "
          "otherwise; fire when the counter becomes exactly n.")
def _t_sustained(fn):
    _fn(fn)
    cases = [([1, 5, 5, 5, 1, 5, 5, 5, 5], 3, 3), ([5, 5, 5, 5, 5], 3, 2), ([1, 2, 3], 5, 1),
             ([9, 1, 9, 1, 9], 5, 2), ([9, 9, float("nan"), 9, 9], 5, 2), ([], 1, 1), ([4, 4, 4], 3, 1)]
    for v, thr, n in cases:
        got, want = fn(list(v), thr, n), _ref_sustained_alerts(v, thr, n)
        assert list(got) == want, (f"sustained_alerts({v}, threshold={thr}, n={n}) should be {want}, got "
                                   f"{list(got)} (fire once per run, when the run reaches n; NaN breaks a run)")


# ============================================================================ notebook 43 tests
@exercise("w11.bin_edges", hint="np.quantile(reference, np.linspace(0, 1, bins + 1)[1:-1]) gives the inner edges; "
          "np.unique removes repeats; put -inf in front and inf at the end.")
def _t_bin_edges(fn):
    _fn(fn)
    rng = np.random.default_rng(1)
    for ref, bins in [(rng.normal(size=1000), 10), (rng.exponential(size=333), 5), (np.arange(100.0), 4),
                      (np.array([1, 1, 1, 1, 2, 2, 3.0]), 4)]:
        got, want = np.asarray(fn(ref, bins), float), _ref_bin_edges(ref, bins)
        assert got[0] == -np.inf and got[-1] == np.inf, "the outer edges should be -inf and inf"
        assert got.shape == want.shape and np.allclose(got[1:-1], want[1:-1]), (
            f"expected {len(want)} edges with inner edges at the reference quantiles (repeats removed)")
    assert len(fn(rng.normal(size=500))) == 11, "bins should default to 10 (11 edges)"


@exercise("w11.psi", hint="Bin both samples with the reference's edges, divide counts by the sample size, floor "
          "the shares at eps, then sum((q - p) * log(q / p)).")
def _t_psi(fn):
    _fn(fn)
    rng = np.random.default_rng(2)
    ref = rng.normal(size=2000)
    cases = [(ref, rng.normal(size=500)), (ref, rng.normal(0.5, 1, 500)), (ref, rng.normal(0, 2, 800)),
             (ref, rng.normal(10, 1, 300)), (rng.exponential(size=700), rng.exponential(1.5, 400))]
    for r, c in cases:
        got, want = fn(r, c), psi(r, c)
        assert isinstance(got, (float, np.floating)) and np.isfinite(got), \
            "PSI should be a finite number (floor empty shares at eps so the log is defined)"
        assert abs(got - want) < 1e-6 * max(1, want), f"expected PSI about {want:.4f}, got {got:.4f}"
    assert abs(fn(ref, ref)) < 1e-9, "a sample compared with itself has PSI 0"
    cur = np.random.default_rng(9).normal(0.3, 1, 400)
    assert abs(fn(ref, cur, bins=5) - psi(ref, cur, 5)) < 1e-6, "use the bins argument"


@exercise("w11.ks_statistic", hint="Evaluate both empirical CDFs at every value of either sample "
          "(np.searchsorted(sorted, grid, side='right') / n) and take the largest absolute difference.")
def _t_ks(fn):
    from scipy.stats import ks_2samp

    _fn(fn)
    rng = np.random.default_rng(4)
    cases = [(rng.normal(size=300), rng.normal(size=200)), (rng.normal(size=100), rng.normal(1, 1, 150)),
             (np.array([1, 2, 2, 3, 3, 3.0]), np.array([2, 3, 4, 4.0])), (np.arange(10.0), np.arange(10.0) + 100)]
    for a, b in cases:
        got = fn(a, b)
        want = ks_2samp(a, b).statistic
        assert abs(got - want) < 1e-9, f"expected KS {want:.4f}, got {got:.4f} (ties: use side='right')"


@exercise("w11.drift_report", hint="Loop over the features; for each compute psi and ks_statistic on the two "
          "columns; build a DataFrame indexed by feature; drifted = psi > psi_threshold.")
def _t_drift_report(fn):
    _fn(fn)
    s = make_sensor_stream(days=60, per_day=60, seed=3)
    ref, cur = s[s.day < 20], s[s.day >= 40]
    feats = ["temperature", "vibration", "pressure"]
    got, want = fn(ref, cur, feats), _ref_drift_report(ref, cur, feats)
    assert isinstance(got, pd.DataFrame) and list(got.index) == feats, "one row per feature, indexed by feature"
    for col in ["psi", "ks", "drifted"]:
        assert col in got.columns, f"missing column {col!r}"
    assert np.allclose(got["psi"].astype(float), want["psi"], atol=1e-6), "the psi column is off"
    assert np.allclose(got["ks"].astype(float), want["ks"], atol=1e-6), "the ks column is off"
    assert list(got["drifted"].astype(bool)) == list(want["drifted"]), "drifted should be psi > psi_threshold"
    got2 = fn(ref, cur, feats, psi_threshold=100.0)
    assert not got2["drifted"].any(), "use the psi_threshold argument"


def _stream_with_alarms(seed=5):
    s = make_sensor_stream(days=40, per_day=30, seed=seed)
    rng = np.random.default_rng(seed)
    s["alarm"] = ((s["vibration"] > 2.0) | (rng.uniform(size=len(s)) < 0.02)).astype(int)
    return s


@exercise("w11.known_recall", hint="Keep rows with day <= as_of - delay_days and fault == 1; recall is the share "
          "of them with alarm == 1; return NaN when there are none.")
def _t_known_recall(fn):
    _fn(fn)
    s = _stream_with_alarms()
    for as_of, delay in [(39, 7), (20, 0), (10, 3), (39, 30), (5, 7)]:
        got, want = fn(s.copy(), as_of, delay), _ref_known_recall(s, as_of, delay)
        if math.isnan(want):
            assert got is not None and math.isnan(got), \
                f"as_of={as_of}, delay={delay}: no labels are known yet, so return NaN (not 0, not an error)"
        else:
            assert abs(got - want) < 1e-9, (f"as_of={as_of}, delay={delay}: expected {want:.3f}, got {got:.3f}. "
                                            "Only labels at least delay_days old are known.")


@exercise("w11.diagnose", hint="Check for a recall drop first (that is what hurts), then for drifted features.")
def _t_diagnose(fn):
    _fn(fn)
    cases = [([], 0.9, 0.9), (["temperature"], 0.9, 0.91), (["temperature"], 0.7, 0.9), ([], 0.7, 0.9),
             ([], 0.86, 0.9), ([], 0.849, 0.9), (["a", "b"], float("nan"), 0.9), ([], float("nan"), 0.9)]
    for c in cases:
        got, want = fn(*c), _ref_diagnose(*c)
        assert got == want, (f"diagnose(drifted={c[0]}, recall_now={c[1]}, recall_reference={c[2]}) should be "
                             f"{want!r}, got {got!r} (a NaN recall means 'not known yet', not a drop)")
    assert fn([], 0.7, 0.9, tolerance=0.3) == "healthy", "use the tolerance argument"


@exercise("w11.shadow_agreement", hint="Convert both to NumPy arrays; agreement = (a == b).mean(); count the two "
          "kinds of disagreement separately.")
def _t_shadow(fn):
    _fn(fn)
    for a, b in [([1, 0, 1, 1, 0], [1, 1, 0, 1, 0]), ([0, 0, 0], [0, 0, 0]), ([1, 1], [0, 0]),
                 (np.array([0, 1] * 50), np.array([1, 1] * 50))]:
        got, want = fn(a, b), _ref_shadow_agreement(a, b)
        assert set(got) >= set(want), "return a dict with agreement, only_current and only_candidate"
        assert abs(got["agreement"] - want["agreement"]) < 1e-9, "agreement is the share of equal predictions"
        assert got["only_current"] == want["only_current"] and got["only_candidate"] == want["only_candidate"], \
            "only_current counts current=1, candidate=0; only_candidate the opposite"
    try:
        fn([1, 0], [1])
    except ValueError:
        pass
    else:
        raise AssertionError("lists of different lengths cannot be compared: raise ValueError")


@exercise("w11.canary_route", hint="int(hashlib.sha256(request_id.encode()).hexdigest(), 16) % 100 gives a "
          "stable number from 0 to 99 for each id.")
def _t_canary(fn):
    _fn(fn)
    ids = [f"req-{i}" for i in range(5000)]
    first = [fn(i, 10) for i in ids[:200]]
    assert first == [fn(i, 10) for i in ids[:200]], \
        "the same request id must always get the same route (no random numbers)"
    assert set(first) <= {"candidate", "current"}, "return 'candidate' or 'current'"
    share = np.mean([fn(i, 10) == "candidate" for i in ids])
    assert 0.07 <= share <= 0.13, f"with percent=10 about 10 % should go to the candidate; got {share:.1%}"
    share = np.mean([fn(i, 50) == "candidate" for i in ids])
    assert 0.45 <= share <= 0.55, f"with percent=50 about half should go to the candidate; got {share:.1%}"
    assert all(fn(i, 0) == "current" for i in ids[:500]), "percent=0 sends nobody to the candidate"
    assert all(fn(i, 100) == "candidate" for i in ids[:500]), "percent=100 sends everybody to the candidate"
    in10 = {i for i in ids if fn(i, 10) == "candidate"}
    in20 = {i for i in ids if fn(i, 20) == "candidate"}
    assert in10 <= in20, "raising the percentage should keep the users who were already on the candidate"


@exercise("w11.canary_decision", hint="Order matters: first 'wait' if there are too few requests, then 'rollback' "
          "if either guardrail is broken, else 'promote'.")
def _t_canary_decision(fn):
    _fn(fn)
    base = {"requests": 5000, "error_rate": 0.004, "p95_latency_ms": 80.0}
    cases = [{"requests": 150, "error_rate": 0.5, "p95_latency_ms": 900.0},
             {"requests": 600, "error_rate": 0.005, "p95_latency_ms": 90.0},
             {"requests": 600, "error_rate": 0.02, "p95_latency_ms": 90.0},
             {"requests": 600, "error_rate": 0.004, "p95_latency_ms": 140.0},
             {"requests": 600, "error_rate": 0.014, "p95_latency_ms": 130.0},
             {"requests": 200, "error_rate": 0.0, "p95_latency_ms": 60.0}]
    for c in cases:
        got, want = fn(base, c), _ref_canary_decision(base, c)
        assert got == want, f"for canary {c} expected {want!r}, got {got!r}"
    assert fn(base, cases[2], max_error_increase=0.05) == "promote", "use the max_error_increase argument"
    assert fn(base, cases[0], min_requests=100) == "rollback", "use the min_requests argument"


# ============================================================================ notebook 44 tests
def _experiments():
    return {"syn/1": synthetic_experiment(seed=1), "syn/2": synthetic_experiment(seed=2, fault_at=None),
            "syn/3": synthetic_experiment(seed=3, drop=4.0, offset=3.0)}


@exercise("w11.monitor_record", hint="Run detect() on the flow column, time it with time.perf_counter(), and fill "
          "the record's fields from the alarms and z-scores.")
def _t_monitor_record(fn):
    _fn(fn)
    for name, df in _experiments().items():
        got, want = fn(name, df.copy(), "zscore_v1"), _ref_monitor_record(name, df, "zscore_v1")
        assert isinstance(got, dict), "return a dict"
        for k in ["experiment", "model_version", "n_readings", "n_alarms", "first_alarm", "max_z", "flow_mean"]:
            assert k in got, f"missing field {k!r}"
            if isinstance(want[k], float):
                assert abs(float(got[k]) - want[k]) < 0.01, f"{name}: {k} should be about {want[k]}"
            else:
                assert got[k] == want[k], f"{name}: {k} should be {want[k]!r}, got {got[k]!r}"
        assert "latency_ms" in got and got["latency_ms"] >= 0, "measure latency_ms (time.perf_counter)"
        json.dumps(got)  # must be JSON-safe
    rec = fn("x", synthetic_experiment(seed=1), "zscore_v1")
    assert isinstance(rec["n_alarms"], int) and (rec["first_alarm"] is None or isinstance(rec["first_alarm"], int)), \
        "use plain int (not numpy types) so the record can be written as JSON"


@exercise("w11.run_monitoring", hint="Loop over experiments; try monitor_record; on ValueError log a record with "
          "an 'error' field instead; append every record to the JSONL file; return a DataFrame of the records.")
def _t_run_monitoring(fn):
    _fn(fn)
    d = _tmp()
    try:
        exps = _experiments()
        exps["syn/short"] = synthetic_experiment(n=50, fault_at=None)
        flat = synthetic_experiment(seed=4, fault_at=None)
        flat[FLOW] = 31.0
        exps["syn/flat"] = flat
        path = d / "monitor" / "log.jsonl"
        df = fn(exps, path, "zscore_v1")
        assert isinstance(df, pd.DataFrame) and len(df) == 5, "one row per experiment, including the failed ones"
        lines = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
        assert len(lines) == 5, "write one JSON line per experiment to log_path (create its folder)"
        by = {r["experiment"]: r for r in lines}
        for bad in ["syn/short", "syn/flat"]:
            assert "error" in by[bad] and by[bad]["error"], \
                f"{bad} cannot be scored: log a record with an 'error' message instead of crashing or skipping it"
        assert by["syn/1"]["n_alarms"] == _ref_monitor_record("syn/1", exps["syn/1"], "v")["n_alarms"]
        assert all(r["model_version"] == "zscore_v1" for r in lines), "every record carries the model version"
    finally:
        shutil.rmtree(d, ignore_errors=True)


@exercise("w11.drift_table", hint="A dict {experiment: {feature: psi(reference[f], df[f])}} turned into a "
          "DataFrame with pd.DataFrame.from_dict(..., orient='index').")
def _t_drift_table(fn):
    _fn(fn)
    ref = synthetic_experiment(n=800, seed=11, fault_at=None)
    exps = _experiments()
    feats = ["Temperature", FLOW, "Current"]
    got, want = fn(ref, exps, feats), _ref_drift_table(ref, exps, feats)
    assert isinstance(got, pd.DataFrame), "return a DataFrame"
    assert list(got.index) == list(exps) and list(got.columns) == feats, \
        "rows = experiments (in order), columns = the features (in order)"
    assert np.allclose(got.to_numpy(float), want.to_numpy(float), atol=1e-6), "the PSI values are off"
    assert got.loc["syn/3", "Temperature"] > 1, "sanity: syn/3's temperature is shifted, so its PSI must be large"


@exercise("w11.ops_table", hint="Index both tables by experiment; n_alarms from the log, max_psi = the row-wise "
          "max of the drift table, drift_alert = max_psi > threshold, error = the log has an error message.")
def _t_ops_table(fn):
    _fn(fn)
    exps = _experiments()
    exps["syn/short"] = synthetic_experiment(n=50, fault_at=None)
    d = _tmp()
    try:
        log = _ref_run_monitoring(exps, d / "l.jsonl", "v1")
    finally:
        shutil.rmtree(d, ignore_errors=True)
    drift = _ref_drift_table(synthetic_experiment(n=800, seed=11, fault_at=None), exps, ["Temperature", FLOW])
    for thr in [0.25, 5.0]:
        got, want = fn(log.copy(), drift.copy(), thr), _ref_ops_table(log, drift, thr)
        assert isinstance(got, pd.DataFrame) and list(got.index) == list(want.index), \
            "one row per experiment, in the drift table's order"
        for c in ["n_alarms", "max_psi", "drift_alert", "error"]:
            assert c in got.columns, f"missing column {c!r}"
        assert np.allclose(got["max_psi"].astype(float), want["max_psi"]), "max_psi is the largest PSI in each row"
        assert list(got["drift_alert"].astype(bool)) == list(want["drift_alert"]), \
            "drift_alert should be max_psi > psi_threshold (use the argument)"
        assert list(got["error"].astype(bool)) == list(want["error"]), \
            "error should be True exactly for experiments whose log record has an error message"
        a, b = got["n_alarms"].astype(float).to_numpy(), want["n_alarms"].astype(float).to_numpy()
        assert np.allclose(a, b, equal_nan=True), "n_alarms should come from the log (NaN where scoring failed)"


@exercise("w11.make_dashboard", hint="plt.subplots(2, 1); ax.bar(...) for max_psi with ax.axhline(threshold), and "
          "ax.bar(...) for n_alarms; titles on both; return fig.")
def _t_make_dashboard(fn):
    _fn(fn)
    import matplotlib
    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure

    table = pd.DataFrame({"n_alarms": [3, 0, np.nan, 12], "max_psi": [0.1, 2.0, 0.4, 7.5],
                          "drift_alert": [False, True, True, True], "error": [False, False, True, False]},
                         index=pd.Index(["a/1", "a/2", "b/1", "b/2"], name="experiment"))
    fig = fn(table, 0.25)
    try:
        assert isinstance(fig, Figure), "return the matplotlib Figure"
        bar_axes = [ax for ax in fig.axes if len(ax.patches) >= len(table)]
        assert len(bar_axes) >= 2, "two bar panels, each with one bar per experiment (max PSI, number of alarms)"
        assert any(ax.lines for ax in bar_axes), "draw the PSI threshold as a horizontal line (ax.axhline)"
        assert all(ax.get_title() or ax.get_ylabel() for ax in bar_axes), "label every panel"
    finally:
        plt.close("all")


@exercise("w11.ops_note", hint="Write the three headings exactly; quote the counts from your ops table; 120-400 "
          "words.")
def _t_ops_note(answer):
    if not (isinstance(answer, tuple) and len(answer) == 2):
        raise AssertionError("pass (ops_note, table)")
    note, table = answer
    if note is None or (isinstance(note, str) and not note.strip()):
        raise NotImplementedError
    assert isinstance(note, str), "ops_note should be a string"
    for h in ["## What is monitored", "## What we found", "## Limits"]:
        assert h.lower() in note.lower(), f"the note needs the heading '{h}'"
    words = len(note.split())
    assert 120 <= words <= 400, f"aim for 120-400 words; yours has {words}"
    n_exp, n_drift = len(table), int(table["drift_alert"].sum())
    assert str(n_exp) in note, f"say how many experiments were monitored ({n_exp} in your table)"
    assert str(n_drift) in note, f"say how many experiments raised a drift alert ({n_drift} in your table)"
    assert "YOUR" not in note, "replace the placeholder text"


# ============================================================================ quizzes
register_quiz(
    "w11.41_q1", "b",
    "Temporary credentials from a role expire on their own and are tied to a sign-in, so a leak has a short life. "
    "A long-lived access key works until someone notices and deletes it.",
    {"a": "Roles are not about speed; both kinds of credential sign requests the same way.",
     "c": "Roles can have any permissions; least privilege is a separate decision you still have to make.",
     "d": "Access keys work outside AWS too; that is exactly why a leaked one is dangerous."})
register_quiz(
    "w11.41_q2", "c",
    "Git keeps every version. Deleting the line in a new commit leaves the key in history, forks and clones, so "
    "the only safe fix is to deactivate (rotate) the key, then clean up.",
    {"a": "The old commit still contains the key; anyone with a clone can read it.",
     "b": "Making the repository private later does not reach copies already made, and scanners find keys in "
          "minutes.",
     "d": "Renaming the variable leaves the value in history."})
register_quiz(
    "w11.41_q3", "a",
    "A budget alert costs nothing and is the only part of the list that tells you about money you did not mean "
    "to spend; it has to exist before anything that can bill.",
    {"b": "A custom domain is optional and has nothing to do with cost control.",
     "c": "Autoscaling can raise the bill; it is not a safety net for cost.",
     "d": "A load balancer is itself billed by the hour."})
register_quiz(
    "w11.41_q4", "d",
    "A rollback should be one command to a version that is known to work: the previous image, kept and tagged. "
    "Building a fix under pressure is slower and riskier.",
    {"a": "Debugging in production while users see errors is what a rollback is meant to avoid.",
     "b": "Rebuilding the old version from source may not give the same image (new base image, new packages).",
     "c": "Deleting the service takes everything down, including what still worked."})
register_quiz(
    "w11.41_q5", "c",
    "Cost of a container service grows with size x number of tasks x hours running. Halving the hours halves the "
    "compute cost; the price per hour does not change.",
    {"a": "A bigger instance costs more per hour, not less.",
     "b": "Logs are usually a small part of such a bill; compute hours dominate.",
     "d": "The region changes the unit price a little; running half the time changes the bill by half."})

register_quiz(
    "w11.42_q1", "b",
    "One JSON object per line can be parsed, filtered and aggregated by machines: you can ask 'p95 latency of "
    "model v3 between 14:00 and 15:00' without regular expressions.",
    {"a": "JSON lines are usually larger than plain text, not smaller.",
     "c": "Structured logs still need care: nothing stops you from logging personal data in JSON.",
     "d": "print() works in production too; the problem is that its output is hard to query."})
register_quiz(
    "w11.42_q2", "c",
    "Averages hide the slow tail: one in twenty users waiting 2 s barely moves the mean but shows up in p95.",
    {"a": "Percentiles are not faster to compute than a mean.",
     "b": "The mean of latencies is well defined; it is just misleading for skewed data.",
     "d": "Both use all requests; the difference is what they summarise."})
register_quiz(
    "w11.42_q3", "a",
    "A 422 means the caller sent bad input, and the service handled it correctly. Counting it as a server error "
    "would page you for someone else's bug; track it separately.",
    {"b": "422s are not ignored: a sudden rise is worth a look (a client changed its format). They are just not "
          "server errors.",
     "c": "422 is decided before the model runs; it says nothing about the model's quality.",
     "d": "Status codes do not depend on the HTTP method in that way."})
register_quiz(
    "w11.42_q4", "d",
    "Requiring several bad windows in a row filters out one-off blips, so the alert that does fire is worth "
    "waking up for. The price is a slightly later alert.",
    {"a": "It makes alerts later, not earlier.",
     "b": "It reduces noise but does not change what is measured.",
     "c": "Thresholds still matter; persistence only decides how long they must be crossed."})
register_quiz(
    "w11.42_q5", "b",
    "An alert should mean 'a person must act now'. Alerts that fire daily for nothing teach people to ignore all "
    "alerts, including the real one.",
    {"a": "More alerts do not mean more safety if nobody reads them.",
     "c": "Dashboards are for looking; alerts are for acting. Both are useful, for different jobs.",
     "d": "Lower thresholds give more false alarms, not fewer."})

register_quiz(
    "w11.43_q1", "c",
    "The model barely uses temperature, and faults still look the same, so inputs moved but predictions did not "
    "get worse. Drift is a reason to look, not proof of harm.",
    {"a": "Retraining on recalibrated data is not needed when performance is unchanged; check the data source.",
     "b": "PSI was computed correctly; the shift is real. It just does not matter to this model.",
     "d": "Recall was measured on labels; it did not fall."})
register_quiz(
    "w11.43_q2", "b",
    "Degradation is a change in how inputs relate to the label. Only labels can show it, and here they arrive a "
    "week late, so you see it late.",
    {"a": "Input statistics barely moved in period C; that is the point of the example.",
     "c": "Latency has nothing to do with whether faults are recognised.",
     "d": "Prediction volume stayed the same; only their correctness changed."})
register_quiz(
    "w11.43_q3", "a",
    "PSI on a small window is noisy: with few samples some bins are nearly empty by chance, and PSI grows even "
    "with no drift. Calibrate thresholds for your window size.",
    {"b": "PSI does not depend on the order of rows.",
     "c": "Small windows make PSI larger and noisier, not more accurate.",
     "d": "PSI is defined for any sample size; it is just unreliable on small ones."})
register_quiz(
    "w11.43_q4", "d",
    "A shadow model sees real traffic but its answers are never used, so users are not affected while you "
    "compare it with the current model.",
    {"a": "That is a canary: a small share of users gets the new model's answers.",
     "b": "Shadow deployments run alongside, not instead.",
     "c": "Offline evaluation on a test set is useful but does not see live traffic."})
register_quiz(
    "w11.43_q5", "c",
    "Hashing the request (or user) id gives each one a stable bucket, so the same user does not flip between "
    "models, and you can raise the percentage gradually.",
    {"a": "random.random() would send the same user to different models on different requests.",
     "b": "Time-based routing sends everyone at once, which is what a canary avoids.",
     "d": "Sending by error rate would decide routing on the outcome you are trying to measure."})

register_quiz(
    "w11.44_q1", "b",
    "Each SKAB experiment was recorded at a different time and setup, so comparing them with one reference "
    "flags almost everything. The detector itself avoids this by using each experiment's own burn-in.",
    {"a": "PSI is computed correctly; the reference is the problem.",
     "c": "The anomalies are only part of each file; drift is also large in normal operation.",
     "d": "Bins come from the reference; changing their number will not remove differences this large."})
register_quiz(
    "w11.44_q2", "a",
    "Detector alarms are the product's output; ops alerts are about the system that produces them (errors, "
    "drift, latency). Mixing them would page the on-call engineer for every fault the detector correctly found.",
    {"b": "Both should be logged; they serve different readers.",
     "c": "Alarms can be wrong too, but that is a model-quality question measured with labels.",
     "d": "Latency matters, but it is not the reason to separate the two."})
register_quiz(
    "w11.44_q3", "d",
    "Writing the reason into the log keeps a record of every input that could not be scored, so failures are "
    "counted and visible instead of silently missing.",
    {"a": "Crashing stops the whole run for one bad file.",
     "b": "Skipping silently makes the log look healthier than the system is.",
     "c": "Inventing a score hides the failure and pollutes the metrics."})
register_quiz(
    "w11.44_q4", "c",
    "The labels arrive late (or, in SKAB, only because it is a test bench), so in operation you watch inputs, "
    "errors and alarm rates now and recall later, when labels exist.",
    {"a": "Recall needs labels, which do not exist at prediction time.",
     "b": "Input drift alone cannot prove the detector got worse.",
     "d": "Latency says nothing about whether faults are caught."})
